"""Web UI 端到端冒烟测试。"""

import json
import time
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from coupangads.web.app import app

client = TestClient(app)


def test_web_upload_generate_progress_flow(tmp_path, monkeypatch) -> None:
    """模拟上传 → 触发 → 进度流完整链路，无需真实 API Key。"""
    from coupangads.core import config
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path / "result")
    monkeypatch.setattr(config, "GEMINI_API_KEY_FILE", tmp_path / "apikey.md")
    monkeypatch.setattr(config, "PROVIDER_CONFIG_FILE", tmp_path / "provider.json")

    (tmp_path / "apikey.md").write_text("test-key", encoding="utf-8")
    (tmp_path / "provider.json").write_text(
        json.dumps({"default_provider": "gemini"}, ensure_ascii=False),
        encoding="utf-8",
    )

    # 上传（流水线要求至少 3 张产品图）
    upload = client.post(
        "/api/upload",
        data={"product_name": "web-test"},
        files=[
            ("files", ("img1.jpg", b"fake", "image/jpeg")),
            ("files", ("img2.jpg", b"fake", "image/jpeg")),
            ("files", ("img3.jpg", b"fake", "image/jpeg")),
        ],
    )
    assert upload.status_code == 200

    # 触发（mock pipeline，并通过回调模拟进度）
    def _fake_run(input_dir, output_dir):
        from coupangads.web.api import _task_states
        _task_states["web-test"] = {
            "step": "images",
            "status": "completed",
            "progress": 100,
            "message": "模拟完成",
        }

    mock_pipeline = MagicMock()
    mock_pipeline.run.side_effect = _fake_run
    with patch("coupangads.web.api.ProductPipeline", return_value=mock_pipeline):
        gen = client.post("/api/generate/web-test")
        assert gen.status_code == 200
        assert gen.json()["status"] == "started"

        # 等待后台线程执行 mock
        for _ in range(50):
            if mock_pipeline.run.called:
                break
            time.sleep(0.01)

    mock_pipeline.run.assert_called_once()

    # 进度 SSE 应返回完成状态
    response = client.get("/api/progress/web-test")
    assert response.status_code == 200
    content = ""
    for chunk in response.iter_text():
        content += chunk
        if "\n\n" in content:
            break
    event_data = content.replace("data:", "").strip()
    assert json.loads(event_data)["progress"] == 100
