# TASK BOARD

最后更新：2026-07-06

## 当前阶段

- V2.3：Done
- V2.3 Demo Sprint：Active（周五经理演示版）
- V2.4：Backlog

## 本周评分目标

围绕五个评分项组织 Demo Sprint：

- 业务价值：批量上传、敏感文件按任务确认、可直接进入业务流程
- 技术稳定性：保持现有 OCR 主链路稳定，不做高风险重构
- 创新（AI 应用方式）：引入 DeepSeek AI Processing，一键翻译/后处理
- 用户体验：去首页、优化新建任务、空状态、任务中心展示
- 完成度：Windows install/start、Demo Script、PPT、About/Version

## V2.3 Demo Sprint

### P0 - 今天优先

1. AI 一键翻译（DeepSeek）
   - 定位：AI Processing / AI Enhancement，而不是单纯 Translate
   - 目标流程：PDF -> MinerU OCR -> DeepSeek Translation -> DOCX / Translated DOCX
   - Demo 价值：证明 GreatOCR 不是 MinerU 封装，而是可扩展 AI Document Workflow
   - 要求：不破坏现有 OCR Only 流程；DeepSeek 配置缺失时给出清晰提示

2. 多文件上传
   - 支持一次选择多个 PDF
   - 可以顺序创建多个任务，不要求并发
   - 任务中心能看到多个任务

3. 敏感文件选项放到新建任务
   - Sensitive file / security confirmation 应作为每个任务的配置
   - 不应只放在全局 Settings

4. 默认进入新建任务页
   - 打开应用后直接进入业务流程
   - 保留侧边导航：新建任务 / 任务中心 / Settings

### P1 - 明天优化

1. Provider / AI Engine 展示区升级
   - MinerU：OCR Provider
   - DeepSeek：AI Processing Provider
   - Azure OCR / OpenAI OCR / Google Document AI：Coming Soon
   - 可以只做展示和占位，不强制实现增删改

2. 空状态优化
   - 无任务时提示"暂无任务，点击新建任务开始 OCR"
   - 无输出时提示下一步动作

3. About / Version 信息
   - GreatOCR version
   - Build date
   - Local-first / Provider-based / AI Processing 标识

4. 连接错误提示优化
   - Provider/API/SSL/网络错误要显示中文可读原因
   - 不暴露 API Key

### P2 - 演示材料

1. Demo Script
   - 3 分钟主流程
   - 备用流程：如外部 API 不稳定时展示已生成结果

2. PPT
   - 产品定位：GreatOCR = AI Document Platform
   - 架构：Input Document -> OCR Provider -> AI Processing -> Output Document
   - 评分项映射：业务价值 / 稳定性 / 创新 / 体验 / 完成度

3. Release Notes
   - 当前能力
   - 已知限制
   - 下一步 Roadmap

## Demo 主线

推荐演示路径：

1. 双击 start.bat 启动 GreatOCR
2. 默认进入新建任务页
3. 上传一个或多个 PDF
4. 选择页码范围
5. 勾选 Sensitive file 确认
6. 选择 AI Processing：OCR Only 或 OCR + Translation
7. 创建任务
8. 在任务中心查看进度
9. 打开输出目录
10. 展示 result.docx / translated_result.docx

## 产品叙事

GreatOCR 不是单一 OCR 工具，而是一个可扩展的 AI 文档处理平台：

Input Document
  ↓
OCR Provider（MinerU / Future Providers）
  ↓
AI Processing（DeepSeek / Future LLMs）
  ↓
Structured Outputs（DOCX / Reports / Translated Docs）

## V2.4 Backlog

### P0

- OCR 识别质量优化
- 版式恢复
- AI 后处理能力扩展
  - 摘要
  - 术语统一
  - 表格规范化
  - 格式润色

### P1

- 多 Provider 管理
- Settings 重构
- 任务模板（保存常用配置）
- Provider 增删改查
- API Key 多 Provider 安全存储

### P2

- 印章识别
- 签字识别
- 更多导出格式
- UI 美化
- 企业网络/代理/SSL 兼容配置

---

## V2.3 Release Summary（已完成交付，保留）

| 项目 | 状态 |
| --- | --- |
| M1 后端 API + App Shell | Done |
| M2 上传文件 + OCR 调用 | Done |
| M3 任务列表 + 结果展示 | Done |
| M3.1 PDF 指定页码上传 | Done |
| M3.4 任务中心完善 | Done |
| M3.5 任务中心列表化 | Done |
| M4 设置中心 + Provider 管理 | Done |
| M4.5 MVP 可用性修复 | Done |
| RC1 最终验收 | Done |
| V2.3 Release 文档整理 | Done |
| Windows MVP install/start scripts | Done |

## 已完成交付

- 本地 Web 工作流上线
- Provider 配置与 Preferences 持久化
- 任务中心结果下载、打开输出目录、批量删除
- `fake-default` 离线链路与 MinerU 接入路径
- `result.docx` 与 `quality-report.docx` 输出
- Windows MVP 一键安装与启动脚本（install.bat / start.bat）
