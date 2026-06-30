# GreatOCR Phase 7 Codex Skill Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将本地文档引擎包装为 Codex Skill 工作流，让用户能通过对话完成问答、确认、处理和交付。

**Architecture:** Skill 保持轻量，只写触发说明、默认问答、安全边界和调用脚本方式。实际 PDF 处理继续由 `greatocr` Python 包完成。

**Tech Stack:** Codex Skill 文件结构、Markdown、Python CLI。

---

## 可改范围

允许创建或修改：

- `skills/greatocr-document-reconstruction/SKILL.md`
- `skills/greatocr-document-reconstruction/references/default-questionnaire.md`
- `skills/greatocr-document-reconstruction/references/security-policy.md`
- `skills/greatocr-document-reconstruction/scripts/run_greatocr.py`
- `tests/test_skill_static.py`

不允许在 Skill 内复制大量 PRD 或实现复杂业务逻辑。

## 验收条件

- Skill 名称使用 lowercase hyphen：`greatocr-document-reconstruction`。
- `SKILL.md` frontmatter 只有 `name` 和 `description`。
- Skill 能指导 Codex 先问默认问题，再调用 CLI。
- Skill 明确敏感文件默认禁用公共 API。
- 脚本不保存 API Key，不隐式上传文件。

## 测试方式

- 静态测试 frontmatter、文件存在、无敏感占位密钥。
- 脚本 dry-run 测试。
- 人工端到端演练：给本地 PDF 路径，Codex 按问答默认值运行。

## 任务

### Task 7.1: 创建 Skill 目录和 SKILL.md

**Files:**
- Create: `skills/greatocr-document-reconstruction/SKILL.md`
- Create: `tests/test_skill_static.py`

- [ ] 写测试：`SKILL.md` 存在且 frontmatter 包含 `name` 和 `description`。
- [ ] 写测试：skill name 等于 `greatocr-document-reconstruction`。
- [ ] 写 `SKILL.md`，包含触发场景、处理流程、安全提醒、输出说明。
- [ ] 运行 `python -m pytest tests/test_skill_static.py -v`。

### Task 7.2: 添加默认问答参考

**Files:**
- Create: `skills/greatocr-document-reconstruction/references/default-questionnaire.md`
- Modify: `skills/greatocr-document-reconstruction/SKILL.md`

- [ ] 写默认问答：敏感文件否、语言自动、输出可编辑 Word、翻译否、保留页眉页脚是、分页尽可能保持、数字/日期保留原格式、供应商上次批准、中间文件普通模式保留 JSON/Markdown。
- [ ] 在 `SKILL.md` 指明开始处理前读取该参考文件。
- [ ] 运行 `python -m pytest tests/test_skill_static.py -v`。

### Task 7.3: 添加安全策略参考

**Files:**
- Create: `skills/greatocr-document-reconstruction/references/security-policy.md`
- Modify: `skills/greatocr-document-reconstruction/SKILL.md`

- [ ] 写普通模式和敏感模式的数据流向规则。
- [ ] 写“真实上传前必须显示供应商和确认”的流程。
- [ ] 写“不记录 API Key、不绕过 PDF 密码、不上传到未批准中转服务”的硬规则。
- [ ] 在 `SKILL.md` 指明遇到敏感文件时读取该参考文件。
- [ ] 运行 `python -m pytest tests/test_skill_static.py -v`。

### Task 7.4: 添加 Skill 调用脚本

**Files:**
- Create: `skills/greatocr-document-reconstruction/scripts/run_greatocr.py`
- Modify: `tests/test_skill_static.py`

- [ ] 写测试：脚本支持 `--dry-run` 并调用 `python -m greatocr.cli convert`。
- [ ] 实现脚本参数透传：PDF 路径、输出目录、敏感模式、provider、dry-run。
- [ ] 确保脚本不读取或打印 API Key。
- [ ] 运行 `python -m pytest tests/test_skill_static.py -v`。

### Task 7.5: 人工演练记录

**Files:**
- Create: `docs/superpowers/plans/2026-06-24-greatocr-v1-mvp-task-package/phase-7-manual-runbook.md`

- [ ] 写演练步骤：用户提供 PDF 路径 → Codex 读取默认问答 → dry-run → 用户确认上传 → convert → 交付 DOCX 和报告。
- [ ] 写演练通过标准：无未经确认上传、输出路径清楚、失败时说明下一步。
- [ ] 不在演练记录中写真实文件内容或 API Key。

## Phase 7 完成后交付物

- Codex Skill 工作流入口。
- 默认问答参考。
- 安全策略参考。
- 调用脚本。

