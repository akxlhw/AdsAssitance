"""模板加载与 Prompt 组装。"""

import json
from pathlib import Path

from coupangads.infra.io import read_text_file


class TemplateLoader:
    """从 templates/ 目录加载提示词模板，支持 config/prompt_overrides.json 覆盖。"""

    def __init__(
        self,
        templates_dir: Path = Path("templates"),
        overrides_path: Path = Path("config/prompt_overrides.json"),
    ) -> None:
        self.templates_dir = templates_dir
        self.overrides_path = overrides_path
        self._overrides = self._load_overrides()

    def _load_overrides(self) -> dict[str, str]:
        if not self.overrides_path.exists():
            return {}
        try:
            data = json.loads(self.overrides_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            return {str(k): str(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def load(self, name: str) -> str:
        """加载指定模板文件；若存在覆盖层则优先返回覆盖内容。"""
        if name in self._overrides:
            return self._overrides[name]
        return read_text_file(self.templates_dir / name)

    def is_overridden(self, name: str) -> bool:
        return name in self._overrides

    def save_override(self, name: str, content: str) -> None:
        """保存用户自定义模板到覆盖层。"""
        self._overrides[name] = content
        self._persist_overrides()

    def reset_override(self, name: str) -> None:
        """删除覆盖层，恢复默认模板。"""
        self._overrides.pop(name, None)
        self._persist_overrides()

    def _persist_overrides(self) -> None:
        self.overrides_path.parent.mkdir(parents=True, exist_ok=True)
        self.overrides_path.write_text(
            json.dumps(self._overrides, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def assemble_text_prompt(template: str, **kwargs: str) -> str:
    """使用 str.format 将变量填充到模板中。"""
    return template.format(**kwargs)


def assemble_image_prompt(
    template: str,
    style_rules: str,
    product_context: str,
    screen: str,
    block: str,
    block_content: str,
) -> str:
    """组装单张图片生成提示词。"""
    return template.format(
        style_rules=style_rules,
        product_context=product_context,
        screen=screen,
        block=block,
        block_content=block_content,
    )
