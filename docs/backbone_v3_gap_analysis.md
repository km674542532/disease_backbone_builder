# Backbone v3 Gap Analysis

## 当前 coverage 短板
- v2 中 hallmarks/modules 受 seed 和模板链限制，覆盖不足。
- key_genes 缺少机制绑定导致核心机制稀疏。

## 当前 normalization 短板
- 基因 alias 未集中治理，SNCA/DJ-1/PINK-1 等存在碎片化。
- phenotype 与 mechanism 混层，导致模块语义不稳定。

## 当前 chain generation 短板
- v2 使用固定模板链，无法随证据拓展。
- relation edge 未使用 source quality 进行加权。

## 本轮修复策略
- 引入 source_tier/source_weight 与可解释 confidence breakdown。
- 新增 normalization 子层（gene/disease/mechanism/phenotype）。
- 升级为 graph-based canonical chain builder。