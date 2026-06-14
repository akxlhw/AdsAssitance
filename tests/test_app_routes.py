"""测试前端页面路由返回 SPA shell（所有路由都返回同一个 index.html）。"""

from fastapi.testclient import TestClient

from coupangads.web.app import app

client = TestClient(app)


def test_index_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "CoupangAds" in response.text


def test_create_page() -> None:
    """所有路由都返回 SPA shell；具体内容由前端 workspace.setMode 决定。"""
    response = client.get("/create")
    assert response.status_code == 200
    assert "workspace-view" in response.text
    assert "main.js" in response.text


def test_progress_page() -> None:
    response = client.get("/progress/test-product")
    assert response.status_code == 200
    assert "workspace-view" in response.text


def test_result_page() -> None:
    response = client.get("/result/test-product")
    assert response.status_code == 200
    assert "workspace-view" in response.text
