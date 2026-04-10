# Confidence Scoring v3

- confidence = clamp((source_support_score + source_diversity_score + normalization_score + structural_completeness_score + chain_connectivity_score - penalty_score) / 5, 0, 1)
- hallmark/module/gene/relation/chain 全部写入 confidence_breakdown。
- core 条目最低要求：非零 confidence 且满足加权证据门槛。