from fastapi.testclient import TestClient

import pytest

from coupangads.text.template_loader import TemplateLoader
from coupangads.web import api
from coupangads.web.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_prompt_service(tmp_path, monkeypatch):
    """每个测试使用独立的模板目录与覆盖层，避免污染仓库。"""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text(
        "default report prompt", encoding="utf-8"
    )
    overrides_path = tmp_path / "prompt_overrides.json"
    monkeypatch.setattr(
        api, "_load_templates", lambda: TemplateLoader(templates_dir, overrides_path)
    )
    api.get_prompt_service.cache_clear()
    yield
    api.get_prompt_service.cache_clear()


def test_list_prompts() -> None:
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    names = {p["name"] for p in data}
    assert "product_report.txt" in names


def test_get_prompt() -> None:
    response = client.get("/api/prompts/product_report.txt")
    assert response.status_code == 200
    assert "content" in response.json()


def test_update_and_reset_prompt() -> None:
    response = client.put(
        "/api/prompts/product_report.txt",
        json={"content": "custom prompt"},
    )
    assert response.status_code == 200

    response = client.get("/api/prompts/product_report.txt")
    assert response.json()["content"] == "custom prompt"
    assert response.json()["is_overridden"] is True

    response = client.delete("/api/prompts/product_report.txt")
    assert response.status_code == 200

    response = client.get("/api/prompts/product_report.txt")
    assert response.json()["is_overridden"] is False


def test_update_unknown_prompt() -> None:
    response = client.put("/api/prompts/unknown.txt", json={"content": "x"})
    assert response.status_code == 404
