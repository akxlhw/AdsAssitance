"""Web API 路由。"""

import asyncio
import json
import os
import re
import threading
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from coupangads.adapters.doubao import DoubaoClientAdapter
from coupangads.adapters.gemini import GeminiClientAdapter
from coupangads.adapters.mock import MockImageAdapter, MockTextAdapter
from coupangads.adapters.openai_compatible import OpenAICompatibleTextAdapter
from coupangads.core import config
from coupangads.core.logging import get_logger
from coupangads.infra.api_keys import read_api_key
from coupangads.infra.io import write_text_file
from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.text.prompt_service import PromptService
from coupangads.text.template_loader import TemplateLoader

router = APIRouter(prefix="/api")

_prompt_service: PromptService | None = None


def get_prompt_service() -> PromptService:
    global _prompt_service
    if _prompt_service is None:
        templates = _load_templates()
        _prompt_service = PromptService(templates)
    return _prompt_service


class GenerationAborted(Exception):
    """用户主动中止生成。"""


# 内存中的任务状态（MVP 简版，v2.0 迁移到数据库）
_task_states: dict[str, dict] = {}

# 内存中的中止标记（MVP 简版，按 product_id 存储）
_abort_flags: dict[str, bool] = {}


def _set_abort_flag(product_id: str) -> None:
    _abort_flags[product_id] = True


def _check_abort_flag(product_id: str) -> bool:
    return _abort_flags.get(product_id, False)


def _clear_abort_flag(product_id: str) -> None:
    _abort_flags.pop(product_id, None)


def _safe_name(name: str) -> str:
    """清理名称：只允许字母、数字、下划线、连字符。"""
    # 将连续的点替换为单个下划线，防止 ".." 路径遍历
    cleaned = re.sub(r"\.+", "_", name)
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", cleaned)


def _safe_filename(filename: str) -> str:
    """保留扩展名，但阻止路径遍历并清理危险字符。"""
    base = Path(filename).name
    if not base or ".." in base or "/" in base or "\\" in base:
        raise HTTPException(status_code=400, detail="Invalid filename")
    # 将空格替换为下划线，保留扩展名点号
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)


def _resolve_under(base: Path, *parts: str) -> Path:
    """解析路径，并确保结果在 base 目录下。"""
    target = (base / _safe_name("/".join(parts))).resolve()
    base_resolved = base.resolve()
    try:
        target.relative_to(base_resolved)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc
    return target


def _load_provider_config() -> dict:
    """Load provider configuration with backward compatibility."""
    defaults = {
        "text_provider": "gemini",
        "image_provider": "gemini",
        "deepseek_model": config.DEEPSEEK_TEXT_MODEL,
    }
    if config.PROVIDER_CONFIG_FILE.exists():
        try:
            data = json.loads(
                config.PROVIDER_CONFIG_FILE.read_text(encoding="utf-8")
            )
            # Legacy single-provider setting maps to both text and image
            if "default_provider" in data and "text_provider" not in data:
                data["text_provider"] = data["image_provider"] = data.pop(
                    "default_provider"
                )
            defaults.update(data)
        except Exception:
            pass
    return defaults


def _build_text_adapter(provider: str) -> object:
    """Build the text adapter for the configured provider."""
    if os.environ.get("COUPANGADS_MOCK") in ("1", "true", "yes"):
        return MockTextAdapter()
    if provider == "mock":
        return MockTextAdapter()
    if provider == "doubao":
        api_key = read_api_key(config.DOUBAO_API_KEY_FILE, env_var="DOUBAO_API_KEY")
        return DoubaoClientAdapter(api_key)
    if provider == "deepseek":
        cfg = _load_provider_config()
        api_key = read_api_key(
            config.DEEPSEEK_API_KEY_FILE, env_var="DEEPSEEK_API_KEY"
        )
        model = cfg.get("deepseek_model") or config.DEEPSEEK_TEXT_MODEL
        return OpenAICompatibleTextAdapter(
            api_key=api_key,
            base_url=config.DEEPSEEK_BASE_URL,
            model=model,
        )
    api_key = read_api_key(config.GEMINI_API_KEY_FILE, env_var="GEMINI_API_KEY")
    return GeminiClientAdapter(api_key)


def _build_image_adapter(provider: str) -> object:
    """Build the image adapter for the configured provider."""
    if os.environ.get("COUPANGADS_MOCK") in ("1", "true", "yes"):
        return MockImageAdapter()
    if provider == "mock":
        return MockImageAdapter()
    if provider == "doubao":
        api_key = read_api_key(config.DOUBAO_API_KEY_FILE, env_var="DOUBAO_API_KEY")
        return DoubaoClientAdapter(api_key)
    api_key = read_api_key(config.GEMINI_API_KEY_FILE, env_var="GEMINI_API_KEY")
    return GeminiClientAdapter(api_key)


