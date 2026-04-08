"""JSON/JSONL IO helpers with directory creation and logging."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterable, List

logger = logging.getLogger(__name__)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: str | Path, payload: Any) -> None:
    p = Path(path)
    ensure_parent(p)
    try:
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("failed_write_json path=%s", p)
        raise


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path: str | Path, rows: Iterable[Any]) -> None:
    p = Path(path)
    ensure_parent(p)
    try:
        with p.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("failed_write_jsonl path=%s", p)
        raise


def read_jsonl(path: str | Path) -> List[Any]:
    p = Path(path)
    rows: List[Any] = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows
