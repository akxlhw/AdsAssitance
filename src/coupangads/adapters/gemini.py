"""Google Gemini 适配器。"""

from pathlib import Path

from google import genai
from google.genai import types

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.core import config
from coupangads.core.models import ReferenceImage


class GeminiClientAdapter(TextAdapter, ImageAdapter):
    """Gemini 双线路适配器：文本用对话模式，图片用独立请求模式。"""

    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model_text = config.GEMINI_TEXT_MODEL
        self.model_image = config.GEMINI_IMAGE_MODEL
        self._chat = None

    def _ensure_chat(self) -> None:
        if self._chat is None:
            self._chat = self.client.chats.create(model=self.model_text)

    def chat(self, prompt: str) -> str:
        """使用对话模式发送文本请求。"""
        self._ensure_chat()
        response = self._chat.send_message(prompt)
        return response.text or ""

    def generate_image(
        self,
        prompt: str,
        references: list[ReferenceImage],
        output_path: Path,
    ) -> bool:
        """独立请求生成图片，每次携带完整提示词和参考图。"""
        contents: list[types.Content] = []

        for ref in references:
            contents.append(ref.image)

        contents.append(prompt)

        response = self.client.models.generate_content(
            model=self.model_image,
            contents=contents,
        )

        if not response.candidates:
            return False

        for part in response.candidates[0].content.parts or []:
            if part.inline_data:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                return True

        return False
