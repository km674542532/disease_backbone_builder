# Normalization External Sources Gap Analysis

## 当前实现概况
- 现有流程已接入 HGNC/MONDO/MeSH/Orphanet 离线快照驱动，并保留本地 mechanism/phenotype controlled vocab。

## 缺失的权威外部源支持
- phenotype 尚未接 HPO；mechanism 尚未接 GO/Reactome；disease 仍缺 OMIM 专用快照。

## 易误归一/漏归一环节
- 模糊匹配候选在多候选时仅标记冲突，不做上下文判别。
- 新名词若不在快照中会进入 unresolved，需周期更新快照。

## 本轮修复计划
- 统一 normalization schema + QA 统计闭环 + unresolved/conflict 落盘输出。