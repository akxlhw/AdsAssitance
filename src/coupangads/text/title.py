"""商品标题生成服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.infra.io import write_text_file
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_product_title(
    adapter: TextAdapter,
    product_report: str,
    output_path: Path,
    templates: TemplateLoader,
) -> str:
    """生成商品标题。"""
    template = templates.load("product_title.txt")
    prompt = assemble_text_prompt(template, product_report=product_report)
    title = adapter.chat(prompt)
    write_text_file(output_path, title)
    return title
