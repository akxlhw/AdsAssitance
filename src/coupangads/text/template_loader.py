"""模板加载与 Prompt 组装。"""

from pathlib import Path

from coupangads.infra.io import read_text_file


class TemplateLoader:
    """从 templates/ 目录加载提示词模板。"""

    def __init__(self, templates_dir: Path = Path("templates")) -> None:
        self.templates_dir = templates_dir

    def load(self, name: str) -> str:
        """加载指定模板文件（不含扩展名需自行补全）。"""
        return read_text_file(self.templates_dir / name)


def assemble_text_prompt(template: str, **kwargs: str) -> str:
    """使用 str.format 将变量填充到模板中。"""
    return template.format(**kwargs)


def assemble_image_prompt(
    template: str,
    style_rules: str,
    product_context: str,
    screen: str,
    block: str,
    block_content: str,
) -> str:
    """组装单张图片生成提示词。"""
    return template.format(
        style_rules=style_rules,
        product_context=product_context,
        screen=screen,
        block=block,
        block_content=block_content,
    )
