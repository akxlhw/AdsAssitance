"""模板加载与 Prompt 组装。"""

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path

from coupangads.core.logging import get_logger
from coupangads.infra.io import read_text_file


logger = get_logger(__name__)


class TemplateLoader:
    """从 templates/ 目录加载提示词模板，支持 config/prompt_overrides.json 覆盖。"""

    def __init__(
        self,
        templates_dir: Path = Path("templates"),
        overrides_path: Path = Path("config/prompt_overrides.json"),
    ) -> None:
        self.templates_dir = templates_dir
        self.overrides_path = overrides_path
        self._lock = threading.Lock()
        self._overrides = self._load_overrides()

    def _load_overrides(self) -> dict[str, str]:
        """加载覆盖层文件；文件损坏时自动备份并返回空字典。"""
        if not self.overrides_path.exists():
            return {}

        try:
            data = json.loads(self.overrides_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning(
                "覆盖配置文件 JSON 损坏，已备份并忽略: %s (%s)",
                self.overrides_path,
                exc,
            )
            self._backup_corrupt_override_file()
            return {}
        except OSError as exc:
            logger.warning(
                "无法读取覆盖配置文件: %s (%s)",
                self.overrides_path,
                exc,
            )
            return {}

        if not isinstance(data, dict):
            logger.warning(
                "覆盖配置文件内容应为对象，已备份并忽略: %s",
                self.overrides_path,
            )
            self._backup_corrupt_override_file()
            return {}

        validated: dict[str, str] = {}
        for key, value in data.items():
            if not isinstance(value, str):
                logger.warning(
                    "覆盖配置文件包含非字符串值，已备份并忽略: %s "
                    "(key=%r, type=%s)",
                    self.overrides_path,
                    key,
                    type(value).__name__,
                )
                self._backup_corrupt_override_file()
                return {}
            validated[key] = value
        return validated

    def _backup_corrupt_override_file(self) -> None:
        """将损坏的覆盖文件重命名为带时间戳的备份。"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        backup_path = self.overrides_path.parent / (
            f"{self.overrides_path.name}.bak.{timestamp}"
        )
        counter = 1
        while backup_path.exists():
            backup_path = self.overrides_path.parent / (
                f"{self.overrides_path.name}.bak.{timestamp}.{counter}"
            )
            counter += 1
        try:
            os.replace(self.overrides_path, backup_path)
        except OSError as exc:
            logger.warning(
                "备份损坏的覆盖配置文件失败: %s -> %s (%s)",
                self.overrides_path,
                backup_path,
                exc,
            )

    def load(self, name: str) -> str:
        """加载指定模板文件；若存在覆盖层则优先返回覆盖内容。"""
        with self._lock:
            override = self._overrides.get(name)
        if override is not None:
            return override
        return read_text_file(self.templates_dir / name)

    def is_overridden(self, name: str) -> bool:
        with self._lock:
            return name in self._overrides

    def save_override(self, name: str, content: str) -> None:
        """保存用户自定义模板到覆盖层。"""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("模板名称必须是非空字符串")
        if not isinstance(content, str):
            raise ValueError("模板覆盖内容必须是字符串")
        if not content.strip():
            raise ValueError("模板覆盖内容不能为空字符串或仅包含空白字符")
        with self._lock:
            self._overrides[name] = content
            self._persist_overrides()

    def reset_override(self, name: str) -> None:
        """删除覆盖层，恢复默认模板。"""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("模板名称必须是非空字符串")
        with self._lock:
            self._overrides.pop(name, None)
            self._persist_overrides()

    def _persist_overrides(self) -> None:
        """原子性地将覆盖层写入 JSON 文件。"""
        self.overrides_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.overrides_path.with_suffix(
            f"{self.overrides_path.suffix}.tmp"
        )
        temp_path.write_text(
            json.dumps(self._overrides, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, self.overrides_path)

    # ----- 版本历史 -----

    @property
    def _history_dir(self) -> Path:
        """快照目录：与覆盖文件同目录下的 prompt_overrides.history/。"""
        return self.overrides_path.parent / "prompt_overrides.history"

    def save_override_with_snapshot(self, name: str, content: str) -> None:
        """保存新覆盖前，先把当前覆盖（若存在）写到 history 目录。

        没有当前覆盖时不留快照（首次覆盖无需回滚到"自定义前"）。
        保留 save_override() 的入参校验语义。
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("模板名称必须是非空字符串")
        if not isinstance(content, str):
            raise ValueError("模板覆盖内容必须是字符串")
        if not content.strip():
            raise ValueError("模板覆盖内容不能为空字符串或仅包含空白字符")

        with self._lock:
            current = self._overrides.get(name)
            if current is not None and current != content:
                self._write_snapshot(name, current)
            self._overrides[name] = content
            self._persist_overrides()

    def _write_snapshot(self, name: str, content: str) -> str:
        """把单条覆盖内容写到 history 目录，返回 snapshot_id。

        不持有锁——调用方负责。
        """
        self._history_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9_.\-]", "_", name)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        snapshot_id = f"{safe_name}.{timestamp}"
        path = self._history_dir / f"{snapshot_id}.txt"
        counter = 1
        while path.exists():
            path = self._history_dir / f"{snapshot_id}.{counter}.txt"
            counter += 1
        path.write_text(content, encoding="utf-8")
        return path.stem

    def list_history(self, name: str) -> list[dict]:
        """列出指定模板的历史快照，按时间倒序。

        返回 [{id, timestamp, size}]，timestamp 为 ISO 字符串。
        """
        if not self._history_dir.exists():
            return []
        safe_name = re.sub(r"[^a-zA-Z0-9_.\-]", "_", name)
        files = sorted(
            (p for p in self._history_dir.iterdir()
             if p.name.startswith(f"{safe_name}.") and p.suffix == ".txt"),
            key=lambda p: p.name,
            reverse=True,
        )
        result: list[dict] = []
        for p in files:
            stem = p.stem  # <safe_name>.<ts>[.counter]
            # 去掉前缀得到 snapshot_id
            snapshot_id = stem
            ts_part = stem[len(safe_name) + 1:].split(".")[0]
            ts = self._parse_ts(ts_part)
            result.append({
                "id": snapshot_id,
                "timestamp": ts,
                "size": p.stat().st_size,
            })
        return result

    @staticmethod
    def _parse_ts(ts_part: str) -> str:
        """把 %Y%m%d%H%M%S%f 解析成 ISO 字符串；失败原样返回。"""
        try:
            dt = datetime.strptime(ts_part, "%Y%m%d%H%M%S%f")
            return dt.isoformat()
        except ValueError:
            return ts_part

    def read_history(self, name: str, snapshot_id: str) -> str | None:
        """读取单条快照内容；不存在返回 None。"""
        path = self._history_dir / f"{self._safe_snapshot_id(snapshot_id)}.txt"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def restore_history(self, name: str, snapshot_id: str) -> str | None:
        """把快照恢复为当前覆盖；返回恢复后的内容，找不到快照返回 None。

        恢复 = 把当前覆盖另存一条新快照，然后用历史内容覆盖当前。
        """
        with self._lock:
            historical = self.read_history(name, snapshot_id)
            if historical is None:
                return None
            current = self._overrides.get(name)
            if current is not None and current != historical:
                self._write_snapshot(name, current)
            self._overrides[name] = historical
            self._persist_overrides()
            return historical

    @staticmethod
    def _safe_snapshot_id(snapshot_id: str) -> str:
        """清理 snapshot_id，防止路径遍历。"""
        if not snapshot_id or ".." in snapshot_id or "/" in snapshot_id or "\\" in snapshot_id:
            raise ValueError("Invalid snapshot id")
        return re.sub(r"[^a-zA-Z0-9_.\-]", "_", snapshot_id)


def assemble_text_prompt(template: str, **kwargs: str) -> str:
    """使用 str.format 将变量填充到模板中。"""
    return template.format(**kwargs)


def assemble_image_prompt(
    template: str,
    style_rules: str,
    product_context: str,
    screen: str,
    block: str,
    block_content: str,
) -> str:
    """组装单张图片生成提示词。"""
    return template.format(
        style_rules=style_rules,
        product_context=product_context,
        screen=screen,
        block=block,
        block_content=block_content,
    )
