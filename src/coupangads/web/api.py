"""Web API 路由。"""

import asyncio
import json
import re
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from coupangads.core import config

router = APIRouter(prefix="/api")

# 内存中的任务状态（MVP 简版，v2.0 迁移到数据库）
_task_states: dict[str, dict] = {}


def _safe_name(name: str) -> str:
    """移除危险字符，仅保留字母、数字、下划线、连字符和点。"""
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", name)


@router.post("/upload")
async def upload_product(
    product_name: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """上传产品图。"""
    safe_product = _safe_name(product_name)
    product_dir = config.DEFAULT_INPUT_DIR / safe_product
    product_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for file in files:
        safe_filename = _safe_name(file.filename or "unnamed")
        target = product_dir / safe_filename
        content = await file.read()
        target.write_bytes(content)
        saved.append(safe_filename)

    return {"product_id": safe_product, "file_count": len(saved)}


@router.post("/generate/{product_id}")
async def generate_product(product_id: str):
    """触发生成（后台任务）。"""
    _task_states[product_id] = {"status": "pending", "progress": 0}
    # 实际实现将调用 ProductPipeline 在后台运行
    return {"status": "started", "product_id": product_id}


@router.get("/progress/{product_id}")
async def progress_stream(product_id: str):
    """SSE 实时进度流。"""
    from fastapi.responses import StreamingResponse

    async def event_generator():
        while True:
            state = _task_states.get(product_id, {"progress": 0, "status": "unknown"})
            yield f"data: {json.dumps(state)}\n\n"
            if state.get("status") in ("completed", "error"):
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/result/{product_id}")
async def get_result(product_id: str):
    """获取结果文件列表。"""
    safe_id = _safe_name(product_id)
    output_dir = config.DEFAULT_OUTPUT_DIR / safe_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output not found")

    text_files = [p.name for p in output_dir.glob("*.md") if p.name != config.RUN_LOG_FILE]
    images = [p.name for p in output_dir.glob("*.png")]
    return {"product_id": safe_id, "text_files": text_files, "images": images}


@router.get("/download/{product_id}")
async def download_product(product_id: str):
    """下载 ZIP 资产包。"""
    safe_id = _safe_name(product_id)
    output_dir = config.DEFAULT_OUTPUT_DIR / safe_id
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
    """获取 API 配置状态（不返回完整密钥）。"""
    gemini_path = config.GEMINI_API_KEY_FILE
    doubao_path = config.DOUBAO_API_KEY_FILE
    provider = "gemini"
    if config.PROVIDER_CONFIG_FILE.exists():
        try:
            data = json.loads(config.PROVIDER_CONFIG_FILE.read_text(encoding="utf-8"))
            provider = data.get("default_provider", "gemini")
        except Exception:
            pass
    return {
        "gemini_configured": gemini_path.exists() and gemini_path.read_text().strip() != "",
        "doubao_configured": doubao_path.exists() and doubao_path.read_text().strip() != "",
        "default_provider": provider,
    }


@router.post("/config")
async def update_config(payload: dict):
    """更新 API 密钥与默认线路。"""
    gemini_key = payload.get("gemini_api_key", "").strip()
    doubao_key = payload.get("doubao_api_key", "").strip()
    provider = payload.get("default_provider", "gemini").strip()

    if gemini_key:
        from coupangads.infra.io import write_text_file
        write_text_file(config.GEMINI_API_KEY_FILE, gemini_key + "\n")
    if doubao_key:
        from coupangads.infra.io import write_text_file
        write_text_file(config.DOUBAO_API_KEY_FILE, doubao_key + "\n")

    write_text_file(
        config.PROVIDER_CONFIG_FILE,
        json.dumps({"default_provider": provider}, ensure_ascii=False, indent=2),
    )

    return {"status": "saved"}
