"""Web API 单元测试。"""

from fastapi.testclient import TestClient

from coupangads.web.app import app

client = TestClient(app)


def test_upload_endpoint(tmp_path, monkeypatch) -> None:
    from pathlib import Path
    from coupangads.core import config
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", tmp_path)

    response = client.post(
        "/api/upload",
        data={"product_name": "test-prod"},
        files={"files": ("img.jpg", b"fake", "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["file_count"] == 1


def test_config_endpoint(tmp_path, monkeypatch) -> None:
    from coupangads.core import config
    monkeypatch.setattr(config, "GEMINI_API_KEY_FILE", tmp_path / "apikey.md")
    monkeypatch.setattr(config, "DOUBAO_API_KEY_FILE", tmp_path / "dbkey.md")

    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["gemini_configured"] is False

    response = client.post("/api/config", json={"gemini_api_key": "test-key"})
    assert response.status_code == 200

    response = client.get("/api/config")
    assert response.json()["gemini_configured"] is True
