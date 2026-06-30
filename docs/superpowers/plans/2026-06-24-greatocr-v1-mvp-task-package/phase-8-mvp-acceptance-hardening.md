# GreatOCR Phase 8 MVP Acceptance and Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用脱敏真实样本验证 V1 MVP，修复阻断交付的问题，并形成可交接的验收记录。

**Architecture:** Phase 8 不扩展产品范围，只做验收、回归、安全检查、性能记录和文档交接。任何新增需求进入后续版本清单。

**Tech Stack:** pytest、人工 Microsoft Word 检查、Markdown 验收表。

---

## 可改范围

允许创建或修改：

- `docs/acceptance/v1-sample-matrix.md`
- `docs/acceptance/v1-acceptance-report.md`
- `docs/acceptance/v1-known-limitations.md`
- `scripts/run_acceptance.py`
- `tests/test_no_secret_leakage.py`
- `tests/test_end_to_end_fake_provider.py`

只允许修复 V1 范围内缺陷；不允许加入翻译、批处理或高保真模式。

## 验收条件

- fake provider 端到端稳定通过。
- 至少 3 份脱敏样本完成真实或半真实验收记录。
- `result.docx` 可由 Microsoft Word 打开，无修复提示。
- `quality-report.docx` 内容完整。
- 日志和输出目录不包含 API Key。
- 已知限制写清楚，不把限制伪装成已完成能力。

## 测试方式

- 自动回归：全量 `pytest`。
- fake provider 端到端：无需网络。
- 可选 MinerU smoke：只使用非敏感样本且用户确认上传。
- 人工 Word 检查：打开 DOCX 并按评分表记录。

## 任务

### Task 8.1: 建立样本矩阵

**Files:**
- Create: `docs/acceptance/v1-sample-matrix.md`

- [ ] 记录样本类型：中文合同、英文合同、中英混合、董事会决议、财务报表、混合 PDF、扫描 PDF。
- [ ] 对每份样本记录页数、是否敏感、是否允许上传、关键验收点。
- [ ] 对每份样本记录预期降级区域，例如复杂表格可图片化。

### Task 8.2: 端到端 fake provider 回归

**Files:**
- Create: `tests/test_end_to_end_fake_provider.py`
- Create: `scripts/run_acceptance.py`

- [ ] 写测试：fake provider 输入 → `result.docx`、`quality-report.docx`、`document.json` 全部生成。
- [ ] 写测试：敏感模式只保留最终 DOCX 和质量报告。
- [ ] 实现 `scripts/run_acceptance.py --provider fake`。
- [ ] 运行 `python -m pytest tests/test_end_to_end_fake_provider.py -v`。

### Task 8.3: 安全泄漏检查

**Files:**
- Create: `tests/test_no_secret_leakage.py`

- [ ] 写测试：任务目录、manifest、quality report 不包含形如 API Key 的环境变量值。
- [ ] 写测试：异常消息不包含密钥。
- [ ] 写测试：日志不包含完整正文片段和敏感路径片段。
- [ ] 运行 `python -m pytest tests/test_no_secret_leakage.py -v`。

### Task 8.4: 人工 Word 验收

**Files:**
- Create: `docs/acceptance/v1-acceptance-report.md`

- [ ] 对每份脱敏样本记录 Word 是否无修复提示打开。
- [ ] 记录标题、段落、表格、图片、页眉页脚、分页评分。
- [ ] 记录用户预计返工时间：无需返工、少量微调、需要重排。
- [ ] 记录不通过样本的阻断原因和修复结论。

### Task 8.5: 已知限制和交接说明

**Files:**
- Create: `docs/acceptance/v1-known-limitations.md`

- [ ] 写清 V1 不支持翻译、文件夹批处理、高保真模式、段落级原位替换。
- [ ] 写清 MinerU 接口、限额、留存政策由用户企业批准。
- [ ] 写清复杂表格、低质扫描、手写内容可能降级或需人工复核。
- [ ] 写清下一版本建议优先级。

### Task 8.6: 最终验证

**Files:**
- Modify only files required by failing V1-scope tests.

- [ ] 运行 `python -m pytest -v`。
- [ ] 运行 `python scripts/run_acceptance.py --provider fake`。
- [ ] 若用户批准并提供 MinerU 配置，运行 1 份非敏感样本真实 smoke。
- [ ] 输出最终结果摘要：通过项、失败项、已知限制、建议进入 V2 的事项。

## Phase 8 完成后交付物

- V1 验收报告。
- 样本矩阵。
- 已知限制。
- 可复跑的验收脚本。