def _load_templates() -> TemplateLoader:
    """定位提示词模板目录。"""
    templates = TemplateLoader(config.DEFAULT_INPUT_DIR.parent / "templates")
    if not templates.templates_dir.exists():
        templates = TemplateLoader(Path("templates"))
    return templates


def _status_file_path(product_id: str) -> Path:
    """任务状态持久化文件路径。"""
    output_dir = config.DEFAULT_OUTPUT_DIR / _safe_name(product_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / ".status.json"


def _write_status_file(product_id: str, state: dict) -> None:
    """将任务状态写入文件，页面刷新后仍可读取。"""
    try:
        write_text_file(
            _status_file_path(product_id),
            json.dumps({"product_id": product_id, **state}, ensure_ascii=False, indent=2),
        )
    except Exception:
        pass


def _run_pipeline(product_id: str, enabled_steps: set[str] | None = None) -> None:
    """在后台线程中运行产品流水线。"""

    def update_progress(data: dict) -> None:
        _task_states[product_id] = data
        _write_status_file(product_id, data)

    update_progress({"status": "pending", "progress": 0, "message": "任务排队中"})
    _clear_abort_flag(product_id)

    try:
        provider_cfg = _load_provider_config()
        text_provider = provider_cfg.get("text_provider", "gemini")
        image_provider = provider_cfg.get("image_provider", "gemini")

        logger = get_logger("pipeline.web")
        logger.info(
            f"Pipeline start for {product_id}: text={text_provider}, image={image_provider}, "
            f"mock_env={os.environ.get('COUPANGADS_MOCK', '0')}"
        )

        try:
            text_adapter = _build_text_adapter(text_provider)
            image_adapter = _build_image_adapter(image_provider)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"缺少 {text_provider}/{image_provider} 的 API key 文件：{exc}. "
                "请在配置面板选择 Mock（离线开发）模式，或放置正确的 key 文件。"
            ) from exc

        # If the text provider is not vision-capable (e.g. DeepSeek text-only),
        # reuse the image provider's adapter for the product report step.
        vision_adapter = image_adapter if text_provider != image_provider else None

        templates = _load_templates()
        input_dir = config.DEFAULT_INPUT_DIR / product_id
        output_dir = config.DEFAULT_OUTPUT_DIR / product_id

        def check_abort() -> None:
            if _check_abort_flag(product_id):
                raise GenerationAborted()

        pipeline = ProductPipeline(
            text_adapter=text_adapter,
            image_adapter=image_adapter,
            vision_adapter=vision_adapter,
            templates=templates,
            overwrite=False,
            progress_callback=update_progress,
            request_delay=2.0,
            enabled_steps=enabled_steps,
            abort_callback=check_abort,
        )
        pipeline.run(input_dir, output_dir)
        text_files = [
            p.name for p in output_dir.glob("*.md")
            if p.name != config.RUN_LOG_FILE
        ]
        images = [p.name for p in output_dir.glob("*.png")]
        update_progress(
            {
                "status": "completed",
                "progress": 100,
                "message": "全部完成",
                "text_files": sorted(text_files),
                "images": sorted(images),
            }
        )
    except GenerationAborted:
        update_progress(
            {
                "status": "aborted",
                "progress": _task_states.get(product_id, {}).get("progress", 0),
                "message": "已中止",
            }
        )
    except Exception as exc:
        import traceback
        logger = get_logger("pipeline.web")
        logger.error(f"Pipeline failed for {product_id}: {exc}\n{traceback.format_exc()}")
        update_progress(
            {"step": "error", "status": "error", "progress": 0, "message": str(exc)}
        )
    finally:
        _clear_abort_flag(product_id)


@router.post("/upload")
async def upload_product(
    product_name: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """上传产品图。"""
    safe_product = _safe_name(product_name)
    product_dir = _resolve_under(config.DEFAULT_INPUT_DIR, safe_product)
    product_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for file in files:
        safe_filename = _safe_filename(file.filename or "unnamed")
        target = product_dir / safe_filename
        content = await file.read()
        target.write_bytes(content)
        saved.append(safe_filename)

    return {"product_id": safe_product, "file_count": len(saved)}


@router.post("/generate/{product_id}")
async def generate_product(product_id: str, payload: dict | None = None):
    """触发生成（后台任务）。"""
    payload = payload or {}
    steps = payload.get("steps")
    all_steps = set(ProductPipeline.STEP_DEPENDENCIES.keys())

    if steps is None:
        enabled_steps = all_steps
    else:
        if not isinstance(steps, list) or not steps:
            raise HTTPException(status_code=400, detail="steps must be a non-empty list")
        unknown = [s for s in steps if s not in all_steps]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"unknown steps: {unknown}; valid: {sorted(all_steps)}",
            )
        enabled_steps = set(steps)

    _task_states[product_id] = {"status": "pending", "progress": 0, "message": "任务排队中"}
    thread = threading.Thread(
        target=_run_pipeline, args=(product_id, enabled_steps), daemon=True
    )
    thread.start()
    return {"status": "started", "product_id": product_id, "steps": sorted(enabled_steps)}


