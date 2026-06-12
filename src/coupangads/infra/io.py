"""文件 IO 工具。"""

import json
from pathlib import Path


def read_text_file(path: Path) -> str:
    """读取 UTF-8 文本文件。"""
    return path.read_text(encoding="utf-8")


def write_text_file(path: Path, content: str) -> None:
    """写入 UTF-8 文本文件，自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json_file(path: Path, data: object) -> None:
    """以格式化 JSON 写入文件，自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
