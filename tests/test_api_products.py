import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from coupangads.web.app import app

client = TestClient(app)


@pytest.fixture
def empty_dirs(monkeypatch, tmp_path):
    """使用临时 input/output 目录，避免污染仓库。"""
    from coupangads.core import config

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    monkeypatch.setattr(config, "DEFAULT_INPUT_DIR", input_dir)
    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", output_dir)
    yield input_dir, output_dir


@pytest.fixture
def empty_output_dir(monkeypatch, tmp_path):
    """使用临时 output 目录，避免污染仓库。"""
    from coupangads.core import config

    monkeypatch.setattr(config, "DEFAULT_OUTPUT_DIR", tmp_path)
    yield tmp_path


def test_list_products_empty(empty_output_dir) -> None:
    response = client.get("/api/products")
    assert response.status_code == 200
    assert response.json() == {"products": []}


def test_list_products_with_one_product(empty_output_dir) -> None:
    product_dir = empty_output_dir / "test-product"
    product_dir.mkdir()
    (product_dir / "report.md").write_text("report", encoding="utf-8")
    (product_dir / "image_01.png").write_bytes(b"fake png")

    created_at = datetime.now(timezone.utc).isoformat()
    status_data = {
        "status": "completed",
        "message": "已完成",
        "completed_steps": ["product_report", "title"],
        "created_at": created_at,
        "completed_at": created_at,
    }
    status_file = product_dir / ".status.json"
    status_file.write_text(json.dumps(status_data, ensure_ascii=False), encoding="utf-8")

    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) == 1
    product = data["products"][0]
    assert product["product_id"] == "test-product"
    assert product["status"] == "completed"
    assert product["text_count"] == 1
    assert product["image_count"] == 1
    assert product["progress"] == [True, True, True, True, True]
    assert product["thumbnail"] == "/api/result/test-product/image_01.png"


def test_delete_product(empty_dirs) -> None:
    input_dir, output_dir = empty_dirs
    (input_dir / "prod-a").mkdir(parents=True)
    (input_dir / "prod-a" / "img.png").write_bytes(b"img")
    (output_dir / "prod-a").mkdir(parents=True)
    (output_dir / "prod-a" / "report.md").write_text("report")

    response = client.delete("/api/products/prod-a")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert not (input_dir / "prod-a").exists()
    assert not (output_dir / "prod-a").exists()


def test_delete_product_not_found(empty_dirs) -> None:
    response = client.delete("/api/products/not-exist")
    assert response.status_code == 404


def test_rename_product(empty_dirs) -> None:
    input_dir, output_dir = empty_dirs
    (input_dir / "old-name").mkdir(parents=True)
    (input_dir / "old-name" / "img.png").write_bytes(b"img")
    (output_dir / "old-name").mkdir(parents=True)
    (output_dir / "old-name" / ".status.json").write_text(
        json.dumps({"product_id": "old-name", "status": "completed"}, ensure_ascii=False)
    )

    response = client.patch(
        "/api/products/old-name",
        json={"new_product_id": "new-name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "renamed"
    assert data["new_product_id"] == "new-name"
    assert (input_dir / "new-name" / "img.png").exists()
    assert (output_dir / "new-name" / ".status.json").exists()
    status = json.loads((output_dir / "new-name" / ".status.json").read_text())
    assert status["product_id"] == "new-name"


def test_rename_conflict(empty_dirs) -> None:
    input_dir, output_dir = empty_dirs
    (input_dir / "a").mkdir(parents=True)
    (input_dir / "b").mkdir(parents=True)
    response = client.patch("/api/products/a", json={"new_product_id": "b"})
    assert response.status_code == 409


def test_update_product(empty_dirs) -> None:
    input_dir, output_dir = empty_dirs
    (input_dir / "prod-x").mkdir(parents=True)
    (input_dir / "prod-x" / "keep.png").write_bytes(b"keep")
    (input_dir / "prod-x" / "remove.png").write_bytes(b"remove")

    response = client.put(
        "/api/products/prod-x",
        data={"keep_files": ["keep.png"]},
        files={"files": ("new.png", b"new", "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_product_id"] == "prod-x"
    assert (input_dir / "prod-x" / "keep.png").exists()
    assert not (input_dir / "prod-x" / "remove.png").exists()
    assert (input_dir / "prod-x" / "new.png").exists()


def test_update_product_rename(empty_dirs) -> None:
    input_dir, output_dir = empty_dirs
    (input_dir / "old").mkdir(parents=True)
    (input_dir / "old" / "img.png").write_bytes(b"img")
    (output_dir / "old").mkdir(parents=True)
    (output_dir / "old" / ".status.json").write_text(
        json.dumps({"product_id": "old", "status": "completed"}, ensure_ascii=False)
    )

    response = client.put(
        "/api/products/old",
        data={"product_name": "renamed", "keep_files": ["img.png"]},
    )
    assert response.status_code == 200
    assert response.json()["new_product_id"] == "renamed"
    assert (input_dir / "renamed" / "img.png").exists()
    status = json.loads((output_dir / "renamed" / ".status.json").read_text())
    assert status["product_id"] == "renamed"


def test_delete_result_file(empty_dirs) -> None:
    _, output_dir = empty_dirs
    (output_dir / "prod").mkdir(parents=True)
    (output_dir / "prod" / "report.md").write_text("report")

    response = client.delete("/api/result/prod/report.md")
    assert response.status_code == 200
    assert not (output_dir / "prod" / "report.md").exists()


def test_delete_result_file_not_found(empty_dirs) -> None:
    response = client.delete("/api/result/prod/missing.md")
    assert response.status_code == 404
