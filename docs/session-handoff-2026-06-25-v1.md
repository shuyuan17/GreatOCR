# GreatOCR V1 会话交接摘要

日期：2026-06-25

## 项目位置

- 工作区：`D:\codex-workspace\GreatOCR`
- Python：用户说明 E 盘有 Python 3.12
- 测试样例：`D:\codex-workspace\GreatOCR\testsamples`
- MinerU API key：`D:\codex-workspace\GreatOCR\MinerU API key.txt`
- 注意：不要打印、提交、复制或写入 API key 明文。

## 已完成内容

- 已按 `docs\superpowers\plans\2026-06-24-greatocr-v1-mvp-task-package\00-codex-execution-prompt` 完成 GreatOCR V1 MVP 主体。
- 已实现：
  - `src/greatocr` 包结构和 CLI。
  - PDF 预检与安全检查。
  - provider 抽象、fake provider、MinerU provider。
  - MinerU 官方 API v4 流程：
    - `POST /api/v4/file-urls/batch`
    - `PUT` signed upload URL
    - `GET /api/v4/extract-results/batch/{batch_id}`
    - 下载 `full_zip_url`
  - `MinerUConfig.from_key_file(path)`。
  - MinerU `result.zip` 标准化解析：`src/greatocr/providers/mineru_zip.py`。
  - 统一 document model、Markdown 输出、关键字段提取。
  - DOCX 构建、图片/表格处理、DOCX 校验。
  - JSON/DOCX 质量报告。
  - task manifest、progress、checkpoint、resume/rework。
  - Codex skill：`skills/greatocr-document-reconstruction`。
  - 验收脚本和测试。

## 真实 MinerU smoke test

用户已明确允许上传：

- `D:\codex-workspace\GreatOCR\testsamples\中英夹杂的.pdf`

MinerU 公共 API smoke test 信息：

- `batch_id=f66a7f50-66b9-496c-9ddf-ca8d840079b5`
- 输出目录：`D:\codex-workspace\GreatOCR\outputs\mineru-smoke-20260625-155848`
- 主要输出：
  - `result.docx`
  - `quality-report.docx`
  - `intermediates\document.json`
  - `intermediates\content.md`
  - `intermediates\quality-report.json`
  - `intermediates\provider-raw\result.json`
  - `intermediates\provider-raw\result.zip`

已验证：

- `document_pages=2`
- `document_issues=3`
- `result.docx` 校验通过。
- `quality-report.docx` 校验通过。
- 输出目录未发现 API key 明文。
- pytest 曾全量通过：`107 passed in 19.18s`。

## V1 基线与回退点

当前版本已封为 V1：

- V1 目录：`D:\codex-workspace\GreatOCR\releases\v1`
- 当前结果副本：`D:\codex-workspace\GreatOCR\releases\v1\result`
- 源码快照：`D:\codex-workspace\GreatOCR\releases\v1\greatocr-v1-source-snapshot.zip`
- 说明文件：`D:\codex-workspace\GreatOCR\releases\v1\README.md`
- 校验文件：`D:\codex-workspace\GreatOCR\releases\v1\SHA256SUMS.txt`

V1 封版验证：

- release 总文件数：14
- V1 结果文件数：11
- 校验清单覆盖文件数匹配：13 / 13
- 源码快照未包含：
  - `MinerU API key.txt`
  - `testsamples/`
  - `outputs/`
  - `releases/`
  - `.pytest_cache/`
  - `__pycache__/`
  - `.pyc`
- release 文本文件中未发现 API key 明文。

如果后续优化效果不好，可以用 `greatocr-v1-source-snapshot.zip` 回退到当前代码基线。

## 当前限制与注意事项

- 当前目录不是可用 git repo：`git rev-parse` 显示不是 git repository，虽然存在 `.git` 目录。
- 不要擅自初始化 git，除非用户明确要求。
- 需要联网或访问 MinerU API 时，必须请求网络权限。
- 使用国内镜像安装依赖。
- 真实 MinerU 上传前，除已确认的 `中英夹杂的.pdf` smoke test 外，应再次取得用户明确确认。

## 下一轮优化建议入口

优先让用户对 V1 的 `result.docx` 和 `quality-report.docx` 做人工审阅，然后按问题类型优化：

- 版式还原：标题、段落、换行、页眉页脚、页码、列表。
- 表格还原：合并单元格、边框、列宽、表格内换行。
- 图片处理：图片位置、大小、裁剪、顺序。
- 中英混排：空格、字体、标点、段落断句。
- 质量报告：问题分类、可读性、可操作性。
- CLI/流程体验：参数、输出目录、失败恢复、日志。

## 给新 Codex 会话的简洁 Prompt

```text
请接手 D:\codex-workspace\GreatOCR 的 GreatOCR V1 优化工作。

先读取 docs/session-handoff-2026-06-25-v1.md，并把 D:\codex-workspace\GreatOCR\releases\v1 当作当前可回退基线。不要打印或写入 MinerU API key 明文。当前目录不是可用 git repo，不要擅自初始化 git。

V1 已完成 MinerU API smoke test，输出在 D:\codex-workspace\GreatOCR\releases\v1\result。请先检查当前代码和 V1 输出，再根据我接下来指出的问题做小步优化。每次优化后请运行相关测试；如果效果不好，需要能回退到 releases\v1\greatocr-v1-source-snapshot.zip。

Python 3.12 在 E 盘；需要下载依赖时用中国国内镜像。测试样例在 D:\codex-workspace\GreatOCR\testsamples。真实上传 MinerU 公共 API 前必须先获得我的明确确认。
```
