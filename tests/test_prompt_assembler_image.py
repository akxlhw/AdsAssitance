"""图片提示词组装单元测试。"""

from pathlib import Path

from coupangads.image_pipeline.prompt_assembler import assemble_image_prompts


def test_assemble_image_prompts_count(tmp_path: Path) -> None:
    selling_points = {f"B{i}": f"卖点{i}" for i in range(1, 10)}
    style_rules = "## STYLE A\n高级风\n## STYLE B\n生活风"
    template = "风格：{style_rules} 区块：{block} 内容：{block_content}"
    output = tmp_path / "prompts.json"
    prompts = assemble_image_prompts(
        selling_points, style_rules, "ctx", template, output
    )
    assert len(prompts) == 18
    assert prompts[0].filename == "A_B1.png"
    assert output.exists()
