"""图片提示词组装服务。"""

from pathlib import Path

from coupangads.core.models import ImagePrompt
from coupangads.infra.io import write_json_file
from coupangads.text.parsers import extract_style_rules
from coupangads.text.template_loader import assemble_image_prompt


def build_product_context(
    product_report: str,
    product_title: str,
    keywords: str,
    global_constraints: str,
) -> str:
    """组装精简产品上下文。"""
    return f"""{global_constraints}

产品标题：
{product_title}

关键词：
{keywords}

商品画像摘要：
{product_report[:2000]}
"""


def assemble_image_prompts(
    selling_points: dict[str, str],
    style_rules_text: str,
    product_context: str,
    prompt_template: str,
    output_path: Path,
) -> list[ImagePrompt]:
    """组装 A/B 双风格 × B1-B9 共 18 条图片提示词。"""
    style_rules = extract_style_rules(style_rules_text)
    blocks = [f"B{i}" for i in range(1, 10)]
    prompts: list[ImagePrompt] = []

    for style_code, style_rule in style_rules.items():
        for block in blocks:
            content = selling_points.get(block, "")
            prompt_text = assemble_image_prompt(
                template=prompt_template,
                style_rules=style_rule,
                product_context=product_context,
                screen=f"第 {block[1]} 屏",
                block=block,
                block_content=content,
            )
            prompts.append(
                ImagePrompt(
                    style=style_code,
                    screen=f"第 {block[1]} 屏",
                    block=block,
                    prompt=prompt_text,
                    filename=f"{style_code}_{block}.png",
                )
            )

    write_json_file(
        output_path,
        [
            {
                "style": p.style,
                "screen": p.screen,
                "block": p.block,
                "prompt": p.prompt,
                "filename": p.filename,
            }
            for p in prompts
        ],
    )
    return prompts
