"""Web API 单元测试。"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.web import api
from coupangads.web.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_api_state():
    """每个测试前后清空 web api 的内存状态，避免用例间相互污染。"""
    api._task_states.clear()
    api._abort_flags.clear()
    api.get_prompt_service.cache_clear()
    yield
    api._task_states.clear()
    api._abort_flags.clear()
    api.get_prompt_service.cache_clear()


def _wait_for_status(product_id: str, targets: set[str], timeout: float = 3.0) -> dict:
    """轮询 /api/status 直到状态命中目标集合之一。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/status/{product_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") in targets:
                return data
        time.sleep(0.001)
    raise TimeoutError(f"status of {product_id} did not reach {targets}")


def _wait_for_abort_flag_cleared(product_id: str, timeout: float = 3.0) -> None:
    """轮询直到内部 abort 标记被 _run_pipeline 的 finally 清理。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if product_id not in api._abort_flags:
            return
        time.sleep(0.001)
    raise TimeoutError(f"abort flag of {product_id} was not cleared")


def test_upload_endpoint(tmp_path, monkeypatch) -> None:
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
    from coupangads.web.api import _safe_filename
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
    # 文件应被写入安全化后的子目录，且扩展名保留
    safe_filename = _safe_filename("../escape.txt")
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
    """确认 /generate 返回 started，不启动真实后台任务。"""
    with patch("coupangads.web.api._run_pipeline") as mock_run:
        response = client.post("/api/generate/test-prod")
    assert response.status_code == 200
    assert response.json()["status"] == "started"
    all_steps = {
        "product_report",
        "title",
        "keywords",
        "selling_points",
        "instagram",
        "images",
    }
    mock_run.assert_called_once_with("test-prod", all_steps)


def test_generate_endpoint_with_custom_steps() -> None:
    """确认 /generate 支持自定义 steps 参数。"""
    with patch("coupangads.web.api._run_pipeline") as mock_run:
        response = client.post(
            "/api/generate/test-prod",
            json={"steps": ["title", "keywords"]},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "started"
    mock_run.assert_called_once_with("test-prod", {"title", "keywords"})


def test_generate_endpoint_rejects_unknown_steps() -> None:
    """确认 /generate 对未知 step 返回 400。"""
    response = client.post(
        "/api/generate/test-prod",
        json={"steps": ["title", "unknown_step"]},
    )
    assert response.status_code == 400
    assert "unknown_step" in response.json()["detail"]


def test_generate_endpoint_rejects_empty_steps() -> None:
    """确认 /generate 对空 steps 返回 400。"""
    response = client.post(
        "/api/generate/test-prod",
        json={"steps": []},
    )
    assert response.status_code == 400


def test_generate_starts_pipeline(tmp_path, monkeypatch) -> None:
    """确认 /generate 会启动后台线程调用 ProductPipeline。"""
    from coupangads.core import config
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", tmp_path)
    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(config, "GEMINI_API_KEY_FILE", tmp_path / "apikey.md")
    monkeypatch.setattr(config, "PROVIDER_CONFIG_FILE", tmp_path / "provider.json")

    product_dir = tmp_path / "test-prod"
    product_dir.mkdir()
    # 流水线要求至少 3 张产品图
    for i in range(3):
        (product_dir / f"img{i}.jpg").write_bytes(b"fake")
    (tmp_path / "apikey.md").write_text("test-key", encoding="utf-8")
    (tmp_path / "provider.json").write_text(
        json.dumps({"default_provider": "gemini"}, ensure_ascii=False),
        encoding="utf-8",
    )

    started_event = threading.Event()
    mock_pipeline = MagicMock()
    mock_pipeline.run.side_effect = lambda *args, **kwargs: started_event.set()
    with patch("coupangads.web.api.ProductPipeline", return_value=mock_pipeline):
        response = client.post("/api/generate/test-prod")
        assert response.status_code == 200
        assert response.json()["status"] == "started"

        # 等待后台线程执行并调用 mock pipeline
        assert started_event.wait(timeout=2.0), "pipeline run did not start"

    mock_pipeline.run.assert_called_once()


def test_progress_endpoint() -> None:
    from coupangads.web.api import _task_states

    # 直接设置一个已完成任务，避免和 /api/generate 启动的后台线程竞争状态
    _task_states["progress-test"] = {"status": "completed", "progress": 100}

    response = client.get("/api/progress/progress-test")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    # Read first event
    content = ""
    for chunk in response.iter_text():
        content += chunk
        if "\n\n" in content:
            break
    assert content.startswith("data:")

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


class FakePipeline:
    """事件驱动的伪流水线：不 sleep，完全由测试通过 threading.Event 控制推进。"""

    STEP_DEPENDENCIES = ProductPipeline.STEP_DEPENDENCIES

    def __init__(
        self,
        *,
        started_event: threading.Event | None = None,
        step_event: threading.Event | None = None,
        progress_event: threading.Event | None = None,
        total_steps: int = 10,
        **kwargs,
    ) -> None:
        self.started_event = started_event
        self.step_event = step_event
        self.progress_event = progress_event
        self.total_steps = total_steps
        self.abort_callback = kwargs.get("abort_callback")
        self.progress_callback = kwargs.get("progress_callback")

    def run(self, input_dir, output_dir) -> None:
        if self.started_event is not None:
            self.started_event.set()
        for i in range(1, self.total_steps + 1):
            if self.step_event is not None:
                self.step_event.wait()
                self.step_event.clear()
            self.progress_callback(
                {"status": "running", "progress": i * 10, "message": f"step {i}"}
            )
            if self.progress_event is not None:
                self.progress_event.set()
            self.abort_callback()
        self.progress_callback(
            {"status": "completed", "progress": 100, "message": "done"}
        )


def _advance_step(step_event: threading.Event, progress_event: threading.Event) -> None:
    """让伪流水线前进一步，并等待其完成进度回调。"""
    progress_event.clear()
    step_event.set()
    assert progress_event.wait(timeout=2.0), "pipeline step did not complete"


def _fake_pipeline_class(**fake_kwargs):
    """构造可被 api.py 识别的伪流水线类（保留 STEP_DEPENDENCIES）。"""

    class _FakePipelineWrapper:
        STEP_DEPENDENCIES = ProductPipeline.STEP_DEPENDENCIES

        def __init__(self, **kwargs) -> None:
            self._impl = FakePipeline(**fake_kwargs, **kwargs)

        def run(self, input_dir, output_dir) -> None:
            self._impl.run(input_dir, output_dir)

    return _FakePipelineWrapper


def _patch_pipeline_run_dependencies(monkeypatch) -> None:
    """把真实流水线的重依赖替换为轻量 mock，保证测试快速且不调用 API。"""
    monkeypatch.setattr(api, "_build_text_adapter", lambda provider: MagicMock())
    monkeypatch.setattr(api, "_build_image_adapter", lambda provider: MagicMock())
    monkeypatch.setattr(api, "_load_templates", lambda: MagicMock())


def test_abort_basic_request() -> None:
    """POST /api/abort/{product_id} 返回 200 并对 product_id 做安全清理。"""
    product_id = "bad..name"
    safe_id = api._safe_name(product_id)
    response = client.post(f"/api/abort/{product_id}")
    assert response.status_code == 200
    assert response.json() == {
        "status": "abort_requested",
        "product_id": safe_id,
    }
    assert safe_id == "bad_name"


def test_abort_before_generation_starts(tmp_path, monkeypatch) -> None:
    """生成启动后立即中止，流水线应提前结束且进度不到 100。"""
    from coupangads.core import config

    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", tmp_path)
    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path)

    product_id = "abort-early"
    started_event = threading.Event()
    step_event = threading.Event()

    _patch_pipeline_run_dependencies(monkeypatch)
    monkeypatch.setattr(
        api,
        "ProductPipeline",
        _fake_pipeline_class(started_event=started_event, step_event=step_event),
    )

    response = client.post(f"/api/generate/{product_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "started"

    # 等待流水线实际开始后再请求中止，避免在 thread 启动前设置标记被清空。
    assert started_event.wait(timeout=2.0), "pipeline run did not start"

    response = client.post(f"/api/abort/{product_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "abort_requested"

    # 放行一步，让流水线在 check_abort 处抛出 GenerationAborted
    step_event.set()

    state = _wait_for_status(product_id, {"aborted", "completed", "error"})
    assert state["status"] == "aborted"
    assert state["progress"] < 100
    _wait_for_abort_flag_cleared(product_id)


def test_abort_during_generation(tmp_path, monkeypatch) -> None:
    """生成进行到一定进度后中止，状态应过渡为 aborted。"""
    from coupangads.core import config

    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", tmp_path)
    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path)

    product_id = "abort-during"
    step_event = threading.Event()
    progress_event = threading.Event()

    _patch_pipeline_run_dependencies(monkeypatch)
    monkeypatch.setattr(
        api,
        "ProductPipeline",
        _fake_pipeline_class(step_event=step_event, progress_event=progress_event),
    )

    response = client.post(f"/api/generate/{product_id}")
    assert response.status_code == 200

    # 精确推进到第 3 步（progress = 30）
    for _ in range(3):
        _advance_step(step_event, progress_event)

    response = client.post(f"/api/abort/{product_id}")
    assert response.status_code == 200

    # 再放行一步，流水线应检测到 abort 标记并结束
    _advance_step(step_event, progress_event)

    state = _wait_for_status(product_id, {"aborted", "completed", "error"})
    assert state["status"] == "aborted"
    assert state["progress"] < 100
    _wait_for_abort_flag_cleared(product_id)


def test_abort_flag_cleanup(tmp_path, monkeypatch) -> None:
    """中止完成后内部标记应被清理，后续同产品可重新正常生成。"""
    from coupangads.core import config

    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", tmp_path)
    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path)

    product_id = "abort-cleanup"
    started_event = threading.Event()
    step_event = threading.Event()

    _patch_pipeline_run_dependencies(monkeypatch)
    monkeypatch.setattr(
        api,
        "ProductPipeline",
        _fake_pipeline_class(started_event=started_event, step_event=step_event),
    )

    # 第一次生成：启动后立刻中止
    response = client.post(f"/api/generate/{product_id}")
    assert response.status_code == 200
    assert started_event.wait(timeout=2.0), "pipeline run did not start"

    response = client.post(f"/api/abort/{product_id}")
    assert response.status_code == 200

    step_event.set()
    state = _wait_for_status(product_id, {"aborted", "completed", "error"})
    assert state["status"] == "aborted"
    _wait_for_abort_flag_cleared(product_id)

    # 第二次生成：应能正常跑完
    started_event.clear()
    monkeypatch.setattr(
        api,
        "ProductPipeline",
        _fake_pipeline_class(started_event=started_event),
    )
    response = client.post(f"/api/generate/{product_id}")
    assert response.status_code == 200
    assert started_event.wait(timeout=2.0), "second pipeline run did not start"

    state = _wait_for_status(product_id, {"completed", "error"})
    assert state["status"] == "completed"
    assert state["progress"] == 100
    _wait_for_abort_flag_cleared(product_id)


def test_abort_idempotent() -> None:
    """多次调用 abort 返回相同响应，不会报错。"""
    product_id = "idempotent-prod"
    expected = {"status": "abort_requested", "product_id": product_id}
    for _ in range(3):
        response = client.post(f"/api/abort/{product_id}")
        assert response.status_code == 200
        assert response.json() == expected


def _setup_templates(tmp_path: Path) -> Path:
    """在临时目录下创建输入目录与 templates 子目录，供 PromptService 测试使用。"""
    from coupangads.core import config

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text(
        "商品画像模板 {image_count}", encoding="utf-8"
    )
    (templates_dir / "product_title.txt").write_text(
        "标题模板 {product_report}", encoding="utf-8"
    )
    return input_dir


def test_get_prompt_service_singleton(tmp_path, monkeypatch) -> None:
    """get_prompt_service() 返回同一个 PromptService 实例。"""
    from coupangads.core import config

    input_dir = _setup_templates(tmp_path)
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", input_dir)

    svc1 = api.get_prompt_service()
    svc2 = api.get_prompt_service()

    assert isinstance(svc1, api.PromptService)
    assert svc1 is svc2


def test_get_prompt_service_lists_and_reads_templates(tmp_path, monkeypatch) -> None:
    """PromptService 能列出已注册 Prompt 并读取模板内容。"""
    from coupangads.core import config

    input_dir = _setup_templates(tmp_path)
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", input_dir)

    svc = api.get_prompt_service()
    prompts = svc.list_prompts()
    names = {p.name for p in prompts}

    assert "product_report.txt" in names
    assert "product_title.txt" in names
    assert svc.get_prompt("product_report") == "商品画像模板 {image_count}"


def test_get_prompt_service_cache_clear_reinitializes(tmp_path, monkeypatch) -> None:
    """cache_clear() 后再次调用会重新初始化 PromptService。"""
    from coupangads.core import config

    input_dir = _setup_templates(tmp_path)
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", input_dir)

    svc1 = api.get_prompt_service()
    api.get_prompt_service.cache_clear()

    # 修改模板内容，验证重新初始化后读取到新内容
    templates_dir = tmp_path / "templates"
    (templates_dir / "product_report.txt").write_text(
        "更新后的商品画像模板", encoding="utf-8"
    )
    svc2 = api.get_prompt_service()

    assert svc1 is not svc2
    assert svc2.get_prompt("product_report") == "更新后的商品画像模板"


def test_get_prompt_service_warns_missing_templates(
    tmp_path, monkeypatch, caplog
) -> None:
    """模板目录不存在时，get_prompt_service() 应记录警告。"""
    missing_dir = tmp_path / "missing_templates"
    monkeypatch.setattr(
        api, "_load_templates", lambda: api.TemplateLoader(missing_dir)
    )

    with caplog.at_level("WARNING", logger="api.prompt_service"):
        svc = api.get_prompt_service()

    assert isinstance(svc, api.PromptService)
    assert "模板目录不存在" in caplog.text
