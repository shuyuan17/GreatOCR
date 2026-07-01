from pathlib import Path

from greatocr.task.versions import publish_result_version


def source_docx(path: Path, content: str) -> Path:
    path.write_bytes(content.encode("utf-8"))
    return path


def test_new_result_version_preserves_previous_file(tmp_path: Path) -> None:
    v1 = publish_result_version(tmp_path, source_docx(tmp_path / "one.docx", "one"))
    v2 = publish_result_version(tmp_path, source_docx(tmp_path / "two.docx", "two"))

    assert v1.name == "result-v1.docx"
    assert v2.name == "result-v2.docx"
    assert v1.read_bytes() == b"one"
    assert v2.read_bytes() == b"two"
    assert (tmp_path / "result.docx").read_bytes() == b"two"


def test_first_rework_preserves_existing_unversioned_result(tmp_path: Path) -> None:
    (tmp_path / "result.docx").write_bytes(b"original")

    version = publish_result_version(
        tmp_path,
        source_docx(tmp_path / "reworked.docx", "reworked"),
    )

    assert (tmp_path / "result-v1.docx").read_bytes() == b"original"
    assert version.name == "result-v2.docx"
    assert (tmp_path / "result.docx").read_bytes() == b"reworked"
