# GreatOCR V1 MVP 任务包

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:writing-plans` to understand this package. During implementation use `superpowers:subagent-driven-development` or `superpowers:executing-plans`; use `superpowers:test-driven-development` before writing feature code; use `superpowers:verification-before-completion` before claiming completion.

**Goal:** 将已确认的 PRD 拆成可执行的 V1 MVP 阶段计划，产出“单个 PDF → 可编辑 DOCX + Word 质量报告 + 结构化中间数据 + 进度/检查点 + 有限局部返工”的第一版。

**Architecture:** V1 采用 Python 本地文档引擎 + 可插拔解析供应商适配器 + Codex Skill 工作流入口。文档引擎独立于 Codex 对话运行；Codex Skill 只负责任务问答、安全确认、调用脚本、展示进度和交付结果。

**Tech Stack:** Python 3.11+、pytest、pydantic、python-docx、pypdf、pymupdf 或等价 PDF 库、requests/httpx、MinerU 在线 API、标准 `.docx` 输出。

---

## 任务包文件

- `00-codex-execution-prompt.md`：给 Codex 总执行者的完整启动 prompt。
- `phase-0-project-scaffold.md`：工程脚手架、配置、测试框架和样例夹。
- `phase-1-ingestion-preflight.md`：PDF 输入、预检、页面分类、安全确认。
- `phase-2-parser-provider-mineru.md`：解析供应商抽象、MinerU 适配器、假供应商测试夹具。
- `phase-3-unified-document-model.md`：统一文档模型、Markdown 中间稿、关键字段保护。
- `phase-4-docx-reconstruction.md`：可编辑 Word 重建、表格/图片/页眉页脚/字体策略。
- `phase-5-quality-report-validation.md`：输出验证、Word 质量报告、完整性检查。
- `phase-6-progress-checkpoint-rework.md`：进度、预计剩余时间、检查点、页/表格局部返工。
- `phase-7-codex-skill-workflow.md`：Codex Skill 入口和用户工作流包装。
- `phase-8-mvp-acceptance-hardening.md`：真实样本验收、性能/安全硬化、发布交接。

## Phase 总览

| Phase | 目标 | 可改范围 | 验收条件 | 测试方式 |
| --- | --- | --- | --- | --- |
| 0 | 建立可测试的 Python 工程骨架 | 新建工程目录、依赖、测试配置、CLI 空壳 | `pytest` 和 CLI 帮助命令可运行 | 单元测试、CLI smoke test |
| 1 | 完成 PDF 输入、预检和安全确认 | 输入模块、配置模块、预检报告 | 能识别文件状态、页数、页面类型和数据流向 | 单元测试 + 小型 PDF 夹具 |
| 2 | 接入解析供应商抽象和 MinerU | provider 接口、MinerU 客户端、mock/fake provider | 无真实 API 时可用 fake 数据跑通；配置齐全时可调用 MinerU | mock 测试、契约测试、可选真实 API smoke |
| 3 | 建立统一文档模型和结构校正基础 | pydantic 模型、provider 映射、Markdown 导出、关键字段标记 | 解析结果可稳定转成 `document.json` 和 `content.md` | schema 测试、快照测试 |
| 4 | 生成可编辑 DOCX | docx builder、样式映射、表格/图片降级 | Word 可打开，无修复提示；基础结构可编辑 | 自动解包校验 + 人工 Word 检查 |
| 5 | 生成质量报告并做完整性验证 | validator、issue 收集、`quality-report.docx` | 每个风险有页码、片段、原因、建议 | 单元测试、报告内容快照 |
| 6 | 加入进度、预计时长、检查点、局部返工 | task manifest、progress、checkpoint、rework | 中断后可恢复；指定页/表格可重解析并重生成 DOCX | 状态机测试、fake provider 调用计数测试 |
| 7 | 包装为 Codex Skill 工作流 | skill 文件、脚本入口、问答默认值、安全提示 | Codex 能按标准流程调用本地引擎 | skill 静态校验、端到端演练 |
| 8 | MVP 验收与硬化 | 样本清单、验收脚本、发布说明 | 满足 V1 验收表；列出已知限制 | 脱敏样本验收、回归测试、安全检查 |

## V1 不做的内容

- 翻译、双语对照和术语表。
- 文件夹批处理。
- 高保真文本框式 Word。
- 段落级原位替换。
- 自动部署本地大模型。
- 自动安装或控制 Microsoft Word。
- 像素级一致承诺。

## 推荐执行顺序

严格按 Phase 0 → Phase 8 执行。每个 phase 完成后先做验收，再进入下一阶段。若任一阶段发现 PRD 级别冲突，停止实现并更新 PRD 或计划。

## 用户需准备内容

1. MinerU 在线 API 的访问方式：Base URL、认证方式、API Key、接口文档或示例请求。
2. 可用于测试的脱敏 PDF 样本：至少 3 份中文、2 份英文、1 份中英混合、2 份财务表格、1 份董事会决议。
3. 每份样本的人工验收记录：哪些页面必须保真、哪些表格必须可编辑、哪些区域允许图片降级。
4. 企业可接受的数据流向说明：普通文件是否允许上传 MinerU，敏感文件可用的企业私有端点。
5. 运行环境确认：Python 版本、是否可安装依赖、是否允许命令行读取本地 PDF。
6. Microsoft Word 人工验收环境：至少一台用于打开结果 DOCX 的桌面版 Word。

