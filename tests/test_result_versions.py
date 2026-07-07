from pathlib import Path

from greatocr.task.versions import publish_result_version


def source_docx(path: Path, content: str) -> Path:
    path.write_bytes(content.encode("utf-8"))
    return path


def test_new_result_version_preserves_previous_file(tmp_path: Path) -> None:
    v1 = publish_result_version(
        tmp_path,
        source_docx(tmp_path / "one.docx", "one"),
        latest_name="sample.docx",
    )
    v2 = publish_result_version(
        tmp_path,
        source_docx(tmp_path / "two.docx", "two"),
        latest_name="sample.docx",
    )

    assert v1.name == "result-v1.docx"
    assert v2.name == "result-v2.docx"
    assert v1.read_bytes() == b"one"
    assert v2.read_bytes() == b"two"
    assert (tmp_path / "sample.docx").read_bytes() == b"two"
    assert not (tmp_path / "result.docx").exists()
    assert (tmp_path / "intermediates" / "versions" / "result-v1.docx").is_file()
    assert (tmp_path / "intermediates" / "versions" / "result-v2.docx").is_file()


def test_first_rework_preserves_existing_unversioned_result(tmp_path: Path) -> None:
    (tmp_path / "sample.docx").write_bytes(b"original")

    version = publish_result_version(
        tmp_path,
        source_docx(tmp_path / "reworked.docx", "reworked"),
        latest_name="sample.docx",
    )

    assert (tmp_path / "intermediates" / "versions" / "result-v1.docx").read_bytes() == b"original"
    assert version.name == "result-v2.docx"
    assert (tmp_path / "sample.docx").read_bytes() == b"reworked"
