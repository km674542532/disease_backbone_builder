# Standard Sources Setup

- HGNC: `data/standards/hgnc/hgnc_complete_set.json`
- MONDO: `data/standards/mondo/mondo_snapshot.json`
- MeSH: `data/standards/mesh/mesh_snapshot.json`
- Orphanet: `data/standards/orphanet/orphanet_snapshot.json`

支持 JSON（records 列表）格式，推荐包含 `source_version` 与 `snapshot_date`。
更新快照后重新运行 build 命令即可自动加载最新本地快照。