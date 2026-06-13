"""经典版入口：报告 + 提示词 + 图片三段式。"""

import argparse
from pathlib import Path

from coupangads.cli.full_pipeline import build_parser as full_build_parser
from coupangads.core import config


def main() -> None:
    """经典版复用完整版入口，但强制跳过标题/关键词/INS 生成阶段。"""
    parser = full_build_parser()
    parser.description = "CoupangAds 经典版入口（报告 + 提示词 + 图片）"
    args = parser.parse_args()
    # 通过调用 full_pipeline 并传入特殊模式实现
    # 实际实现可在 ProductPipeline 增加 classic_mode 标志
    print("经典版入口：请使用 --max-images 0 先生成文本资产，再单独跑图片生成")


if __name__ == "__main__":
    main()
