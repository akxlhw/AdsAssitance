"""端到端冒烟测试（不调用真实 API）。"""

from pathlib import Path

from PIL import Image

from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.text.template_loader import TemplateLoader


class FakeTextAdapter:
    def chat(self, prompt: str) -> str:
        return "한국어 샘플 응답"


class FakeImageAdapter:
    def generate_image(self, prompt, references, output_path: Path) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1200, 1800), color=(200, 200, 200))
        img.save(output_path, "PNG")
        return True


def test_full_pipeline_end_to_end(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw-material" / "test-dog-harness"
    output_dir = tmp_path / "result" / "test-dog-harness"
    input_dir.mkdir(parents=True)

    # 创建 3 张测试图
    for i in range(3):
        img = Image.new("RGB", (800, 1200), color=(100 + i * 50, 100, 100))
        img.save(input_dir / f"img_{i}.jpg", "JPEG")

    # 创建模板
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("{image_count}", encoding="utf-8")
    (templates_dir / "product_title.txt").write_text("{product_report}", encoding="utf-8")
    (templates_dir / "wing_keywords.txt").write_text(
        "{product_report}{product_title}", encoding="utf-8"
    )
    (templates_dir / "selling_points.txt").write_text(
        "{product_report}\n{product_title}\n{wing_keywords}\n"
        "# B1\n한국어\n# B2\n한국어\n# B3\n한국어\n"
        "# B4\n한국어\n# B5\n한국어\n# B6\n한국어\n"
        "# B7\n한국어\n# B8\n한국어\n# B9\n한국어",
        encoding="utf-8",
    )
    (templates_dir / "instagram.txt").write_text(
        "{product_report}\n{product_title}\n{wing_keywords}\n{selling_points}",
        encoding="utf-8",
    )
    (templates_dir / "image_prompt.txt").write_text(
        "{style_rules}{product_context}{screen}{block}{block_content}", encoding="utf-8"
    )
    (templates_dir / "style_rules.txt").write_text(
        "## STYLE A\nA\n## STYLE B\nB", encoding="utf-8"
    )
    (templates_dir / "image_global_constraints.txt").write_text(
        "global", encoding="utf-8"
    )

    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
    )
    pipeline.run(input_dir, output_dir)

    assert (output_dir / "productreport.md").exists()
    assert (output_dir / "product_title.md").exists()
    assert (output_dir / "wing_keywords.md").exists()
    assert (output_dir / "selling_points.md").exists()
    assert (output_dir / "selling_points.json").exists()
    assert (output_dir / "instagram.md").exists()
    assert (output_dir / "product_context.md").exists()
    assert (output_dir / "image_prompts.json").exists()
    assert (output_dir / "best_reference_images.json").exists()
    assert (output_dir / "A_B1.png").exists()
    assert (output_dir / "B_B9.png").exists()
