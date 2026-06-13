import json
from pathlib import Path

import pytest

from coupangads.text.template_loader import TemplateLoader


def test_load_default_template(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default prompt", encoding="utf-8")

    loader = TemplateLoader(templates_dir=templates_dir)
    assert loader.load("product_report.txt") == "default prompt"


def test_override_takes_precedence(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default prompt", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(json.dumps({"product_report.txt": "override prompt"}, ensure_ascii=False), encoding="utf-8")

    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)
    assert loader.load("product_report.txt") == "override prompt"


def test_save_and_reset_override(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default prompt", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)

    loader.save_override("product_report.txt", "override prompt")
    assert loader.load("product_report.txt") == "override prompt"
    data = json.loads(overrides_path.read_text(encoding="utf-8"))
    assert data["product_report.txt"] == "override prompt"

    loader.reset_override("product_report.txt")
    assert loader.load("product_report.txt") == "default prompt"
    data = json.loads(overrides_path.read_text(encoding="utf-8"))
    assert "product_report.txt" not in data


def test_corrupt_override_file_is_backed_up_and_returns_defaults(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default prompt", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text("this is not json", encoding="utf-8")

    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)
    assert loader.load("product_report.txt") == "default prompt"
    assert not overrides_path.exists()

    backups = list(tmp_path.glob("overrides.json.bak.*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "this is not json"


def test_non_dict_override_file_is_backed_up_and_returns_defaults(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default prompt", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(json.dumps(["list", "not", "dict"], ensure_ascii=False), encoding="utf-8")

    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)
    assert loader.load("product_report.txt") == "default prompt"
    assert not overrides_path.exists()

    backups = list(tmp_path.glob("overrides.json.bak.*"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == ["list", "not", "dict"]


def test_is_overridden(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "a.txt").write_text("a", encoding="utf-8")
    (templates_dir / "b.txt").write_text("b", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(json.dumps({"a.txt": "override a"}, ensure_ascii=False), encoding="utf-8")

    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)
    assert loader.is_overridden("a.txt") is True
    assert loader.is_overridden("b.txt") is False


@pytest.mark.parametrize("content", ["", "   ", "\n\t"])
def test_save_empty_or_whitespace_content_raises_value_error(tmp_path: Path, content: str) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default prompt", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)

    with pytest.raises(ValueError, match="不能为空字符串"):
        loader.save_override("product_report.txt", content)


def test_non_string_values_in_override_file_are_backed_up_and_return_defaults(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default prompt", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(json.dumps({"product_report.txt": ["not", "a", "string"]}, ensure_ascii=False), encoding="utf-8")

    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)
    assert loader.load("product_report.txt") == "default prompt"
    assert not overrides_path.exists()

    backups = list(tmp_path.glob("overrides.json.bak.*"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == {"product_report.txt": ["not", "a", "string"]}


@pytest.mark.parametrize("name", ["", "   ", "\n\t", 123, None])
def test_reset_override_invalid_name_raises_value_error(tmp_path: Path, name) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("default prompt", encoding="utf-8")

    overrides_path = tmp_path / "overrides.json"
    loader = TemplateLoader(templates_dir=templates_dir, overrides_path=overrides_path)

    with pytest.raises(ValueError, match="必须是非空字符串"):
        loader.reset_override(name)
