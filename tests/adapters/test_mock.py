"""Mock adapter tests."""

from pathlib import Path

import pytest
from PIL import Image

from coupangads.adapters.mock import MockImageAdapter, MockTextAdapter


class TestMockTextAdapter:
    def setup_method(self):
        self.adapter = MockTextAdapter()

    def test_chat_returns_non_empty_string(self):
        result = self.adapter.chat("generate a product title")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_title_contains_mock_marker(self):
        result = self.adapter.chat("请生成商品标题")
        assert "MOCK" in result
        assert "标题" in result or "Title" in result

    def test_chat_keywords_returns_keywords(self):
        result = self.adapter.chat("请生成关键词")
        assert "关键词" in result
        assert "MOCK" in result

    def test_chat_with_images_returns_report_with_count(self):
        paths = [Path("a.jpg"), Path("b.jpg"), Path("c.jpg")]
        result = self.adapter.chat_with_images("analyze images", paths)
        assert "商品画像报告" in result
        assert "3 张" in result


class TestMockImageAdapter:
    def setup_method(self):
        self.adapter = MockImageAdapter()

    def test_generate_image_creates_png(self, tmp_path: Path):
        output = tmp_path / "A_B1.png"
        success = self.adapter.generate_image(
            prompt="A style product photo MOCK",
            references=[],
            output_path=output,
        )
        assert success is True
        assert output.exists()

        with Image.open(output) as img:
            assert img.format == "PNG"
            assert img.size == (1200, 1800)

    def test_generate_image_extracts_style_b(self, tmp_path: Path):
        output = tmp_path / "B_B2.png"
        self.adapter.generate_image(
            prompt="B style lifestyle scene MOCK",
            references=[],
            output_path=output,
        )
        assert output.exists()