@router.post("/abort/{product_id}")
async def abort_generation(product_id: str):
    """请求中止正在运行的生成任务。"""
    safe_id = _safe_name(product_id)
    _set_abort_flag(safe_id)
    return {"status": "abort_requested", "product_id": safe_id}


@router.get("/status/{product_id}")
async def get_task_status(product_id: str):
    """返回当前任务状态（非 SSE，用于结果页轮询）。"""
    safe_id = _safe_name(product_id)
    if safe_id in _task_states:
        return {"product_id": safe_id, **_task_states[safe_id]}

    status_path = _status_file_path(safe_id)
    if status_path.exists():
        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
            return {"product_id": safe_id, **data}
        except Exception:
            pass

    return {"product_id": safe_id, "status": "unknown", "progress": 0, "message": "无任务记录"}


@router.get("/progress/{product_id}")
async def progress_stream(product_id: str):
    """SSE 实时进度流。"""
    async def event_generator():
        while True:
            state = _task_states.get(product_id, {"progress": 0, "status": "unknown"})
            yield f"data: {json.dumps(state)}\n\n"
            status = state.get("status")
            progress = state.get("progress", 0)
            # 单个步骤完成时 status 也是 completed，必须等进度 100 才结束 SSE
            if status == "error" or (status == "completed" and progress == 100):
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/result/{product_id}")
async def get_result(product_id: str):
    """获取结果文件列表。"""
    safe_id = _safe_name(product_id)
    output_dir = _resolve_under(config.DEFAULT_OUTPUT_DIR, safe_id)
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output not found")

    text_files = [p.name for p in output_dir.glob("*.md") if p.name != config.RUN_LOG_FILE]
    images = [p.name for p in output_dir.glob("*.png")]
    return Response(
        content=json.dumps(
            {"product_id": safe_id, "text_files": text_files, "images": images},
            ensure_ascii=False,
        ),
        media_type="application/json",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/result/{product_id}/{filename}")
async def serve_result_file(product_id: str, filename: str):
    """提供结果文件预览。"""
    safe_id = _safe_name(product_id)
    safe_filename = _safe_filename(filename)
    output_dir = _resolve_under(config.DEFAULT_OUTPUT_DIR, safe_id)
    file_path = output_dir / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@router.get("/download/{product_id}")
async def download_product(product_id: str):
    """下载 ZIP 资产包。"""
    safe_id = _safe_name(product_id)
    output_dir = _resolve_under(config.DEFAULT_OUTPUT_DIR, safe_id)
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output not found")

    zip_path = output_dir / f"{safe_id}.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        for file in output_dir.iterdir():
            if file.is_file() and file.suffix != ".zip":
                zf.write(file, arcname=file.name)

    return FileResponse(zip_path, filename=zip_path.name)


@router.get("/config")
async def get_config():
    """Get API configuration status without returning full keys."""
    gemini_path = config.GEMINI_API_KEY_FILE
    doubao_path = config.DOUBAO_API_KEY_FILE
    deepseek_path = config.DEEPSEEK_API_KEY_FILE
    provider_cfg = _load_provider_config()

    def _configured(path: Path) -> bool:
        return path.exists() and path.read_text().strip() != ""

    return {
        "gemini_configured": _configured(gemini_path),
        "doubao_configured": _configured(doubao_path),
        "deepseek_configured": _configured(deepseek_path),
        "text_provider": provider_cfg.get("text_provider", "gemini"),
        "image_provider": provider_cfg.get("image_provider", "gemini"),
        "deepseek_model": provider_cfg.get("deepseek_model", config.DEEPSEEK_TEXT_MODEL),
    }


@router.post("/config")
async def update_config(payload: dict):
    """Update API keys and provider selection."""
    gemini_key = payload.get("gemini_api_key", "").strip()
    doubao_key = payload.get("doubao_api_key", "").strip()
    deepseek_key = payload.get("deepseek_api_key", "").strip()
    text_provider = payload.get("text_provider", "gemini").strip()
    image_provider = payload.get("image_provider", "gemini").strip()
    deepseek_model = payload.get("deepseek_model", config.DEEPSEEK_TEXT_MODEL).strip()

    from coupangads.infra.io import write_text_file

    if gemini_key:
        write_text_file(config.GEMINI_API_KEY_FILE, gemini_key + "\n")
    if doubao_key:
        write_text_file(config.DOUBAO_API_KEY_FILE, doubao_key + "\n")
    if deepseek_key:
        write_text_file(config.DEEPSEEK_API_KEY_FILE, deepseek_key + "\n")

    provider_data = {
        "text_provider": text_provider,
        "image_provider": image_provider,
        "deepseek_model": deepseek_model,
    }
    write_text_file(
        config.PROVIDER_CONFIG_FILE,
        json.dumps(provider_data, ensure_ascii=False, indent=2),
    )

    return {"status": "saved"}
