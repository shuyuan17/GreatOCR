# GreatOCR V1 MVP 总执行 Prompt

把下面整段复制给新的 Codex 执行线程使用。

```text
你是 GreatOCR V1 MVP 的总执行 Codex。请在 D:\codex-workspace\GreatOCR 中工作。

必须先阅读：
1. D:\codex-workspace\GreatOCR\docs\superpowers\specs\2026-06-23-greatocr-document-reconstruction-design.md
2. D:\codex-workspace\GreatOCR\docs\superpowers\plans\2026-06-24-greatocr-v1-mvp-task-package\README.md
3. 当前要执行的 phase markdown 文件。

执行规则：
- 先使用 superpowers:using-git-worktrees 检查是否需要隔离工作区；当前仓库若不是 git 仓库，不要擅自初始化 git，直接说明并在当前工作区安全执行。
- 每个 phase 开始前使用 superpowers:test-driven-development；先写失败测试，再写最小实现，再跑测试。
- 若按任务拆给子代理，使用 superpowers:subagent-driven-development；若在当前线程连续执行，使用 superpowers:executing-plans。
- 每个 phase 完成前使用 superpowers:verification-before-completion，必须给出实际命令和结果。
- 不实现 PRD 中明确排除的功能：翻译、文件夹批处理、高保真文本框式 Word、段落级原位替换、自动安装 Word、自动部署本地大模型。
- 不把 API Key 写入代码、日志、任务目录或测试夹具。
- 不把用户文件上传到未确认的第三方服务。真实 MinerU 调用必须由用户明确确认。
- 对数字、金额、日期、账号、人名、公司名等关键字段采用保守策略；不能让 LLM 或校正规则无依据改写。

V1 目标：
实现单个 PDF 转可编辑 DOCX，输出 result.docx、quality-report.docx、intermediates/document.json、intermediates/content.md、intermediates/task-manifest.json。支持普通模式和敏感模式留存差异；支持进度、预计剩余时间、检查点；支持按页或表格重新解析并重新生成整份 DOCX。

Phase 执行顺序：
0. phase-0-project-scaffold.md
1. phase-1-ingestion-preflight.md
2. phase-2-parser-provider-mineru.md
3. phase-3-unified-document-model.md
4. phase-4-docx-reconstruction.md
5. phase-5-quality-report-validation.md
6. phase-6-progress-checkpoint-rework.md
7. phase-7-codex-skill-workflow.md
8. phase-8-mvp-acceptance-hardening.md

每完成一个 phase，输出：
- 已完成目标
- 修改文件
- 测试命令和结果
- 未进入范围的事项
- 进入下一 phase 前需要用户确认或提供的内容
```

