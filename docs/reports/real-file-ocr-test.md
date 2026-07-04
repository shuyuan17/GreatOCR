# GreatOCR V2.3 M2 — 真实文件 OCR 测试报告

- **测试时间**: 2026-07-03 17:25
- **测试人**: 产品/业务
- **工作目录**: `D:\codeprojects\codex-workspace\GreatOCR\.worktrees\v2-3-local-web-app`
- **分支**: `codex/v2-3-local-web-app`

---

## 1. 测试文件类型

| 属性 | 值 |
|------|-----|
| 文件名 | `中英夹杂的.pdf` |
| 来源 | `D:\codeprojects\codex-workspace\GreatOCR\testsamples\` |
| 页数 | 2 |
| 页面类型 | 扫描件 (scanned) × 2 |
| 页面尺寸 | A4 横版 (842 × 595) |
| 内容特征 | 中英双语董事会决议，含财务数据、签字人名单、盖章区域 |
| 是否加密 | 否 |
| 文件大小 | 351 KB |

---

## 2. 使用 OCR Provider

- **Provider**: `mineru-default` (MinerU)
- **连接方式**: 通过 MinerU API 在线解析
- **API Key**: 已配置（不在此报告中披露）
- **Endpoint**: `https://mineru.net`

---

## 3. 测试流程

```
1. 启动后端：.venv\Scripts\python.exe scripts\serve.py
2. 启动前端：cd frontend && node.exe .\node_modules\vite\bin\vite.js
3. 浏览器打开 http://localhost:5173/
4. 进入「新建任务」页面
5. 选择测试文件：中英夹杂的.pdf
6. Provider 选择：MinerU
7. 点击「开始 OCR」
8. 观察状态流转：上传中 → 启动中 → 处理中 → 已完成（约 10-20 秒）
9. 进入「任务中心」查看结果
10. 打开输出目录中的 result.docx 和 quality-report.docx 验证
```

---

## 4. 成功点

| 项目 | 结果 |
|------|------|
| 前端文件上传 | ✅ 正常 |
| 后端文件保存 | ✅ 正常 |
| 任务创建 | ✅ 正常 |
| 管道完整执行 | ✅ 通过（parse → model → docx → quality 四阶段） |
| 输出文件 | ✅ result.docx (50KB), quality-report.docx (37KB), result-v1.docx |
| 质量评分 | **high**（总体质量评级） |
| 中英双语识别 | ✅ 中文段落和英文段落均被正确提取 |
| 标题层级 | ✅ 标题被识别为 Heading 1 样式 |
| 财务数字 | ✅ 关键数字已识别（如 52,077,455.23） |
| 表格降级 | 0 个表格被降级 |
| 字体替换 | 0 处 |
| 自动校正 | 0 处（无过度校正） |

---

## 5. 识别结果问题

| 问题 | 位置 | 严重程度 | 详情 |
|------|------|----------|------|
| 单词粘连 | 英文段落 | 中 | `THEUNDERSIGNED` 应为 `THE UNDERSIGNED`；`theCompany` 应为 `the Company`；`profit after tax in 2024 isCNY` 缺空格 |
| 数字格式不一致 | 中文段落 | 低 | 同一段内 `52,077,455.23` 和 `52.077.455.23` 混用 |
| 签名文字识别错误 | 签字区域 | 中 | `Beoto 2ste` 疑似识别错误（非正确人名），可能为签名笔迹或盖章模糊 |
| 页眉/页脚信息 | 全文 | 低 | 未发现页眉页码文本，但矿机报告提及 `page_number` 类型块未被归类 |

---

## 6. 版式问题

| 问题 | 详情 | 影响 |
|------|------|------|
| 未知块类型 | 质量报告记录 2 处 `unknown_provider_block`，类型为 `page_number` | MinerU 识别了页码但块类型未映射到模型，当前被跳过 |
| 分页漂移警告 | 质量报告记录 `pagination_may_drift` | DOCX 分页可能与源 PDF 不一致，影响人工审阅时对照页码 |
| 阅读顺序 | 中英双语段落交替出现，当前按原始顺序输出，未做语言分组优化 | 不影响信息完整性，但可读性可优化 |

---

## 7. 印章/签字识别问题

| 项目 | 结果 |
|------|------|
| 签字人姓名 | ✅ 已识别为普通文本（Olli, Mr. Wang Weiliang, Mueller Thilo 等） |
| 印章区域 | ❌ 未见印章图像或印章文本提取，签字区域仅输出为文字 |
| 盖章内容 | ❌ 未检测到圆形公章、公司名称印章等视觉元素 |
| 签名笔迹 | ❌ 签名被作为文本识别（如 `Beoto 2ste` 可能为笔迹误识别） |

**结论**：当前 MinerU 管道主要做文字 OCR 提取，印章/签字以图像方式被跳过或误识别为文字。如需印章提取需额外能力。

---

## 8. PDF 页码选择功能是否缺失

**当前状态：缺失。**

- 前端上传时不提供页码选择，后端默认处理全部页面
- `POST /api/tasks/upload-file` 端点支持 `pages` 参数（逗号分隔），但前端未暴露此选项
- 后端 `TaskService.start()` 要求 `selected_pages` 非空，当前由上传端点自动填充为全部页面

**影响**：用户无法选择只处理 PDF 中的特定页面，大文件必须全部处理。

---

## 9. 建议拆出的后续任务

| 任务编号 | 名称 | 说明 | 优先级 |
|----------|------|------|--------|
| M3.1 | PDF 指定页码上传 | 前端新增页码选择输入（如 "1-3,5,7-9"），传递给后端 `pages` 参数 | 高 |
| M3.2 | OCR 识别质量参数优化 | 调查单词粘连、数字格式混用问题，评估是否需要调整 MinerU 参数或增加后处理校正 | 中 |
| M3.3 | 版式还原优化 | 处理 `unknown_provider_block` 类型映射，减少分页漂移 | 中 |
| M3.4 | 印章/签字识别能力评估 | 系统性地测试印章/签字场景，评估是否需要集成专用印章识别模型 | 低 |
| M3.5 | 结果导出/展示优化 | 前端增加结果 DOCX 预览/下载、识别文本展示、问题项高亮 | 高 |

---

## 附录：输出文件清单

```
data/tasks/ad042f6dc3e54d398a5af1ed032dbd0c/
├── result.docx          (50 KB)  → OCR 重建的 Word 文档
├── result-v1.docx       (50 KB)  → 版本化管理的一号输出
└── quality-report.docx  (37 KB)  → 质量报告（评级: high）
```
