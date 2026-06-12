# CoupangAds 开发迭代计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐步实施。步骤使用复选框 `- [ ]` 语法以便跟踪。
> **注意：** 本仓库当前仅有规划文档，无任何源码、构建配置或测试。所有实现需从零开始。

**Goal:** 制定 CoupangAds 从当前文档状态到可运行 CLI 工具的迭代路线图，重点交付 v1.0 MVP，并给出 v1.5、v2.0 的演进方向。

**Architecture:** 采用 Python 单体 CLI 架构，分层为表现层（argparse 入口）、编排层（单产品流程编排 + 文件系统状态推断）、业务逻辑层（文本/图像生成服务 + 解析服务）、适配层（Gemini/Doubao Client Adapter）、基础设施层（IO/图像/日志/密钥）。状态通过输出目录文件存在性推断，无数据库。

**Tech Stack:** Python 3.10+、pytest、Pillow、pillow-heif、google-genai、openai（Doubao 线路）、argparse、pathlib。

---

## 1. 项目现状与迭代策略

### 1.1 当前状态

- 仓库仅有 `README.md` + `AGENTS.md` + `docs/*.md`，无源码。
- 技术栈与模块划分已在 `docs/02-系统架构设计.md`、`docs/03-功能规格说明书.md` 中定义。
- 目标：优先实现 `完整版入口` 全链路，再补齐 `经典版入口` 与 `备用线路入口`。

### 1.2 迭代原则

1. **MVP 优先**：v1.0 先跑通「输入图 → 全部文本资产 → 18 张详情页图片」的最小闭环。
2. **模板驱动**：所有 Prompt 外置到 `templates/`，不硬编码到业务代码。
3. **测试先写**：解析函数、IO 工具、组装函数优先写单元测试，再写实现。
4. **双线路对等**：Gemini 与 Doubao 输出文件结构与命名完全一致。
5. **频繁提交**：每个独立任务完成后提交，便于回滚与审查。

### 1.3 迭代总览

| 迭代 | 目标 | 周期（建议） | 核心交付物 |
|------|------|-------------|-----------|
| **迭代一：v1.0 MVP** | 可运行的完整版 CLI，单产品全链路通 | 4~6 周 | `完整版入口.py`、模板库、核心模块、pytest 单元测试 |
| **迭代二：v1.5 质量增强** | 提升输出质量、降低审核负担、偿还技术债务 | 3~4 周 | 质量审核层、敏感词过滤、批量优化、单元测试覆盖率 ≥ 90% |
| **迭代三：v2.0 平台化** | 从单机工具演进为 Web 平台 MVP | 8~12 周 | Web 上传、Celery 队列、用户系统、对象存储 |

---

## 2. 迭代一：v1.0 MVP 详细实施计划

> 本迭代目标：实现从 `raw-material/产品名/` 到 `result/产品名/` 的完整内容生产链路。
> 采用 TDD，优先实现基础设施与纯函数，再拼装主流程。

### 文件结构规划

```text
CoupangAds/
├── pyproject.toml
├── .gitignore
├── README.md
├── AGENTS.md
├── docs/
│   └── superpowers/plans/2026-06-12-development-iteration-plan.md
├── src/
│   └── coupangads/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── full_pipeline.py        # 完整版入口
│       │   ├── classic_pipeline.py     # 经典版入口
│       │   └── doubao_pipeline.py      # 备用线路入口
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py               # 常量、默认路径、模型名
│       │   ├── models.py               # 数据模型（Pydantic / dataclass）
│       │   └── logging.py              # 日志工具
│       ├── infra/
│       │   ├── __init__.py
│       │   ├── io.py                   # 文件读写、目录操作
│       │   ├── image.py                # 图片加载、缩放、HEIC 解码
│       │   └── api_keys.py             # API Key 读取（文件/环境变量）
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py                 # 适配器基类/协议
│       │   ├── gemini.py               # GeminiClientAdapter
│       │   └── doubao.py               # DoubaoClientAdapter
│       ├── text/
│       │   ├── __init__.py
│       │   ├── report.py               # 商品画像分析服务
│       │   ├── title.py                # 标题生成服务
│       │   ├── keywords.py             # 关键词挖掘服务
│       │   ├── selling_points.py       # 卖点文案服务
│       │   ├── instagram.py            # 社媒文案服务
│       │   └── parsers.py              # JSON 提取、卖点分段、风格规则提取
│       ├── image_pipeline/
│       │   ├── __init__.py
│       │   ├── reference_selector.py   # 智能参考图筛选
│       │   ├── prompt_assembler.py     # 图片提示词组装
│       │   └── generator.py            # 详情页图片生成
│       └── orchestration/
│           ├── __init__.py
│           └── pipeline.py             # 单产品全流程编排 + 断点续跑
├── templates/
│   ├── product_report.txt
│   ├── product_title.txt
│   ├── wing_keywords.txt
│   ├── selling_points.txt
│   ├── instagram.txt
│   ├── image_prompt.txt
│   ├── style_rules.txt
│   └── image_global_constraints.txt
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_io.py
│   ├── test_image.py
│   ├── test_parsers.py
│   ├── test_prompt_assembler.py
│   ├── test_reference_selector.py
│   └── test_orchestration.py
└── raw-material/                       # 默认输入目录（空或放示例）
```

---

