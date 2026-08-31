"""Tests for Approach B over HTTP.

`data/models/` is not committed -- the repository carries the recipe rather than
the result -- so nothing here reads a trained artefact. The models these tests
serve are built in the test's own directory from a rule that is known, which also
means the verdicts they produce can be stated by hand.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.tree import DecisionTreeClassifier

from javasmell.api.app import MODEL_NEEDS_PROJECT, create_app
from javasmell.api.settings import Settings
from javasmell.ml.features import feature_names
from javasmell.ml.serving import SERVED, slug
from javasmell.ml.training import library_versions

# One measurement is enough to exercise the whole path, and keeping it to one
# means the median and therefore every verdict can be worked out on paper.
FEATURE = "c_WMC"
BOUNDARY = 10.0

# Twelve trivial methods. Each contributes one unit of cyclomatic complexity, so
# WMC is 12 -- above the boundary of 10 the fixture models were fitted on, which
# makes every verdict here one that can be stated in advance.
WIDE = """package com.acme;

public class Wide {
    public void m0() { System.out.println(0); }
    public void m1() { System.out.println(1); }
    public void m2() { System.out.println(2); }
    public void m3() { System.out.println(3); }
    public void m4() { System.out.println(4); }
    public void m5() { System.out.println(5); }
    public void m6() { System.out.println(6); }
    public void m7() { System.out.println(7); }
    public void m8() { System.out.println(8); }
    public void m9() { System.out.println(9); }
    public void m10() { System.out.println(10); }
    public void m11() { System.out.println(11); }
}
"""


def write_dataset(path: Path) -> None:
    """Twenty rows per smell where WMC runs 0..19 and the label is WMC > 10.

    The median of 0..19 is 9.5, which sits below the boundary: a class measured
    above 10 is flagged, and setting its WMC to the median would un-flag it.

    Every column the dataset defines is written, not only the one the fixture
    models read. `features.load` drops a row that is missing any of them, and a
    narrower file would be dropped entirely -- leaving no rows to take a median
    over and testing nothing.
    """
    columns = ["sample_id", "repository", "smell", "smelly_mean"]
    everything = sorted({name for smell in SERVED for name in feature_names(smell)})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns + everything)
        writer.writeheader()
        for smell in SERVED:
            for value in range(20):
                row = dict.fromkeys(everything, "1.0")
                row[FEATURE] = repr(float(value))
                row.update(
                    sample_id=f"{slug(smell)}-{value}",
                    repository=f"repo-{value % 4}",
                    smell=smell,
                    smelly_mean="1" if value > BOUNDARY else "0",
                )
                writer.writerow(row)


def write_models(models: Path, libraries: dict[str, str] | None = None) -> None:
    """A fitted tree per smell, plus the manifest that says how to read it."""
    models.mkdir(parents=True, exist_ok=True)
    x = np.array([[float(value)] for value in range(20)], dtype=np.float64)
    estimator = DecisionTreeClassifier(random_state=0).fit(x, x[:, 0] > BOUNDARY)
    for smell in SERVED:
        joblib.dump(estimator, models / f"{slug(smell)}.joblib")
        (models / f"{slug(smell)}.json").write_text(
            json.dumps(
                {
                    "features": [FEATURE],
                    "label": "smelly_mean",
                    "libraries": libraries or library_versions(),
                    "smell": smell,
                    "trained_on": 20,
                }
            ),
            encoding="utf-8",
        )


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    (root / "src" / "Wide.java").write_text(WIDE, encoding="utf-8")
    return root


@pytest.fixture
def trained(tmp_path, workspace):
    """A server whose models exist and can be applied."""
    dataset = tmp_path / "dataset.csv"
    write_dataset(dataset)
    write_models(tmp_path / "models")
    return TestClient(
        create_app(
            Settings(
                root=workspace,
                max_files=50,
                max_bytes=1_000_000,
                models_dir=tmp_path / "models",
                dataset_csv=dataset,
            )
        )
    )


@pytest.fixture
def untrained(tmp_path, workspace):
    """A server on a checkout where nobody has run the training script."""
    return TestClient(
        create_app(
            Settings(
                root=workspace,
                max_files=50,
                max_bytes=1_000_000,
                models_dir=tmp_path / "absent",
                dataset_csv=tmp_path / "absent.csv",
            )
        )
    )


def test_the_model_is_not_consulted_unless_asked(trained):
    """Approach A must cost what it always cost."""
    body = trained.post("/analyze", json={"path": "src"}).json()
    assert "model" not in body


def test_asking_for_the_model_adds_it_beside_the_rules(trained):
    body = trained.post("/analyze", json={"path": "src", "include_model": True}).json()

    # The rules are unaffected by the second opinion being requested.
    assert body["summary"]["classes"] == 1
    assert body["model"]["available"] is True
    assert {report["smell"] for report in body["model"]["smells"]} == set(SERVED)


def test_a_class_level_model_judges_the_class(trained):
    body = trained.post("/analyze", json={"path": "src", "include_model": True}).json()
    blob = next(r for r in body["model"]["smells"] if r["smell"] == "blob")

    # One class in the workspace, so one entity considered and none skipped.
    assert (blob["considered"], blob["incomplete"]) == (1, 0)
    assert [p["method"] for p in blob["predictions"]] == [None]


def test_a_method_level_model_judges_every_method(trained):
    body = trained.post("/analyze", json={"path": "src", "include_model": True}).json()
    long_method = next(r for r in body["model"]["smells"] if r["smell"] == "long method")

    # Wide declares twelve methods and no constructor.
    assert (long_method["considered"], long_method["incomplete"]) == (12, 0)


def test_a_flagged_entity_carries_the_measurement_that_explains_it(trained):
    """The asymmetry this feature exists to remove: B has to say why too."""
    body = trained.post("/analyze", json={"path": "src", "include_model": True}).json()
    blob = next(r for r in body["model"]["smells"] if r["smell"] == "blob")
    found = blob["predictions"][0]

    # WMC = 12 is above the boundary, so the class is flagged, and the single
    # measurement the model was given is necessarily the one that carries it:
    # set to the median of 0..19 it falls to 9.5, below the boundary of 10.
    assert found["class_name"] == "Wide"
    assert found["probability"] >= 0.5
    assert found["contributions"][0] == {
        "feature": FEATURE,
        "value": 12.0,
        "typical": 9.5,
        "drop": 1.0,
        "decisive": True,
    }


def test_an_untrained_checkout_says_so_without_losing_the_rules(untrained):
    body = untrained.post("/analyze", json={"path": "src", "include_model": True}).json()

    # The rules ran and found what they found; only the second opinion is missing.
    assert body["summary"]["classes"] == 1
    assert body["model"]["available"] is False
    assert "train_models" in body["model"]["reason"]


def test_a_single_file_gets_no_model_verdict(trained):
    """Measured without the project, the columns the model reads are not the
    columns it was fitted on, so it is not asked."""
    body = trained.post("/analyze", json={"path": "src/Wide.java", "include_model": True}).json()

    assert body["model"] == {"available": False, "reason": MODEL_NEEDS_PROJECT}


def test_a_model_fitted_by_another_library_is_not_served(tmp_path, workspace):
    dataset = tmp_path / "dataset.csv"
    write_dataset(dataset)
    write_models(tmp_path / "models", libraries={"scikit-learn": "0.0.0-not-installed"})
    client = TestClient(
        create_app(
            Settings(
                root=workspace,
                max_files=50,
                max_bytes=1_000_000,
                models_dir=tmp_path / "models",
                dataset_csv=dataset,
            )
        )
    )

    body = client.post("/analyze", json={"path": "src", "include_model": True}).json()
    assert body["model"]["available"] is False
    assert "scikit-learn" in body["model"]["reason"]
