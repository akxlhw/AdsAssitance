import json
from pathlib import Path

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