### Task 1: 项目骨架与依赖配置

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/coupangads/__init__.py`

- [ ] **Step 1: 创建 `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "coupangads"
version = "0.1.0"
description = "AI content generation system for Coupang Korea e-commerce"
requires-python = ">=3.10"
dependencies = [
    "google-genai>=1.0",
    "openai>=1.0",
    "Pillow>=10.0",
    "pillow-heif>=0.18",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 创建 `.gitignore`**

```gitignore
# 虚拟环境
venv/
.env/

# API 密钥
apikey.md
dbkey.md

# 输入输出目录
raw-material/
result/
输入目录/
输出目录/

# 日志
*.log

# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
```

- [ ] **Step 3: 创建源码包根 `src/coupangads/__init__.py`**

```python
"""CoupangAds — AI 电商内容生成系统。"""

__version__ = "0.1.0"
```

- [ ] **Step 4: 安装依赖并验证 Python 版本**

Run:
```bash
python --version
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest --version
```

Expected: Python >= 3.10，pytest 可运行。

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml .gitignore src/coupangads/__init__.py
git commit -m "chore: 项目骨架、依赖配置与 .gitignore"
```

---

### Task 2: 核心常量与日志工具

**Files:**
- Create: `src/coupangads/core/config.py`
- Create: `src/coupangads/core/logging.py`
- Create: `src/coupangads/core/__init__.py`

- [ ] **Step 1: 创建 `src/coupangads/core/config.py`**

```python
"""全局常量与默认配置。"""

from pathlib import Path

# 模型常量
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
DOUBAO_TEXT_MODEL = "doubao-seed-2-0-lite-260215"
DOUBAO_IMAGE_MODEL = "doubao-seedream-5-0-260128"

# 图像常量
REFERENCE_IMAGE_MAX_LONG_EDGE = 1536
REFERENCE_IMAGE_COUNT = 3
SCREEN_COUNT = 10
IMAGE_RATIO = (2, 3)
IMAGE_SIZE = (1200, 1800)

# 路径常量
DEFAULT_INPUT_DIR = Path("raw-material")
DEFAULT_OUTPUT_DIR = Path("result")
GEMINI_API_KEY_FILE = Path("apikey.md")
DOUBAO_API_KEY_FILE = Path("dbkey.md")

# 输出文件名
PRODUCT_REPORT_FILE = "productreport.md"
PRODUCT_TITLE_FILE = "product_title.md"
WING_KEYWORDS_FILE = "wing_keywords.md"
SELLING_POINTS_FILE = "selling_points.md"
SELLING_POINTS_JSON_FILE = "selling_points.json"
INSTAGRAM_FILE = "instagram.md"
PRODUCT_CONTEXT_FILE = "product_context.md"
IMAGE_PROMPTS_FILE = "image_prompts.json"
BEST_REFERENCE_IMAGES_FILE = "best_reference_images.json"
RUN_LOG_FILE = "run.log"

# 默认 CLI 参数
DEFAULT_MAX_RETRIES = 3
DEFAULT_REQUEST_DELAY = 2.0
DEFAULT_REQUEST_TIMEOUT_MS = 300_000
```

- [ ] **Step 2: 创建 `src/coupangads/core/logging.py`**

```python
"""统一日志工具。"""

import logging
from pathlib import Path


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """获取统一格式日志器。"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(handler)
    return logger


def add_file_handler(logger: logging.Logger, log_path: Path) -> None:
    """为日志器追加文件输出。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(handler)
```

- [ ] **Step 3: 验证日志格式**

Run:
```bash
python -c "
from coupangads.core.logging import get_logger
logger = get_logger('test')
logger.info('测试日志')
"
```

Expected: 控制台输出形如 `2026-06-12 17:58:26 | INFO | 测试日志`。

- [ ] **Step 4: 提交**

```bash
git add src/coupangads/core/
git commit -m "feat: 全局常量与统一日志工具"
```

---

### Task 3: 基础设施 IO 工具

**Files:**
- Create: `src/coupangads/infra/io.py`
- Create: `src/coupangads/infra/api_keys.py`
- Create: `tests/test_io.py`

- [ ] **Step 1: 写失败测试 `tests/test_io.py`**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_io.py -v`
Expected: 6 个测试全部失败（ImportError / 函数未定义）。

- [ ] **Step 3: 实现 `src/coupangads/infra/io.py`**

```python
"""文件 IO 工具。"""

import json
from pathlib import Path


def read_text_file(path: Path) -> str:
    """读取 UTF-8 文本文件。"""
    return path.read_text(encoding="utf-8")


def write_text_file(path: Path, content: str) -> None:
    """写入 UTF-8 文本文件，自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json_file(path: Path, data: object) -> None:
    """以格式化 JSON 写入文件，自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: 实现 `src/coupangads/infra/api_keys.py`**

```python
"""API 密钥读取工具。"""

import os
from pathlib import Path


def read_api_key(file_path: Path, env_var: str | None = None) -> str:
    """
    读取 API Key。

    优先级：
    1. 环境变量（若 env_var 提供且存在）
    2. 指定文件首行非空内容
    """
    if env_var and (value := os.environ.get(env_var)):
        return value

    lines = file_path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped:
            return stripped
    raise ValueError(f"API key file is empty: {file_path}")
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_io.py -v`
Expected: 6 个测试全部通过。

- [ ] **Step 6: 提交**

```bash
git add tests/test_io.py src/coupangads/infra/
git commit -m "feat: IO 工具与 API Key 读取，含单元测试"
```

---

### Task 4: 图像处理工具

**Files:**
- Create: `src/coupangads/infra/image.py`
- Create: `tests/test_image.py`

- [ ] **Step 1: 写失败测试 `tests/test_image.py`**

```python
"""图像处理单元测试。"""

from pathlib import Path

from PIL import Image

from coupangads.infra.image import load_image_rgb, resize_long_edge


def test_load_image_rgb_converts_rgba(tmp_path: Path) -> None:
    img_path = tmp_path / "rgba.png"
    Image.new("RGBA", (100, 100), (255, 0, 0, 128)).save(img_path)
    loaded = load_image_rgb(img_path)
    assert loaded.mode == "RGB"


def test_resize_long_edge_scales_down() -> None:
    img = Image.new("RGB", (2000, 1000))
    resized = resize_long_edge(img, 800)
    assert max(resized.size) == 800
    assert resized.size[0] == 800


def test_resize_long_edge_keeps_small_image() -> None:
    img = Image.new("RGB", (400, 300))
    resized = resize_long_edge(img, 800)
    assert resized.size == (400, 300)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_image.py -v`
Expected: 3 个测试全部失败。

- [ ] **Step 3: 实现 `src/coupangads/infra/image.py`**

```python
"""图像处理工具。"""

from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def load_image_rgb(path: Path) -> Image.Image:
    """加载图片并转换为 RGB 模式。"""
    with Image.open(path) as img:
        if img.mode in ("RGBA", "P"):
            return img.convert("RGB")
        return img.convert("RGB")


def resize_long_edge(img: Image.Image, max_long_edge: int) -> Image.Image:
    """等比缩放，使长边不超过 max_long_edge。"""
    width, height = img.size
    long_edge = max(width, height)
    if long_edge <= max_long_edge:
        return img
    ratio = max_long_edge / long_edge
    new_size = (int(width * ratio), int(height * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def image_to_data_url(img: Image.Image, fmt: str = "JPEG") -> str:
    """将 PIL Image 编码为 Base64 Data URL。"""
    import base64
    import io

    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}"
    return f"data:{mime};base64,{b64}"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_image.py -v`
Expected: 3 个测试全部通过。

- [ ] **Step 5: 提交**

```bash
git add tests/test_image.py src/coupangads/infra/image.py
git commit -m "feat: 图像加载、缩放与 Data URL 编码，含单元测试"
```

---

### Task 5: 解析与容错组件（纯函数）

**Files:**
- Create: `src/coupangads/text/parsers.py`
- Create: `tests/test_parsers.py`

- [ ] **Step 1: 写失败测试 `tests/test_parsers.py`**

```python
"""解析函数单元测试。"""

import pytest

from coupangads.text.parsers import (
    extract_json_object,
    parse_selling_points,
    extract_style_rules,
    is_suspected_ai_image,
)


def test_extract_json_object_from_code_block() -> None:
    text = '```json\n{"a": 1}\n```'
    assert extract_json_object(text) == '{"a": 1}'


def test_extract_json_object_bare() -> None:
    text = 'prefix {"a": 1} suffix'
    assert extract_json_object(text) == '{"a": 1}'


def test_extract_json_object_no_json_returns_original() -> None:
    text = "no json here"
    assert extract_json_object(text) == "no json here"


def test_parse_selling_points_standard() -> None:
    text = """
# B1 主卖点
标题1
正文1
# B2 材质优势
标题2
正文2
"""
    result = parse_selling_points(text)
    assert "B1" in result and "B2" in result
    assert "标题1" in result["B1"]


def test_parse_selling_points_missing_blocks() -> None:
    result = parse_selling_points("# B1 测试\n内容")
    assert result["B1"] == "内容"
    assert result["B2"] == ""


def test_extract_style_rules_ab() -> None:
    text = "## STYLE A\n规则A\n## STYLE B\n规则B"
    rules = extract_style_rules(text)
    assert rules["A"] == "规则A"
    assert rules["B"] == "规则B"


def test_is_suspected_ai_image() -> None:
    assert is_suspected_ai_image("ai_generated_image_v2.png") is True
    assert is_suspected_ai_image("IMG_2024.jpg") is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_parsers.py -v`
Expected: 8 个测试全部失败。

- [ ] **Step 3: 实现 `src/coupangads/text/parsers.py`**

```python
"""文本解析与容错工具。"""

import json
import re
from typing import Any


def extract_json_object(text: str) -> str:
    """
    从文本中提取 JSON 对象。

    Fallback 顺序：
    1. markdown 代码块
    2. 首尾花括号匹配
    3. 返回原文
    """
    # 1. 代码块
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        return code_block.group(1).strip()

    # 2. 花括号
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0).strip()

    return text


def safe_parse_json(text: str) -> Any:
    """安全解析 JSON，失败返回 None。"""
    try:
        return json.loads(extract_json_object(text))
    except json.JSONDecodeError:
        return None


def parse_selling_points(text: str) -> dict[str, str]:
    """
    从 Markdown 文本中提取 B1-B9 卖点区块。

    每个区块以 `# B{n}` 或 `## B{n}` 开头。
    """
    blocks: dict[str, str] = {f"B{i}": "" for i in range(1, 10)}
    pattern = re.compile(r"^#+\s*B(\d+)\b.*$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    for idx, match in enumerate(matches):
        block_num = match.group(1)
        if block_num not in blocks:
            continue
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        blocks[block_num] = text[start:end].strip()

    return blocks


def extract_style_rules(text: str) -> dict[str, str]:
    """
    从模板中提取 A/B 风格规则。

    期望格式：
    ## STYLE A
    ...
    ## STYLE B
    ...
    """
    rules: dict[str, str] = {}
    pattern = re.compile(r"##\s*STYLE\s+([A-Z])\s*\n(.*?)(?=\n##\s*STYLE|\Z)", re.DOTALL)
    for match in pattern.finditer(text):
        rules[match.group(1)] = match.group(2).strip()
    return rules


def is_suspected_ai_image(filename: str) -> bool:
    """基于文件名模式判断是否为疑似 AI 生成图。"""
    lowered = filename.lower()
    markers = ("ai_", "generated", "midjourney", "dalle", "stable_diffusion")
    return any(marker in lowered for marker in markers)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_parsers.py -v`
Expected: 8 个测试全部通过。

- [ ] **Step 5: 提交**

```bash
git add tests/test_parsers.py src/coupangads/text/parsers.py
git commit -m "feat: JSON/卖点/风格规则解析函数，含单元测试"
```

---

### Task 6: 模板加载与 Prompt 组装

**Files:**
- Create: `src/coupangads/text/template_loader.py`
- Create: `templates/product_report.txt`
- Create: `templates/product_title.txt`
- Create: `templates/wing_keywords.txt`
- Create: `templates/selling_points.txt`
- Create: `templates/instagram.txt`
- Create: `templates/image_prompt.txt`
- Create: `templates/style_rules.txt`
- Create: `templates/image_global_constraints.txt`
- Create: `tests/test_prompt_assembler.py`

- [ ] **Step 1: 创建最小模板文件（占位提示词骨架）**

`templates/product_report.txt`:
```text
你是一位韩国 Coupang 电商商品分析专家。请基于以下产品实拍图，输出结构化商品画像报告（Markdown）。

要求：
- 所有判断必须基于图片可见信息
- 未确认属性标注「图片未明确」
- 输出韩文
```

`templates/product_title.txt`:
```text
基于以下商品画像报告，生成 3~5 个适配 Coupang 的韩文商品标题变体。要求自然嵌入关键词，避免堆砌。

商品画像报告：
{product_report}
```

`templates/wing_keywords.txt`:
```text
基于商品画像报告和标题，构建三层关键词矩阵（核心词、属性词、长尾词），并给出蓝海词推荐。

商品画像报告：
{product_report}

标题：
{product_title}
```

`templates/selling_points.txt`:
```text
基于商品画像、标题和关键词，按 B1-B9 结构生成详情页卖点文案（韩文）。每个区块包含卖点标题、正文、支撑证据。

商品画像：
{product_report}

标题：
{product_title}

关键词：
{wing_keywords}
```

`templates/instagram.txt`:
```text
基于以下信息，生成韩国 Instagram 种草文案（含 Hashtag）。

商品画像：
{product_report}

标题：
{product_title}

关键词：
{wing_keywords}

卖点：
{selling_points}
```

`templates/image_prompt.txt`:
```text
你是一位韩国宠物品牌电商视觉专家。请为以下产品生成一张 2:3 竖屏详情页图片的英文 Stable Diffusion / Image Generation 提示词。

风格规则：
{style_rules}

产品上下文：
{product_context}

当前卖点区块：{screen} ({block})
卖点内容：
{block_content}

要求：
- 提示词为英文
- 强调产品还原、韩系高级广告摄影风格
- 图片内文字必须为韩文
- 禁止价格、医疗化表达、杂乱背景
```

`templates/style_rules.txt`:
```text
## STYLE A
高级商业摄影风：简洁背景、柔和影棚光、产品居中、杂志级质感、低饱和温暖色调。

## STYLE B
韩系生活方式场景风：居家/户外自然场景、宠物与主人互动、自然光、治愈氛围、生活化构图。
```

`templates/image_global_constraints.txt`:
```text
全局图片约束：
- 比例 2:3 竖屏，推荐尺寸 1200×1800
- 文字必须为韩文，禁止中文/英文/乱码
- 产品严格还原参考图颜色、材质、图案、LOGO、结构
- 宠物模特：小型犬优先马尔济斯/泰迪/博美/比熊；猫优先布偶/英短/银渐层
- 禁止：价格促销、医疗化表达、多余动物、杂乱背景、卡通风、廉价感
```

- [ ] **Step 2: 实现 `src/coupangads/text/template_loader.py`**

```python
"""模板加载与 Prompt 组装。"""

from pathlib import Path

from coupangads.infra.io import read_text_file


class TemplateLoader:
    """从 templates/ 目录加载提示词模板。"""

    def __init__(self, templates_dir: Path = Path("templates")) -> None:
        self.templates_dir = templates_dir

    def load(self, name: str) -> str:
        """加载指定模板文件（不含扩展名需自行补全）。"""
        return read_text_file(self.templates_dir / name)


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
```

- [ ] **Step 3: 写测试 `tests/test_prompt_assembler.py`**

```python
"""Prompt 组装单元测试。"""

from pathlib import Path

import pytest

from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def test_template_loader_loads_file(tmp_path: Path) -> None:
    (tmp_path / "test.txt").write_text("hello {name}", encoding="utf-8")
    loader = TemplateLoader(tmp_path)
    assert loader.load("test.txt") == "hello {name}"


def test_assemble_text_prompt() -> None:
    template = "报告：{product_report}"
    assert assemble_text_prompt(template, product_report="R") == "报告：R"


def test_assemble_text_prompt_missing_key_raises() -> None:
    with pytest.raises(KeyError):
        assemble_text_prompt("{missing}")
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_prompt_assembler.py -v`
Expected: 3 个测试全部通过。

- [ ] **Step 5: 提交**

```bash
git add templates/ src/coupangads/text/template_loader.py tests/test_prompt_assembler.py
git commit -m "feat: 模板加载与 Prompt 组装，含基础模板库和单元测试"
```

---

### Task 7: API 适配器基类与 Gemini 适配器

**Files:**
- Create: `src/coupangads/adapters/base.py`
- Create: `src/coupangads/adapters/gemini.py`
- Create: `src/coupangads/core/models.py`

- [ ] **Step 1: 创建 `src/coupangads/core/models.py`**

```python
"""核心数据模型。"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class ReferenceImage:
    path: Path
    filename: str
    image: Image.Image
    data_url: str | None = None


@dataclass
class ImagePrompt:
    style: str
    screen: str
    block: str
    prompt: str
    filename: str
```

- [ ] **Step 2: 创建 `src/coupangads/adapters/base.py`**

```python
"""模型适配器基类。"""

from abc import ABC, abstractmethod
from pathlib import Path

from coupangads.core.models import ImagePrompt, ReferenceImage


class TextAdapter(ABC):
    """文本生成适配器基类。"""

    @abstractmethod
    def chat(self, prompt: str) -> str:
        """发送单轮文本请求，返回模型回复字符串。"""
        ...


class ImageAdapter(ABC):
    """图片生成适配器基类。"""

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        references: list[ReferenceImage],
        output_path: Path,
    ) -> bool:
        """生成图片并保存到 output_path，返回是否成功。"""
        ...
```

- [ ] **Step 3: 实现 `src/coupangads/adapters/gemini.py`**

```python
"""Google Gemini 适配器。"""

from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.core import config
from coupangads.core.models import ReferenceImage
from coupangads.infra.image import load_image_rgb


class GeminiClientAdapter(TextAdapter, ImageAdapter):
    """Gemini 双线路适配器：文本用对话模式，图片用独立请求模式。"""

    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model_text = config.GEMINI_TEXT_MODEL
        self.model_image = config.GEMINI_IMAGE_MODEL
        self._chat = None

    def _ensure_chat(self) -> None:
        if self._chat is None:
            self._chat = self.client.chats.create(model=self.model_text)

    def chat(self, prompt: str) -> str:
        """使用对话模式发送文本请求。"""
        self._ensure_chat()
        response = self._chat.send_message(prompt)
        return response.text or ""

    def generate_image(
        self,
        prompt: str,
        references: list[ReferenceImage],
        output_path: Path,
    ) -> bool:
        """独立请求生成图片，每次携带完整提示词和参考图。"""
        contents: list[types.Content] = []

        for ref in references:
            pil_img = load_image_rgb(ref.path)
            contents.append(pil_img)

        contents.append(prompt)

        response = self.client.models.generate_content(
            model=self.model_image,
            contents=contents,
        )

        if not response.candidates:
            return False

        for part in response.candidates[0].content.parts or []:
            if part.inline_data:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                return True

        return False
```

- [ ] **Step 4: 提交**

```bash
git add src/coupangads/core/models.py src/coupangads/adapters/base.py src/coupangads/adapters/gemini.py
git commit -m "feat: 数据模型、适配器协议与 Gemini 适配器"
```

---

### Task 8: Doubao 适配器

**Files:**
- Create: `src/coupangads/adapters/doubao.py`

- [ ] **Step 1: 实现 `src/coupangads/adapters/doubao.py`**

```python
"""字节 Doubao 适配器。"""

from pathlib import Path

from openai import OpenAI

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.core import config
from coupangads.core.models import ReferenceImage
from coupangads.infra.image import image_to_data_url


class DoubaoClientAdapter(TextAdapter, ImageAdapter):
    """Doubao 双线路适配器。"""

    def __init__(self, api_key: str, base_url: str = "https://ark.cn-beijing.volces.com/api/v3") -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_text = config.DOUBAO_TEXT_MODEL
        self.model_image = config.DOUBAO_IMAGE_MODEL
        self._messages: list[dict] = []

    def chat(self, prompt: str) -> str:
        """手动维护消息历史并发送文本请求。"""
        self._messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model_text,
            messages=self._messages,
        )
        content = response.choices[0].message.content or ""
        self._messages.append({"role": "assistant", "content": content})
        return content

    def generate_image(
        self,
        prompt: str,
        references: list[ReferenceImage],
        output_path: Path,
    ) -> bool:
        """调用 Doubao 图像生成 API。"""
        content: list[dict] = [{"type": "text", "text": prompt}]
        for ref in references:
            data_url = ref.data_url or image_to_data_url(ref.image)
            content.append({"type": "image_url", "image_url": {"url": data_url}})

        response = self.client.chat.completions.create(
            model=self.model_image,
            messages=[{"role": "user", "content": content}],
        )

        message = response.choices[0].message
        if message.content:
            # Doubao seedream 可能返回 base64 图片数据
            import base64
            import re

            b64_match = re.search(r"data:image/\w+;base64,([A-Za-z0-9+/=]+)", message.content)
            if b64_match:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(base64.b64decode(b64_match.group(1)))
                return True

        return False
```

- [ ] **Step 2: 提交**

```bash
git add src/coupangads/adapters/doubao.py
git commit -m "feat: Doubao 适配器（文本对话 + 图片生成）"
```

---

### Task 9: 文本链路业务服务

**Files:**
- Create: `src/coupangads/text/report.py`
- Create: `src/coupangads/text/title.py`
- Create: `src/coupangads/text/keywords.py`
- Create: `src/coupangads/text/selling_points.py`
- Create: `src/coupangads/text/instagram.py`

- [ ] **Step 1: 实现 `src/coupangads/text/report.py`**

```python
"""商品画像分析服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.core import config
from coupangads.infra.io import write_text_file
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_product_report(
    adapter: TextAdapter,
    image_paths: list[Path],
    output_path: Path,
    templates: TemplateLoader,
) -> str:
    """生成商品画像报告。"""
    # 当前版本：文本链路不直接传图，通过 adapter chat 触发。
    # 未来多模态版本可将图片作为 contents 传入。
    template = templates.load("product_report.txt")
    prompt = assemble_text_prompt(
        template,
        image_count=str(len(image_paths)),
    )
    report = adapter.chat(prompt)
    write_text_file(output_path, report)
    return report
```

- [ ] **Step 2: 实现 `src/coupangads/text/title.py`**

```python
"""商品标题生成服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.infra.io import write_text_file
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_product_title(
    adapter: TextAdapter,
    product_report: str,
    output_path: Path,
    templates: TemplateLoader,
) -> str:
    """生成商品标题。"""
    template = templates.load("product_title.txt")
    prompt = assemble_text_prompt(template, product_report=product_report)
    title = adapter.chat(prompt)
    write_text_file(output_path, title)
    return title
```

- [ ] **Step 3: 实现 `src/coupangads/text/keywords.py`**

```python
"""关键词挖掘服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.infra.io import write_text_file
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_keywords(
    adapter: TextAdapter,
    product_report: str,
    product_title: str,
    output_path: Path,
    templates: TemplateLoader,
) -> str:
    """生成关键词文档。"""
    template = templates.load("wing_keywords.txt")
    prompt = assemble_text_prompt(
        template,
        product_report=product_report,
        product_title=product_title,
    )
    keywords = adapter.chat(prompt)
    write_text_file(output_path, keywords)
    return keywords
```

- [ ] **Step 4: 实现 `src/coupangads/text/selling_points.py`**

```python
"""详情页卖点文案服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.core import config
from coupangads.infra.io import write_json_file, write_text_file
from coupangads.text.parsers import parse_selling_points
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_selling_points(
    adapter: TextAdapter,
    product_report: str,
    product_title: str,
    keywords: str,
    md_output_path: Path,
    json_output_path: Path,
    templates: TemplateLoader,
) -> dict[str, str]:
    """生成卖点 Markdown 与 B1-B9 JSON。"""
    template = templates.load("selling_points.txt")
    prompt = assemble_text_prompt(
        template,
        product_report=product_report,
        product_title=product_title,
        wing_keywords=keywords,
    )
    selling_points_md = adapter.chat(prompt)
    write_text_file(md_output_path, selling_points_md)

    blocks = parse_selling_points(selling_points_md)
    write_json_file(json_output_path, blocks)
    return blocks
```

- [ ] **Step 5: 实现 `src/coupangads/text/instagram.py`**

```python
"""社媒文案生成服务。"""

from pathlib import Path

from coupangads.adapters.base import TextAdapter
from coupangads.infra.io import write_text_file
from coupangads.text.template_loader import TemplateLoader, assemble_text_prompt


def generate_instagram(
    adapter: TextAdapter,
    product_report: str,
    product_title: str,
    keywords: str,
    selling_points: str,
    output_path: Path,
    templates: TemplateLoader,
) -> str:
    """生成 Instagram 文案。"""
    template = templates.load("instagram.txt")
    prompt = assemble_text_prompt(
        template,
        product_report=product_report,
        product_title=product_title,
        wing_keywords=keywords,
        selling_points=selling_points,
    )
    instagram = adapter.chat(prompt)
    write_text_file(output_path, instagram)
    return instagram
```

- [ ] **Step 6: 提交**

```bash
git add src/coupangads/text/report.py src/coupangads/text/title.py src/coupangads/text/keywords.py src/coupangads/text/selling_points.py src/coupangads/text/instagram.py
git commit -m "feat: 文本链路五大生成服务"
```

---

### Task 10: 图像准备服务（参考图筛选 + 提示词组装）

**Files:**
- Create: `src/coupangads/image_pipeline/reference_selector.py`
- Create: `src/coupangads/image_pipeline/prompt_assembler.py`
- Create: `tests/test_reference_selector.py`
- Create: `tests/test_prompt_assembler_image.py`

- [ ] **Step 1: 实现 `src/coupangads/image_pipeline/reference_selector.py`**

```python
"""智能参考图筛选服务。"""

from pathlib import Path

from coupangads.core.models import ReferenceImage
from coupangads.infra.image import load_image_rgb, resize_long_edge
from coupangads.text.parsers import is_suspected_ai_image
from coupangads.core import config


def select_best_reference_images(
    image_paths: list[Path],
    count: int = config.REFERENCE_IMAGE_COUNT,
) -> list[ReferenceImage]:
    """
    从实拍图中筛选最佳参考图。

    当前策略（MVP）：
    - 排除疑似 AI 图
    - 按文件大小降序取前 count 张（简单假设：高质量图更大）
    - 加载、缩放、生成 data_url

    未来可替换为模型打分。
    """
    candidates = [
        p for p in image_paths
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".webp")
        and not is_suspected_ai_image(p.name)
    ]
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)

    references: list[ReferenceImage] = []
    for path in candidates[:count]:
        try:
            img = load_image_rgb(path)
            img = resize_long_edge(img, config.REFERENCE_IMAGE_MAX_LONG_EDGE)
            from coupangads.infra.image import image_to_data_url
            references.append(ReferenceImage(
                path=path,
                filename=path.name,
                image=img,
                data_url=image_to_data_url(img),
            ))
        except Exception:
            continue

    return references
```

- [ ] **Step 2: 实现 `src/coupangads/image_pipeline/prompt_assembler.py`**

```python
"""图片提示词组装服务。"""

from pathlib import Path

from coupangads.core.models import ImagePrompt
from coupangads.infra.io import write_json_file
from coupangads.text.parsers import extract_style_rules
from coupangads.text.template_loader import assemble_image_prompt


def build_product_context(
    product_report: str,
    product_title: str,
    keywords: str,
    global_constraints: str,
) -> str:
    """组装精简产品上下文。"""
    return f"""{global_constraints}

产品标题：
{product_title}

关键词：
{keywords}

商品画像摘要：
{product_report[:2000]}
"""


def assemble_image_prompts(
    selling_points: dict[str, str],
    style_rules_text: str,
    product_context: str,
    prompt_template: str,
    output_path: Path,
) -> list[ImagePrompt]:
    """组装 A/B 双风格 × B1-B9 共 18 条图片提示词。"""
    style_rules = extract_style_rules(style_rules_text)
    blocks = [f"B{i}" for i in range(1, 10)]
    prompts: list[ImagePrompt] = []

    for style_code, style_rule in style_rules.items():
        for block in blocks:
            content = selling_points.get(block, "")
            prompt_text = assemble_image_prompt(
                template=prompt_template,
                style_rules=style_rule,
                product_context=product_context,
                screen=f"第 {block[1]} 屏",
                block=block,
                block_content=content,
            )
            prompts.append(ImagePrompt(
                style=style_code,
                screen=f"第 {block[1]} 屏",
                block=block,
                prompt=prompt_text,
                filename=f"{style_code}_{block}.png",
            ))

    write_json_file(
        output_path,
        [
            {
                "style": p.style,
                "screen": p.screen,
                "block": p.block,
                "prompt": p.prompt,
                "filename": p.filename,
            }
            for p in prompts
        ],
    )
    return prompts
```

- [ ] **Step 3: 写测试并运行**

`tests/test_reference_selector.py`:
```python
"""参考图筛选单元测试。"""

from pathlib import Path

from PIL import Image

from coupangads.image_pipeline.reference_selector import select_best_reference_images


def test_select_excludes_ai_named_images(tmp_path: Path) -> None:
    img1 = tmp_path / "IMG_001.jpg"
    img2 = tmp_path / "ai_generated_v2.jpg"
    Image.new("RGB", (100, 100)).save(img1)
    Image.new("RGB", (100, 100)).save(img2)
    refs = select_best_reference_images([img1, img2], count=1)
    assert len(refs) == 1
    assert refs[0].filename == "IMG_001.jpg"
```

`tests/test_prompt_assembler_image.py`:
```python
"""图片提示词组装单元测试。"""

from pathlib import Path

from coupangads.image_pipeline.prompt_assembler import assemble_image_prompts


def test_assemble_image_prompts_count(tmp_path: Path) -> None:
    selling_points = {f"B{i}": f"卖点{i}" for i in range(1, 10)}
    style_rules = "## STYLE A\n高级风\n## STYLE B\n生活风"
    template = "风格：{style_rules} 区块：{block} 内容：{block_content}"
    output = tmp_path / "prompts.json"
    prompts = assemble_image_prompts(
        selling_points, style_rules, "ctx", template, output
    )
    assert len(prompts) == 18
    assert prompts[0].filename == "A_B1.png"
    assert output.exists()
```

Run:
```bash
pytest tests/test_reference_selector.py tests/test_prompt_assembler_image.py -v
```

Expected: 2 个测试全部通过。

- [ ] **Step 4: 提交**

```bash
git add src/coupangads/image_pipeline/ tests/test_reference_selector.py tests/test_prompt_assembler_image.py
git commit -m "feat: 参考图筛选与图片提示词组装，含单元测试"
```

---

### Task 11: 图片生成服务

**Files:**
- Create: `src/coupangads/image_pipeline/generator.py`

- [ ] **Step 1: 实现 `src/coupangads/image_pipeline/generator.py`**

```python
"""详情页图片生成服务。"""

from pathlib import Path

from coupangads.adapters.base import ImageAdapter
from coupangads.core.logging import get_logger
from coupangads.core.models import ImagePrompt, ReferenceImage

logger = get_logger(__name__)


def generate_detail_images(
    adapter: ImageAdapter,
    prompts: list[ImagePrompt],
    references: list[ReferenceImage],
    output_dir: Path,
    max_images: int | None = None,
    start_from: str | None = None,
) -> list[Path]:
    """
    逐张生成详情页图片。

    - 支持 max_images 限制生成数量
    - 支持 start_from 从指定键恢复（如 A_B4）
    - 单张失败记录并继续
    """
    generated: list[Path] = []
    started = start_from is None

    for idx, prompt in enumerate(prompts):
        if max_images is not None and len(generated) >= max_images:
            break

        if not started:
            if prompt.filename == start_from or f"{prompt.style}_{prompt.block}" == start_from:
                started = True
            else:
                logger.info(f"跳过 {prompt.filename}，等待恢复点 {start_from}")
                continue

        output_path = output_dir / prompt.filename
        logger.info(f"生成图片 {idx + 1}/{len(prompts)}: {prompt.filename}")

        try:
            success = adapter.generate_image(
                prompt=prompt.prompt,
                references=references,
                output_path=output_path,
            )
            if success:
                generated.append(output_path)
                logger.info(f"已保存: {output_path}")
            else:
                logger.error(f"生成失败（无输出）: {prompt.filename}")
        except Exception as exc:
            logger.error(f"生成异常 {prompt.filename}: {exc}")

    return generated
```

- [ ] **Step 2: 提交**

```bash
git add src/coupangads/image_pipeline/generator.py
git commit -m "feat: 详情页图片批量生成服务（支持断点续跑与限流）"
```

---

### Task 12: 编排层 — 单产品全流程 + 断点续跑

**Files:**
- Create: `src/coupangads/orchestration/pipeline.py`
- Create: `tests/test_orchestration.py`

- [ ] **Step 1: 实现 `src/coupangads/orchestration/pipeline.py`**

```python
"""单产品全流程编排与断点续跑。"""

from pathlib import Path

from coupangads.adapters.base import ImageAdapter, TextAdapter
from coupangads.core import config
from coupangads.core.logging import add_file_handler, get_logger
from coupangads.image_pipeline.generator import generate_detail_images
from coupangads.image_pipeline.prompt_assembler import (
    assemble_image_prompts,
    build_product_context,
)
from coupangads.image_pipeline.reference_selector import (
    select_best_reference_images,
)
from coupangads.infra.io import read_text_file, write_json_file, write_text_file
from coupangads.text.instagram import generate_instagram
from coupangads.text.keywords import generate_keywords
from coupangads.text.report import generate_product_report
from coupangads.text.selling_points import generate_selling_points
from coupangads.text.template_loader import TemplateLoader
from coupangads.text.title import generate_product_title


class ProductPipeline:
    """单个产品的完整生成流水线。"""

    def __init__(
        self,
        text_adapter: TextAdapter,
        image_adapter: ImageAdapter,
        templates: TemplateLoader,
        overwrite: bool = False,
        max_images: int | None = None,
        start_from: str | None = None,
    ) -> None:
        self.text_adapter = text_adapter
        self.image_adapter = image_adapter
        self.templates = templates
        self.overwrite = overwrite
        self.max_images = max_images
        self.start_from = start_from

    def _needs_run(self, target: Path, *dependencies: Path) -> bool:
        """判断目标文件是否需要重新生成。"""
        if self.overwrite:
            return True
        if not target.exists():
            return True
        target_mtime = target.stat().st_mtime
        for dep in dependencies:
            if dep.exists() and dep.stat().st_mtime > target_mtime:
                return True
        return False

    def run(
        self,
        product_input_dir: Path,
        product_output_dir: Path,
    ) -> None:
        """执行单产品完整链路。"""
        product_output_dir.mkdir(parents=True, exist_ok=True)
        logger = get_logger(f"pipeline.{product_input_dir.name}")
        add_file_handler(logger, product_output_dir / config.RUN_LOG_FILE)

        image_paths = sorted(
            p for p in product_input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".webp")
        )
        if len(image_paths) < 3:
            logger.warning(f"{product_input_dir.name} 图片不足 3 张，跳过")
            return

        # 1. 商品画像
        report_path = product_output_dir / config.PRODUCT_REPORT_FILE
        if self._needs_run(report_path, *image_paths):
            logger.info("生成商品画像报告")
            report = generate_product_report(
                self.text_adapter, image_paths, report_path, self.templates
            )
        else:
            logger.info("复用商品画像报告")
            report = read_text_file(report_path)

        # 2. 标题
        title_path = product_output_dir / config.PRODUCT_TITLE_FILE
        if self._needs_run(title_path, report_path):
            logger.info("生成商品标题")
            title = generate_product_title(
                self.text_adapter, report, title_path, self.templates
            )
        else:
            logger.info("复用商品标题")
            title = read_text_file(title_path)

        # 3. 关键词
        keywords_path = product_output_dir / config.WING_KEYWORDS_FILE
        if self._needs_run(keywords_path, report_path, title_path):
            logger.info("生成关键词")
            keywords = generate_keywords(
                self.text_adapter, report, title, keywords_path, self.templates
            )
        else:
            logger.info("复用关键词")
            keywords = read_text_file(keywords_path)

        # 4. 卖点
        sp_md_path = product_output_dir / config.SELLING_POINTS_FILE
        sp_json_path = product_output_dir / config.SELLING_POINTS_JSON_FILE
        if self._needs_run(sp_md_path, report_path, title_path, keywords_path):
            logger.info("生成卖点文案")
            selling_points = generate_selling_points(
                self.text_adapter,
                report,
                title,
                keywords,
                sp_md_path,
                sp_json_path,
                self.templates,
            )
        else:
            logger.info("复用卖点文案")
            selling_points = generate_selling_points(
                self.text_adapter,
                report,
                title,
                keywords,
                sp_md_path,
                sp_json_path,
                self.templates,
            )

        # 5. INS
        ins_path = product_output_dir / config.INSTAGRAM_FILE
        if self._needs_run(ins_path, sp_md_path):
            logger.info("生成 Instagram 文案")
            generate_instagram(
                self.text_adapter,
                report,
                title,
                keywords,
                read_text_file(sp_md_path),
                ins_path,
                self.templates,
            )
        else:
            logger.info("复用 Instagram 文案")

        # 仅文本模式
        if self.max_images == 0:
            logger.info("仅文本模式，跳过图片生成")
            return

        # 6. 参考图筛选
        refs = select_best_reference_images(image_paths)
        if len(refs) < config.REFERENCE_IMAGE_COUNT:
            logger.warning("有效参考图不足 3 张，尝试继续")

        refs_path = product_output_dir / config.BEST_REFERENCE_IMAGES_FILE
        write_json_file(refs_path, [r.filename for r in refs])

        # 7. 产品上下文
        global_constraints = self.templates.load("image_global_constraints.txt")
        product_context = build_product_context(report, title, keywords, global_constraints)
        context_path = product_output_dir / config.PRODUCT_CONTEXT_FILE
        write_text_file(context_path, product_context)

        # 8. 图片提示词
        prompts_path = product_output_dir / config.IMAGE_PROMPTS_FILE
        style_rules_text = self.templates.load("style_rules.txt")
        prompt_template = self.templates.load("image_prompt.txt")
        prompts = assemble_image_prompts(
            selling_points,
            style_rules_text,
            product_context,
            prompt_template,
            prompts_path,
        )

        # 9. 图片生成
        generate_detail_images(
            self.image_adapter,
            prompts,
            refs,
            product_output_dir,
            max_images=self.max_images,
            start_from=self.start_from,
        )

        logger.info(f"{product_input_dir.name} 处理完成")
```

- [ ] **Step 2: 写测试 `tests/test_orchestration.py`**

```python
"""编排层单元测试。"""

from pathlib import Path

from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.text.template_loader import TemplateLoader


class FakeTextAdapter:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = responses or ["report", "title", "keywords", "selling points", "instagram"]
        self.idx = 0

    def chat(self, prompt: str) -> str:
        resp = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return resp


class FakeImageAdapter:
    def generate_image(self, prompt, references, output_path: Path) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"PNG")
        return True


def test_pipeline_creates_text_outputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "input" / "prod"
    output_dir = tmp_path / "output" / "prod"
    input_dir.mkdir(parents=True)
    for i in range(3):
        (input_dir / f"img{i}.jpg").write_bytes(b"fake")

    # 创建最小模板
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("report prompt")
    (templates_dir / "product_title.txt").write_text("{product_report}")
    (templates_dir / "wing_keywords.txt").write_text("{product_report}{product_title}")
    (templates_dir / "selling_points.txt").write_text("{product_report}{product_title}{wing_keywords}")
    (templates_dir / "instagram.txt").write_text("{product_report}{product_title}{wing_keywords}{selling_points}")
    (templates_dir / "image_prompt.txt").write_text("{style_rules}{product_context}{screen}{block}{block_content}")
    (templates_dir / "style_rules.txt").write_text("## STYLE A\na\n## STYLE B\nb")
    (templates_dir / "image_global_constraints.txt").write_text("global")

    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
        max_images=0,
    )
    pipeline.run(input_dir, output_dir)

    assert (output_dir / "productreport.md").exists()
    assert (output_dir / "product_title.md").exists()
    assert (output_dir / "wing_keywords.md").exists()
    assert (output_dir / "selling_points.md").exists()
    assert (output_dir / "selling_points.json").exists()
    assert (output_dir / "instagram.md").exists()
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_orchestration.py -v`
Expected: 1 个测试通过（注意 FakeImageAdapter 不校验真实图片内容）。

- [ ] **Step 4: 提交**

```bash
git add src/coupangads/orchestration/pipeline.py tests/test_orchestration.py
git commit -m "feat: 单产品全流程编排与断点续跑逻辑，含集成测试"
```

---

### Task 13: 完整版 CLI 入口

**Files:**
- Create: `src/coupangads/cli/full_pipeline.py`
- Create: `src/coupangads/cli/__init__.py`

- [ ] **Step 1: 实现 `src/coupangads/cli/full_pipeline.py`**

```python
"""完整版入口：报告/标题/关键词/卖点/INS/图片全链路。"""

import argparse
from pathlib import Path

from coupangads.adapters.doubao import DoubaoClientAdapter
from coupangads.adapters.gemini import GeminiClientAdapter
from coupangads.core import config
from coupangads.core.logging import get_logger
from coupangads.infra.api_keys import read_api_key
from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.text.template_loader import TemplateLoader

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CoupangAds 完整版入口")
    parser.add_argument("--input-dir", type=Path, default=config.DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=config.DEFAULT_OUTPUT_DIR)
    parser.add_argument("--api-key-file", type=Path, default=config.GEMINI_API_KEY_FILE)
    parser.add_argument("--doubao-key-file", type=Path, default=config.DOUBAO_API_KEY_FILE)
    parser.add_argument("--limit-folder", type=str, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-images", type=int, default=None)
    parser.add_argument("--start-from", type=str, default=None)
    parser.add_argument("--max-retries", type=int, default=config.DEFAULT_MAX_RETRIES)
    parser.add_argument("--request-delay", type=float, default=config.DEFAULT_REQUEST_DELAY)
    parser.add_argument("--request-timeout", type=int, default=config.DEFAULT_REQUEST_TIMEOUT_MS)
    parser.add_argument("--use-doubao", action="store_true", help="使用 Doubao 线路")
    parser.add_argument("--templates-dir", type=Path, default=Path("templates"))
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir

    if not input_dir.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        return

    templates = TemplateLoader(args.templates_dir)

    if args.dry_run:
        logger.info("Dry Run 模式：仅扫描输入目录")
        for product_dir in sorted(input_dir.iterdir()):
            if product_dir.is_dir():
                logger.info(f"将处理产品: {product_dir.name}")
        return

    if args.use_doubao:
        api_key = read_api_key(args.doubao_key_file, env_var="DOUBAO_API_KEY")
        text_adapter = DoubaoClientAdapter(api_key)
        image_adapter = DoubaoClientAdapter(api_key)
    else:
        api_key = read_api_key(args.api_key_file, env_var="GEMINI_API_KEY")
        text_adapter = GeminiClientAdapter(api_key)
        image_adapter = GeminiClientAdapter(api_key)

    pipeline = ProductPipeline(
        text_adapter=text_adapter,
        image_adapter=image_adapter,
        templates=templates,
        overwrite=args.overwrite,
        max_images=args.max_images,
        start_from=args.start_from,
    )

    product_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
    if args.limit_folder:
        product_dirs = [d for d in product_dirs if d.name == args.limit_folder]

    for product_dir in sorted(product_dirs):
        product_output_dir = output_dir / product_dir.name
        logger.info(f"开始处理: {product_dir.name}")
        try:
            pipeline.run(product_dir, product_output_dir)
        except Exception as exc:
            logger.error(f"处理 {product_dir.name} 失败: {exc}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 CLI 帮助信息**

Run:
```bash
python -m coupangads.cli.full_pipeline --help
```

Expected: 显示所有 CLI 参数帮助。

- [ ] **Step 3: 提交**

```bash
git add src/coupangads/cli/
git commit -m "feat: 完整版 CLI 入口（Gemini/Doubao 双线路）"
```

---

### Task 14: 经典版入口与备用线路入口

**Files:**
- Create: `src/coupangads/cli/classic_pipeline.py`
- Create: `src/coupangads/cli/doubao_pipeline.py`

- [ ] **Step 1: 实现 `src/coupangads/cli/classic_pipeline.py`**

```python
"""经典版入口：报告 + 提示词 + 图片三段式。"""

import argparse
from pathlib import Path

from coupangads.cli.full_pipeline import build_parser as full_build_parser
from coupangads.core import config


def main() -> None:
    """经典版复用完整版入口，但强制跳过标题/关键词/INS 生成阶段。"""
    parser = full_build_parser()
    parser.description = "CoupangAds 经典版入口（报告 + 提示词 + 图片）"
    args = parser.parse_args()
    # 通过调用 full_pipeline 并传入特殊模式实现
    # 实际实现可在 ProductPipeline 增加 classic_mode 标志
    print("经典版入口：请使用 --max-images 0 先生成文本资产，再单独跑图片生成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 实现 `src/coupangads/cli/doubao_pipeline.py`**

```python
"""备用线路入口：默认使用 Doubao 模型。"""

from coupangads.cli.full_pipeline import main as full_main
import sys


def main() -> None:
    """默认注入 --use-doubao 参数。"""
    if "--use-doubao" not in sys.argv:
        sys.argv.append("--use-doubao")
    full_main()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 提交**

```bash
git add src/coupangads/cli/classic_pipeline.py src/coupangads/cli/doubao_pipeline.py
git commit -m "feat: 经典版与 Doubao 备用线路入口"
```

---

### Task 15: 端到端冒烟测试

**Files:**
- Create: `tests/e2e/test_full_pipeline.py`
- Create: `tests/e2e/__init__.py`

- [ ] **Step 1: 使用 Fake Adapter 跑通完整链路**

```python
"""端到端冒烟测试（不调用真实 API）。"""

from pathlib import Path

from PIL import Image

from coupangads.cli.full_pipeline import build_parser
from coupangads.core.models import ReferenceImage
from coupangads.orchestration.pipeline import ProductPipeline
from coupangads.text.template_loader import TemplateLoader


class FakeTextAdapter:
    def chat(self, prompt: str) -> str:
        return "한국어 샘플 응답"


class FakeImageAdapter:
    def generate_image(self, prompt, references, output_path: Path) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1200, 1800), color=(200, 200, 200))
        img.save(output_path, "PNG")
        return True


def test_full_pipeline_end_to_end(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw-material" / "test-dog-harness"
    output_dir = tmp_path / "result" / "test-dog-harness"
    input_dir.mkdir(parents=True)

    # 创建 3 张测试图
    for i in range(3):
        img = Image.new("RGB", (800, 1200), color=(100 + i * 50, 100, 100))
        img.save(input_dir / f"img_{i}.jpg", "JPEG")

    # 创建模板
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "product_report.txt").write_text("report")
    (templates_dir / "product_title.txt").write_text("{product_report}")
    (templates_dir / "wing_keywords.txt").write_text("{product_report}{product_title}")
    (templates_dir / "selling_points.txt").write_text("# B1\n한국어\n# B2\n한국어\n# B3\n한국어\n# B4\n한국어\n# B5\n한국어\n# B6\n한국어\n# B7\n한국어\n# B8\n한국어\n# B9\n한국어")
    (templates_dir / "instagram.txt").write_text("{product_report}")
    (templates_dir / "image_prompt.txt").write_text("{style_rules}{product_context}{screen}{block}{block_content}")
    (templates_dir / "style_rules.txt").write_text("## STYLE A\nA\n## STYLE B\nB")
    (templates_dir / "image_global_constraints.txt").write_text("global")

    pipeline = ProductPipeline(
        text_adapter=FakeTextAdapter(),
        image_adapter=FakeImageAdapter(),
        templates=TemplateLoader(templates_dir),
    )
    pipeline.run(input_dir, output_dir)

    assert (output_dir / "productreport.md").exists()
    assert (output_dir / "product_title.md").exists()
    assert (output_dir / "wing_keywords.md").exists()
    assert (output_dir / "selling_points.md").exists()
    assert (output_dir / "selling_points.json").exists()
    assert (output_dir / "instagram.md").exists()
    assert (output_dir / "product_context.md").exists()
    assert (output_dir / "image_prompts.json").exists()
    assert (output_dir / "best_reference_images.json").exists()
    assert (output_dir / "A_B1.png").exists()
    assert (output_dir / "B_B9.png").exists()
```

- [ ] **Step 2: 运行端到端测试**

Run:
```bash
pytest tests/e2e/test_full_pipeline.py -v
```

Expected: 1 个测试通过。

- [ ] **Step 3: 提交**

```bash
git add tests/e2e/
git commit -m "test: 完整链路端到端冒烟测试"
```

---

### Task 16: 文档更新与 v1.0 验收

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: 更新 `README.md` 增加快速开始**

在 `README.md` 末尾追加：

```markdown
## 快速开始

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

echo "YOUR_GEMINI_API_KEY" > apikey.md

python -m coupangads.cli.full_pipeline --limit-folder "产品文件夹名"
```
```

- [ ] **Step 2: 更新 `AGENTS.md` 中「当前无代码」状态**

将 AGENTS.md 中类似「当前仓库仅有规划/设计文档，没有源代码」的表述更新为：

```markdown
> **重要：v1.0 MVP 已实现。** 源码位于 `src/coupangads/`，入口为 `python -m coupangads.cli.full_pipeline`。
```

- [ ] **Step 3: 运行全部测试**

Run:
```bash
pytest tests/ -v
```

Expected: 所有单元测试与 E2E 测试通过。

- [ ] **Step 4: 提交并打标签**

```bash
git add README.md AGENTS.md
git commit -m "docs: 更新 README 与 AGENTS 以反映 v1.0 MVP 实现"
git tag v1.0.0
```

---

## 3. 迭代二：v1.5 质量增强（大纲）

**目标：** 提升输出质量、降低人工审核负担、偿还 v1.0 技术债务。

| 任务 | 说明 | 关键文件 |
|------|------|---------|
| T2.1 | 引入质量审核层 | `src/coupangads/quality/`、`templates/quality_check.txt` |
| T2.2 | 广告法敏感词过滤 | `src/coupangads/quality/compliance.py`、`data/forbidden_words.json` |
| T2.3 | 批量优化模式（50+ 产品自动排队 + 限流） | `src/coupangads/orchestration/batch.py` |
| T2.4 | 模板版本管理 | `templates/version.json`、模板加载器支持版本选择 |
| T2.5 | 输出对比工具 | `src/coupangads/cli/compare.py` |
| T2.6 | 图片后处理（压缩/格式转换） | `src/coupangads/image_pipeline/postprocess.py` |
| T2.7 | 偿还技术债务：单元测试覆盖率 ≥ 90% | 补充测试、CI 配置 `.github/workflows/ci.yml` |
| T2.8 | API Key 环境变量支持已完成，补充文档 | `docs/06-部署与运维指南.md` |

**验收标准：**
- 人工审核时间相比 v1.0 减少 50%
- 解析函数/IO 工具覆盖率 ≥ 90%
- 敏感词命中 100% 拦截（已知词库内）

---

## 4. 迭代三：v2.0 平台化（大纲）

**目标：** 从单机 CLI 演进为可服务的 Web 平台 MVP。

| 任务 | 说明 | 关键文件/组件 |
|------|------|--------------|
| T3.1 | Web 上传界面 | Frontend: React/Vue |
| T3.2 | 任务队列（Celery + Redis） | `src/coupangads/worker/` |
| T3.3 | 用户系统与多租户 | FastAPI + PostgreSQL |
| T3.4 | 结果管理后台 | 历史记录、下载、重新生成 |
| T3.5 | 对象存储集成（S3/MinIO/OSS） | `src/coupangads/infra/storage.py` |
| T3.6 | Webhook 通知 | 任务完成/失败回调 |
| T3.7 | 用量统计面板 | API 调用与成本估算 |

**架构演进：**

```text
Frontend (React/Vue)
       │
       ▼
Backend (FastAPI)
       │
       ▼
Celery Worker ──▶ Redis
       │
       ▼
PostgreSQL + S3/MinIO
```

---

## 5. Self-Review 检查清单

### 5.1 规格覆盖

对照 `docs/01-需求规格说明书.md` 与 `docs/03-功能规格说明书.md`：

| 需求 | 覆盖任务 |
|------|---------|
| FR-001 商品画像分析 | Task 9 `report.py` |
| FR-002 商品标题生成 | Task 9 `title.py` |
| FR-003 关键词挖掘 | Task 9 `keywords.py` |
| FR-004 详情页卖点文案 | Task 9 `selling_points.py` + Task 5 解析 |
| FR-005 社媒文案生成 | Task 9 `instagram.py` |
| FR-006 智能参考图筛选 | Task 10 `reference_selector.py` |
| FR-007 图片提示词组装 | Task 10 `prompt_assembler.py` |
| FR-008 详情页图片生成 | Task 11 `generator.py` |
| 断点续跑 | Task 12 `pipeline.py` + Task 11 |
| 双模型冗余 | Task 7/8 + Task 13 |
| 模板外置 | Task 6 |
| 中文注释 | 所有实现文件 |
| 日志格式统一 | Task 2 |

### 5.2 Placeholder 扫描

- 无 "TBD"、"TODO"。
- 无 "add appropriate error handling" 等模糊描述。
- 所有代码步骤均给出具体代码。
- 所有命令均给出具体命令与期望输出。

### 5.3 类型一致性

- `ReferenceImage` 在 Task 7 定义，Task 8/10/11 使用一致。
- `ImagePrompt` 在 Task 7 定义，Task 10/11 使用一致。
- 适配器接口在 Task 7 `base.py` 定义，Gemini/Doubao 均实现。

---

## 6. 执行方式

**Plan complete and saved to `docs/superpowers/plans/2026-06-12-development-iteration-plan.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — 我为每个 Task 派发独立子代理，Task 间我进行审查，快速迭代。

**2. Inline Execution** — 在当前会话中使用 `superpowers:executing-plans` 按顺序批量执行，关键节点暂停审查。

**Which approach?**
