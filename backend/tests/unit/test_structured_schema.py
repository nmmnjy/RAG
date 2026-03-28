from app.schemas.document_parse import DocumentMetadata, DocumentStatus


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
