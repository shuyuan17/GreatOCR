from __future__ import annotations

import pytest

from greatocr.translation import (
    ChatCompletionsTranslator,
    DeepSeekTranslator,
    TranslationError,
)


def test_missing_api_key_message_is_provider_neutral() -> None:
    with pytest.raises(TranslationError, match="翻译 Provider API Key 未配置"):
        ChatCompletionsTranslator(
            "",
            endpoint="https://example.test/chat/completions",
            model_name="glm-4-plus",
        )


def test_deepseek_import_remains_backward_compatible() -> None:
    translator = DeepSeekTranslator(
        "secret",
        endpoint="https://example.test/chat/completions",
        model_name="deepseek-chat",
    )

    assert isinstance(translator, ChatCompletionsTranslator)
