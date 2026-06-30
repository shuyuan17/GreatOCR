# GreatOCR Phase 2 Parser Provider and MinerU Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立文档解析供应商抽象，并实现 MinerU 在线 API 适配器和可离线测试的 fake provider。

**Architecture:** 业务流程依赖 `DocumentParser` 接口，不直接依赖 MinerU 字段。MinerU 适配器只负责上传、提交、轮询、下载和把原始结果保存到任务目录。

**Tech Stack:** Python 3.11+、httpx 或 requests、pytest、responses/respx 或 monkeypatch。

---

## 可改范围

允许创建或修改：

- `src/greatocr/providers/base.py`
- `src/greatocr/providers/mineru.py`
- `src/greatocr/providers/fake.py`
- `src/greatocr/pipeline.py`
- `src/greatocr/config.py`
- `tests/test_provider_contract.py`
- `tests/test_mineru_adapter.py`
- `tests/fixtures/provider_outputs/`

不允许把真实 API Key 写入仓库；不允许无确认真实上传文件。

## 验收条件

- provider 能声明能力：是否支持 native/scanned、坐标、表格、公式、语言。
- fake provider 可返回固定解析结果，用于后续端到端测试。
- MinerU 适配器缺少配置时给出明确错误且不泄露密钥。
- 配置齐全并经用户确认时，允许运行真实 API smoke test。

## 测试方式

- Provider 契约测试：fake 和 MinerU adapter 都符合接口。
- HTTP mock 测试：上传、提交、轮询成功、失败、限流、超时。
- 可选真实 API smoke：只对用户提供的非敏感样本执行。

## 任务

### Task 2.1: 定义 DocumentParser 接口

**Files:**
- Create: `src/greatocr/providers/base.py`
- Create: `tests/test_provider_contract.py`

- [ ] 写测试：provider 必须返回 `ProviderCapabilities`。
- [ ] 写测试：`parse_document` 返回 `ParserJobResult`，包含原始结果目录和 provider 元数据。
- [ ] 实现 `ProviderCapabilities`、`ParserJobResult`、`DocumentParser` 抽象类。
- [ ] 运行 `python -m pytest tests/test_provider_contract.py -v`。

### Task 2.2: 实现 fake provider

**Files:**
- Create: `src/greatocr/providers/fake.py`
- Add: `tests/fixtures/provider_outputs/simple_contract.json`
- Modify: `tests/test_provider_contract.py`

- [ ] 创建固定 provider 输出夹具，覆盖标题、段落、表格、图片、页眉页脚。
- [ ] 实现 `FakeDocumentParser`，从夹具读取结果。
- [ ] 写测试：fake provider 不访问网络，返回稳定结果。
- [ ] 运行 `python -m pytest tests/test_provider_contract.py -v`。

### Task 2.3: 实现 MinerU 配置和适配器骨架

**Files:**
- Create: `src/greatocr/providers/mineru.py`
- Modify: `src/greatocr/config.py`
- Create: `tests/test_mineru_adapter.py`

- [ ] 写测试：缺少 `MINERU_API_KEY` 时抛出 `ProviderConfigurationError`。
- [ ] 写测试：异常信息和日志不包含密钥值。
- [ ] 实现 `MinerUConfig.from_env()`。
- [ ] 实现 `MinerUDocumentParser.capabilities()`。
- [ ] 运行 `python -m pytest tests/test_mineru_adapter.py -v`。

### Task 2.4: 实现 MinerU 上传、提交和轮询

**Files:**
- Modify: `src/greatocr/providers/mineru.py`
- Modify: `tests/test_mineru_adapter.py`

- [ ] 写 HTTP mock 测试：上传成功后提交任务。
- [ ] 写 HTTP mock 测试：轮询从 `running` 到 `succeeded`。
- [ ] 写 HTTP mock 测试：`failed` 状态转成 `ProviderJobFailed`。
- [ ] 写 HTTP mock 测试：429 或临时错误按固定次数重试。
- [ ] 实现上传、提交、轮询、下载原始结果。
- [ ] 运行 `python -m pytest tests/test_mineru_adapter.py -v`。

### Task 2.5: 接入 pipeline 的解析阶段

**Files:**
- Create: `src/greatocr/pipeline.py`
- Modify: `src/greatocr/cli.py`
- Create: `tests/test_pipeline_parse.py`

- [ ] 写测试：使用 fake provider 时，pipeline 生成 `intermediates/provider-raw/`。
- [ ] 写测试：敏感模式下若 provider 是 public 且未批准，pipeline 停止。
- [ ] 实现 `run_parse_stage(task_dir, preflight, parser, security_summary)`。
- [ ] 运行 `python -m pytest tests/test_pipeline_parse.py -v`。

## Phase 2 完成后交付物

- 解析供应商抽象。
- fake provider。
- MinerU adapter。
- 解析阶段 pipeline。

