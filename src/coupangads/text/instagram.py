"""社媒文案生成服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.infra.io import write_text_file
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_instagram(
    adapter: TextAdapter,
    product_report: str,
    product_title: str,
    keywords: str,
    selling_points: str,
    output_path: Path,
    templates: TemplateLoader,
) -> str:
    """生成 Instagram 文案。"""
    template = templates.load("instagram.txt")
    prompt = assemble_text_prompt(
        template,
        product_report=product_report,
        product_title=product_title,
        wing_keywords=keywords,
        selling_points=selling_points,
    )
    instagram = adapter.chat(prompt)
    write_text_file(output_path, instagram)
    return instagram
