"""商品画像分析服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.core import config  # noqa: F401
from coupangads.infra.io import write_text_file
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_product_report(
    adapter: TextAdapter,
    image_paths: list[Path],
    output_path: Path,
    templates: TemplateLoader,
) -> str:
    """生成商品画像报告。"""
    template = templates.load("product_report.txt")
    prompt = assemble_text_prompt(
        template,
        image_count=str(len(image_paths)),
    )
    report = adapter.chat_with_images(prompt, image_paths)
    write_text_file(output_path, report)
    return report
