# 生成过程中止功能设计文档

## 背景

当前生成一旦开始就无法中止，用户必须等待全部完成或刷新页面。需要提供一个可控的中止机制。

## 目标

允许用户在生成过程中点击中止按钮，后端在当前步骤完成后停止后续步骤，前端保留已生成的部分结果。

## 交互设计

### 进度页

- 在百分比/进度条区域增加一个「中止生成」按钮
- 按钮样式为低调的次级按钮，避免与主视觉冲突
- 点击后按钮变为禁用状态，文案变为「正在中止...」

### 中止流程

1. 用户点击「中止生成」
2. 前端发送 `POST /api/abort/{product_id}`
3. 后端设置该任务的中止标记
4. 后端流水线在当前步骤完成后检测到标记，停止执行
5. 后端推送 `status: 'aborted'` 给 SSE
6. 前端关闭 SSE，显示「已中止」提示
7. 已生成的预览卡片保留可见
8. 显示「查看已生成结果」按钮，点击后跳到结果页

### 结果页

- 结果页正常加载已生成的文件
- 未生成的步骤对应的文件不存在，不显示

## 技术实现

### 后端

- 新增 `_abort_flags: dict[str, bool]`
- 新增 `POST /api/abort/{product_id}` endpoint
- `_run_pipeline` 中每完成一个步骤调用 `check_abort(product_id)`
- `ProductPipeline.run` 增加 `abort_callback` 参数，在关键断点检查
- 中止时抛出 `GenerationAborted` 异常，被 `_run_pipeline` 捕获后状态设为 `aborted`

### 前端

- `progress.js` 中渲染中止按钮
- 绑定点击事件发送 abort 请求
- SSE 收到 `aborted` 后关闭连接、更新 UI
- 显示「查看已生成结果」按钮

### 需要修改的文件

- `src/coupangads/web/api.py`
- `src/coupangads/orchestration/pipeline.py`
- `src/coupangads/web/static/js/progress.js`
- `src/coupangads/web/static/css/components.css`
- `src/coupangads/web/templates/index.html`

## 验收标准

1. 进度页显示「中止生成」按钮
2. 点击后后端在当前步骤完成后停止
3. SSE 推送 `aborted` 状态
4. 前端显示「已中止」和「查看已生成结果」
5. 已生成文件保留并可预览
6. 未中止时功能完全不变
