from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScoreNormalizationMethod(str, Enum):
    min_max = "min_max"


class FusionStrategyName(str, Enum):
    weighted_sum = "weighted_sum"


class KeywordQueryRequest(BaseModel):
    kb_id: str
    query_text: str
    top_k: int = Field(default=20, ge=1, le=100)
    doc_id: str | None = None


class KeywordQueryHit(BaseModel):
    chunk_id: str
    doc_id: str
    kb_id: str
    content: str
    section_path: list[str] = Field(default_factory=list)
    score_keyword: float
    citation: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HybridFusionConfig(BaseModel):
    strategy_name: FusionStrategyName = FusionStrategyName.weighted_sum
    normalization_method: ScoreNormalizationMethod = ScoreNormalizationMethod.min_max
    vector_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.4, ge=0.0, le=1.0)


class HybridRetrieveTuningConfig(BaseModel):
    top_k: int = Field(default=5, ge=1, le=100)
    vector_top_k: int = Field(default=20, ge=1, le=100)
    keyword_top_k: int = Field(default=20, ge=1, le=100)
    enable_rerank: bool = False
    fusion_config: HybridFusionConfig = Field(default_factory=HybridFusionConfig)


class HybridRetrieveRequest(BaseModel):
    kb_id: str
    query_text: str
    top_k: int = Field(default=5, ge=1, le=100)
    vector_top_k: int = Field(default=20, ge=1, le=100)
    keyword_top_k: int = Field(default=20, ge=1, le=100)
    doc_id: str | None = None
    fusion_config: HybridFusionConfig = Field(default_factory=HybridFusionConfig)
    enable_rerank: bool = False
    tuning_config: HybridRetrieveTuningConfig | None = None

    def get_effective_tuning_config(self) -> HybridRetrieveTuningConfig:
        if self.tuning_config is None:
            return HybridRetrieveTuningConfig(
                top_k=self.top_k,
                vector_top_k=self.vector_top_k,
                keyword_top_k=self.keyword_top_k,
                enable_rerank=self.enable_rerank,
                fusion_config=self.fusion_config,
            )
        return self.tuning_config


class HybridRetrieveHit(BaseModel):
    chunk_id: str
    doc_id: str
    kb_id: str
    content: str
    section_path: list[str] = Field(default_factory=list)
    score_vector: float = 0.0
    score_keyword: float = 0.0
    score_final: float = 0.0
    citation: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HybridRetrieveResult(BaseModel):
    kb_id: str
    query_text: str
    top_k: int
    hits: list[HybridRetrieveHit] = Field(default_factory=list)
    debug: dict[str, Any] = Field(default_factory=dict)


class RerankRequest(BaseModel):
    query_text: str
    hits: list[HybridRetrieveHit] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=100)
