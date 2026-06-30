from __future__ import annotations

import json
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile


def load_mineru_zip_result(
    zip_path: Path,
    assets_dir: Path,
    *,
    task_dir: Path | None = None,
) -> dict:
    task_dir = task_dir or assets_dir
    with ZipFile(zip_path) as zf:
        content_name = _find_content_list(zf.namelist())
        content_list = json.loads(zf.read(content_name).decode("utf-8"))
        fingerprints = _extract_images(zf, assets_dir)

    pages: dict[int, list[dict]] = {}
    for item in content_list:
        if not isinstance(item, dict):
            continue
        page_number = int(item.get("page_idx", 0)) + 1
        block = _normalize_item(item, assets_dir, task_dir, fingerprints)
        if block:
            pages.setdefault(page_number, []).append(block)

    return {
        "provider": {"name": "mineru"},
        "document": {
            "pages": [
                {"page_number": page_number, "blocks": blocks}
                for page_number, blocks in sorted(pages.items())
            ]
        },
    }


def _find_content_list(names: list[str]) -> str:
    candidates = [
        name
        for name in names
        if name.endswith("_content_list.json") and not name.endswith("_content_list_v2.json")
    ]
    if not candidates:
        raise FileNotFoundError("MinerU result zip missing *_content_list.json")
    return candidates[0]


def _extract_images(zf: ZipFile, assets_dir: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    assets_dir.mkdir(parents=True, exist_ok=True)
    assets_root = assets_dir.resolve()
    for name in zf.namelist():
        if not name.startswith("images/") or name.endswith("/"):
            continue
        target = (assets_root / name).resolve()
        try:
            target.relative_to(assets_root)
        except ValueError:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        content = zf.read(name)
        target.write_bytes(content)
        fingerprints[name] = hashlib.sha256(content).hexdigest()
    return fingerprints


def _normalize_item(
    item: dict,
    assets_dir: Path,
    task_dir: Path,
    fingerprints: dict[str, str],
) -> dict | None:
    item_type = item.get("type")
    bbox = item.get("bbox")
    if item_type == "text":
        block_type = "title" if item.get("text_level") == 1 else "paragraph"
        return {
            "type": block_type,
            "text": item.get("text", ""),
            "bbox": bbox,
            "confidence": 1.0,
        }
    if item_type == "page_number":
        return {"type": "page_number", "text": item.get("text", ""), "bbox": bbox}
    if item_type == "image":
        image_path = item.get("img_path") or item.get("image_path")
        extracted_path = assets_dir / image_path if image_path else None
        return {
            "type": "image",
            "asset_id": Path(image_path or "image").stem,
            "path": (
                extracted_path.relative_to(task_dir).as_posix()
                if extracted_path and extracted_path.is_relative_to(task_dir)
                else None
            ),
            "content_fingerprint": fingerprints.get(image_path or ""),
            "bbox": bbox,
        }
    if item_type == "table":
        return {
            "type": "table",
            "rows": _parse_table_rows(item.get("table_body", "")),
            "bbox": bbox,
            "confidence": 1.0,
        }
    return None


def _parse_table_rows(table_html: str) -> list[list[str]]:
    parser = _TableParser()
    parser.feed(table_html or "")
    return parser.rows


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in {"td", "th"}:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_row is not None and self._current_cell is not None:
            self._current_row.append("".join(self._current_cell).strip())
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            self.rows.append(self._current_row)
            self._current_row = None
