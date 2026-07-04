# PROJECT STATUS

- Current Version: `v2.3.0`
- Status: `Released`
- Release Date: `2026-07-04`

## V2.3 完成内容

- 发布本地 Web 版本工作流：FastAPI 后端 + React 前端
- 支持 PDF 上传、页码范围选择、OCR 任务创建与执行
- 支持任务中心查看状态、下载结果、打开输出目录、删除与批量删除
- 支持设置中心管理 Provider、API Key、连接测试与常用偏好设置
- 支持 `fake-default` 离线演示链路与 MinerU 真实 OCR 链路
- 支持 `result.docx` 输出与可选 `quality-report.docx`
- 支持本地 SQLite 持久化任务、Provider 与 Preferences
- 完成 V2.3 RC1 验证并整理为正式发布版本

## 当前功能边界

- 已具备可运行、可验证的本地 OCR MVP
- 主流程覆盖：上传 -> 选页 -> OCR -> 查看结果 -> 打开输出 -> 删除记录
- 适合本地验证、日常试用与后续 Windows 打包准备

## 已知限制

- 当前仍需分别启动后端与前端
- 尚未提供 Windows 打包交付物
- OCR 识别质量和版式恢复仍有提升空间
- 印章/签字识别、批量 OCR、更多导出格式尚未完成

## 下一阶段目标

### Windows Packaging

- 生成可分发的 Windows 打包版本
- 验证干净环境安装与启动
- 收敛启动方式，降低运行门槛
- 补齐发布说明与交付材料
