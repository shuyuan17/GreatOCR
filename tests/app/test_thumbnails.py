from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from greatocr.app.services.thumbnails import ThumbnailService


def pdf_with_pages(tmp_path: Path, page_count: int) -> Path:
    path = tmp_path / "many-pages.pdf"
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def test_thumbnail_service_renders_only_requested_window(tmp_path: Path) -> None:
    service = ThumbnailService(tmp_path / "cache", max_cached_pages=20)

    result = service.render(pdf_with_pages(tmp_path, 100), pages=range(41, 51))

    assert [item.page_number for item in result] == list(range(41, 51))
    assert all(item.path.exists() for item in result)
    assert len(list((tmp_path / "cache").glob("*.png"))) == 10


def test_thumbnail_service_rejects_out_of_range_page(tmp_path: Path) -> None:
    service = ThumbnailService(tmp_path / "cache", max_cached_pages=20)

    try:
        service.render(pdf_with_pages(tmp_path, 3), pages=[4])
    except ValueError as exc:
        assert "outside PDF range" in str(exc)
    else:
        raise AssertionError("expected an out-of-range page error")


def test_thumbnail_cache_never_exceeds_limit(tmp_path: Path) -> None:
    service = ThumbnailService(tmp_path / "cache", max_cached_pages=20)
    source = pdf_with_pages(tmp_path, 30)

    service.render(source, pages=range(1, 16))
    service.render(source, pages=range(16, 31))

    assert len(list((tmp_path / "cache").glob("*.png"))) == 20
