"""Prompt 管理服务：封装 TemplateLoader，提供业务级读写接口。"""

from dataclasses import dataclass

from coupangads.text.template_loader import TemplateLoader


PROMPT_REGISTRY: dict[str, dict[str, list[str] | str]] = {
    "product_report.txt": {
        "label": "商品画像",
        "description": "基于实拍图输出结构化商品画像报告",
        "variables": ["image_count"],
    },
    "product_title.txt": {
        "label": "标题",
        "description": "生成适配 Coupang 的韩文商品标题变体",
        "variables": ["product_report"],
    },
    "wing_keywords.txt": {
        "label": "关键词",
        "description": "构建三层关键词矩阵并给出蓝海词推荐",
        "variables": ["product_report", "product_title"],
    },
    "selling_points.txt": {
        "label": "卖点文案",
        "description": "按 B1-B9 结构生成详情页卖点文案",
        "variables": ["product_report", "product_title", "wing_keywords"],
    },
    "instagram.txt": {
        "label": "INS 文案",
        "description": "生成韩国 Instagram 种草文案（含 Hashtag）",
        "variables": ["product_report", "product_title", "wing_keywords", "selling_points"],
    },
    "image_prompt.txt": {
        "label": "图片生成 Prompt",
        "description": "为单张详情页图片生成英文 Image Generation 提示词",
        "variables": ["style_rules", "product_context", "screen", "block", "block_content"],
    },
    "image_global_constraints.txt": {
        "label": "图片全局约束",
        "description": "所有图片必须遵守的全局约束",
        "variables": [],
    },
    "style_rules.txt": {
        "label": "风格规则",
        "description": "图片风格与场景规则库",
        "variables": [],
    },
}


@dataclass(frozen=True)
class PromptMeta:
    name: str
    label: str
    description: str
    variables: list[str]
    is_overridden: bool

    def __getitem__(self, key: str):
        """支持以字典方式访问字段，便于序列化与模板渲染。"""
        return self.__dict__[key]


class PromptService:
    def __init__(self, loader: TemplateLoader) -> None:
        self._loader = loader

    @staticmethod
    def _canonical_name(name: str) -> str:
        """将业务名称统一为带 .txt 后缀的注册表键。"""
        return name if name.endswith(".txt") else f"{name}.txt"

    @staticmethod
    def _display_name(name: str) -> str:
        """将注册表键转换为业务展示名称（去掉 .txt 后缀）。"""
        return name[:-4] if name.endswith(".txt") else name

    def list_prompts(self) -> list[PromptMeta]:
        """列出所有已注册 Prompt 的元信息，包括变量与覆盖状态。"""
        result = []
        for name, meta in PROMPT_REGISTRY.items():
            result.append(
                PromptMeta(
                    name=self._display_name(name),
                    label=meta["label"],
                    description=meta["description"],
                    variables=meta["variables"],
                    is_overridden=self._loader.is_overridden(name),
                )
            )
        return result

    def get_prompt(self, name: str) -> str:
        """加载指定 Prompt 的模板内容；存在覆盖层时优先返回覆盖内容。"""
        canonical = self._canonical_name(name)
        if canonical not in PROMPT_REGISTRY:
            raise KeyError(f"Unknown prompt: {name}")
        return self._loader.load(canonical)

    def update_prompt(self, name: str, content: str) -> None:
        """更新指定 Prompt 的内容并持久化到覆盖层；未知 Prompt 会抛出 KeyError。"""
        canonical = self._canonical_name(name)
        if canonical not in PROMPT_REGISTRY:
            raise KeyError(f"Unknown prompt: {name}")
        self._loader.save_override(canonical, content)

    def reset_prompt(self, name: str) -> None:
        """重置指定 Prompt 为默认模板；未知 Prompt 会抛出 KeyError。"""
        canonical = self._canonical_name(name)
        if canonical not in PROMPT_REGISTRY:
            raise KeyError(f"Unknown prompt: {name}")
        self._loader.reset_override(canonical)

    def is_overridden(self, name: str) -> bool:
        """返回指定 Prompt 是否被覆盖；未知 Prompt 会抛出 KeyError。"""
        canonical = self._canonical_name(name)
        if canonical not in PROMPT_REGISTRY:
            raise KeyError(f"Unknown prompt: {name}")
        return self._loader.is_overridden(canonical)
