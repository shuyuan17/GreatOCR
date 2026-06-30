from __future__ import annotations

import json
import shutil
from pathlib import Path

from greatocr.docx.builder import build_docx
from greatocr.docx.validate_docx import validate_docx_package
from greatocr.ingest.preflight import PreflightResult
from greatocr.model.critical_fields import detect_critical_fields
from greatocr.model.document import Document
from greatocr.model.mapper import map_provider_result
from greatocr.model.markdown_export import export_markdown
from greatocr.providers.base import DocumentParser, ParserJobResult
from greatocr.providers.mineru_zip import load_mineru_zip_result
from greatocr.reports.quality_docx import write_quality_docx
from greatocr.reports.quality_json import write_quality_json
from greatocr.security import DataFlowSummary
from greatocr.task.checkpoints import load_or_create_manifest, mark_stage
from greatocr.validation.checks import run_integrity_checks
from greatocr.validation.quality import compute_quality_summary


class SecurityApprovalRequired(PermissionError):
    """Raised when parsing would send data to an unapproved external provider."""


def run_parse_stage(
    task_dir: Path,
    preflight: PreflightResult,
    parser: DocumentParser,
    security_summary: DataFlowSummary,
) -> ParserJobResult:
    capabilities = parser.capabilities()
    if (
        capabilities.data_residency != "local-fixture"
        and not security_summary.external_upload_allowed
    ):
        raise SecurityApprovalRequired(
            f"Provider {security_summary.provider_name} is not approved for upload."
        )

    raw_result_dir = task_dir / "intermediates" / "provider-raw"
    return parser.parse_document(preflight.source_path, raw_result_dir)


def run_model_stage(
    task_dir: Path,
    preflight: PreflightResult,
    parser_result: ParserJobResult,
) -> Document:
    result_zip_path = parser_result.raw_result_dir / "result.zip"
    if result_zip_path.exists():
        raw_result = load_mineru_zip_result(
            result_zip_path,
            task_dir / "intermediates" / "assets",
            task_dir=task_dir,
        )
    else:
        raw_result_path = parser_result.raw_result_dir / "result.json"
        raw_result = json.loads(raw_result_path.read_text(encoding="utf-8"))
    document = detect_critical_fields(map_provider_result(raw_result, preflight))

    intermediates_dir = task_dir / "intermediates"
    intermediates_dir.mkdir(parents=True, exist_ok=True)
    (intermediates_dir / "document.json").write_text(
        document.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (intermediates_dir / "content.md").write_text(
        export_markdown(document),
        encoding="utf-8",
    )
    return document


def run_docx_stage(task_dir: Path, document: Document) -> Document:
    output_path = task_dir / "result.docx"
    build_result = build_docx(document, output_path, task_dir=task_dir)
    validation = validate_docx_package(output_path)
    updated = document.model_copy(
        update={"issues": [*document.issues, *build_result.issues, *validation.issues]},
        deep=True,
    )

    intermediates_dir = task_dir / "intermediates"
    intermediates_dir.mkdir(parents=True, exist_ok=True)
    (intermediates_dir / "document.json").write_text(
        updated.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return updated


def run_quality_stage(
    task_dir: Path,
    document: Document,
    preflight: PreflightResult,
    security_summary: DataFlowSummary,
) -> Document:
    integrity_issues = run_integrity_checks(document, preflight)
    all_issues = [*document.issues, *integrity_issues]
    updated = document.model_copy(update={"issues": all_issues}, deep=True)
    summary = compute_quality_summary(updated, all_issues)

    write_quality_docx(summary, all_issues, task_dir / "quality-report.docx")

    intermediates_dir = task_dir / "intermediates"
    if security_summary.retention_policy.keep_intermediates:
        write_quality_json(summary, all_issues, intermediates_dir / "quality-report.json")
        (intermediates_dir / "document.json").write_text(
            updated.model_dump_json(indent=2),
            encoding="utf-8",
        )

    return updated


def run_pipeline(
    task_dir: Path,
    preflight: PreflightResult,
    parser: DocumentParser,
    security_summary: DataFlowSummary,
    *,
    resume: bool = False,
) -> Document:
    manifest = load_or_create_manifest(
        task_dir,
        preflight.file_sha256,
        {"provider": security_summary.provider_name},
    )

    try:
        raw_result_dir = task_dir / "intermediates" / "provider-raw"
        document_path = task_dir / "intermediates" / "document.json"
        model_done = resume and manifest.stages.get("model", None) and manifest.stages["model"].status == "succeeded"
        parse_done = resume and manifest.stages.get("parse", None) and manifest.stages["parse"].status == "succeeded"

        if model_done and document_path.exists():
            parser_result = ParserJobResult(
                provider_name=security_summary.provider_name,
                raw_result_dir=raw_result_dir,
                metadata={},
            )
        elif parse_done and (raw_result_dir / "result.json").exists():
            parser_result = ParserJobResult(
                provider_name=security_summary.provider_name,
                raw_result_dir=raw_result_dir,
                metadata={},
            )
        else:
            manifest = mark_stage(task_dir, manifest, "parse", "running")
            parser_result = run_parse_stage(task_dir, preflight, parser, security_summary)
            manifest = mark_stage(
                task_dir,
                manifest,
                "parse",
                "succeeded",
                outputs={"provider_raw": "intermediates/provider-raw"},
            )

        if model_done and document_path.exists():
            document = Document.model_validate_json(document_path.read_text(encoding="utf-8"))
        else:
            manifest = mark_stage(task_dir, manifest, "model", "running")
            document = run_model_stage(task_dir, preflight, parser_result)
            manifest = mark_stage(
                task_dir,
                manifest,
                "model",
                "succeeded",
                outputs={
                    "document_json": "intermediates/document.json",
                    "content_md": "intermediates/content.md",
                },
            )

        docx_done = resume and manifest.stages.get("docx", None) and manifest.stages["docx"].status == "succeeded"
        if not (docx_done and (task_dir / "result.docx").exists()):
            manifest = mark_stage(task_dir, manifest, "docx", "running")
            document = run_docx_stage(task_dir, document)
            manifest = mark_stage(
                task_dir,
                manifest,
                "docx",
                "succeeded",
                outputs={"result_docx": "result.docx"},
            )

        quality_done = resume and manifest.stages.get("quality", None) and manifest.stages["quality"].status == "succeeded"
        if not (quality_done and (task_dir / "quality-report.docx").exists()):
            manifest = mark_stage(task_dir, manifest, "quality", "running")
            document = run_quality_stage(task_dir, document, preflight, security_summary)
            mark_stage(
                task_dir,
                manifest,
                "quality",
                "succeeded",
                outputs={"quality_report_docx": "quality-report.docx"},
            )

        if not security_summary.retention_policy.keep_intermediates:
            shutil.rmtree(task_dir / "intermediates", ignore_errors=True)

        return document
    except Exception as exc:
        mark_stage(task_dir, manifest, "pipeline", "failed", message=type(exc).__name__)
        raise
