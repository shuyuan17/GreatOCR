from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import run_preflight
from greatocr.pipeline import run_pipeline
from greatocr.providers.fake import FakeDocumentParser
from greatocr.security import build_data_flow_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GreatOCR V1 acceptance checks.")
    parser.add_argument("--provider", choices=["fake"], default="fake")
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="greatocr-acceptance-") as temp:
        root = Path(temp)
        pdf_path = root / "acceptance.pdf"
        _create_pdf(pdf_path)
        preflight = run_preflight(pdf_path)
        summary = build_data_flow_summary(
            EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
            preflight,
        )
        fixture = Path("tests/fixtures/provider_outputs/simple_contract.json")
        task_dir = root / "task"
        run_pipeline(task_dir, preflight, FakeDocumentParser(fixture), summary)

        required = [
            task_dir / "result.docx",
            task_dir / "quality-report.docx",
            task_dir / "intermediates" / "document.json",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            print("missing acceptance outputs: " + ", ".join(missing))
            return 1

    print("fake provider acceptance passed")
    return 0


def _create_pdf(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawString(72, 720, "GreatOCR acceptance sample")
    pdf.save()


if __name__ == "__main__":
    raise SystemExit(main())
