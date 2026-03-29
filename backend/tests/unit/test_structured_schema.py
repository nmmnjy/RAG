from app.schemas.document_parse import DocumentMetadata, DocumentStatus, StructuredDocument


def test_document_metadata_required_fields() -> None:
    metadata = DocumentMetadata(
        doc_id="doc_001",
        kb_id="kb_001",
        source="upload",
        format="pdf",
        version="v1",
        status=DocumentStatus.pending,
    )
    assert metadata.doc_id == "doc_001"
    assert metadata.kb_id == "kb_001"
    assert metadata.source == "upload"
    assert metadata.format == "pdf"
    assert metadata.version == "v1"
    assert metadata.status == "pending"


def test_structured_document_frozen_keys_for_02_contract() -> None:
    structured_document = StructuredDocument(
        doc_id="doc_001",
        kb_id="kb_001",
        source="file://sample.md",
        format="markdown",
        version="v1",
        status="succeeded",
        sections=[],
    )
    keys = structured_document.model_dump().keys()
    for required_key in ["doc_id", "kb_id", "source", "format", "version", "status"]:
        assert required_key in keys
