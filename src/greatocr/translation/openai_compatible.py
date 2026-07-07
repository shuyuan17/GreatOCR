from __future__ import annotations

import json
from typing import Literal, Protocol

import httpx

from greatocr.model.document import Document, Page, TableCell, TextSpan


TranslationMode = Literal["page"]
DEFAULT_TARGET_LANGUAGE = "中文"


class TranslationError(RuntimeError):
    """Raised when translation cannot be completed successfully."""


class Translator(Protocol):
    def translate_texts(self, texts: list[str]) -> list[str]: ...


class ChatCompletionsTranslator:
    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str,
        model_name: str,
        target_language: str = DEFAULT_TARGET_LANGUAGE,
        provider_name: str = "翻译 Provider",
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise TranslationError(f"{provider_name} API Key 未配置")
        if not endpoint:
            raise TranslationError(f"{provider_name} endpoint 未配置")
        if not model_name:
            raise TranslationError(f"{provider_name} model 未配置")
        self.api_key = api_key
        self.endpoint = endpoint
        self.model_name = model_name
        self.target_language = target_language or DEFAULT_TARGET_LANGUAGE
        self.provider_name = provider_name or "翻译 Provider"
        self.client = client or httpx.Client(timeout=120)

    def translate_texts(self, texts: list[str]) -> list[str]:
        if not texts:
            return []
        payload_texts = [text if text is not None else "" for text in texts]
        if not any(text.strip() for text in payload_texts):
            return list(payload_texts)

        system_prompt = (
            f"你是一名专业翻译。请将用户提供的每一条文本翻译为{self.target_language}。"
            "保持原有格式、术语、编号与专有名词。\n"
            '请仅返回一个 JSON 对象，形如 {"translations": [...]}。'
            "其中数组的每一个元素是对应输入条目的译文，顺序与输入完全一致，元素数量与输入相同。"
            "不要输出任何额外说明文字。"
        )
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
                        {"role": "user", "content": json.dumps(payload_texts, ensure_ascii=False)},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            envelope = response.json()
            content = envelope["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise TranslationError(f"{self.provider_name} 返回结果解析失败") from exc
        except httpx.HTTPError as exc:
            raise TranslationError(f"{self.provider_name} 请求失败: {exc}") from exc

        translations = data.get("translations") if isinstance(data, dict) else None
        if not isinstance(translations, list):
            raise TranslationError(f"{self.provider_name} 返回结构不符合预期（缺少 translations 数组）")
        if len(translations) != len(payload_texts):
            raise TranslationError(
                f"{self.provider_name} 返回的译文数量({len(translations)})与输入({len(payload_texts)})不一致"
            )
        return ["" if item is None else str(item) for item in translations]


class OpenAICompatibleTranslator(ChatCompletionsTranslator):
    """Backward-friendly alias for the provider-neutral translator."""


class DeepSeekTranslator(ChatCompletionsTranslator):
    """Backward-compatible alias for older imports."""


def _collect_translation_targets(page: Page) -> tuple[list[object], list[str]]:
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


def translate_page(page: Page, translator: Translator) -> None:
    targets, texts = _collect_translation_targets(page)
    if not targets:
        return
    translations = translator.translate_texts(texts)
    _apply_translations(targets, translations)


def translate_document(document: Document, translator: Translator) -> Document:
    translated = document.model_copy(deep=True)
    for page in translated.pages:
        translate_page(page, translator)
    return translated
