from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.retrieval import FusionStrategyName, HybridFusionConfig, ScoreNormalizationMethod


def normalize_scores(scores: dict[str, float], method: ScoreNormalizationMethod) -> dict[str, float]:
    if not scores:
        return {}
    if method == ScoreNormalizationMethod.min_max:
        values = list(scores.values())
        min_value = min(values)
        max_value = max(values)
        if max_value == min_value:
            if max_value <= 0:
                return {key: 0.0 for key in scores}
            return {key: 1.0 for key in scores}
        return {key: (value - min_value) / (max_value - min_value) for key, value in scores.items()}
    return scores


class FusionStrategy(ABC):
    @property
    @abstractmethod
    def strategy_name(self) -> FusionStrategyName:
        raise NotImplementedError

    @abstractmethod
    def fuse(
        self,
        vector_scores: dict[str, float],
        keyword_scores: dict[str, float],
        config: HybridFusionConfig,
    ) -> dict[str, float]:
        raise NotImplementedError


class WeightedSumFusionStrategy(FusionStrategy):
    @property
    def strategy_name(self) -> FusionStrategyName:
        return FusionStrategyName.weighted_sum

    def fuse(
        self,
        vector_scores: dict[str, float],
        keyword_scores: dict[str, float],
        config: HybridFusionConfig,
    ) -> dict[str, float]:
        norm_vector = normalize_scores(vector_scores, config.normalization_method)
        norm_keyword = normalize_scores(keyword_scores, config.normalization_method)
        chunk_ids = set(norm_vector.keys()) | set(norm_keyword.keys())
        fused: dict[str, float] = {}
        for chunk_id in chunk_ids:
            score_vector = norm_vector.get(chunk_id, 0.0)
            score_keyword = norm_keyword.get(chunk_id, 0.0)
            fused[chunk_id] = (config.vector_weight * score_vector) + (config.keyword_weight * score_keyword)
        return fused


FUSION_STRATEGY_REGISTRY: dict[FusionStrategyName, FusionStrategy] = {
    FusionStrategyName.weighted_sum: WeightedSumFusionStrategy(),
}


def resolve_fusion_strategy(strategy_name: FusionStrategyName) -> FusionStrategy:
    return FUSION_STRATEGY_REGISTRY.get(strategy_name, FUSION_STRATEGY_REGISTRY[FusionStrategyName.weighted_sum])


def fuse_scores(
    vector_scores: dict[str, float],
    keyword_scores: dict[str, float],
    config: HybridFusionConfig,
) -> dict[str, float]:
    strategy = resolve_fusion_strategy(config.strategy_name)
    return strategy.fuse(vector_scores=vector_scores, keyword_scores=keyword_scores, config=config)
