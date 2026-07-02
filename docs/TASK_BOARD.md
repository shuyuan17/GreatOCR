# TASK BOARD

最后更新：2026-07-02

## 项目总览

- 项目名称：`GreatOCR`
- 主线目标：把本地 PDF 重建能力逐步做成可运行、可测试、可交付的 Windows 应用
- 当前主线状态：`main` 已完成 `V2.2`
- 当前开发重点：`V2.3` 本地 Web 应用
- 后续目标：`V2.4` Windows 打包与完整交付

当前工作目录：

- `D:\codeprojects\codex-workspace\GreatOCR\.worktrees\v2-3-local-web-app`

## 阶段看板

| 阶段 | 名称 | 内容 | 状态 |
| --- | --- | --- | --- |
| V2.1 | 重建质量核心 | PDF 预检、解析、结构化映射、Word 重建、质量报告 | ✅ 完成 |
| V2.2 | 选页与多 provider | 选页表达式、多 provider、fallback、返工、版本管理 | ✅ 完成 |
| V2.3 | 本地 Web 应用 | FastAPI + React、本地图形界面、任务流、设置页、结果展示 | ⏳ 进行中 |
| V2.4 | Windows 打包与发布 | 打包、干净环境验证、完整验收、发布说明 | ⏳ 未开始 |

## 分支规划

| 分支 | 对应阶段/任务 | 说明 | 状态 |
| --- | --- | --- | --- |
| `main` | 稳定主线 | 当前稳定版本，已完成 V2.2 | ✅ 稳定 |
| `codex/v2-3-local-web-app` | V2.3 | 当前 Web 应用开发工作树分支 | ⏳ 进行中 |
| `feature/upload-ocr-flow` | V2.3 M2 | 上传文件 + OCR 调用链路 | ⏳ 建议下一步 |
| `feature/task-results` | V2.3 M3 | 任务列表、任务详情、结果展示 | ⏳ 待开始 |
| `feature/settings-provider` | V2.3 M4 | 设置页、Provider 管理、连接测试 | ⏳ 待开始 |
| `feature/windows-package` | V2.4 M5 | Windows 打包、验收与发布整理 | ⏳ 后续 |

## 模块拆解

| 模块 | 前后端 | 内容 | 状态 |
| --- | --- | --- |
| 核心引擎 | 后端 | PDF 预检、解析、重建、质量报告、返工 | ✅ 已完成主能力 |
| Provider 体系 | 后端 | MinerU、fake provider、多 provider、fallback | ✅ 已完成基础能力 |
| 本地 API | 后端 | `/api/health`、`/api/tasks`、`/api/providers` | ✅ 基础可用 |
| Web 前端 | 前端 | App Shell、导航、健康检查、页面骨架 | ✅ 基础可用 |
| 任务流 | 前后端 | 上传、创建任务、启动 OCR、查看进度和结果 | ⏳ 进行中 |
| 设置中心 | 前后端 | Provider 配置、连接测试、安全/本地设置 | ⏳ 未开始 |
| 打包发布 | 集成/发布 | Windows 打包、安装/运行验证、最终交付 | ⏳ 未开始 |

## 当前任务拆解

| 任务 | 模块 | 内容 | 状态 |
| --- | --- | --- | --- |
| T1 | 核心引擎 | CLI、重建、质量报告、返工能力 | ✅ 完成 |
| T2 | Provider 体系 | 选页、多 provider、fallback、安全策略 | ✅ 完成 |
| T3 | 后端 API | FastAPI 框架、认证、健康检查、任务与 Provider 接口 | ✅ 完成 |
| T4 | 前端 App Shell | React 壳、导航、`/api/health` 连通 | ✅ 完成 |
| T5 | 上传与 OCR | 上传文件、创建任务、触发 OCR、处理状态流转 | ⏳ 下一步 |
| T6 | 任务与结果页 | 任务列表、任务详情、结果展示、版本查看 | ⏳ 未开始 |
| T7 | 设置与 Provider 管理 | 设置页、Provider 配置、连接测试 | ⏳ 未开始 |
| T8 | 集成与打包 | 前后端一体化、Windows 打包、完整验收 | ⏳ 未开始 |

## V2.3 里程碑

| 里程碑 | 内容 | 状态 |
| --- | --- | --- |
| M1 | 后端 API + App Shell | ✅ 完成 |
| M2 | 上传文件 + OCR 调用 | ⏳ 下一步 |
| M3 | 任务列表 + 结果展示 | ⏳ |
| M4 | 设置 + Provider 管理 | ⏳ |
| M5 | Windows 打包 + 完整验收 | ⏳ |
| M6 | 合并到 `main` | ⏳ 最后一步 |

## 当前判断

- 后端已经能启动
- 前端已经能启动
- 前端已经能访问 `/api/health`
- App Shell 已通过基础验证
- 主线能力完整，但 Web 端仍未走完整业务流
- 现在还不算完整产品，重点应转到真实业务页面和端到端流程

## 参考报告

- [RUN_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/.worktrees/v2-3-local-web-app/RUN_REPORT.md)
- [FRONTEND_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/.worktrees/v2-3-local-web-app/FRONTEND_REPORT.md)
- [VALIDATION_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/.worktrees/v2-3-local-web-app/VALIDATION_REPORT.md)

## 下一步建议

1. 先做 `M2 / T5`：上传文件 + OCR 调用
2. 再做 `M3 / T6`：任务列表 + 结果展示
3. 然后做 `M4 / T7`：设置 + Provider 管理
4. 完成后进入 `M5 / T8`：Windows 打包 + 完整验收
5. 最后再做 `M6`：合并到 `main`
