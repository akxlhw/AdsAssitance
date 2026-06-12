# CoupangAds MVP 前端设计文档

> **状态**：已确认，待实现  
> **关联计划**：`docs/superpowers/plans/2026-06-12-development-iteration-plan.md`

---

## 1. 设计目标

为 CoupangAds v1.0 MVP 提供一个**本地 Web UI**，让跨境卖家可以通过浏览器完成从产品图上传到内容资产下载的完整流程。同时保留原有 CLI 入口，实现双入口并存。

核心目标：

- **降低使用门槛**：不需要记忆命令行参数。
- **即时反馈**：上传、生成进度、结果预览全部在一个页面内完成。
- **视觉差异化**：内置 6 套可切换主题，让工具本身就有品牌感。
- **可扩展**：主题系统和组件系统便于后续增加更多主题和功能。

---

## 2. 设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端形态 | 本地 Web UI | 用户选择 A，平衡开发成本与交互体验 |
| 页面结构 | 单页三态（上传/生成/结果） | 用户选择 A，信息密度低，学习成本最小 |
| 主题数量 | 6 个内置主题 | 用户在 5-8 个范围内选择全部 6 个推荐主题 |
| 主题实现 | CSS 变量 + `data-theme` | 无刷新切换，便于扩展 |
| 后端框架 | FastAPI | Python 原生、异步、API 文档自动生成 |
| 前端技术 | 纯 HTML + CSS + JS | 无构建步骤，与 CSS 变量主题系统天然契合 |
| 实时进度 | Server-Sent Events (SSE) | 单向推送足够，复杂度低于 WebSocket |
| API 配置 | 本地文件 + Web UI 设置面板 | 密钥不落浏览器存储，后端写入 apikey.md / dbkey.md |
| CLI 入口 | 保留 | 与 Web UI 共用底层生成链路 |

---

## 3. 用户旅程

```text
打开浏览器 → http://localhost:8000
    │
    ▼
[上传态]
  ├─ 拖放/选择产品图（3-10 张）
  ├─ 切换主题预览
  ├─ 选择 API 线路（Gemini / Doubao）
  └─ 点击「开始生成」
    │
    ▼
[生成态]
  ├─ 总进度条
  ├─ 文本链路步骤：画像 → 标题 → 关键词 → 卖点 → INS
  ├─ 图片链路网格：18 张逐步生成
  └─ 可展开实时日志
    │
    ▼
[结果态]
  ├─ 文案卡片（报告/标题/关键词/卖点/INS）
  ├─ 图片画廊（A 风格 / B 风格 Tab）
  └─ 一键下载 ZIP
```

---

## 4. 架构

```text
┌─────────────────────────────────────────┐
│            浏览器（前端）                │
│  ├─ 单页应用（index.html）               │
│  ├─ 主题切换（CSS 变量）                 │
│  ├─ 上传组件                             │
│  ├─ 进度面板（SSE）                      │
│  └─ 结果画廊                             │
└─────────────────────────────────────────┘
                    │ HTTP / SSE
                    ▼
┌─────────────────────────────────────────┐
│         FastAPI 后端（Python）           │
│  ├─ /api/upload       上传产品图         │
│  ├─ /api/config       读取/更新 API 配置 │
│  ├─ /api/generate     触发生成           │
│  ├─ /api/progress     SSE 实时进度       │
│  ├─ /api/result       结果文件列表       │
│  └─ /api/download     ZIP 下载           │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│      Python 生成链路（复用 CLI）          │
│  ├─ ProductPipeline                     │
│  ├─ TextAdapter / ImageAdapter          │
│  └─ 输出到 result/产品名/                │
└─────────────────────────────────────────┘
```

---

## 5. 页面结构

### 5.1 全局布局

