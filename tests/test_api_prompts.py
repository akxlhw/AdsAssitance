from fastapi.testclient import TestClient

import pytest

from coupangads.text.template_loader import TemplateLoader
from coupangads.web import api
from coupangads.web.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_prompt_service(tmp_path, monkeypatch):
    """每个测试使用独立的模板目录与覆盖层，避免污染仓库。"""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text(
        "default report prompt", encoding="utf-8"
    )
    overrides_path = tmp_path / "prompt_overrides.json"
    monkeypatch.setattr(
        api, "_load_templates", lambda: TemplateLoader(templates_dir, overrides_path)
    )
    api.get_prompt_service.cache_clear()
    yield
    api.get_prompt_service.cache_clear()


def test_list_prompts() -> None:
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    names = {p["name"] for p in data}
    assert "product_report.txt" in names


def test_get_prompt() -> None:
    response = client.get("/api/prompts/product_report.txt")
    assert response.status_code == 200
    assert "content" in response.json()


def test_update_and_reset_prompt() -> None:
    response = client.put(
        "/api/prompts/product_report.txt",
        json={"content": "custom prompt"},
    )
    assert response.status_code == 200

    response = client.get("/api/prompts/product_report.txt")
    assert response.json()["content"] == "custom prompt"
    assert response.json()["is_overridden"] is True

    response = client.delete("/api/prompts/product_report.txt")
    assert response.status_code == 200

    response = client.get("/api/prompts/product_report.txt")
    assert response.json()["is_overridden"] is False


def test_update_unknown_prompt() -> None:
    response = client.put("/api/prompts/unknown.txt", json={"content": "x"})
    assert response.status_code == 404


def test_get_unknown_prompt() -> None:
    response = client.get("/api/prompts/unknown.txt")
    assert response.status_code == 404


def test_update_prompt_empty_content() -> None:
    response = client.put("/api/prompts/product_report.txt", json={"content": ""})
    assert response.status_code == 400

    response = client.put(
        "/api/prompts/product_report.txt", json={"content": "   "}
    )
    assert response.status_code == 400


def test_delete_unknown_prompt() -> None:
    response = client.delete("/api/prompts/unknown.txt")
    assert response.status_code == 404


def test_get_prompt_missing_template_file() -> None:
    """已注册但默认模板文件缺失时返回 404。"""
    response = client.get("/api/prompts/product_title.txt")
    assert response.status_code == 404
    assert "模板文件不存在" in response.json()["detail"]


def test_update_prompt_persistence_failure(monkeypatch) -> None:
    """覆盖层持久化失败时返回 500。"""
    loader = api.get_prompt_service()._loader
    original_persist = loader._persist_overrides

    def _raise_oserror() -> None:
        raise OSError("disk full")

    monkeypatch.setattr(loader, "_persist_overrides", _raise_oserror)
    try:
        response = client.put(
            "/api/prompts/product_report.txt",
            json={"content": "custom prompt"},
        )
        assert response.status_code == 500
        assert "持久化 Prompt 覆盖失败" in response.json()["detail"]
    finally:
        monkeypatch.setattr(loader, "_persist_overrides", original_persist)


def test_history_snapshot_on_update() -> None:
    """二次 PUT 应在 history 目录留下前一次覆盖的快照。"""
    # 第一次 PUT（无当前覆盖 → 不留快照）
    r = client.put(
        "/api/prompts/product_report.txt",
        json={"content": "v1"},
    )
    assert r.status_code == 200
    assert client.get("/api/prompts/product_report.txt/history").json() == []

    # 第二次 PUT（v1 → v2，应快照 v1）
    r = client.put(
        "/api/prompts/product_report.txt",
        json={"content": "v2"},
    )
    assert r.status_code == 200
    history = client.get("/api/prompts/product_report.txt/history").json()
    assert len(history) == 1
    snapshot = history[0]
    assert snapshot["size"] == 2  # "v1"

    # 读取快照内容
    r = client.get(
        f"/api/prompts/product_report.txt/history/{snapshot['id']}"
    )
    assert r.status_code == 200
    assert r.json()["content"] == "v1"


def test_history_restore() -> None:
    """restore 应把快照内容写回当前覆盖，并把当前覆盖另存为新快照。"""
    client.put("/api/prompts/product_report.txt", json={"content": "v1"})
    client.put("/api/prompts/product_report.txt", json={"content": "v2"})
    history = client.get("/api/prompts/product_report.txt/history").json()
    snapshot_id = history[0]["id"]

    r = client.post(
        f"/api/prompts/product_report.txt/history/{snapshot_id}/restore"
    )
    assert r.status_code == 200
    # 当前覆盖应回到 v1
    assert client.get("/api/prompts/product_report.txt").json()["content"] == "v1"
    # v2 应作为新快照出现
    new_history = client.get("/api/prompts/product_report.txt/history").json()
    assert len(new_history) == 2


def test_history_not_found() -> None:
    """未知快照返回 404。"""
    client.put("/api/prompts/product_report.txt", json={"content": "x"})
    r = client.post("/api/prompts/product_report.txt/history/nonexistent/restore")
    assert r.status_code == 404


def test_history_unknown_prompt() -> None:
    """未知 prompt 调用 history 接口返回 404。"""
    assert client.get("/api/prompts/unknown.txt/history").status_code == 404


def test_preview_image_prompt(tmp_path) -> None:
    """image_prompt.txt 的 preview 返回渲染后的样本。"""
    # 准备模板文件
    templates_dir = api.get_prompt_service()._loader.templates_dir
    (templates_dir / "image_prompt.txt").write_text(
        "STYLE={style_rules} CTX={product_context} SCREEN={screen} "
        "BLOCK={block} CONTENT={block_content}",
        encoding="utf-8",
    )
    (templates_dir / "image_global_constraints.txt").write_text(
        "GLOBAL", encoding="utf-8"
    )
    (templates_dir / "style_rules.txt").write_text(
        "## A 风格\n红色\n## B 风格\n蓝色", encoding="utf-8"
    )
    api.get_prompt_service.cache_clear()

    r = client.post("/api/prompts/image_prompt.txt/preview", json={})
    assert r.status_code == 200
    body = r.json()
    assert "rendered" in body
    # 没有产品数据时仍能渲染出样本
    assert "STYLE=" in body["rendered"]


def test_preview_unknown_prompt() -> None:
    """未知 prompt 的 preview 返回 404。"""
    r = client.post("/api/prompts/unknown.txt/preview", json={})
    assert r.status_code == 404
