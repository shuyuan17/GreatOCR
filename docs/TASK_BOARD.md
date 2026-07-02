# TASK BOARD

最后更新：2026-07-02

## 项目阶段

1. V2.1：重建质量核心
2. V2.2：选页与多 provider 架构
3. V2.3：本地 FastAPI + React 图形界面
4. V2.4：便携打包与发布验收

## 当前总体判断

- 主线 `main`：已完成 V2.2，可作为稳定 CLI/引擎基线
- V2.3：正在独立工作树推进，后端与 App Shell 已完成基础验证
- V2.4：尚未开始

## 已完成

### 主线能力

- PDF 预检
- 安全策略与敏感模式
- MinerU provider 适配
- fake provider 离线链路
- 文档模型、版面修复、Word 重建
- 质量报告
- 返工与版本管理
- CLI：`doctor`、`convert`、`rework`

### V2.3 已完成

- FastAPI 后端基础接口
- `/api/health`
- `/api/tasks` 与 `/api/providers` 的测试覆盖
- 前端 `vite`/`vitest`/`TypeScript` 基础配置
- React App Shell
- `/api/health` 前端连通显示
- V2.3 App Shell 人工验证通过

参考报告：

- [docs/reports/RUN_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/RUN_REPORT.md)
- [docs/reports/FRONTEND_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/FRONTEND_REPORT.md)
- [docs/reports/VALIDATION_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/VALIDATION_REPORT.md)

## 进行中

### V2.3 本地 Web 应用

当前结论：

- 后端可启动
- 前端可启动
- 页面可显示
- 但仍未达到完整交付标准

尚缺：

- 任务中心页面
- 新建任务向导
- 任务详情页
- 设置页
- 前端构建产物接入 FastAPI
- 端到端流程验收

## 下一步建议

### 优先级 P1

1. 完成 V2.3 Task 6 页面实现
2. 把导航占位页替换为真实页面
3. 继续补前端页面级测试

### 优先级 P2

1. 完成 V2.3 Task 7 前后端集成
2. 接入前端构建产物
3. 跑通 fake provider 端到端验收

### 优先级 P3

1. 进入 V2.4 便携打包
2. 做干净环境验证
3. 补发布说明

## 风险与注意事项

- 主线与工作树状态不同，写文档时要明确区分
- 当前 V2.3 启动方式仍偏开发态，后端缺少统一 CLI 启动入口
- 前端虽已验证可运行，但仍是 App Shell 阶段，不等于完整产品
- 根目录 `MinerU API key.txt` 必须继续遵守“不读取、不打印、不提交”
