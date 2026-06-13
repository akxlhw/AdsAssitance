"""完整版入口：报告/标题/关键词/卖点/INS/图片全链路。"""

import argparse
from pathlib import Path

from coupangads.adapters.doubao import DoubaoClientAdapter
from coupangads.adapters.gemini import GeminiClientAdapter
from coupangads.core import config
from coupangads.core.logging import get_logger
from coupangads.infra.api_keys import read_api_key
from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.text.template_loader import TemplateLoader

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CoupangAds 完整版入口")
    parser.add_argument("--input-dir", type=Path, default=config.DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=config.DEFAULT_OUTPUT_DIR)
    parser.add_argument("--api-key-file", type=Path, default=config.GEMINI_API_KEY_FILE)
    parser.add_argument("--doubao-key-file", type=Path, default=config.DOUBAO_API_KEY_FILE)
    parser.add_argument("--limit-folder", type=str, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-images", type=int, default=None)
    parser.add_argument("--start-from", type=str, default=None)
    parser.add_argument("--max-retries", type=int, default=config.DEFAULT_MAX_RETRIES)
    parser.add_argument("--request-delay", type=float, default=config.DEFAULT_REQUEST_DELAY)
    parser.add_argument("--request-timeout", type=int, default=config.DEFAULT_REQUEST_TIMEOUT_MS)
    parser.add_argument("--use-doubao", action="store_true", help="使用 Doubao 线路")
    parser.add_argument("--templates-dir", type=Path, default=Path("templates"))
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir

    if not input_dir.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        return

    templates = TemplateLoader(args.templates_dir)

    if args.dry_run:
        logger.info("Dry Run 模式：仅扫描输入目录")
        for product_dir in sorted(input_dir.iterdir()):
            if product_dir.is_dir():
                logger.info(f"将处理产品: {product_dir.name}")
        return

    if args.use_doubao:
        api_key = read_api_key(args.doubao_key_file, env_var="DOUBAO_API_KEY")
        text_adapter = DoubaoClientAdapter(api_key, max_retries=args.max_retries, request_timeout=args.request_timeout)
        image_adapter = DoubaoClientAdapter(api_key, max_retries=args.max_retries, request_timeout=args.request_timeout)
    else:
        api_key = read_api_key(args.api_key_file, env_var="GEMINI_API_KEY")
        text_adapter = GeminiClientAdapter(api_key, max_retries=args.max_retries, request_timeout=args.request_timeout)
        image_adapter = GeminiClientAdapter(api_key, max_retries=args.max_retries, request_timeout=args.request_timeout)

    pipeline = ProductPipeline(
        text_adapter=text_adapter,
        image_adapter=image_adapter,
        templates=templates,
        overwrite=args.overwrite,
        max_images=args.max_images,
        start_from=args.start_from,
        request_delay=args.request_delay,
    )

    product_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
    if args.limit_folder:
        product_dirs = [d for d in product_dirs if d.name == args.limit_folder]

    for product_dir in sorted(product_dirs):
        product_output_dir = output_dir / product_dir.name
        logger.info(f"开始处理: {product_dir.name}")
        try:
            pipeline.run(product_dir, product_output_dir)
        except Exception as exc:
            logger.error(f"处理 {product_dir.name} 失败: {exc}")


if __name__ == "__main__":
    main()
