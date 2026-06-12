"""API 密钥读取工具。"""

import os
from pathlib import Path


def read_api_key(file_path: Path, env_var: str | None = None) -> str:
    """
    读取 API Key。

    优先级：
    1. 环境变量（若 env_var 提供且存在）
    2. 指定文件首行非空内容
    """
    if env_var and (value := os.environ.get(env_var)):
        return value

    lines = file_path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped:
            return stripped
    raise ValueError(f"API key file is empty: {file_path}")
