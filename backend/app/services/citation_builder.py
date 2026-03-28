from __future__ import annotations

from app.schemas.answer_generation import AnswerCitation
from app.schemas.retrieval import HybridRetrieveHit


class CitationBuilder:
    """Builds stable frontend citation payload from module-04 hits."""

    def build(self, hits: list[HybridRetrieveHit]) -> list[AnswerCitation]:
        citations: list[AnswerCitation] = []
        for index, hit in enumerate(hits, start=1):
            source = None
            if isinstance(hit.citation, dict):
                source = hit.citation.get("source")
            citations.append(
                AnswerCitation(
                    citation_id=f"c{index}",
                    chunk_id=hit.chunk_id,
                    doc_id=hit.doc_id,
                    kb_id=hit.kb_id,
                    section_path=hit.section_path,
                    snippet=hit.content[:200],
                    score_final=hit.score_final,
                    source=source,
                    citation=hit.citation,
                )
            )
        return citations