```text
┌─────────────────────────────────────────┐
│  Logo              [主题切换器]          │  ← header 固定
├─────────────────────────────────────────┤
│                                         │
│           主体内容区（三态之一）          │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

### 5.2 上传态

```text
┌─────────────────────────────────────────┐
│          CoupangAds    [主题▼]          │
├─────────────────────────────────────────┤
│                                         │
│     ┌─────────────────────────┐        │
│     │                         │        │
│     │      📁 拖放图片到这里   │        │
│     │      支持 JPG/PNG/HEIC  │        │
│     │                         │        │
│     └─────────────────────────┘        │
│                                         │
│   [缩略图预览网格]                       │
│                                         │
│   ▼ 高级选项                             │
│   模型线路：● Gemini  ○ Doubao          │
│   最大图片数：[ 18  ]                    │
│   [ 强制覆盖 ]                           │
│                                         │
│          [  开 始 生 成  ]               │
│                                         │
└─────────────────────────────────────────┘
```

### 5.3 生成态

```text
┌─────────────────────────────────────────┐
│  总进度 ████████████░░░░ 60%            │
├─────────────────────────────────────────┤
│  文本链路                                │
│  ✅ 商品画像  ✅ 标题  ✅ 关键词         │
│  ✅ 卖点      ⏳ INS    ○ 图片          │
├─────────────────────────────────────────┤
│  图片生成                                │
│  ┌────┐┌────┐┌────┐┌────┐...           │
│  │A_B1││B_B1││A_B2││B_B2│...           │
│  └────┘└────┘└────┘└────┘              │
│                                         │
│  [展开实时日志]                          │
└─────────────────────────────────────────┘
```

### 5.4 结果态

```text
┌─────────────────────────────────────────┐
│  [文案] [图片] [日志]                    │
├─────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐      │
│  │ 商品画像     │  │ 商品标题     │      │
│  │ [复制]      │  │ [复制]      │      │
│  └─────────────┘  └─────────────┘      │
│                                         │
│  [A 风格] [B 风格]                       │
│  ┌────┐┌────┐┌────┐┌────┐              │
│  │    ││    ││    ││    │              │
│  └────┘└────┘└────┘└────┘              │
│                                         │
│      [  下 载 全 部 资 产  ]             │
└─────────────────────────────────────────┘
```

---

## 6. 主题系统

### 6.1 主题列表

| 主题 ID | 名称 | 气质 | 适用场景 |
|---------|------|------|---------|
| `korean-minimal` | 韩系极简高级 | 白底、黑字、精致衬线 | 专业、商务 |
| `editorial` | 编辑杂志风 | 黑底、高对比、大字号 | 创意团队 |
| `warm-healing` | 温暖治愈风 | 暖 beige、圆润、亲和 | 宠物品牌卖家 |
| `dark-industrial` | 暗色工业风 | 深灰、等宽字体、数据感 | 技术型运营、夜间 |
| `retro-film` | 复古胶片风 | 暖棕、颗粒、胶片边框 | 强调真实摄影质感 |
| `cyber-neon` | 赛博荧光风 | 深黑、霓虹 accent、发光 | 年轻团队 |

### 6.2 CSS 变量规范

每个主题文件必须定义以下变量：

```css
:root[data-theme="korean-minimal"] {
  --bg-primary: #ffffff;
  --bg-secondary: #fafafa;
  --bg-tertiary: #f5f5f5;
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --accent: #111111;
  --accent-secondary: #4ade80;
  --border: #e5e5e5;
  --font-display: 'Noto Serif KR', serif;
  --font-body: 'Noto Sans KR', sans-serif;
  --radius: 12px;
}
```

### 6.3 主题切换

- 通过 JavaScript 修改 `<html>` 的 `data-theme` 属性。
- 所有使用 CSS 变量的元素自动过渡。
- 主题选择记忆在 `localStorage`。

---

## 7. 组件规范

### 7.1 上传区

- 默认显示大拖放区。
- 拖拽进入时：边框颜色变为 `--accent`，背景轻微变亮。
- 上传后显示缩略图网格，每张图右上角有删除按钮。

### 7.2 进度条

- 顶部固定总进度条。
- 渐变色：从 `--accent` 到 `--accent-secondary`。
- 未完成部分使用 `--bg-tertiary`。

### 7.3 步骤条

- 文本链路 5 步，每步三种状态：未开始 / 进行中 / 完成。
- 完成态使用 `--accent` 背景。

### 7.4 图片网格

- 18 张卡片，按 A/B 风格分组或交错排列。
- 生成前显示占位图（灰度 + 文件名）。
- 生成完成后以缩放动画替换为真实图片。

### 7.5 文案卡片

- 可折叠面板。
- 标题栏固定，内容区 Markdown 渲染。
- 右上角「复制」按钮。

### 7.6 API 配置面板

- **入口**：右上角设置图标 ⚙️，点击打开模态框。
- **内容**：
  - Gemini API Key 输入框
  - Doubao API Key 输入框
  - 默认模型线路选择（Gemini / Doubao）
- **安全约束**：
  - 密钥输入框默认显示为掩码（`••••••`）。
  - 密钥通过后端写入 `apikey.md` / `dbkey.md`，**不存储在浏览器 localStorage**。
  - 前端仅显示「已配置 / 未配置」状态。
- **校验**：保存时后端尝试读取文件首行非空内容，空值报错。

---

## 8. 动效规范

| 场景 | 效果 | 时长 |
|------|------|------|
| 主题切换 | 背景/文字/边框颜色过渡 | 0.5s ease |
| 状态切换（上传→生成→结果） | 淡入 + 上移 20px | 0.4s ease-out |
| 进度更新 | 宽度变化 + 脉冲 | 0.3s ease |
| 图片完成 | 占位图缩放消失，真实图缩放出现 | 0.5s ease |
| 卡片悬停 | 上移 4px + 阴影加深 | 0.2s ease |
| 上传区拖拽 | 边框高亮 + scale(1.01) | 0.2s ease |

---

## 9. API 设计

### 9.1 上传产品图

```http
POST /api/upload
Content-Type: multipart/form-data

product_name: string
files: File[]
```

响应：

```json
{
  "product_id": "test-dog-harness",
  "product_dir": "raw-material/test-dog-harness",
  "file_count": 5
}
```

### 9.2 触发生成

```http
POST /api/generate/{product_id}
Content-Type: application/json

