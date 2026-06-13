"""单产品全流程编排与断点续跑。"""

from pathlib import Path
from typing import Callable

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.core import config
from coupangads.core.logging import add_file_handler, get_logger
from coupangads.image_pipeline.generator import generate_detail_images
from coupangads.image_pipeline.prompt_assembler import (
    assemble_image_prompts,
    build_product_context,
)
from coupangads.image_pipeline.reference_selector import (
    select_best_reference_images,
)
from coupangads.infra.io import read_text_file, write_json_file, write_text_file
from coupangads.text.instagram import generate_instagram
from coupangads.text.keywords import generate_keywords
from coupangads.text.parsers import parse_selling_points
from coupangads.text.report import generate_product_report
from coupangads.text.selling_points import generate_selling_points
from coupangads.text.template_loader import TemplateLoader
from coupangads.text.title import generate_product_title


class ProductPipeline:
    """单个产品的完整生成流水线。"""

    STEP_DEPENDENCIES: dict[str, tuple[str, ...]] = {
        "product_report": (),
        "title": ("product_report",),
        "keywords": ("product_report", "title"),
        "selling_points": ("product_report", "title", "keywords"),
        "instagram": ("product_report", "title", "keywords", "selling_points"),
        "images": ("product_report", "title", "keywords", "selling_points"),
    }

    def __init__(
        self,
        text_adapter: TextAdapter,
        image_adapter: ImageAdapter,
        templates: TemplateLoader,
        overwrite: bool = False,
        max_images: int | None = None,
        start_from: str | None = None,
        request_delay: float = 0.0,
        progress_callback: Callable[[dict], None] | None = None,
        vision_adapter: TextAdapter | None = None,
        enabled_steps: set[str] | None = None,
        abort_callback: Callable[[], None] | None = None,
    ) -> None:
        self.text_adapter = text_adapter
        self.image_adapter = image_adapter
        self.vision_adapter = vision_adapter or text_adapter
        self.templates = templates
        self.overwrite = overwrite
        self.max_images = max_images
        self.start_from = start_from
        self.request_delay = request_delay
        self.progress_callback = progress_callback
        self.enabled_steps = enabled_steps or set(self.STEP_DEPENDENCIES.keys())
        self.required_steps = self._compute_required_steps(self.enabled_steps)
        self._abort_callback = abort_callback

    def _compute_required_steps(self, enabled: set[str]) -> set[str]:
        """计算需要执行的步骤集合（包含上游依赖）。"""
        required: set[str] = set()

        def add_step(step: str) -> None:
            if step in required:
                return
            required.add(step)
            for dep in self.STEP_DEPENDENCIES.get(step, ()):
                add_step(dep)

        for step in enabled:
            if step in self.STEP_DEPENDENCIES:
                add_step(step)
        return required

    def _emit_progress(
        self, step: str, status: str, progress: int, message: str = ""
    ) -> None:
        """向外部报告当前进度。"""
        if self.progress_callback:
            self.progress_callback(
                {
                    "step": step,
                    "status": status,
                    "progress": progress,
                    "message": message,
                }
            )

    def _check_abort(self) -> None:
        """如果外部请求中止，则调用回调；回调抛出的异常原样向上传播。"""
        if self._abort_callback is not None:
            self._abort_callback()

    def _needs_run(self, target: Path, *dependencies: Path) -> bool:
        """判断目标文件是否需要重新生成。"""
        if self.overwrite:
            return True
        if not target.exists():
            return True
        target_mtime = target.stat().st_mtime
        for dep in dependencies:
            if not dep.exists() or dep.stat().st_mtime > target_mtime:
                return True
        return False

    def run(
        self,
        product_input_dir: Path,
        product_output_dir: Path,
    ) -> None:
        """执行单产品完整链路。"""
        product_output_dir.mkdir(parents=True, exist_ok=True)
        logger = get_logger(f"pipeline.{product_input_dir.name}")
        add_file_handler(logger, product_output_dir / config.RUN_LOG_FILE)

        self._check_abort()

        if not self.required_steps:
            self._emit_progress("images", "completed", 100, "没有选择任何步骤")
            return

        self._emit_progress("product_report", "started", 5, "开始生成商品画像")

        image_paths = sorted(
            p for p in product_input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".webp")
        )
        if len(image_paths) < 3:
            logger.warning(f"{product_input_dir.name} 图片不足 3 张，跳过")
            self._emit_progress(
                "product_report", "error", 0, f"{product_input_dir.name} 图片不足 3 张"
            )
            return

        # 1. 商品画像（需要视觉能力，使用 vision_adapter）
        report_path = product_output_dir / config.PRODUCT_REPORT_FILE
        if "product_report" in self.required_steps:
            self._check_abort()
            if self._needs_run(report_path, *image_paths):
                logger.info("生成商品画像报告")
                report = generate_product_report(
                    self.vision_adapter, image_paths, report_path, self.templates
                )
            else:
                logger.info("复用商品画像报告")
                report = read_text_file(report_path)
            self._emit_progress("product_report", "completed", 15, "商品画像完成")

        # 2. 标题
        title_path = product_output_dir / config.PRODUCT_TITLE_FILE
        if "title" in self.required_steps:
            self._check_abort()
            if self._needs_run(title_path, report_path):
                logger.info("生成商品标题")
                title = generate_product_title(
                    self.text_adapter, report, title_path, self.templates
                )
            else:
                logger.info("复用商品标题")
                title = read_text_file(title_path)
            self._emit_progress("title", "completed", 30, "标题完成")

        # 3. 关键词
        keywords_path = product_output_dir / config.WING_KEYWORDS_FILE
        if "keywords" in self.required_steps:
            self._check_abort()
            if self._needs_run(keywords_path, report_path, title_path):
                logger.info("生成关键词")
                keywords = generate_keywords(
                    self.text_adapter, report, title, keywords_path, self.templates
                )
            else:
                logger.info("复用关键词")
                keywords = read_text_file(keywords_path)
            self._emit_progress("keywords", "completed", 40, "关键词完成")

        # 4. 卖点
        sp_md_path = product_output_dir / config.SELLING_POINTS_FILE
        sp_json_path = product_output_dir / config.SELLING_POINTS_JSON_FILE
        if "selling_points" in self.required_steps:
            self._check_abort()
            if self._needs_run(sp_md_path, report_path, title_path, keywords_path):
                logger.info("生成卖点文案")
                selling_points = generate_selling_points(
                    self.text_adapter,
                    report,
                    title,
                    keywords,
                    sp_md_path,
                    sp_json_path,
                    self.templates,
                )
            else:
                logger.info("复用卖点文案")
                selling_points = parse_selling_points(read_text_file(sp_md_path))
            self._emit_progress("selling_points", "completed", 50, "卖点完成")

        # 5. INS
        ins_path = product_output_dir / config.INSTAGRAM_FILE
        if "instagram" in self.required_steps:
            self._check_abort()
            if self._needs_run(ins_path, sp_md_path):
                logger.info("生成 Instagram 文案")
                generate_instagram(
                    self.text_adapter,
                    report,
                    title,
                    keywords,
                    read_text_file(sp_md_path),
                    ins_path,
                    self.templates,
                )
            else:
                logger.info("复用 Instagram 文案")
            self._emit_progress("instagram", "completed", 55, "INS 文案完成")

        # 图片阶段
        if "images" not in self.required_steps or self.max_images == 0:
            logger.info("跳过图片生成")
            self._emit_progress("images", "completed", 100, "文本内容全部完成")
            return

        self._check_abort()

        # 6. 参考图筛选
        refs = select_best_reference_images(image_paths)
        if len(refs) < config.REFERENCE_IMAGE_COUNT:
            logger.warning("有效参考图不足 3 张，尝试继续")

        refs_path = product_output_dir / config.BEST_REFERENCE_IMAGES_FILE
        write_json_file(refs_path, [r.filename for r in refs])

        self._check_abort()

        # 7. 产品上下文
        global_constraints = self.templates.load("image_global_constraints.txt")
        product_context = build_product_context(report, title, keywords, global_constraints)
        context_path = product_output_dir / config.PRODUCT_CONTEXT_FILE
        write_text_file(context_path, product_context)

        self._check_abort()

        # 8. 图片提示词
        prompts_path = product_output_dir / config.IMAGE_PROMPTS_FILE
        style_rules_text = self.templates.load("style_rules.txt")
        prompt_template = self.templates.load("image_prompt.txt")
        prompts = assemble_image_prompts(
            selling_points,
            style_rules_text,
            product_context,
            prompt_template,
            prompts_path,
        )

        # 9. 图片生成
        if self.overwrite or self.start_from:
            prompts_to_run = prompts
        else:
            prompts_to_run = [
                p for p in prompts
                if not (product_output_dir / p.filename).exists()
            ]

        self._emit_progress("images", "started", 60, "开始生成图片")
        if prompts_to_run:
            logger.info(f"将生成 {len(prompts_to_run)} 张图片")

            def _image_progress(completed: int, total: int, filename: str) -> None:
                progress = int(60 + (completed / total) * 35)
                self._emit_progress(
                    "images",
                    "in_progress",
                    progress,
                    f"生成图片 {completed}/{total}: {filename}",
                )

            generate_detail_images(
                self.image_adapter,
                prompts_to_run,
                refs,
                product_output_dir,
                max_images=self.max_images,
                start_from=self.start_from,
                delay=self.request_delay,
                progress_callback=_image_progress,
                abort_callback=self._check_abort,
            )
        else:
            logger.info("所有图片已存在，跳过图片生成")

        self._emit_progress("images", "completed", 100, "全部完成")
        logger.info(f"{product_input_dir.name} 处理完成")
