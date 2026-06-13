"""Web UI 端到端冒烟测试。"""

from fastapi.testclient import TestClient

from coupangads.web.app import app

client = TestClient(app)


def test_web_upload_and_result_api(tmp_path, monkeypatch) -> None:
    from coupangads.core import config
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path / "result")

    # 上传
    upload = client.post(
        "/api/upload",
        data={"product_name": "web-test"},
        files={"files": ("img.jpg", b"fake", "image/jpeg")},
    )
    assert upload.status_code == 200

    # 触发
    gen = client.post("/api/generate/web-test")
    assert gen.status_code == 200

    # 结果（生成未真实运行，会 404；此测试验证接口连通性）
    result = client.get("/api/result/web-test")
    assert result.status_code in (200, 404)
