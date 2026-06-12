"""Prompt 组装单元测试。"""

from pathlib import Path

import pytest

from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def test_template_loader_loads_file(tmp_path: Path) -> None:
    (tmp_path / "test.txt").write_text("hello {name}", encoding="utf-8")
    loader = TemplateLoader(tmp_path)
    assert loader.load("test.txt") == "hello {name}"


def test_assemble_text_prompt() -> None:
    template = "报告：{product_report}"
    assert assemble_text_prompt(template, product_report="R") == "报告：R"


def test_assemble_text_prompt_missing_key_raises() -> None:
    with pytest.raises(KeyError):
        assemble_text_prompt("{missing}")
