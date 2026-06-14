"""离线 mock 适配器，用于无 API 额度时的开发和 UI 测试。

可通过环境变量模拟真实 API 行为：
- COUPANGADS_MOCK_IMAGE_DELAY：每张图等待秒数（默认 0）
- COUPANGADS_MOCK_TEXT_DELAY：每个文本步骤等待秒数（默认 0）
- COUPANGADS_MOCK_IMAGE_FAIL_RATE：随机失败率 0~1（默认 0）
- COUPANGADS_MOCK_IMAGE_HANG_RATE：随机卡死率 0~1（默认 0）
  卡死模式会等待远超 pipeline 超时的时长，用于触发 timeout 路径
"""

import hashlib
import os
import random
import time
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.core import config
from coupangads.core.models import ImagePrompt, ReferenceImage


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _chunked_sleep(total_sec: float, chunk: float = 0.5) -> None:
    """按 chunk 切片 sleep，避免单次长 sleep 阻塞线程池回收。

    hang 模式下也用这个：pipeline 层的 timeout 会在 worker thread 外
    通过 fut.result(timeout=...) 放弃等待，本线程睡多久都不阻塞主流程。
    """
    if total_sec <= 0:
        return
    remaining = total_sec
    while remaining > 0:
        step = min(chunk, remaining)
        time.sleep(step)
        remaining -= step


class MockTextAdapter(TextAdapter):
    """返回确定性占位文本，不调用任何真实 API。"""

    def __init__(self, delay_sec: float | None = None) -> None:
        # delay_sec 显式入参优先；否则读环境变量；最后回退到 config 默认
        self.delay_sec = (
            delay_sec if delay_sec is not None
            else _env_float("COUPANGADS_MOCK_TEXT_DELAY", config.MOCK_TEXT_DELAY_SEC)
        )

    def _simulate_latency(self) -> None:
        """模拟文本 API 延迟，按 0.5s 步进以便 abort 能尽快响应。"""
        if self.delay_sec <= 0:
            return
        _chunked_sleep(self.delay_sec, chunk=0.5)

    def chat(self, prompt: str) -> str:
        """根据 prompt 类型返回固定模板内容。"""
        self._simulate_latency()
        prompt_lower = prompt.lower()
        if "标题" in prompt or "title" in prompt_lower:
            return self._fake_title(prompt)
        if "关键词" in prompt or "keyword" in prompt_lower or "wing" in prompt_lower:
            return self._fake_keywords(prompt)
        if "卖点" in prompt or "selling" in prompt_lower:
            return self._fake_selling_points(prompt)
        if "instagram" in prompt_lower or "ins" in prompt_lower or "社交" in prompt:
            return self._fake_instagram(prompt)
        return self._fake_generic(prompt)

    def chat_with_images(self, prompt: str, image_paths: list[Path]) -> str:
        """返回伪造的商品画像报告。"""
        self._simulate_latency()
        count = len(image_paths)
        return f"""# 商品画像报告（Mock）

## 基础信息
- 图片数量：{count} 张
- 分析状态：离线开发模式生成

## 视觉观察
从上传的 {count} 张产品图可以看出，这是一款宠物用品。产品整体设计感良好，
适合韩国市场审美。图片光线充足，主体清晰，建议用于详情页主图和场景图。

## 核心卖点（Mock）
1. 材质安全舒适，适合宠物长时间使用
2. 设计简洁高级，符合韩系极简风格
3. 功能实用，解决养宠日常痛点
4. 尺寸合理，适配多数宠物体型

## 目标客群
25-40 岁都市养宠人群，注重产品颜值与实用性。

## 建议风格
韩系高级宠物品牌广告、真实摄影感、温暖治愈、杂志级排版。
"""

    def _seed(self, prompt: str) -> str:
        """生成稳定的伪随机种子文本。"""
        h = hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8]
        return h.upper()

    def _fake_title(self, prompt: str) -> str:
        seed = self._seed(prompt)
        return f"""# 商品标题（Mock）

[MOCK-{seed}] 韩国高端宠物用品 舒适耐用 狗狗猫咪通用 居家外出必备
"""

    def _fake_keywords(self, prompt: str) -> str:
        seed = self._seed(prompt)
        return f"""# 关键词（Mock）

[MOCK-{seed}]

- 核心词：펫용품, 강아지용품, 고양이용품
- 属性词：고급, 편안한, 내구성
- 场景词：집, 외출, 데일리
- 功能词：안전, 실용, 미니멀
"""

    def _fake_selling_points(self, prompt: str) -> str:
        seed = self._seed(prompt)
        return f"""# 卖点文案（Mock）

## B1 主视觉氛围
[MOCK-{seed}] 第一眼的高级感，从极简设计开始

## B2 核心功能
精选材质，安全无刺激，给宠物更舒适的体验

## B3 使用场景
居家休闲与外出散步都能轻松搭配

## B4 细节工艺
每一个细节都经过打磨，耐用且易于清洁

## B5 用户痛点
解决宠物用品常见的不适、易脏、不耐用问题

## B6 情感价值
让宠物和主人都能享受更有品质的生活

## B7 品牌调性
韩系极简，温暖治愈，杂志级视觉

## B8 尺寸适配
适合大多数犬猫体型，佩戴自然

## B9 购买理由
高性价比、高颜值、高实用性

---

```json
{{
  "B1": "[MOCK-{seed}] 第一眼的高级感，从极简设计开始",
  "B2": "精选材质，安全无刺激，给宠物更舒适的体验",
  "B3": "居家休闲与外出散步都能轻松搭配",
  "B4": "每一个细节都经过打磨，耐用且易于清洁",
  "B5": "解决宠物用品常见的不适、易脏、不耐用问题",
  "B6": "让宠物和主人都能享受更有品质的生活",
  "B7": "韩系极简，温暖治愈，杂志级视觉",
  "B8": "适合大多数犬猫体型，佩戴自然",
  "B9": "高性价比、高颜值、高实用性"
}}
```
"""

    def _fake_instagram(self, prompt: str) -> str:
        seed = self._seed(prompt)
        return f"""# Instagram 文案（Mock）

[MOCK-{seed}]

✨ 给毛孩子的精致日常

简约不等于简单
每一处设计都为了更舒适的使用体验

🐾 适合狗狗和猫咪
🐾 韩系极简风格
🐾 居家外出都好看

#펫용품 #강아지용품 #고양이용품 #반려동물 #펫스타그램
"""

    def _fake_generic(self, prompt: str) -> str:
        seed = self._seed(prompt)
        return f"""# 生成结果（Mock）

[MOCK-{seed}] 这是离线开发模式返回的占位内容。

Prompt 摘要：{prompt[:80]}...

实际部署时请切换为真实 provider（Gemini / Doubao / DeepSeek）。
"""


