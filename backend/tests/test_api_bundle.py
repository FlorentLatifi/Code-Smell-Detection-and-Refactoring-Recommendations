"""Tests for serving the built interface and the API from one process.

The interface calls the API under ``/api``, the same prefix Vite's proxy strips
in development. If the two ever disagreed, every request from the built page
would 404 while every development session kept working, so the prefix is
checked here against the real application.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from javasmell.api.bundle import InterfaceMissing, create_bundle
from javasmell.api.settings import Settings


@pytest.fixture
def ui(tmp_path):
    """Një ndërtim i vogël ndërfaqeje: faqja dhe një skedar i saj."""
    directory = tmp_path / "dist"
    (directory / "assets").mkdir(parents=True)
    (directory / "index.html").write_text("<!doctype html><title>JavaSmell</title>", "utf-8")
    (directory / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    return directory


@pytest.fixture
def bundle(tmp_path, ui):
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    (root / "src" / "A.java").write_text("class A { void m() {} }", encoding="utf-8")
    settings = Settings(root=root, projects_dir=tmp_path / "projects")
    return TestClient(create_bundle(settings, ui_dir=ui), base_url="http://localhost")


def test_the_page_is_served_at_the_root(bundle):
    response = bundle.get("/")

    assert response.status_code == 200
    assert "<title>JavaSmell</title>" in response.text


def test_the_assets_of_the_page_are_served(bundle):
    assert bundle.get("/assets/app.js").text == "console.log('ok')"


def test_the_api_answers_under_the_prefix_the_interface_uses(bundle):
    assert bundle.get("/api/health").json()["status"] == "ok"

    response = bundle.post("/api/analyze", json={"path": "src"})

    assert response.status_code == 200
    assert response.json()["summary"]["files"] == 1


def test_the_page_itself_cannot_be_framed_by_another_site(bundle):
    """Faqja mban butonin që shkruan në disk; ajo, më shumë se API-ja, duhet mbrojtur."""
    headers = bundle.get("/").headers

    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


def test_the_page_is_not_served_under_a_foreign_host_name(bundle):
    assert bundle.get("/", headers={"Host": "evil.example"}).status_code == 403


def test_the_api_keeps_its_own_guard_behind_the_prefix(bundle):
    response = bundle.post("/api/browse", json={}, headers={"Origin": "https://evil.example"})

    assert response.status_code == 403


def test_a_request_from_the_page_itself_is_accepted(bundle):
    """E njëjta origjinë si faqja: «localhost:8000», jo më portin e Vite-it."""
    response = bundle.post("/api/browse", json={}, headers={"Origin": "http://localhost:8000"})

    assert response.status_code == 200


def test_it_refuses_to_start_without_a_built_interface(tmp_path):
    with pytest.raises(InterfaceMissing, match="npm run build"):
        create_bundle(Settings(root=tmp_path), ui_dir=tmp_path / "missing")
