from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from greatocr.config import EngineConfig, get_runtime_info
from greatocr.ingest.preflight import InvalidPdfError, run_preflight
from greatocr.providers.fake import FakeDocumentParser
from greatocr.rework import rework_pages, rework_tables
from greatocr.security import SecurityMode, build_data_flow_summary
from greatocr.task.progress import format_progress_bar


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="greatocr",
        description="GreatOCR V1 MVP document reconstruction engine.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Print runtime environment checks.")

    convert_parser = subparsers.add_parser(
        "convert",
        help="Validate a single PDF input for future conversion.",
    )
    convert_parser.add_argument("source_pdf", type=Path)
    convert_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run local preflight and print a data-flow summary only.",
    )
    convert_parser.add_argument(
        "--sensitive",
        action="store_true",
        help="Use sensitive-file defaults for security and retention.",
    )
    convert_parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Print text progress while running local checks.",
    )

    rework_parser = subparsers.add_parser(
        "rework",
        help="Rework selected pages or table IDs for an existing task.",
    )
    rework_parser.add_argument("--task-dir", type=Path, required=True)
    rework_parser.add_argument("--pages")
    rework_parser.add_argument("--tables")

    return parser


def run_doctor() -> int:
    runtime = get_runtime_info()
    print(f"Python: {runtime.python_version}")
    print(f"GreatOCR: {runtime.greatocr_version}")
    return 0


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def run_convert(
    source_pdf: Path,
    parser: argparse.ArgumentParser,
    *,
    dry_run: bool = False,
    sensitive: bool = False,
    show_progress: bool = False,
) -> int:
    if not source_pdf.exists():
        parser.error(f"input file does not exist: {source_pdf}")
    if source_pdf.suffix.lower() != ".pdf":
        parser.error(f"expected a .pdf file: {source_pdf}")

    if dry_run:
        if show_progress:
            print(format_progress_bar(50))
        try:
            preflight = run_preflight(source_pdf)
        except InvalidPdfError as exc:
            parser.error(str(exc))

        security_mode = SecurityMode.SENSITIVE if sensitive else SecurityMode.NORMAL
        summary = build_data_flow_summary(
            EngineConfig(security_mode=security_mode),
            preflight,
        )
        page_counts = Counter(page.page_type for page in preflight.pages)

        print(f"Pages: {preflight.page_count}")
        print(f"Encrypted: {yes_no(preflight.encrypted)}")
        print("Page types:")
        for page_type in ("native_text", "scanned", "mixed"):
            print(f"  {page_type}: {page_counts[page_type]}")
        print(f"Provider: {summary.provider_name}")
        print(f"External upload allowed: {yes_no(summary.external_upload_allowed)}")
        print(
            f"Keep intermediates: {yes_no(summary.retention_policy.keep_intermediates)}"
        )
        return 0

    print(f"Input validated: {source_pdf}")
    print("PDF conversion is not implemented in Phase 0.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return run_doctor()
    if args.command == "convert":
        return run_convert(
            args.source_pdf,
            parser,
            dry_run=args.dry_run,
            sensitive=args.sensitive,
            show_progress=args.show_progress,
        )
    if args.command == "rework":
        fixture = Path("tests/fixtures/provider_outputs/simple_contract.json")
        parser_instance = FakeDocumentParser(fixture)
        if args.pages:
            pages = [int(page.strip()) for page in args.pages.split(",") if page.strip()]
            rework_pages(args.task_dir, pages, parser_instance)
            return 0
        if args.tables:
            table_ids = [item.strip() for item in args.tables.split(",") if item.strip()]
            rework_tables(args.task_dir, table_ids, parser_instance)
            return 0
        parser.error("rework requires --pages or --tables")

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
