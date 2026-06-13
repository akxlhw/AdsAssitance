"""测试前端页面路由返回 index.html。"""

from fastapi.testclient import TestClient

from coupangads.web.app import app

client = TestClient(app)


def test_index_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "CoupangAds" in response.text


def test_create_page() -> None:
    response = client.get("/create")
    assert response.status_code == 200
    assert "upload-state" in response.text


def test_progress_page() -> None:
    response = client.get("/progress/test-product")
    assert response.status_code == 200
    assert "progress-state" in response.text


def test_result_page() -> None:
    response = client.get("/result/test-product")
    assert response.status_code == 200
    assert "result-state" in response.text
