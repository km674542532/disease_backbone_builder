# Backbone Audit

- 生成入口: `app/pipelines/build_backbone.py::build`。
- 聚合逻辑: `app/services/aggregator.py::Aggregator.aggregate`。
- schema/validator: `app/schemas/backbone_draft.py` 与 `app/services/validator.py`。
- source packet 处理: `app/services/packetizer.py`, `app/services/llm_extractor.py`, `app/services/normalizer.py`。

## 粗糙问题结论
- 粗糙项主要来自自由抽取候选直接进入聚合，缺少 seed 约束与噪声过滤。
- hallmark/module 早期缺乏强 schema 限制，导致 unknown 或临床管理类词条混入。
- gene-module / chain 绑定薄弱，导致机制链可解释性不足。