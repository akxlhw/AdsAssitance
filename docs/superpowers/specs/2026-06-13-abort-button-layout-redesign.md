# 中止按钮视觉布局重设计

## 背景

当前进度页采用「沉静极简 · 流体进度」风格：大字号百分比、3px 细进度条、shimmer 流光、步骤标签淡入淡出。中止按钮原方案是放在进度条下方的红色描边按钮，视觉上过于抢眼，与整体冷静、极简的氛围冲突。

## 目标

在不降低可发现性的前提下，让「中止生成」控件融入进度页视觉节奏，避免在主视觉区形成突兀色块；同时保持操作反馈清晰（hover、loading、aborted 状态）。

## 设计方案

### 位置

中止控件放在**状态消息行末尾**，与当前步骤消息同行显示。

```
[ 67% ]
[ 正在生成详情页图片...    中止 ]
[==========>          ]
```

### 视觉规范

| 状态 | 字体大小 | 颜色 | 下划线 | cursor |
|------|----------|------|--------|--------|
| 默认 | 0.8rem | `var(--text-secondary)` 50% 透明度 | 无 | pointer |
| hover / focus-visible | 0.8rem | `var(--error)` | 有 | pointer |
| 点击后（loading） | 0.8rem | `var(--text-secondary)` 50% 透明度 | 无 | not-allowed |
| 已中止 | 控件隐藏 | — | — | — |

- 使用 `<button>` 元素而非 `<a>`，确保键盘可访问；`focus-visible` 使用与 hover 一致的红色下划线/轮廓。
- 状态行使用 `display: flex; justify-content: center; align-items: center; gap: 0.5rem;`，保证消息文字与中止控件在同一基线。
- 中止控件在消息较长或移动端小屏时允许自然换行；换行后保持居中。

### 交互状态

#### 生成中

- 默认：浅灰细字「中止」。
- hover：变红并出现下划线，提示为破坏性操作。
- 点击：文字立即变为「正在中止...」，移除 hover 样式，禁用 pointer 事件，保持暗淡，避免用户重复点击。

#### 请求失败

- 在状态消息行下方显示简短 inline 错误：红色小字「中止请求失败，请重试」。
- 恢复「中止」为可点击状态。

#### 已中止

- 中止控件隐藏。
- 状态消息改为「生成已中止」。
- 进度条停止 shimmer，进度保持为实际进度。
- 下方出现「查看已生成结果」主按钮（保持现有行为）。

## 改动范围

- `src/coupangads/web/templates/index.html`：移除独立的 `progress-actions` / `abort-button`，在状态消息容器内内嵌中止控件。
- `src/coupangads/web/static/css/components.css`：
  - 删除或重构 `.progress-actions`、`.abort-button`、`.abort-error` 的现有样式。
  - 新增 `.progress-message` 的 flex 布局与 `.abort-link` 样式。
- `src/coupangads/web/static/js/progress.js`：
  - 更新 DOM 选择器：中止控件改为 `#abort-link`（`<button>`）。
  - 更新 loading / error / aborted 状态的样式切换逻辑。

## 非目标

- 不改中止的后端逻辑、API 接口、SSE 事件。
- 不改「查看已生成结果」按钮位置与样式。
- 不改进度条、百分比、步骤、预览栏的现有样式。

## 验收标准

1. 进度页生成中时，中止控件以浅灰细字显示在状态消息末尾。
2. hover 时变红并出现下划线。
3. 点击后变为「正在中止...」且不可再次点击。
4. 请求失败显示 inline 错误并恢复可点击。
5. 已中止后中止控件消失，状态消息变为「生成已中止」。
6. `pytest -q` 全部通过。
7. 手动 mock 模式验证：能正常中止并跳转结果页。
