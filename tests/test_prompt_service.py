from pathlib import Path

import pytest

from coupangads.text.prompt_service import PromptMeta, PromptService
from coupangads.text.template_loader import TemplateLoader


@pytest.fixture
def service(tmp_path: Path) -> PromptService:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template_files = [
        "product_report.txt",
        "product_title.txt",
        "wing_keywords.txt",
        "selling_points.txt",
        "instagram.txt",
        "image_prompt.txt",
        "image_global_constraints.txt",
        "style_rules.txt",
    ]
    for filename in template_files:
        (templates_dir / filename).write_text("default", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)
    return PromptService(loader)


def test_list_prompts(service: PromptService) -> None:
    prompts = service.list_prompts()
    names = {p["name"] for p in prompts}
    assert "product_report.txt" in names
    assert "product_title.txt" in names


def test_get_prompt_default(service: PromptService) -> None:
    assert service.get_prompt("product_report") == "default"


def test_update_and_get_prompt(service: PromptService) -> None:
    service.update_prompt("product_report", "custom")
    assert service.get_prompt("product_report") == "custom"
    assert service.is_overridden("product_report") is True


def test_reset_prompt(service: PromptService) -> None:
    service.update_prompt("product_report", "custom")
    service.reset_prompt("product_report")
    assert service.get_prompt("product_report") == "default"
    assert service.is_overridden("product_report") is False


def test_unknown_prompt_raises(service: PromptService) -> None:
    with pytest.raises(KeyError):
        service.get_prompt("unknown.txt")


def test_update_unknown_prompt_raises(service: PromptService) -> None:
    with pytest.raises(KeyError):
        service.update_prompt("unknown", "x")


def test_reset_unknown_prompt_raises(service: PromptService) -> None:
    with pytest.raises(KeyError):
        service.reset_prompt("unknown")


def test_update_prompt_empty_content_raises(service: PromptService) -> None:
    for content in ("", "   ", "\n\t"):
        with pytest.raises(ValueError):
            service.update_prompt("product_report", content)


def test_suffix_normalization(service: PromptService) -> None:
    service.update_prompt("product_report.txt", "custom")
    assert service.get_prompt("product_report") == "custom"
    assert service.is_overridden("product_report.txt") is True
    service.reset_prompt("product_report")
    assert service.get_prompt("product_report.txt") == "default"


def test_is_overridden_initially_false(service: PromptService) -> None:
    assert service.is_overridden("product_report") is False


def test_is_overridden_unknown_raises(service: PromptService) -> None:
    with pytest.raises(KeyError):
        service.is_overridden("unknown")


def test_prompt_meta_attribute_and_dict_access() -> None:
    meta = PromptMeta(
        name="test",
        label="测试",
        description="测试描述",
        variables=["a", "b"],
        is_overridden=False,
    )
    assert meta.name == "test"
    assert meta["label"] == "测试"
    assert meta["variables"] == ["a", "b"]
    with pytest.raises(KeyError):
        _ = meta["unknown"]
