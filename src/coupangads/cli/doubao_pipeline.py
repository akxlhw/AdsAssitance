"""备用线路入口：默认使用 Doubao 模型。"""

import sys

from coupangads.cli.full_pipeline import main as full_main


def main() -> None:
    """默认注入 --use-doubao 参数。"""
    if "--use-doubao" not in sys.argv:
        sys.argv.append("--use-doubao")
    full_main()


if __name__ == "__main__":
    main()
