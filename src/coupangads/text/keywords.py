"""关键词挖掘服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.infra.io import write_text_file
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_keywords(
    adapter: TextAdapter,
    product_report: str,
    product_title: str,
    output_path: Path,
    templates: TemplateLoader,
) -> str:
    """生成关键词文档。"""
    template = templates.load("wing_keywords.txt")
    prompt = assemble_text_prompt(
        template,
        product_report=product_report,
        product_title=product_title,
    )
    keywords = adapter.chat(prompt)
    write_text_file(output_path, keywords)
    return keywords
