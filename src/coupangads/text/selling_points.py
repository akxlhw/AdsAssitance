"""详情页卖点文案服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.core import config  # noqa: F401
from coupangads.infra.io import write_json_file, write_text_file
from coupangads.text.parsers import parse_selling_points
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_selling_points(
    adapter: TextAdapter,
    product_report: str,
    product_title: str,
    keywords: str,
    md_output_path: Path,
    json_output_path: Path,
    templates: TemplateLoader,
) -> dict[str, str]:
    """生成卖点 Markdown 与 B1-B9 JSON。"""
    template = templates.load("selling_points.txt")
    prompt = assemble_text_prompt(
        template,
        product_report=product_report,
        product_title=product_title,
        wing_keywords=keywords,
    )
    selling_points_md = adapter.chat(prompt)
    write_text_file(md_output_path, selling_points_md)

    blocks = parse_selling_points(selling_points_md)
    write_json_file(json_output_path, blocks)
    return blocks
