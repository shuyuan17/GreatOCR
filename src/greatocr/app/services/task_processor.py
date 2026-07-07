from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from greatocr.app.db import TaskDatabase
from greatocr.app.schemas import TaskRecord, TaskStatus
from greatocr.app.services.credentials import CredentialService
from greatocr.docx.builder import build_docx
from greatocr.ingest.preflight import InvalidPdfError, run_preflight
from greatocr.pipeline import run_pipeline
from greatocr.providers.mineru import MinerUConfig, MinerUDocumentParser
from greatocr.providers.profiles import ProviderProfile
from greatocr.providers.registry import ProviderRegistry
from greatocr.security import DataFlowSummary, RetentionPolicy, SecurityMode
from greatocr.task.checkpoints import load_or_create_manifest, mark_stage
from greatocr.task.output_files import result_docx_name, translated_docx_name
from greatocr.translation import (
    ChatCompletionsTranslator,
    TranslationError,
    translate_document,
)


_CHINESE_ALIASES = {"中文", "chinese", "zh", "cn", "zho"}
_DEFAULT_TARGET_LANGUAGE = "中文"


def _normalize_target_language(value: str | None) -> str:
    if not value:
        return _DEFAULT_TARGET_LANGUAGE
    if value.strip().lower() in _CHINESE_ALIASES:
        return _DEFAULT_TARGET_LANGUAGE
    return _DEFAULT_TARGET_LANGUAGE


class TaskProcessor:
    def __init__(
        self,
        database: TaskDatabase,
        credentials: CredentialService,
        *,
        source_path_resolver: Callable[[str], Path] | None = None,
        translator_factory: Callable[..., Any] | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.database = database
        self.credentials = credentials
        self.source_path_resolver = source_path_resolver
        self.translator_factory = translator_factory or ChatCompletionsTranslator
        self.logger = logger or print

    def process(self, task: TaskRecord) -> TaskStatus:
        try:
            return self._process(task)
        except InvalidPdfError as exc:
            self.logger(f"[worker] Task {task.task_id} failed preflight: {exc}")
            return "failed"
        except Exception as exc:
            self.logger(f"[worker] Task {task.task_id} failed: {exc}")
            return "failed"

    def _process(self, task: TaskRecord) -> TaskStatus:
        ocr_provider_id = task.ocr_provider_profile_id or task.provider_profile_id
        ocr_profile_dict = self.database.get_provider(ocr_provider_id)
        if ocr_profile_dict is None:
            raise RuntimeError(f"OCR provider {ocr_provider_id} 未找到")
        ocr_profile = ProviderProfile.model_validate(
            {
                "profile_id": ocr_profile_dict["profile_id"],
                "display_name": ocr_profile_dict["display_name"],
                "adapter_type": ocr_profile_dict["adapter_type"],
                "endpoint": ocr_profile_dict["endpoint"] or "",
                "model_name": ocr_profile_dict.get("model"),
                "public": ocr_profile_dict["public"],
                "capabilities": ocr_profile_dict["capabilities"],
            }
        )

        parser = self._create_parser(ocr_profile)
        source_path = self._resolve_source_path(task)
        preflight = run_preflight(source_path)
        task_dir = Path(task.output_dir)
        task_dir.mkdir(parents=True, exist_ok=True)

        security_summary = DataFlowSummary(
            security_mode=SecurityMode.SENSITIVE if task.sensitive else SecurityMode.NORMAL,
            source_file_name=source_path.name,
            page_count=preflight.page_count,
            provider_name=ocr_profile.display_name,
            provider_endpoint=ocr_profile.endpoint or None,
            provider_public=bool(ocr_profile.public),
            external_upload_allowed=True,
            requires_confirmation=False,
            retention_policy=RetentionPolicy(
                keep_intermediates=not task.sensitive,
                keep_page_cache=False,
            ),
        )

        document = run_pipeline(
            task_dir=task_dir,
            preflight=preflight,
            parser=parser,
            security_summary=security_summary,
            selected_pages=task.selected_pages or None,
        )

        if task.processing_mode != "translation":
            return "succeeded"

        translation_provider_id = task.translation_provider_profile_id
        if not translation_provider_id:
            raise RuntimeError("translation_provider_profile_id 未配置")
        translation_profile = self.database.get_provider(translation_provider_id)
        if translation_profile is None:
            raise RuntimeError(f"翻译 provider {translation_provider_id} 未找到")
        if task.sensitive and not bool(translation_profile.get("sensitive_allowed", False)):
            raise RuntimeError("敏感文件不允许发送给当前翻译 Provider")

        translated_path = task_dir / translated_docx_name(source_path.name)
        translated_path.unlink(missing_ok=True)
        manifest = load_or_create_manifest(task_dir, preflight.file_sha256, {})
        manifest = mark_stage(task_dir, manifest, "translation", "running")

        try:
            translator = self.translator_factory(
                api_key=self.credentials.resolve(translation_provider_id).get_secret_value(),
                endpoint=translation_profile.get("endpoint"),
                model_name=translation_profile.get("model"),
                target_language=_normalize_target_language(task.target_language),
                provider_name=translation_profile.get("display_name") or "翻译 Provider",
            )
            translated_document = translate_document(document, translator)
            build_docx(translated_document, translated_path, task_dir=task_dir)
        except (TranslationError, Exception) as exc:
            translated_path.unlink(missing_ok=True)
            provider_name = translation_profile.get("display_name") or translation_provider_id
            mark_stage(
                task_dir,
                manifest,
                "translation",
                "failed",
                message=_safe_translation_error_message(exc),
            )
            self.logger(
                f"[worker] Task {task.task_id} translation failed via {provider_name}: {exc}"
            )
            return "partial"

        mark_stage(
            task_dir,
            manifest,
            "translation",
            "succeeded",
            outputs={"translated_result": translated_docx_name(source_path.name)},
        )
        self.logger(f"[worker] Task {task.task_id} translated -> {translated_path}")
        return "succeeded"

    def _create_parser(self, profile: ProviderProfile):
        if profile.adapter_type == "mineru":
            secret = self.credentials.resolve(profile.profile_id).get_secret_value()
            return MinerUDocumentParser(
                MinerUConfig(base_url=profile.endpoint, api_key=secret),
                upload_confirmed=True,
            )
        registry = ProviderRegistry([profile])
        return registry.create_parser(
            profile.profile_id,
            lambda profile_id: self.credentials.resolve(profile_id).get_secret_value(),
        )

    def _resolve_source_path(self, task: TaskRecord) -> Path:
        if self.source_path_resolver is not None:
            return self.source_path_resolver(task.task_id)
        if task.source_path is None:
            raise RuntimeError("source path not available")
        return Path(task.source_path)


def _safe_translation_error_message(exc: Exception) -> str:
    message = str(exc).lower()
    if any(
        token in message
        for token in ("401", "403", "unauthorized", "forbidden", "api key", "authentication")
    ):
        return "Translation Provider authentication failed. Please check API Key configuration."
    if "model" in message and any(
        token in message for token in ("unavailable", "not found", "does not exist", "invalid")
    ):
        return "Translation Provider model unavailable. Please check model configuration."
    if any(token in message for token in ("connect", "connection", "timeout", "network", "dns")):
        return "Translation Provider connection failed. Please check Provider network configuration."
    if "404" in message:
        return "Translation Provider model unavailable. Please check model configuration."
    return "Translation failed. Please check Provider configuration and try again."
