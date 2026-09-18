"""Tests for the local-only guard in front of every route.

Each test below is one of the requests that were measured against the server
before the guard existed (VD-127): a rebound ``Host`` that read the folder
listing and the source code, a foreign ``Origin`` sending a POST, and a page
framing the interface. They are written as an attacker would send them.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from javasmell.api.app import create_app
from javasmell.api.guard import host_name, origin_is_local
from javasmell.api.settings import Settings, _hosts


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    (root / "src" / "A.java").write_text("class A { void m() {} }", encoding="utf-8")
    settings = Settings(root=root, projects_dir=tmp_path / "projects")
    return TestClient(create_app(settings), base_url="http://localhost")


# ----------------------------------------------------------------------
# DNS rebinding: emri i huaj te koka Host
# ----------------------------------------------------------------------


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8000", "192.168.1.20:8000"])
def test_a_request_under_a_foreign_host_name_is_refused(server, host):
    """E njëjta kërkesë që para mbrojtjes ktheu listën e dosjeve me 200."""
    response = server.post("/browse", json={}, headers={"Host": host})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "host_not_allowed"


def test_the_source_code_is_not_readable_under_a_foreign_host(server):
    response = server.post(
        "/source",
        json={"path": "src/A.java", "start_line": 1, "end_line": 1},
        headers={"Host": "evil.example"},
    )

    assert response.status_code == 403
    assert "lines" not in response.json()


@pytest.mark.parametrize("host", ["localhost", "localhost:8000", "127.0.0.1:8000", "[::1]:8000"])
def test_every_local_name_is_accepted(server, host):
    assert server.get("/health", headers={"Host": host}).status_code == 200


# ----------------------------------------------------------------------
# Kërkesat nga faqe të tjera: koka Origin
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "origin", ["https://evil.example", "http://localhost.evil.example", "null", "file://"]
)
def test_a_post_from_another_site_is_refused_before_any_route_runs(server, origin):
    """Refuzimi është 403 i shprehur, jo 422 që varej nga parser-i i JSON-it."""
    response = server.post(
        "/refactor/apply",
        content=json.dumps({"path": "src", "confirm": True}),
        headers={"Content-Type": "application/json", "Origin": origin},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"


@pytest.mark.parametrize(
    "origin", ["http://localhost:5173", "http://127.0.0.1:4173", "http://[::1]:5173"]
)
def test_the_interface_served_from_this_machine_is_accepted(server, origin):
    response = server.post("/browse", json={}, headers={"Origin": origin})

    assert response.status_code == 200


def test_a_request_without_an_origin_is_a_local_program_and_passes(server):
    """curl, rreshti i komandës dhe skriptet nuk dërgojnë Origin."""
    assert server.post("/browse", json={}).status_code == 200


# ----------------------------------------------------------------------
# Kokat e sigurisë
# ----------------------------------------------------------------------


def test_every_response_forbids_being_framed_by_another_site(server):
    """Pa to, një faqe e huaj mund ta mbështjellë ndërfaqen dhe të mashtrojë klikimin."""
    headers = server.get("/health").headers

    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["x-content-type-options"] == "nosniff"


def test_a_refusal_carries_the_same_headers(server):
    headers = server.get("/health", headers={"Host": "evil.example"}).headers

    assert headers["x-frame-options"] == "DENY"


def test_source_code_is_not_kept_in_the_browser_cache(server):
    response = server.post("/source", json={"path": "src/A.java", "start_line": 1, "end_line": 1})

    assert response.headers["cache-control"] == "no-store"


# ----------------------------------------------------------------------
# Privilegji më i vogël: vetëm kod Java
# ----------------------------------------------------------------------


def test_a_text_file_inside_the_root_is_not_readable_as_source(server, tmp_path):
    """Me rrënjën te Desktopi, `/source` lexonte çdo shënim tekst që ishte aty."""
    (tmp_path / "workspace" / ".env").write_text("TOKEN=s3cret", encoding="utf-8")

    response = server.post("/source", json={"path": ".env", "start_line": 1, "end_line": 1})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "not_java"
    assert "s3cret" not in response.text


def test_a_preview_of_a_file_that_is_not_java_is_refused(server, tmp_path):
    (tmp_path / "workspace" / "notes.txt").write_text("hello", encoding="utf-8")

    response = server.post(
        "/refactor/preview",
        json={"path": "notes.txt", "class_name": "A", "start_line": 1, "smell_type": "LongMethod"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "not_java"


# ----------------------------------------------------------------------
# Leximi i kokave
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("localhost:5173", "localhost"),
        ("LOCALHOST", "localhost"),
        ("[::1]:8000", "::1"),
        ("127.0.0.1", "127.0.0.1"),
        ("[broken", ""),
        ("", ""),
    ],
)
def test_the_host_name_is_read_without_port_or_brackets(header, expected):
    assert host_name(header) == expected


def test_an_origin_on_another_scheme_is_not_local():
    assert origin_is_local("ftp://localhost", {"localhost"}) is False


def test_the_local_names_survive_any_configuration():
    """Një konfigurim që do t'i hiqte do ta bënte ndërfaqen e vetë shërbimit të paarritshme."""
    assert {"localhost", "127.0.0.1", "::1"} <= set(_hosts(""))
    assert "laptop.lan" in _hosts("laptop.lan, ")
