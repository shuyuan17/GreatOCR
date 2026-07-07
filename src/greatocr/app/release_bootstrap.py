from __future__ import annotations

import os
from pathlib import Path

from greatocr.app.db import TaskDatabase


DEFAULT_PREFERENCES = {
    "ocr_language": "auto",
    "sensitive_file_mode": "false",
    "pdf_process_all_pages": "true",
    "pdf_default_page_range": "",
    "output_same_as_input": "true",
    "result_export_docx": "true",
    "result_generate_quality_report": "true",
}


def get_user_data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "GreatOCR"
    return Path.home() / ".greatocr"


def ensure_release_defaults(database: TaskDatabase, *, data_dir: Path) -> None:
    if database.get_provider("mineru-default") is None:
        database.save_provider(
            {
                "profile_id": "mineru-default",
                "display_name": "MinerU",
                "adapter_type": "mineru",
                "endpoint": "https://mineru.net",
                "model": None,
                "public": True,
                "capabilities": {
                    "native_pdf": True,
                    "scanned_pdf": True,
                    "coordinates": True,
                    "layout": True,
                    "tables": True,
                    "images": True,
                    "formulas": True,
                    "languages": ["auto"],
                    "data_residency": "provider-defined",
                },
                "approved_fallback_ids": [],
            }
        )

    if database.get_provider("deepseek-default") is None:
        database.save_provider(
            {
                "profile_id": "deepseek-default",
                "display_name": "DeepSeek 翻译",
                "adapter_type": "deepseek",
                "endpoint": "https://api.deepseek.com/chat/completions",
                "model": "deepseek-chat",
                "public": True,
                "capabilities": {
                    "native_pdf": False,
                    "scanned_pdf": False,
                    "coordinates": False,
                    "tables": False,
                    "formulas": False,
                    "languages": ["*"],
                    "data_residency": "provider-defined",
                    "text": False,
                    "layout": False,
                    "images": False,
                },
                "approved_fallback_ids": [],
            }
        )

    if database.get_provider("zhipu-glm-default") is None:
        database.save_provider(
            {
                "profile_id": "zhipu-glm-default",
                "display_name": "智谱 GLM",
                "adapter_type": "openai-compatible",
                "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "model": "glm-4-plus",
                "public": True,
                "capabilities": {
                    "translation": True,
                    "text_processing": True,
                },
                "approved_fallback_ids": [],
            }
        )

    existing_prefs = database.get_preferences()
    prefs = {
        **DEFAULT_PREFERENCES,
        "output_default_dir": str(data_dir / "exports"),
    }
    for key, value in prefs.items():
        if key not in existing_prefs:
            database.set_preference(key, value)