class MockImageAdapter(ImageAdapter):
    """使用 PIL 绘制占位图片，不调用任何真实 API。"""

    # 每个 style 对应一个背景色
    STYLE_COLORS: dict[str, tuple[int, int, int]] = {
        "A": (245, 245, 240),
        "B": (250, 248, 240),
    }
    STYLE_ACCENT: dict[str, tuple[int, int, int]] = {
        "A": (30, 30, 30),
        "B": (200, 160, 120),
    }

    def __init__(
        self,
        delay_sec: float | None = None,
        fail_rate: float | None = None,
        hang_rate: float | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.delay_sec = (
            delay_sec if delay_sec is not None
            else _env_float("COUPANGADS_MOCK_IMAGE_DELAY", config.MOCK_IMAGE_DELAY_SEC)
        )
        self.fail_rate = (
            fail_rate if fail_rate is not None
            else _env_float("COUPANGADS_MOCK_IMAGE_FAIL_RATE", config.MOCK_IMAGE_FAIL_RATE)
        )
        self.hang_rate = (
            hang_rate if hang_rate is not None
            else _env_float("COUPANGADS_MOCK_IMAGE_HANG_RATE", config.MOCK_IMAGE_HANG_RATE)
        )
        # 稳定 rng 便于复现；外部可注入
        self._rng = rng or random.Random()

    def generate_image(
        self,
        prompt: str,
        references: list[ReferenceImage],
        output_path: Path,
    ) -> bool:
        """绘制一张 2:3 占位图并保存。

        行为由 __init__ 参数 / 环境变量控制：
        - delay_sec：每张图等待时间
        - fail_rate：随机失败概率（返回 False）
        - hang_rate：随机卡死概率（睡 1 小时，让 pipeline 超时接管）
        """
        # 卡死分支：用远超 pipeline 超时的睡眠模拟无响应
        if self.hang_rate > 0 and self._rng.random() < self.hang_rate:
            _chunked_sleep(3600, chunk=1.0)
            raise TimeoutError(f"Mock hang triggered for {output_path.name}")

        # 正常延迟：按 chunk 切，让 abort_callback 有机会介入
        _chunked_sleep(self.delay_sec, chunk=0.5)

        # 随机失败
        if self.fail_rate > 0 and self._rng.random() < self.fail_rate:
            raise RuntimeError(f"Mock random failure for {output_path.name}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 默认 2:3 比例，与配置一致
        width, height = 1200, 1800

        # 从 prompt 或 filename 推断 style code
        style_code = self._extract_style(prompt, output_path.name)
        bg_color = self.STYLE_COLORS.get(style_code, (245, 245, 245))
        accent_color = self.STYLE_ACCENT.get(style_code, (80, 80, 80))

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # 画一个简洁边框
        margin = 80
        draw.rectangle(
            [margin, margin, width - margin, height - margin],
            outline=accent_color,
            width=8,
        )

        # 写文字
        try:
            # 尝试使用系统默认字体
            font_large = ImageFont.truetype("arial.ttf", 80)
            font_small = ImageFont.truetype("arial.ttf", 40)
        except Exception:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # 标题：风格 + 文件名
        title = f"{style_code} | {output_path.stem}"
        draw.text(
            (width // 2, height // 3),
            title,
            fill=accent_color,
            font=font_large,
            anchor="mm",
        )

        # Mock 标记
        draw.text(
            (width // 2, height // 2),
            "MOCK IMAGE",
            fill=accent_color,
            font=font_large,
            anchor="mm",
        )

        # 提示词摘要
        short_prompt = prompt[:80].replace("\n", " ") + "..."
        # 按宽度简单换行
        lines = self._wrap_text(draw, short_prompt, font_small, width - 2 * margin - 80)
        y = height * 2 // 3
        for line in lines[:6]:
            draw.text((width // 2, y), line, fill=accent_color, font=font_small, anchor="mm")
            y += 60

        img.save(output_path, "PNG")
        return True

    def _extract_style(self, prompt: str, filename: str) -> str:
        """从文件名或 prompt 中提取风格代码，默认 A。"""
        if filename.startswith("A_"):
            return "A"
        if filename.startswith("B_"):
            return "B"
        if "STYLE A" in prompt or "## STYLE A" in prompt:
            return "A"
        if "STYLE B" in prompt or "## STYLE B" in prompt:
            return "B"
        return "A"

    def _wrap_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list[str]:
        """简单文本换行。"""
        words = text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width or not current:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines if lines else [text]
