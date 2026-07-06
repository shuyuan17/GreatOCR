"""DeepSeek 翻译能力（OCR + 翻译 MVP 使用）。

设计目标：保持简单。
- 逐页（page-by-page）翻译：每一页的文本单元合并为一次翻译请求。
- 目标语言目前仅支持中文。
- 翻译结果原地替换 Document 中的文本单元（span / table cell），
  从而完整保留原始版式（标题、列表、表格、页眉页脚、图片占位）。
"""

from __future__ import annotations

import json
from typing import Literal

import httpx

from greatocr.model.document import Document, Page, TableCell, TextSpan


TranslationMode = Literal["page"]


class TranslationError(RuntimeError):
    """翻译过程中出现的任何错误（API 失败、返回结构异常等）。"""


DEFAULT_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_TARGET_LANGUAGE = "中文"


class DeepSeekTranslator:
    """基于 DeepSeek OpenAI 兼容接口的翻译器。"""

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str | None = None,
        model_name: str | None = None,
        target_language: str = DEFAULT_TARGET_LANGUAGE,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise TranslationError("DeepSeek API key 未配置")
        self.api_key = api_key
        self.endpoint = endpoint or DEFAULT_DEEPSEEK_ENDPOINT
        self.model_name = model_name or DEFAULT_DEEPSEEK_MODEL
        self.target_language = target_language or DEFAULT_TARGET_LANGUAGE
        self.client = client or httpx.Client(timeout=120)

    def translate_texts(self, texts: list[str]) -> list[str]:
        """将一组文本翻译为目标语言，保持顺序与数量一致。

        返回与输入等长的译文列表。空字符串原样返回。
        """
        if not texts:
            return []
        payload_texts = [t if t is not None else "" for t in texts]
        # 若整页无任何有效文本，直接原样返回，避免浪费一次请求。
        if not any(text.strip() for text in payload_texts):
            return list(payload_texts)

        system_prompt = (
            f"你是一名专业翻译。请将用户提供的每一条文本翻译为{self.target_language}。"
            "保持原有格式、术语、编号与专有名词。\n"
            '请仅返回一个 JSON 对象，形如 {"translations": [...]}，'
            "其中数组的每个元素是对应输入条目的译文，顺序与输入完全一致，元素数量与输入相同。"
            "不要输出任何额外说明文字。"
        )
        user_content = json.dumps(payload_texts, ensure_ascii=False)

        try:
            response = self.client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            envelope = response.json()
            content = envelope["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise TranslationError("DeepSeek 返回结果解析失败") from exc
        except httpx.HTTPError as exc:
            raise TranslationError(f"DeepSeek 请求失败: {exc}") from exc

        translations = data.get("translations") if isinstance(data, dict) else None
        if not isinstance(translations, list):
            raise TranslationError("DeepSeek 返回结构不符合预期（缺少 translations 数组）")
        if len(translations) != len(payload_texts):
            raise TranslationError(
                f"DeepSeek 返回的译文数量({len(translations)})与输入({len(payload_texts)})不一致"
            )
        return ["" if item is None else str(item) for item in translations]


def _collect_translation_targets(page: Page) -> tuple[list[object], list[str]]:
    """收集一页内所有可翻译文本单元及其当前文本。

    顺序固定：先按 block 的 reading_order，每个 block 内再按 spans / cells。
    """
    targets: list[object] = []
    texts: list[str] = []
    for block in sorted(page.blocks, key=lambda item: item.reading_order):
        if block.block_type == "table" and block.table is not None:
            for row in block.table.rows:
                for cell in row:
                    targets.append(cell)
                    texts.append(cell.text)
        else:
            for span in block.spans:
                targets.append(span)
                texts.append(span.current_text)
    return targets, texts


def _apply_translations(targets: list[object], translations: list[str]) -> None:
    for target, translation in zip(targets, translations):
        if isinstance(target, TextSpan):
            target.current_text = translation
        elif isinstance(target, TableCell):
            target.text = translation


def translate_page(page: Page, translator: DeepSeekTranslator) -> None:
    """原地翻译单个页面（page-by-page）。"""
    targets, texts = _collect_translation_targets(page)
    if not targets:
        return
    translations = translator.translate_texts(texts)
    _apply_translations(targets, translations)


def translate_document(
    document: Document,
    translator: DeepSeekTranslator,
) -> Document:
    """逐页翻译整个文档，返回新的 Document（不修改输入）。"""
    translated = document.model_copy(deep=True)
    for page in translated.pages:
        translate_page(page, translator)
    return translated
