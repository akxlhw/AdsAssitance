"""模型适配器基类。"""

from abc import ABC, abstractmethod
from pathlib import Path

from coupangads.core.models import ImagePrompt, ReferenceImage


class TextAdapter(ABC):
    """文本生成适配器基类。"""

    @abstractmethod
    def chat(self, prompt: str) -> str:
        """发送单轮文本请求，返回模型回复字符串。"""
        ...


class ImageAdapter(ABC):
    """图片生成适配器基类。"""

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        references: list[ReferenceImage],
        output_path: Path,
    ) -> bool:
        """生成图片并保存到 output_path，返回是否成功。"""
        ...
