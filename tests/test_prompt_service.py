from pathlib import Path

import pytest

from coupangads.text.prompt_service import PromptMeta, PromptService
from coupangads.text.template_loader import TemplateLoader


@pytest.fixture
def service(tmp_path: Path) -> PromptService:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default", encoding="utf-8")
    (templates_dir / "product_title.txt").write_text("default title", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)
    return PromptService(loader)


def test_list_prompts(service: PromptService) -> None:
    prompts = service.list_prompts()
    names = {p["name"] for p in prompts}
    assert "product_report" in names
    assert "product_title" in names


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
