"""Select ranked reviews into framework buckets and persist decisions."""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from app.schemas.review_selection_record import ReviewSelectionRecord
from app.utils.json_io import write_json, write_jsonl

logger = logging.getLogger(__name__)


class ReviewSelector:
    def __init__(self) -> None:
        self.targets = {
            "anchor_review": (2, 3),
            "systematic_review": (1, 2),
            "specialized_review": (2, 3),
        }

    @staticmethod
    def _bucket(item: Dict[str, object]) -> str:
        rec = item["record"]
        types = {x.lower() for x in rec.publication_types}
        if "systematic review" in types or "meta-analysis" in types:
            return "systematic_review"
        if item["disease_specificity_score"] >= 0.9 and item["review_type_score"] >= 0.9:
            return "anchor_review"
        if item["mechanism_density_score"] >= 0.35:
            return "specialized_review"
        if item["review_rank_score"] >= 0.45:
            return "supplementary_review"
        return "rejected"

    def select(self, ranked_items: List[Dict[str, object]]) -> Tuple[List[ReviewSelectionRecord], Dict[str, object]]:
        logger.info("audit stage=review_ranking_triage.selector status=started ranked=%d", len(ranked_items))
        selected_counts = defaultdict(int)
        records: List[ReviewSelectionRecord] = []

        for idx, item in enumerate(ranked_items, start=1):
            rec = item["record"]
            bucket = self._bucket(item)
            reasons = [f"rank_score={item['review_rank_score']}"]
            flags: List[str] = []

            # ensure specialized reviews are not eliminated solely due to low IF
            if bucket == "specialized_review" and (item.get("impact_factor") or 0) < 5:
                flags.append("low_if_but_mechanism_dense")

            if bucket in self.targets:
                _, max_keep = self.targets[bucket]
                if selected_counts[bucket] < max_keep:
                    decision = "selected"
                    selected_counts[bucket] += 1
                else:
                    bucket = "supplementary_review"
                    decision = "holdout"
                    reasons.append("bucket_quota_reached")
            elif bucket == "supplementary_review":
                decision = "holdout"
            else:
                decision = "rejected"

            record = ReviewSelectionRecord(
                selection_id=f"sel_{idx:04d}",
                pmid=rec.pmid,
                journal=rec.journal,
                publication_year=rec.publication_year,
                review_bucket=bucket,
                impact_factor=item.get("impact_factor"),
                impact_factor_source=item.get("impact_factor_source"),
                review_rank_score=item["review_rank_score"],
                mechanism_density_score=item["mechanism_density_score"],
                disease_specificity_score=item["disease_specificity_score"],
                decision=decision,
                reasons=reasons,
                flags=flags,
            )
            records.append(record)

        # enforce minimum targets when possible
        for bucket, (min_keep, _max_keep) in self.targets.items():
            selected_now = sum(1 for r in records if r.review_bucket == bucket and r.decision == "selected")
            if selected_now >= min_keep:
                continue
            gap = min_keep - selected_now
            for candidate in records:
                if gap <= 0:
                    break
                if candidate.decision == "holdout" and candidate.review_bucket == "supplementary_review":
                    candidate.review_bucket = bucket
                    candidate.decision = "selected"
                    candidate.reasons.append(f"promoted_to_meet_{bucket}_minimum")
                    gap -= 1

        write_jsonl("data/review_selection/review_selection.jsonl", [x.model_dump() for x in records])
        summary = {
            "selected_counts": {
                b: sum(1 for r in records if r.review_bucket == b and r.decision == "selected")
                for b in ["anchor_review", "systematic_review", "specialized_review", "supplementary_review", "rejected"]
            },
            "total_records": len(records),
        }
        write_json(Path("data/review_selection") / "review_summary.json", summary)
        logger.info("audit stage=review_ranking_triage.selector status=completed total=%d", len(records))
        return records, summary
