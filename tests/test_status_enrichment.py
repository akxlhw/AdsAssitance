"""测试生成任务状态文件中的 completed_steps / created_at / completed_at 字段。"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coupangads.web import api


@pytest.fixture
def tmp_output(tmp_path, monkeypatch):
    """使用临时 output 目录并清理 API 状态。"""
    from coupangads.core import config

    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path)
    api._task_states.clear()
    api._abort_flags.clear()
    yield tmp_path
    api._task_states.clear()
    api._abort_flags.clear()


def _build_mock_pipeline_class():
    """构造一个 Mock Pipeline，模拟完成 product_report 与 title 两个步骤后整体完成。"""

    class MockPipeline:
        STEP_DEPENDENCIES = {
            "product_report": (),
            "title": ("product_report",),
            "keywords": ("product_report", "title"),
            "selling_points": ("product_report", "title", "keywords"),
            "instagram": ("product_report", "title", "keywords", "selling_points"),
            "images": ("product_report", "title", "keywords", "selling_points"),
        }

        def __init__(self, **kwargs) -> None:
            self.progress_callback = kwargs.get("progress_callback")
            self.enabled_steps = kwargs.get("enabled_steps")

        def run(self, input_dir: Path, output_dir: Path) -> None:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "product_report.md").write_text("report", encoding="utf-8")
            (output_dir / "product_title.md").write_text("title", encoding="utf-8")

            if self.progress_callback:
                self.progress_callback(
                    {"step": "product_report", "status": "completed", "progress": 15, "message": "画像完成"}
                )
                self.progress_callback(
                    {"step": "title", "status": "completed", "progress": 30, "message": "标题完成"}
                )
                # 真实流水线最后会推送一次整体完成的进度
                self.progress_callback(
                    {"step": "title", "status": "completed", "progress": 100, "message": "全部完成"}
                )

    return MockPipeline


def test_status_file_contains_completed_steps_and_timestamps(tmp_output, monkeypatch) -> None:
    from coupangads.orchestration.pipeline import ProductPipeline

    mock_pipeline_class = _build_mock_pipeline_class()
    monkeypatch.setattr(ProductPipeline, "STEP_DEPENDENCIES", mock_pipeline_class.STEP_DEPENDENCIES)

    input_dir = tmp_output / "input" / "test-prod"
    input_dir.mkdir(parents=True)
    for i in range(3):
        (input_dir / f"img{i}.jpg").write_bytes(b"fake")

    with patch.object(api, "ProductPipeline", mock_pipeline_class):
        with patch.dict(api.os.environ, {"COUPANGADS_MOCK": "1"}, clear=False):
            api._run_pipeline("test-prod")

    status_path = tmp_output / "test-prod" / ".status.json"
    assert status_path.exists()
    data = json.loads(status_path.read_text(encoding="utf-8"))

    assert data["status"] == "completed"
    assert "created_at" in data
    assert "completed_at" in data
    assert "completed_steps" in data
    assert "product_report" in data["completed_steps"]
    assert "title" in data["completed_steps"]