{
  "provider": "gemini",
  "max_images": 18,
  "overwrite": false,
  "start_from": null
}
```

响应：

```json
{
  "status": "started",
  "product_id": "test-dog-harness"
}
```

### 9.3 实时进度（SSE）

```http
GET /api/progress/{product_id}
```

事件流：

```jsonl
event: step
{"step": "product_report", "status": "started", "message": "开始生成商品画像"}

event: step
{"step": "product_report", "status": "completed", "message": "商品画像完成"}

event: image
{"filename": "A_B1.png", "status": "completed"}

event: complete
{"status": "completed", "output_dir": "result/test-dog-harness"}

event: error
{"step": "A_B4.png", "message": "图片生成失败"}
```

### 9.4 获取结果

```http
GET /api/result/{product_id}
```

响应：

```json
{
  "product_id": "test-dog-harness",
  "text_files": [
    {"name": "productreport.md", "path": "..."},
    {"name": "product_title.md", "path": "..."}
  ],
  "images": [
    {"name": "A_B1.png", "style": "A", "block": "B1", "path": "..."}
  ]
}
```

### 9.5 下载 ZIP

```http
GET /api/download/{product_id}
```

响应：ZIP 文件流。

### 9.6 API 配置

```http
GET /api/config
```

响应（掩码处理，不返回完整密钥）：

```json
{
  "gemini_configured": true,
  "doubao_configured": false,
  "default_provider": "gemini"
}
```

```http
POST /api/config
Content-Type: application/json

{
  "gemini_api_key": "...",
  "doubao_api_key": "...",
  "default_provider": "gemini"
}
```

响应：

```json
{
  "status": "saved"
}
```

**安全说明**：
- POST 请求中的密钥由后端写入 `apikey.md` / `dbkey.md`。
- 如果传入空字符串，表示不修改该密钥。
- 返回给前端的状态仅用于显示「已配置 / 未配置」。

---

## 10. 文件结构

```text
src/coupangads/
├── cli/                    # 保留的 CLI 入口
│   ├── full_pipeline.py
│   ├── classic_pipeline.py
│   └── doubao_pipeline.py
├── web/                    # 新增 Web UI
│   ├── __init__.py
│   ├── app.py              # FastAPI 应用工厂
│   ├── api.py              # API 路由
│   ├── static/
│   │   ├── css/
│   │   │   ├── base.css
│   │   │   ├── components.css
│   │   │   └── themes/
│   │   │       ├── korean-minimal.css
│   │   │       ├── editorial.css
│   │   │       ├── warm-healing.css
│   │   │       ├── dark-industrial.css
│   │   │       ├── retro-film.css
│   │   │       └── cyber-neon.css
│   │   └── js/
│   │       ├── main.js
│   │       ├── theme.js
│   │       ├── config.js
│   │       ├── upload.js
│   │       ├── progress.js
│   │       └── gallery.js
│   └── templates/
│       └── index.html
└── ...
```

---

## 11. 错误处理

| 场景 | 前端行为 | 后端行为 |
|------|---------|---------|
| 上传文件格式不支持 | 提示「仅支持 JPG/PNG/HEIC/WEBP」 | 返回 400 |
| 图片不足 3 张 | 提示「建议上传 3-10 张产品图」 | 返回 400 |
| API Key 缺失 | 弹窗提示配置 `apikey.md` | 返回 500 + 明确错误 |
| 单张图片生成失败 | 该卡片显示错误态，继续显示其他结果 | 记录日志，继续下一张 |
| 生成任务取消 | 进度条停止，显示「已取消」 | 停止 pipeline |

---

## 12. 性能考虑

- 图片上传：限制单张 10MB，前端压缩预览图。
- 图片预览：生成缩略图而非原图，避免内存占用。
- SSE 重连：连接断开时自动重连，最多 5 次。
- 主题 CSS：按需加载，默认加载当前主题，切换时动态加载其他主题文件。

---

## 13. 未来扩展

- v1.5：结果对比模式、批量产品列表视图、主题自定义入口。
- v2.0：用户系统、历史任务列表、对象存储、Web 部署。

---

## 14. 视觉参考

设计过程中使用 Visual Companion 生成了以下参考文件，保存在：

```textn.superpowers/brainstorm/1342-1781287999/content/
├── mvp-layout-options.html
├── visual-direction.html
├── theme-set.html
├── theme-system-preview-v2.html
├── theme-switcher-demo.html
└── design-summary.html
```

其中 `theme-switcher-demo.html` 是可直接交互的 6 主题切换演示。

---

## 15. Spec Self-Review

- **Placeholder 扫描**：无 TBD/TODO/模糊描述。
- **内部一致性**：主题变量、API 路径、文件结构前后一致。
- **范围检查**：聚焦 MVP Web UI，未引入 v2.0 功能。
- **歧义检查**：主题 ID、API 字段、文件命名均已明确。
