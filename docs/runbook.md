# Runbook

## 1. 环境准备

- Python: `>=3.10`
- 推荐：`venv` 或 `conda`
- 网络模式：
  - mock 模式可离线
  - PubMed/Qwen 模式需要外网

## 2. 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]
```

## 3. 配置

## 3.1 Mock（最小可运行）
无需 API Key。

## 3.2 Qwen 模式
任选其一：

```bash
export QWEN_API_KEY="..."
# 或
export DASHSCOPE_API_KEY="..."
```

可选：
```bash
export QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

## 3.3 PubMed 模式
运行参数中提供：
- `--pubmed-email`
- 可选 `--pubmed-api-key`

## 4. 运行命令

## 4.1 最小 demo（mock + 本地输入）

```bash
python -m app.pipelines.build_backbone \
  --input data/raw/pd_sources.json \
  --disease "Parkinson disease" \
  --llm-mode mock
```

## 4.2 使用 PubMed（缓存优先）

```bash
python -m app.pipelines.build_backbone \
  --disease "Parkinson disease" \
  --use-pubmed \
  --pubmed-email "your_email@example.com" \
  --max-reviews 30
```

## 4.3 强制刷新 PubMed

```bash
python -m app.pipelines.build_backbone \
  --disease "Parkinson disease" \
  --use-pubmed \
  --pubmed-email "your_email@example.com" \
  --refresh-pubmed
```

## 4.4 指定 Qwen

```bash
python -m app.pipelines.build_backbone \
  --input data/raw/pd_sources.json \
  --disease "Parkinson disease" \
  --llm-mode qwen
```

## 4.5 使用配置文件 + 运行级产物目录

```bash
python -m app.pipelines.build_backbone \
  --input data/raw/pd_sources.json \
  --disease "Parkinson disease" \
  --llm-mode mock \
  --config config/backbone_rules.v1_1.yaml \
  --output-root data/runs \
  --run-id pd_20260409_demo
```

运行后可在 `data/runs/pd_20260409_demo/` 下查看完整分层产物与 `config/effective_builder_config.json`。

## 5. 成功判定

至少检查以下文件存在：

- `data/outputs/disease_backbone_draft.json`
- `data/outputs/validation_report.json`
- `data/extraction_results/extraction_results.jsonl`
- `data/extraction_results/raw_llm_responses.jsonl`

可选快速检查：

```bash
python - <<'PY'
from pathlib import Path
required = [
  'data/outputs/disease_backbone_draft.json',
  'data/outputs/validation_report.json',
]
for p in required:
    print(p, 'OK' if Path(p).exists() else 'MISSING')
PY
```

## 6. 常见报错与排查

1. `ModuleNotFoundError: openai`
   - 现象：测试或 qwen 模式导入失败。
   - 处理：`pip install -e .[dev]`，并确认当前虚拟环境。

2. `No sources available. Provide --input and/or --use-pubmed.`
   - 原因：未提供输入，也未开启 PubMed。
   - 处理：增加 `--input` 或 `--use-pubmed`。

3. `pubmed_email is required when refreshing PubMed retrieval.`
   - 原因：`--refresh-pubmed` 时缺少 email。
   - 处理：补充 `--pubmed-email`。

4. extraction 大量失败且 `raw_response.error` 存在
   - 原因：LLM 不可用、返回非 JSON、schema 不匹配。
   - 处理：
     - 先切换 `--llm-mode mock` 验证主流程。
     - 再检查 API key / 网络 / prompt 与 schema 一致性。

5. 结果过空（hallmark/module 数为 0）
   - 原因：输入文本弱、抽取失败、prune过严。
   - 处理：
     - 提升输入质量
     - 检查 `data/extraction_results/*`
     - 检查 `data/aggregation/prune_log.json`

## 7. 推荐开发调试顺序

1. `pytest -q tests/schemas`
2. `pytest -q tests/services`
3. `pytest -q tests/pipelines`
4. 最后跑一次 mock 端到端
