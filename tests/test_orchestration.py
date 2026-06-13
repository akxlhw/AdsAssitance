"""编排层单元测试。"""

import time
from pathlib import Path

import pytest
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

    def chat_with_images(self, prompt: str, image_paths: list) -> str:
        return self.chat(prompt)


class CountingTextAdapter(FakeTextAdapter):
    """记录 chat 调用次数的适配器。"""

    def __init__(self, responses: list[str] | None = None) -> None:
        super().__init__(responses)
        self.call_count = 0

    def chat(self, prompt: str) -> str:
        self.call_count += 1
        return super().chat(prompt)

    def chat_with_images(self, prompt: str, image_paths: list) -> str:
        self.call_count += 1
        return super().chat_with_images(prompt, image_paths)


class FakeImageAdapter:
    def generate_image(self, prompt, references, output_path: Path) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"PNG")
        return True


class CountingImageAdapter:
    def __init__(self):
        self.calls = 0

    def generate_image(self, prompt, references, output_path: Path) -> bool:
        self.calls += 1
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


def test_pipeline_reuses_existing_images(tmp_path: Path) -> None:
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    image_adapter = CountingImageAdapter()
    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=image_adapter,
        templates=TemplateLoader(templates_dir),
    )
    pipeline.run(input_dir, output_dir)
    first_run_calls = image_adapter.calls
    assert first_run_calls > 0

    # 第二次运行：图片已存在，不应再调用图片生成
    pipeline2 = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=image_adapter,
        templates=TemplateLoader(templates_dir),
    )
    pipeline2.run(input_dir, output_dir)

    assert image_adapter.calls == first_run_calls


def test_pipeline_overwrite_regenerates_images(tmp_path: Path) -> None:
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    image_adapter = CountingImageAdapter()
    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=image_adapter,
        templates=TemplateLoader(templates_dir),
    )
    pipeline.run(input_dir, output_dir)
    first_run_calls = image_adapter.calls
    assert first_run_calls == 18

    pipeline2 = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=image_adapter,
        templates=TemplateLoader(templates_dir),
        overwrite=True,
    )
    pipeline2.run(input_dir, output_dir)

    assert image_adapter.calls - first_run_calls == 18



def test_pipeline_runs_only_selected_steps(tmp_path: Path) -> None:
    """只选择 title 时，仅生成商品画像（依赖）和标题。"""
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    text_adapter = CountingTextAdapter()
    pipeline = ProductPipeline(
        text_adapter=text_adapter,
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        enabled_steps={"title"},
        max_images=0,
    )
    pipeline.run(input_dir, output_dir)

    assert (output_dir / "productreport.md").exists()
    assert (output_dir / "product_title.md").exists()
    assert not (output_dir / "wing_keywords.md").exists()
    assert not (output_dir / "instagram.md").exists()
    # product_report (vision chat counts as 2 in CountingTextAdapter) + title = 3
    assert text_adapter.call_count == 3


def test_pipeline_auto_runs_missing_upstream_for_images(tmp_path: Path) -> None:
    """只选择 images 但上游文件不存在时，自动补齐上游步骤。"""
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    text_adapter = CountingTextAdapter()
    image_adapter = CountingImageAdapter()
    pipeline = ProductPipeline(
        text_adapter=text_adapter,
        image_adapter=image_adapter,
        templates=TemplateLoader(templates_dir),
        enabled_steps={"images"},
    )
    pipeline.run(input_dir, output_dir)

    # 上游文本步骤自动执行：report(vision=2) + title + keywords + selling_points = 5 calls
    assert text_adapter.call_count == 5
    # 18 张图片
    assert image_adapter.calls == 18


def test_pipeline_abort_callback_propagates_exception(tmp_path: Path) -> None:
    """abort_callback 抛出异常时应中断流水线并原样向上传播。"""
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    class AbortNow(Exception):
        pass

    def check_abort() -> None:
        raise AbortNow()

    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        abort_callback=check_abort,
        max_images=0,
    )

    with pytest.raises(AbortNow):
        pipeline.run(input_dir, output_dir)

    assert not (output_dir / "productreport.md").exists()


def test_pipeline_abort_callback_stops_between_steps(tmp_path: Path) -> None:
    """abort_callback 在步骤之间抛出异常时，已完成的文本步骤保留，后续步骤不执行。"""
    input_dir, output_dir, templates_dir = _setup_product(tmp_path)

    class AbortNow(Exception):
        pass

    call_count = 0

    def check_abort() -> None:
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise AbortNow()

    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        abort_callback=check_abort,
        max_images=0,
    )

    with pytest.raises(AbortNow):
        pipeline.run(input_dir, output_dir)

    # 第一个检查点在 run() 开头，第二个在商品画像步骤开始，第三个在标题步骤开始时触发中止
    assert (output_dir / "productreport.md").exists()
    assert not (output_dir / "product_title.md").exists()
