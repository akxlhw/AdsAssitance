"""编排层单元测试。"""

import time
from pathlib import Path

from PIL import Image

from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.text.template_loader import TemplateLoader


def _create_valid_image(path: Path) -> None:
    """创建一张可被 PIL 加载的测试图片。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (100, 100), color="red")
    img.save(path, format="JPEG")


def _setup_product(tmp_path: Path) -> tuple[Path, Path, Path]:
    """准备测试用的输入目录、输出目录和模板目录。"""
    input_dir = tmp_path / "input" / "prod"
    output_dir = tmp_path / "output" / "prod"
    input_dir.mkdir(parents=True)

    for i in range(3):
        _create_valid_image(input_dir / f"img{i}.jpg")

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("report prompt")
    (templates_dir / "product_title.txt").write_text("{product_report}")
    (templates_dir / "wing_keywords.txt").write_text("{product_report}{product_title}")
    (templates_dir / "selling_points.txt").write_text(
        "{product_report}{product_title}{wing_keywords}"
    )
    (templates_dir / "instagram.txt").write_text(
        "{product_report}{product_title}{wing_keywords}{selling_points}"
    )
    (templates_dir / "image_prompt.txt").write_text(
        "{style_rules}{product_context}{screen}{block}{block_content}"
    )
    (templates_dir / "style_rules.txt").write_text("## STYLE A\na\n## STYLE B\nb")
    (templates_dir / "image_global_constraints.txt").write_text("global")

    return input_dir, output_dir, templates_dir


class FakeTextAdapter:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = responses or [
            "report",
            "title",
            "keywords",
            "selling points",
            "instagram",
        ]
        self.idx = 0

    def chat(self, prompt: str) -> str:
        resp = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return resp


class CountingTextAdapter(FakeTextAdapter):
    """记录 chat 调用次数的适配器。"""

    def __init__(self, responses: list[str] | None = None) -> None:
        super().__init__(responses)
        self.call_count = 0

    def chat(self, prompt: str) -> str:
        self.call_count += 1
        return super().chat(prompt)


class FakeImageAdapter:
    def generate_image(self, prompt, references, output_path: Path) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"PNG")
        return True


def test_pipeline_creates_text_outputs(tmp_path: Path) -> None:
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

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


def test_pipeline_generates_images(tmp_path: Path) -> None:
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        max_images=3,
    )
    pipeline.run(input_dir, output_dir)

    assert (output_dir / "A_B1.png").exists()
    assert (output_dir / "A_B2.png").exists()
    assert (output_dir / "A_B3.png").exists()


def test_pipeline_reuses_existing_text_outputs(tmp_path: Path) -> None:
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    adapter = CountingTextAdapter()
    pipeline = ProductPipeline(
        text_adapter=adapter,
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        max_images=0,
    )
    pipeline.run(input_dir, output_dir)
    first_run_calls = adapter.call_count

    # 第二次运行：所有文本输出已存在且上游未变更，不应再调用文本模型
    pipeline2 = ProductPipeline(
        text_adapter=adapter,
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        max_images=0,
    )
    pipeline2.run(input_dir, output_dir)

    assert adapter.call_count == first_run_calls


def test_pipeline_overwrite_regenerates_downstream(tmp_path: Path) -> None:
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    adapter = CountingTextAdapter()
    pipeline = ProductPipeline(
        text_adapter=adapter,
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        max_images=0,
    )
    pipeline.run(input_dir, output_dir)
    first_run_calls = adapter.call_count

    # 修改下游文件并改变 mtime，模拟外部修改
    report_path = output_dir / "productreport.md"
    report_path.write_text("modified report")
    time.sleep(0.01)

    pipeline2 = ProductPipeline(
        text_adapter=adapter,
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        max_images=0,
        overwrite=True,
    )
    pipeline2.run(input_dir, output_dir)

    assert adapter.call_count > first_run_calls
    assert report_path.read_text() != "modified report"
