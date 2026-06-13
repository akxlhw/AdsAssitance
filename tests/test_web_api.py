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


def test_upload_path_traversal_blocked(tmp_path, monkeypatch) -> None:
    """确认 .. 与路径分隔符会被安全清理，无法逃离基础目录。"""
    from coupangads.web.api import _safe_name
    from coupangads.core import config
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", tmp_path)

    response = client.post(
        "/api/upload",
        data={"product_name": ".."},
        files={"files": ("../escape.txt", b"x", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["product_id"] == "_"

    # 不应在 tmp_path 之外创建任何文件
    assert not (tmp_path.parent / "escape.txt").exists()
    # 文件应被写入安全化后的子目录
    safe_filename = _safe_name("../escape.txt")
    safe_file = tmp_path / "_" / safe_filename
    assert safe_file.exists()


def test_config_endpoint(tmp_path, monkeypatch) -> None:
    from coupangads.core import config
    monkeypatch.setattr(config, "GEMINI_API_KEY_FILE", tmp_path / "apikey.md")
    monkeypatch.setattr(config, "DOUBAO_API_KEY_FILE", tmp_path / "dbkey.md")
    monkeypatch.setattr(config, "PROVIDER_CONFIG_FILE", tmp_path / "provider.json")

    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["gemini_configured"] is False

    response = client.post("/api/config", json={"gemini_api_key": "test-key"})
    assert response.status_code == 200

    response = client.get("/api/config")
    assert response.json()["gemini_configured"] is True


def test_generate_endpoint() -> None:
    response = client.post("/api/generate/test-prod")
    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_progress_endpoint() -> None:
    from coupangads.web.api import _task_states

    client.post("/api/generate/test-prod")
    # 将任务置为完成，避免 SSE 流无限挂起
    _task_states["test-prod"] = {"status": "completed", "progress": 100}

    response = client.get("/api/progress/test-prod")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    # Read first event
    content = ""
    for chunk in response.iter_text():
        content += chunk
        if "\n\n" in content:
            break
    assert content.startswith("data:")
    import json

    event_data = content.replace("data:", "").strip()
    assert json.loads(event_data)["status"] == "completed"


def test_result_endpoint_not_found() -> None:
    response = client.get("/api/result/nonexistent-product-12345")
    assert response.status_code == 404


def test_serve_result_file(tmp_path, monkeypatch) -> None:
    from coupangads.core import config
    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path)
    output_dir = tmp_path / "test-prod"
    output_dir.mkdir()
    (output_dir / "A_B1.png").write_bytes(b"PNG")

    response = client.get("/api/result/test-prod/A_B1.png")
    assert response.status_code == 200
    assert response.content == b"PNG"


def test_download_endpoint_not_found() -> None:
    response = client.get("/api/download/nonexistent-product-12345")
    assert response.status_code == 404
