"""编排层单元测试。"""

from pathlib import Path

from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.text.template_loader import TemplateLoader


class FakeTextAdapter:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = responses or ["report", "title", "keywords", "selling points", "instagram"]
        self.idx = 0

    def chat(self, prompt: str) -> str:
        resp = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return resp


class FakeImageAdapter:
    def generate_image(self, prompt, references, output_path: Path) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"PNG")
        return True


def test_pipeline_creates_text_outputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "input" / "prod"
    output_dir = tmp_path / "output" / "prod"
    input_dir.mkdir(parents=True)
    for i in range(3):
        (input_dir / f"img{i}.jpg").write_bytes(b"fake")

    # 创建最小模板
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("report prompt")
    (templates_dir / "product_title.txt").write_text("{product_report}")
    (templates_dir / "wing_keywords.txt").write_text("{product_report}{product_title}")
    (templates_dir / "selling_points.txt").write_text("{product_report}{product_title}{wing_keywords}")
    (templates_dir / "instagram.txt").write_text("{product_report}{product_title}{wing_keywords}{selling_points}")
    (templates_dir / "image_prompt.txt").write_text("{style_rules}{product_context}{screen}{block}{block_content}")
    (templates_dir / "style_rules.txt").write_text("## STYLE A\na\n## STYLE B\nb")
    (templates_dir / "image_global_constraints.txt").write_text("global")

    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        max_images=0,
    )
    pipeline.run(input_dir, output_dir)

    assert (output_dir / "productreport.md").exists()
    assert (output_dir / "product_title.md").exists()
    assert (output_dir / "wing_keywords.md").exists()
    assert (output_dir / "selling_points.md").exists()
    assert (output_dir / "selling_points.json").exists()
    assert (output_dir / "instagram.md").exists()
