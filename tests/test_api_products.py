import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from coupangads.web.app import app

client = TestClient(app)


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
