# GreatOCR Manager Demo Script V1

## Demo Goal

展示 GreatOCR 从 OCR 工具升级为：

> AI Document Processing Platform

核心展示：

- Document → OCR Provider → AI Processing → Business Output
- OCR 与 AI Processing 解耦
- Provider 可配置
- OCR + Translation 完整闭环

预计时间：

**3-4 分钟**

---

# 1. Opening - Product Positioning

## Screen

PPT 首页：
GreatOCR

AI Document Processing Platform

From Document Extraction
to AI-powered Document Workflow


---

## Script

> 我们这次没有把 GreatOCR 定位成一个 OCR 工具，而是希望它成为一个 AI Document Processing Platform。
>
> OCR 只是文档处理的第一步，后续可以通过不同 AI Provider 完成翻译、总结、格式优化、风险检查等任务。

---

## Evaluation Focus

对应：

- AI Innovation
- Business Value

---

# 2. Problem & Solution

## Screen

展示传统流程：


Document

↓

OCR

↓

人工整理

↓

翻译 / 总结 / 格式处理


展示 GreatOCR：


Document

↓

OCR Provider

↓

AI Processing

↓

Business Output


---

## Script

> 传统 OCR 主要解决文字识别问题，但是实际业务场景通常还需要后续处理。
>
> 所以我们将 OCR 和 AI Processing 分离，让不同能力可以组合。

---

## Key Message

不要强调：


我们用了 MinerU


强调：


Provider-based Architecture


---

# 3. Open Application

## Screen

进入 GreatOCR。

页面：


AI Processing

OCR + AI 后处理工作流


---

## Script

> 下面展示一个完整的文档处理流程。

---

# 4. Provider Configuration

## Action

进入：


Settings


展示：

## AI Provider Library

Example:


MinerU

Capabilities:

OCR

智谱 GLM

Capabilities:

Translation
Text Processing

---

## Script

> 我们把模型能力抽象成 Provider。
>
> OCR Provider 和 AI Processing Provider 独立管理。
>
> 当前 OCR 使用 MinerU，翻译使用 GLM。
>
> 后续如果接入 OpenAI、Claude 或本地模型，不需要修改业务流程。

---

## Evaluation Focus

对应：

- Technical Stability
- AI Innovation

---

# 5. Create AI Processing Task

## Action

进入：


AI Processing


上传：


英文签字盖章有页眉的.pdf


---

选择：


Processing Mode:

OCR + Translation

Target Language:

Chinese

Translation Mode:

Page by Page


---

展示：

Current Workflow:


OCR Provider:

MinerU

Translation Provider:

智谱 GLM


---

## Script

> 用户不需要关心底层调用哪个模型，只需要选择业务目标。
>
> 系统会根据 Settings 中配置的 Workflow 自动选择对应 Provider。

---

## Evaluation Focus

对应：

- User Experience
- Technical Stability

---

# 6. Sensitive File Workflow

## Action

展示：


Sensitive File


切换：


Yes


---

如果 Provider 不支持：

展示：


Warning:

Current workflow contains provider
that does not support sensitive files.


---

## Script

> 对企业场景来说，数据安全非常重要。
>
> 敏感文件不是一个全局配置，而是任务级配置。
>
> 系统会根据当前 Workflow 自动检查所有 Provider 是否支持敏感文件。

---

## Evaluation Focus

对应：

- Business Value

---

# 7. Start Processing

## Action

点击：


Start


展示：


Processing

OCR
✓

Translation
✓


---

## Script

> 当前 Demo 展示的是 OCR + Translation 工作流。
>
> 后续这里可以继续扩展更多 AI Processing 能力，例如 Summary、Rewrite、Formatting 等。

---

# 8. Result Output

## Action

进入：


Task Center


展示：


英文签字盖章有页眉的.pdf

Status:
Completed

Files:

📄 OCR Result

📄 Translation Result


---

打开：

## OCR Result

展示：

英文识别结果

---

打开：

## Translation Result

展示：

中文翻译结果

---

## Script

> 最终用户获得的不是 OCR 数据，而是可以直接使用的业务文档。
>
> OCR 输出和 AI Processing 输出独立保存，方便追踪和复用。

---

## Evaluation Focus

对应：

- Business Value
- Completeness

---

# 9. Roadmap

## Screen

展示：


Current:

OCR
+
Translation

Future:

Summary

Rewrite

Formatting

Risk Check


---

## Script

> 当前版本重点验证 AI Document Processing 的基础架构。
>
> 后续可以持续增加更多 AI 能力，而不改变整体 Workflow。

---

# 10. Closing

## Script

> 所以 GreatOCR 的核心不是替代一个 OCR 工具，而是提供一个可扩展的 AI 文档处理平台。

---

# Demo Checklist

Before Demo:

## Environment

- [ ] demo.py 可以正常启动
- [ ] OCR Provider 配置完成
- [ ] Translation Provider 配置完成
- [ ] 测试 PDF 准备完成


## Function Test

- [ ] OCR Only 正常
- [ ] OCR + Translation 正常
- [ ] result.docx 可打开
- [ ] translated_result.docx 可打开
- [ ] Task Center 可以下载结果


## Avoid Showing

不要主动展示：

- API Key
- 后端日志
- 代码
- OCR Provider 内部细节
- OCR 识别缺陷页面


如果被问：

> 当前版本重点验证 AI Processing Workflow，复杂版式 OCR 优化会作为后续 OCR Quality Improvement 方向持续提升。


---

# Core Messages

Demo 中反复强调三个关键词：

## 1. AI Document Processing Platform

不是 OCR 工具。


## 2. Provider-based Architecture

模型只是能力提供方。


## 3. AI Processing Workflow

OCR 是开始，不是终点。