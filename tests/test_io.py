"""IO 工具单元测试。"""

import json
from pathlib import Path

import pytest

from coupangads.infra.io import read_text_file, write_text_file, write_json_file
from coupangads.infra.api_keys import read_api_key


def test_read_text_file_reads_utf8(tmp_path: Path) -> None:
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello 世界", encoding="utf-8")
    assert read_text_file(file_path) == "hello 世界"


def test_read_text_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_text_file(tmp_path / "missing.txt")


def test_write_text_file_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "file.md"
    write_text_file(target, "content")
    assert target.read_text(encoding="utf-8") == "content"


def test_write_json_file_formatted(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    write_json_file(target, {"a": 1})
    text = target.read_text(encoding="utf-8")
    assert json.loads(text) == {"a": 1}
    assert "\n" in text


def test_read_api_key_reads_first_non_empty_line(tmp_path: Path) -> None:
    key_file = tmp_path / "key.md"
    key_file.write_text("\n\nABC123\n\n", encoding="utf-8")
    assert read_api_key(key_file) == "ABC123"


def test_read_api_key_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "ENV_KEY")
    assert read_api_key(Path("nonexistent.md"), env_var="GEMINI_API_KEY") == "ENV_KEY"
