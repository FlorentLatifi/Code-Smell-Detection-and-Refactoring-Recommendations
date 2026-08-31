"""Tests for the HTTP surface.

Two things are checked here that the unit tests cannot: that a rejected path is
still rejected when it arrives over HTTP rather than as a function argument, and
that a failure comes back as a code and a message rather than as a stack trace.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from javasmell.api.app import create_app
from javasmell.api.settings import Settings

# A Long Method needs more than thirty effective lines, and a Data Class needs a
# wide public surface. Both are present so one fixture exercises an automated
# smell and an advisory one.
SMELLY = """package com.acme;

public class Ledger {
    public int total;
    public String name;
    public String note;
    public String owner;
    public String tag;
    public String extra;

    void process(int[] xs) {
        int sum = 0;
        for (int i = 0; i < xs.length; i++) {
            int amount = xs[i];
            if (amount > 0) {
                sum += amount;
                System.out.println(amount);
                System.out.println(sum);
                System.out.println(i);
            } else {
                System.out.println("skip");
                System.out.println(amount);
                System.out.println(i);
            }
            System.out.println("step");
            System.out.println(sum);
            System.out.println(amount);
            System.out.println(xs.length);
            System.out.println(i);
            System.out.println("end of iteration");
            System.out.println(total);
            System.out.println(name);
            System.out.println(note);
            System.out.println(owner);
            System.out.println(tag);
            System.out.println(extra);
            System.out.println("more");
            System.out.println(sum + i);
            System.out.println(amount + i);
        }
        System.out.println(sum);
        System.out.println(total);
        System.out.println(name);
        System.out.println("done");
    }
}
"""


def line_of(body, smell_type):
    """Where the analysis says a smell sits, rather than a number typed by hand."""
    match = next(s for s in body["smells"] if s["smell_type"] == smell_type)
    return match["start_line"]


@pytest.fixture
def client(tmp_path):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    (root / "src" / "Ledger.java").write_text(SMELLY, encoding="utf-8")
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "keys.txt").write_text("s3cret", encoding="utf-8")
    return TestClient(create_app(Settings(root=root, max_files=50, max_bytes=1_000_000)))


def test_health_reports_ready():
    app = create_app(Settings(root=__import__("pathlib").Path(".").resolve()))
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ----------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------


def test_analyze_returns_a_summary_and_the_smells(client):
    response = client.post("/analyze", json={"path": "src"})
    assert response.status_code == 200

    body = response.json()
    assert body["summary"]["classes"] == 1
    assert body["summary"]["smells"] == len(body["smells"])
    assert body["summary"]["smells"] > 0


def test_each_smell_says_whether_the_engine_can_rewrite_it(client):
    smells = client.post("/analyze", json={"path": "src"}).json()["smells"]
    kinds = {s["smell_type"]: s["automated"] for s in smells}

    assert kinds.get("LongMethod") is True
    if "DataClass" in kinds:
        assert kinds["DataClass"] is False  # advisory only: needs every reference


def test_a_smell_carries_the_conditions_that_fired(client):
    """The interface has to explain why, not just that."""
    smells = client.post("/analyze", json={"path": "src"}).json()["smells"]
    assert all(s["rationale"] for s in smells)
    assert all(s["severity"] in {"minor", "major", "critical"} for s in smells)

    # Every clause travels as data too, so the interface can align the measured
    # value against the threshold instead of parsing a sentence.
    #
    # `process` spans 35 lines from its signature to its closing brace, of which
    # three hold nothing but a brace, and none are blank: 35 - 3 = 32 effective
    # lines against a published threshold of 30.
    long_method = next(s for s in smells if s["smell_type"] == "LongMethod")
    assert long_method["conditions"] == [
        {"metric": "MLOC", "operator": ">", "threshold": 30, "value": 32.0}
    ]


def test_metrics_are_returned_per_class_and_method(client):
    body = client.post("/metrics", json={"path": "src"}).json()
    ledger = body["classes"][0]

    assert ledger["name"] == "Ledger"
    assert "WMC" in ledger["metrics"]
    assert any(m["name"] == "process" for m in ledger["methods"])
    assert "MLOC" in next(m for m in ledger["methods"] if m["name"] == "process")["metrics"]


# ----------------------------------------------------------------------
# The path is user input
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["../secret/keys.txt", "src/../../secret", "/etc/passwd", "C:\\Windows\\System32"],
    ids=["traversal", "traversal-through", "absolute-posix", "absolute-windows"],
)
def test_a_path_outside_the_root_is_refused_over_http(client, path):
    response = client.post("/analyze", json={"path": path})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "path_rejected"


def test_an_error_carries_a_code_and_a_message_only(client):
    body = response_body = client.post("/analyze", json={"path": "../secret"}).json()

    assert set(body) == {"error"}
    assert set(response_body["error"]) == {"code", "message"}
    assert "Traceback" not in body["error"]["message"]
    assert "secret" not in body["error"]["message"]


def test_an_empty_path_is_refused_by_validation(client):
    assert client.post("/analyze", json={"path": ""}).status_code == 422


def test_a_path_with_no_java_is_refused(client, tmp_path):
    (tmp_path / "workspace" / "empty").mkdir()
    response = client.post("/analyze", json={"path": "empty"})

    assert response.status_code == 400
    assert "no Java files" in response.json()["error"]["message"]


def test_too_many_files_is_refused(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    for index in range(5):
        (root / f"F{index}.java").write_text("class F {}", encoding="utf-8")
    client = TestClient(create_app(Settings(root=root, max_files=2, max_bytes=1_000_000)))

    response = client.post("/analyze", json={"path": "."})
    assert response.status_code == 400
    assert "more than 2" in response.json()["error"]["message"]


# ----------------------------------------------------------------------
# Refactoring preview
# ----------------------------------------------------------------------


def test_preview_returns_the_rewrite_without_touching_the_file(client, tmp_path):
    source = tmp_path / "workspace" / "src" / "Ledger.java"
    before = source.read_text(encoding="utf-8")

    found = client.post("/analyze", json={"path": "src"}).json()
    response = client.post(
        "/refactor/preview",
        json={
            "path": "src/Ledger.java",
            "class_name": "Ledger",
            "method": "process",
            "start_line": line_of(found, "LongMethod"),
            "smell_type": "LongMethod",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["applied"] is True
    assert "extracted" in body["after"]
    assert body["before"] != body["after"]
    assert source.read_text(encoding="utf-8") == before, "preview must not write"


def test_preview_declines_a_smell_the_engine_only_advises(client):
    response = client.post(
        "/refactor/preview",
        json={
            "path": "src/Ledger.java",
            "class_name": "Ledger",
            "start_line": 3,
            "smell_type": "DataClass",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "advisory_only"
    assert "reference" in response.json()["error"]["message"]


def test_preview_reports_a_refusal_as_a_result_not_an_error(client, tmp_path):
    """Declining is a correct outcome, so it is a 200 with a reason."""
    source = tmp_path / "workspace" / "src" / "Short.java"
    source.write_text(
        "public class Short {\n    void m() {\n        System.out.println(1);\n    }\n}\n",
        encoding="utf-8",
    )

    response = client.post(
        "/refactor/preview",
        json={
            "path": "src/Short.java",
            "class_name": "Short",
            "method": "m",
            "start_line": 2,
            "smell_type": "LongMethod",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["applied"] is False
    assert body["refusal"] == "shape_not_matched"
    assert body["detail"]


def test_preview_of_a_missing_entity_is_a_404(client):
    response = client.post(
        "/refactor/preview",
        json={
            "path": "src/Ledger.java",
            "class_name": "Ledger",
            "method": "nope",
            "start_line": 12,
            "smell_type": "LongMethod",
        },
    )
    assert response.status_code == 404
