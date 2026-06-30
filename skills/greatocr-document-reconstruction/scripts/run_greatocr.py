from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the GreatOCR local CLI.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--sensitive", action="store_true")
    parser.add_argument("--provider")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = [sys.executable, "-m", "greatocr.cli", "convert", str(args.pdf_path)]
    display_command = ["python", "-m", "greatocr.cli", "convert", str(args.pdf_path)]

    if args.dry_run:
        command.append("--dry-run")
        display_command.append("--dry-run")
    if args.sensitive:
        command.append("--sensitive")
        display_command.append("--sensitive")
    if args.output_dir:
        command.extend(["--output-dir", str(args.output_dir)])
        display_command.extend(["--output-dir", str(args.output_dir)])
    if args.provider:
        display_command.extend(["--provider", args.provider])

    print(" ".join(display_command))
    if args.dry_run:
        return 0

    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
