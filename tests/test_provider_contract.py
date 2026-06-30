from pathlib import Path

from greatocr.providers.base import DocumentParser, ParserJobResult, ProviderCapabilities
from greatocr.providers.fake import FakeDocumentParser


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


def test_provider_capabilities_describe_supported_features() -> None:
    parser: DocumentParser = FakeDocumentParser(FIXTURE)

    capabilities = parser.capabilities()

    assert isinstance(capabilities, ProviderCapabilities)
    assert capabilities.native_pdf is True
    assert capabilities.scanned_pdf is True
    assert capabilities.coordinates is True
    assert capabilities.tables is True
    assert capabilities.formulas is False
    assert capabilities.languages == ["auto", "en", "zh"]


def test_parse_document_returns_raw_result_directory_and_metadata(tmp_path: Path) -> None:
    parser: DocumentParser = FakeDocumentParser(FIXTURE)
    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")

    result = parser.parse_document(source_pdf, tmp_path / "provider-raw")

    assert isinstance(result, ParserJobResult)
    assert result.provider_name == "fake"
    assert result.raw_result_dir.is_dir()
    assert (result.raw_result_dir / "result.json").is_file()
    assert result.metadata["fixture"] == str(FIXTURE)


def test_fake_provider_returns_stable_fixture_without_network(tmp_path: Path) -> None:
    parser = FakeDocumentParser(FIXTURE)
    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")

    first = parser.parse_document(source_pdf, tmp_path / "first")
    second = parser.parse_document(source_pdf, tmp_path / "second")

    assert (first.raw_result_dir / "result.json").read_text(encoding="utf-8") == (
        second.raw_result_dir / "result.json"
    ).read_text(encoding="utf-8")
