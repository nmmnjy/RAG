from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import Counter
from math import log

from app.schemas.retrieval import KeywordQueryHit, KeywordQueryRequest


def _tokenize(text: str) -> list[str]:
    return [item for item in re.split(r"[^\w]+", text.lower()) if item]


class KeywordRetriever(ABC):
    @abstractmethod
    def index_documents(self, documents: list[dict]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, request: KeywordQueryRequest) -> list[KeywordQueryHit]:
        raise NotImplementedError


class InMemoryKeywordRetriever(KeywordRetriever):
    def __init__(self) -> None:
        self._documents: dict[str, dict] = {}

    def index_documents(self, documents: list[dict]) -> None:
        for item in documents:
            chunk_id = item["chunk_id"]
            content = item.get("content", "")
            tokens = _tokenize(content)
            term_counts = Counter(tokens)
            self._documents[chunk_id] = {
                **item,
                "tokens": tokens,
                "token_count": max(len(tokens), 1),
                "term_counts": term_counts,
            }

    def search(self, request: KeywordQueryRequest) -> list[KeywordQueryHit]:
        if request.top_k == 0:
            return []
        query_terms = _tokenize(request.query_text)
        if not query_terms:
            return []

        candidates = [
            item
            for item in self._documents.values()
            if item["kb_id"] == request.kb_id and (request.doc_id is None or item["doc_id"] == request.doc_id)
        ]
        if not candidates:
            return []

        doc_freq: Counter[str] = Counter()
        for term in set(query_terms):
            for document in candidates:
                if document["term_counts"].get(term, 0) > 0:
                    doc_freq[term] += 1

        total_docs = len(candidates)
        hits: list[KeywordQueryHit] = []
        for document in candidates:
            score_keyword = 0.0
            for term in query_terms:
                tf = document["term_counts"].get(term, 0) / document["token_count"]
                if tf == 0:
                    continue
                idf = log((1 + total_docs) / (1 + doc_freq[term])) + 1
                score_keyword += tf * idf
            if score_keyword <= 0:
                continue
            hits.append(
                KeywordQueryHit(
                    chunk_id=document["chunk_id"],
                    doc_id=document["doc_id"],
                    kb_id=document["kb_id"],
                    content=document["content"],
                    section_path=document.get("section_path", []),
                    score_keyword=score_keyword,
                    citation=document.get("citation", {}),
                    metadata=document.get("metadata", {}),
                )
            )
        hits.sort(key=lambda item: (-item.score_keyword, item.chunk_id))
        return hits[: request.top_k]
