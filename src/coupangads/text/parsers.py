"""文本解析与容错工具。"""

import json
import re
from typing import Any


def extract_json_object(text: str) -> str:
    """
    从文本中提取 JSON 对象。

    Fallback 顺序：
    1. markdown 代码块
    2. 首尾花括号匹配
    3. 返回原文
    """
    # 1. 代码块
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        return code_block.group(1).strip()

    # 2. 花括号
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0).strip()

    return text


def safe_parse_json(text: str) -> Any:
    """安全解析 JSON，失败返回 None。"""
    try:
        return json.loads(extract_json_object(text))
    except json.JSONDecodeError:
        return None


def parse_selling_points(text: str) -> dict[str, str]:
    """
    从 Markdown 文本中提取 B1-B9 卖点区块。

    每个区块以 `# B{n}` 或 `## B{n}` 开头。
    """
    blocks: dict[str, str] = {f"B{i}": "" for i in range(1, 10)}
    pattern = re.compile(r"^#+\s*B(\d+)\b.*$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    for idx, match in enumerate(matches):
        block_num = match.group(1)
        block_key = f"B{block_num}"
        if block_key not in blocks:
            continue
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        blocks[block_key] = text[start:end].strip()

    return blocks


def extract_style_rules(text: str) -> dict[str, str]:
    """
    从模板中提取 A/B 风格规则。

    期望格式：
    ## STYLE A
    ...
    ## STYLE B
    ...
    """
    rules: dict[str, str] = {}
    pattern = re.compile(r"##\s*STYLE\s+([A-Z])\s*\n(.*?)(?=\n##\s*STYLE|\Z)", re.DOTALL)
    for match in pattern.finditer(text):
        rules[match.group(1)] = match.group(2).strip()
    return rules


def is_suspected_ai_image(filename: str) -> bool:
    """基于文件名模式判断是否为疑似 AI 生成图。"""
    lowered = filename.lower()
    markers = ("ai_", "generated", "midjourney", "dalle", "stable_diffusion")
    return any(marker in lowered for marker in markers)
