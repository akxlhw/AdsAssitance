"""ByteDance Doubao adapter."""

from pathlib import Path

import httpx
from openai import OpenAI

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.core import config
from coupangads.core.models import ReferenceImage
from coupangads.infra.image import image_to_data_url, load_image_rgb


class DoubaoClientAdapter(TextAdapter, ImageAdapter):
    """Doubao dual-mode adapter for text and image generation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        max_retries: int = config.DEFAULT_MAX_RETRIES,
        request_timeout: int = config.DEFAULT_REQUEST_TIMEOUT_MS,
        vision_model: str | None = None,
    ) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=request_timeout,
        )
        self.model_text = config.DOUBAO_TEXT_MODEL
        self.model_image = config.DOUBAO_IMAGE_MODEL
        self.model_vision = vision_model or config.DOUBAO_VISION_MODEL
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self._messages: list[dict] = []

    def chat(self, prompt: str) -> str:
        """Send a text request while maintaining message history."""
        self._messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model_text,
            messages=self._messages,
        )
        content = response.choices[0].message.content or ""
        self._messages.append({"role": "assistant", "content": content})
        return content

    def chat_with_images(self, prompt: str, image_paths: list[Path]) -> str:
        """Send a vision request with the configured Doubao vision model."""
        content: list[dict] = []
        for path in image_paths:
            img = load_image_rgb(path)
            data_url = image_to_data_url(img)
            content.append({"type": "image_url", "image_url": {"url": data_url}})
        content.append({"type": "text", "text": prompt})

        response = self.client.chat.completions.create(
            model=self.model_vision,
            messages=[{"role": "user", "content": content}],
        )
        return response.choices[0].message.content or ""

    def generate_image(
        self,
        prompt: str,
        references: list[ReferenceImage],
        output_path: Path,
    ) -> bool:
        """Call Doubao Seedream image generation API.

        Uses the dedicated /images/generations endpoint. Reference images are
        passed as base64 data URLs when available.
        """
        extra_body: dict = {
            "watermark": False,
            "sequential_image_generation": "disabled",
            "response_format": "url",
        }
        if references:
            image_urls = [
                ref.data_url or image_to_data_url(ref.image) for ref in references
            ]
            extra_body["image"] = image_urls if len(image_urls) > 1 else image_urls[0]

        response = self.client.images.generate(
            model=self.model_image,
            prompt=prompt,
            n=1,
            size="2K",
            response_format="url",
            extra_body=extra_body,
        )

        url = response.data[0].url if response.data else None
        if not url:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=self.request_timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
        return True
