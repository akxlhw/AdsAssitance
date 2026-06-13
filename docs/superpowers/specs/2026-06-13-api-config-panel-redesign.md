# API 配置面板重设计

## 背景

当前 API 配置面板是一个简单的居中 modal，使用原生 `<select>` 和下划线风格的输入框，视觉粗糙，与「沉静极简 · 流体进度」的整体风格不协调。用户反馈「巨丑」，需要重设计。

## 目标

将配置面板改造成干净、 calm、分组清晰的界面，使其与现有 korean-minimal 主题一致，同时提升可用性：
- 一眼看清当前 provider 选择
- 只显示与当前选择相关的字段，减少认知负担
- Mock 模式作为一等选项，明确提示离线状态
- API Key 配置状态可视化（已配置 / 未配置）

## 设计方案

### 容器

保持 **居中 Modal**，但整体视觉升级：
- 更宽的白色卡片（max-width ~420px）
- 柔和阴影 + 半透明 backdrop
- 淡入 + 轻微上滑动画
- 点击 backdrop 或按 ESC 关闭
- 去除显式关闭按钮，保持极简

### 标题区

居中：
- 标题：`API 配置`，字号 1.1rem，字重 600
- 副标题：`选择模型提供商并填写密钥`，字号 0.8rem，`var(--text-secondary)`

### 内容结构

按「文本生成」「图片生成」分成两个卡片区块。

#### 区块 1：文本生成

1. **区块标题**：`文本生成`，字号 0.8rem，字重 600
2. **Provider Segmented Control**：
   - 选项：Gemini / DeepSeek / Mock
   - 当前选中：深色填充（`var(--text-primary)` bg + 白色字）
   - 未选中：浅色边框 + 深色字
   - 三段等宽，圆角 4px
3. **动态字段区**（根据 provider 变化）：
   - **Gemini**：显示 `Gemini API Key` 输入框 + 状态标签
   - **DeepSeek**：显示 `DeepSeek API Key` 输入框 + 状态标签，`DeepSeek Model` 输入框
   - **Mock**：显示绿色提示条「Mock 模式：离线开发，不调用真实 API」，隐藏所有密钥输入

#### 区块 2：图片生成

1. **区块标题**：`图片生成`
2. **Provider Segmented Control**：
   - 选项：Gemini / Doubao / Mock
3. **动态字段区**：
   - **Gemini**：`Gemini API Key` 输入框 + 状态标签
   - **Doubao**：`Doubao API Key` 输入框 + 状态标签
   - **Mock**：绿色提示条，隐藏密钥输入

### 字段细节

- **输入框**：
  - `type="password"`
  - 圆角 `var(--radius)`
  - 边框 1px `var(--border)`
  - 浅灰背景 `#fafafa`
  - 字号 0.75rem
  - placeholder：
    - 已配置状态：`留空以保持不变`
    - 未配置状态：`输入 API Key`

- **状态标签**：
  - 已配置：绿色 `var(--accent)` 或自定义成功绿，字号 0.7rem
  - 未配置：红色 `var(--error)`，字号 0.7rem
  - 位于 label 右侧

- **Mock 提示条**：
  - 背景浅绿 `#f0f9f4`
  - 边框 1px 绿
  - 文字绿色
  - 字号 0.75rem
  - padding 0.625rem
  - 圆角 `var(--radius)`

### 保存按钮

- 底部通栏
- 文案：`保存配置`
- 样式：主按钮（深色背景、白色字）
- 点击后提交表单，关闭 modal，重新初始化配置状态

### 动画

- Modal 打开：backdrop 淡入 0.2s，卡片从 `translateY(10px)` + `opacity: 0` 过渡到原位 0.3s ease
- Modal 关闭：反向动画
- Provider 切换：字段区淡入淡出 0.2s

## 交互逻辑

1. 打开 modal 时：
   - 从 `/api/config` 获取当前配置和密钥状态
   - 设置 segmented control 的当前选中项
   - 根据 provider 显示对应字段
   - 更新状态标签

2. 切换 provider 时：
   - 立即切换显示对应的字段区
   - 保留已填写但未保存的输入值（不丢失用户输入）

3. 保存时：
   - 收集当前所有可见字段的值
   - POST 到 `/api/config`
   - 关闭 modal
   - 重新调用 `initConfigPanel()` 刷新状态

## 改动范围

- `src/coupangads/web/templates/index.html`：重写 `#config-modal` 结构
- `src/coupangads/web/static/css/components.css`：新增/重写 modal 与配置面板样式
- `src/coupangads/web/static/js/config.js`：重写 provider 切换、字段显隐、状态渲染、保存逻辑

## 非目标

- 不改 `/api/config` 后端接口
- 不改 header 上的 ⚙️ 按钮触发方式
- 不增加新的 provider 或配置项
- 不改主题系统

## 验收标准

1. 配置面板以居中 modal 打开，视觉风格与首页一致。
2. 文本/图片生成各有一个 provider segmented control。
3. 切换 provider 时只显示相关字段。
4. 已配置 / 未配置状态标签正确显示。
5. 选中 Mock 时显示绿色提示条，隐藏密钥输入。
6. 保存后配置生效，modal 关闭，状态刷新。
7. 点击 backdrop 或按 ESC 可关闭 modal。
8. `pytest -q` 全部通过。
9. 手动验证各 provider 组合下的字段显示与保存。
