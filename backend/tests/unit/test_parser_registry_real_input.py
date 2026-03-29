from types import SimpleNamespace

from app.parsers.adapters.base import ParseInput
from app.parsers.registry import parser_registry
import app.parsers.registry as parser_registry_module
from app.schemas.document_parse import DocumentMetadata, DocumentStatus


def test_markdown_real_parser_path(monkeypatch, tmp_path) -> None:
    source_file = tmp_path / "sample.md"
    source_file.write_text("# Title\n\nhello markdown parser", encoding="utf-8")
    monkeypatch.setattr(
        parser_registry_module,
        "settings",
        SimpleNamespace(
            doc_parse_provider="hybrid",
            doc_parse_real_formats={"markdown", "txt"},
            doc_parse_enable_fallback=True,
        ),
    )
    parse_input = ParseInput(
        metadata=DocumentMetadata(
            doc_id="doc_md_001",
            kb_id="kb_001",
            source=str(source_file),
            format="markdown",
            version="v1",
            status=DocumentStatus.parsing,
        ),
        file_path=str(source_file),
    )
    structured_document, mode = parser_registry.parse(parse_input)
    assert mode == "real"
    assert structured_document.format == "markdown"
    assert structured_document.sections


def test_txt_real_parser_fallback_to_placeholder(monkeypatch) -> None:
    monkeypatch.setattr(
        parser_registry_module,
        "settings",
        SimpleNamespace(
            doc_parse_provider="real",
            doc_parse_real_formats={"markdown", "txt"},
            doc_parse_enable_fallback=True,
        ),
    )
    parse_input = ParseInput(
        metadata=DocumentMetadata(
            doc_id="doc_txt_001",
            kb_id="kb_001",
            source="file://not-exists.txt",
            format="txt",
            version="v1",
            status=DocumentStatus.parsing,
        ),
        file_path="not-exists.txt",
    )
    structured_document, mode = parser_registry.parse(parse_input)
    assert mode == "placeholder"
    assert structured_document.doc_id == "doc_txt_001"
