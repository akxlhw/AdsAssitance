"""字节 Doubao 适配器。"""

from pathlib import Path

from openai import OpenAI

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.core import config
from coupangads.core.models import ReferenceImage
from coupangads.infra.image import image_to_data_url


class DoubaoClientAdapter(TextAdapter, ImageAdapter):
    """Doubao 双线路适配器。"""

    def __init__(self, api_key: str, base_url: str = "https://ark.cn-beijing.volces.com/api/v3") -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_text = config.DOUBAO_TEXT_MODEL
        self.model_image = config.DOUBAO_IMAGE_MODEL
        self._messages: list[dict] = []

    def chat(self, prompt: str) -> str:
        """手动维护消息历史并发送文本请求。"""
        self._messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model_text,
            messages=self._messages,
        )
        content = response.choices[0].message.content or ""
        self._messages.append({"role": "assistant", "content": content})
        return content

    def generate_image(
        self,
        prompt: str,
        references: list[ReferenceImage],
        output_path: Path,
    ) -> bool:
        """调用 Doubao 图像生成 API。"""
        content: list[dict] = [{"type": "text", "text": prompt}]
        for ref in references:
            data_url = ref.data_url or image_to_data_url(ref.image)
            content.append({"type": "image_url", "image_url": {"url": data_url}})

        response = self.client.chat.completions.create(
            model=self.model_image,
            messages=[{"role": "user", "content": content}],
        )

        message = response.choices[0].message
        if message.content:
            # Doubao seedream 可能返回 base64 图片数据
            import base64
            import re

            b64_match = re.search(r"data:image/\w+;base64,([A-Za-z0-9+/=]+)", message.content)
            if b64_match:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(base64.b64decode(b64_match.group(1)))
                return True

        return False
