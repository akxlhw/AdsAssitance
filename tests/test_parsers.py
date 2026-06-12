"""解析函数单元测试。"""

import pytest

from coupangads.text.parsers import (
    extract_json_object,
    parse_selling_points,
    extract_style_rules,
    is_suspected_ai_image,
)


def test_extract_json_object_from_code_block() -> None:
    text = '```json\n{"a": 1}\n```'
    assert extract_json_object(text) == '{"a": 1}'


def test_extract_json_object_bare() -> None:
    text = 'prefix {"a": 1} suffix'
    assert extract_json_object(text) == '{"a": 1}'


def test_extract_json_object_no_json_returns_original() -> None:
    text = "no json here"
    assert extract_json_object(text) == "no json here"


def test_parse_selling_points_standard() -> None:
    text = """
# B1 主卖点
标题1
正文1
# B2 材质优势
标题2
正文2
"""
    result = parse_selling_points(text)
    assert "B1" in result and "B2" in result
    assert "标题1" in result["B1"]


def test_parse_selling_points_missing_blocks() -> None:
    result = parse_selling_points("# B1 测试\n内容")
    assert result["B1"] == "内容"
    assert result["B2"] == ""


def test_extract_style_rules_ab() -> None:
    text = "## STYLE A\n规则A\n## STYLE B\n规则B"
    rules = extract_style_rules(text)
    assert rules["A"] == "规则A"
    assert rules["B"] == "规则B"


def test_is_suspected_ai_image() -> None:
    assert is_suspected_ai_image("ai_generated_image_v2.png") is True
    assert is_suspected_ai_image("IMG_2024.jpg") is False
