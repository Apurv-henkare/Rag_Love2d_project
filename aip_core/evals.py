"""
aip_core/evals.py — Retrieval, Extraction, Judge Agreement & Statistical Metrics (Labs 1-6).

Mirrors `Plaksha_AI_in_Practise_modified/aip/evals.py`:
- Retrieval metrics: `hit_rate@1`, `hit_rate@5`, `recall@5`, `mrr`, `ndcg@10`
- Structured extraction metrics: per-field accuracy and exact-match `record_accuracy`
- Statistical confidence & hypothesis tests: `wilson_interval` (95% CI) and
  exact binomial `paired_test` (p-value, wins, losses, ties)
- Judge calibration: `cohens_kappa` (chance-corrected inter-annotator agreement)
"""
from __future__ import annotations

import math
from typing import Any, Sequence


# ===========================================================================
# 1. Lab 3 Retrieval Metrics
# ===========================================================================
def retrieval_metrics(
    retrieved_doc_ids: Sequence[str],
    relevant_doc_ids: Sequence[str],
) -> dict[str, float]:
    """
    Compute standard IR metrics for a single query:
      - hit_rate@1: 1.0 if the #1 retrieved chunk is relevant, else 0.0
      - hit_rate@5: 1.0 if ANY of the top-5 retrieved chunks is relevant, else 0.0
      - recall@5:   Fraction of all relevant docs found in the top-5 unique retrieved docs
      - mrr:        Reciprocal rank (1 / rank) of the FIRST relevant chunk
      - ndcg@10:    Normalized Discounted Cumulative Gain at rank 10
    """
    rel_set = {str(d).replace(".pdf", "").replace(".md", "") for d in relevant_doc_ids if d}
    if not rel_set:
        return {}

    norm_ret = [str(d).replace(".pdf", "").replace(".md", "") for d in retrieved_doc_ids]

    # Deduplicate retrieved doc_ids while preserving rank order so multiple chunks
    # from the same PDF don't artificially inflate DCG > IDCG
    dedup_ret: list[str] = []
    for d in norm_ret:
        if d not in dedup_ret:
            dedup_ret.append(d)

    top1 = dedup_ret[:1]
    top5 = dedup_ret[:5]
    top10 = dedup_ret[:10]

    hit1 = 1.0 if any(d in rel_set for d in top1) else 0.0
    hit5 = 1.0 if any(d in rel_set for d in top5) else 0.0
    recall5 = sum(1 for d in top5 if d in rel_set) / float(len(rel_set))

    mrr = 0.0
    for rank_idx, d in enumerate(dedup_ret, start=1):
        if d in rel_set:
            mrr = 1.0 / float(rank_idx)
            break

    dcg = 0.0
    for rank_idx, d in enumerate(top10, start=1):
        if d in rel_set:
            dcg += 1.0 / math.log2(rank_idx + 1.0)

    ideal_hits = min(len(rel_set), 10)
    idcg = sum(1.0 / math.log2(r + 1.0) for r in range(1, ideal_hits + 1))
    ndcg10 = (dcg / idcg) if idcg > 0 else 0.0

    return {
        "hit_rate@1": round(hit1, 4),
        "hit_rate@5": round(hit5, 4),
        "recall@5": round(recall5, 4),
        "mrr": round(mrr, 4),
        "ndcg@10": round(ndcg10, 4),
    }


# ===========================================================================
# 2. Lab 1 & Lab 2 Structured Extraction Metrics
# ===========================================================================
def field_accuracy(pred: Any, gold: dict[str, Any], fields: Sequence[str]) -> dict[str, float]:
    """
    Compare predicted record fields against gold labels.
    Returns:
      - `field.<name>`: 1.0 if pred[name] == gold[name] else 0.0
      - `field_accuracy`: average accuracy across all graded fields
      - `record_accuracy`: 1.0 ONLY if every single graded field is correct (all-or-nothing)
    """
    if hasattr(pred, "model_dump"):
        pred_dict = pred.model_dump()
    elif isinstance(pred, dict):
        pred_dict = pred
    else:
        pred_dict = {}

    scores: dict[str, float] = {}
    for f in fields:
        p_val = pred_dict.get(f)
        g_val = gold.get(f)
        scores[f"field.{f}"] = 1.0 if p_val == g_val else 0.0

    vals = list(scores.values())
    scores["field_accuracy"] = sum(vals) / len(vals) if vals else 0.0
    scores["record_accuracy"] = 1.0 if all(v == 1.0 for v in vals) else 0.0
    return scores


# ===========================================================================
# 3. Statistical Confidence Intervals & Paired Sign Test (Labs 2 & 5)
# ===========================================================================
def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """
    Compute the 95% Wilson score confidence interval for `k` successes out of `n` trials.
    Unlike the naive normal approximation, Wilson works reliably on small samples (n=20..60)
    and near 0% or 100%.
    """
    if n <= 0:
        return (0.0, 0.0)
    p = k / float(n)
    denom = 1.0 + (z * z) / n
    center = (p + (z * z) / (2.0 * n)) / denom
    half = (z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * n)) / n)) / denom
    return (max(0.0, round(center - half, 4)), min(1.0, round(center + half, 4)))


def paired_test(scores_a: Sequence[float], scores_b: Sequence[float]) -> dict[str, float | int]:
    """
    Exact two-sided binomial Sign Test on paired per-item scores (System A vs System B).
      - wins_b: items where B > A
      - wins_a: items where A > B
      - ties:   items where A == B
      - p_value: probability of seeing a split at least this extreme by pure coin-flip chance.
                 If p_value < 0.05, the difference is statistically significant.
    """
    wins_b = sum(1 for a, b in zip(scores_a, scores_b) if b > a)
    wins_a = sum(1 for a, b in zip(scores_a, scores_b) if a > b)
    ties = sum(1 for a, b in zip(scores_a, scores_b) if a == b)
    n_diff = wins_a + wins_b

    if n_diff == 0:
        p_val = 1.0
    else:
        k_min = min(wins_a, wins_b)
        tail = sum(math.comb(n_diff, i) for i in range(k_min + 1)) / float(2**n_diff)
        p_val = min(1.0, 2.0 * tail)

    mean_a = sum(scores_a) / len(scores_a) if scores_a else 0.0
    mean_b = sum(scores_b) / len(scores_b) if scores_b else 0.0

    return {
        "mean_a": round(mean_a, 4),
        "mean_b": round(mean_b, 4),
        "delta": round(mean_b - mean_a, 4),
        "wins_b": wins_b,
        "wins_a": wins_a,
        "ties": ties,
        "p_value": round(p_val, 4),
    }


# ===========================================================================
# 4. Lab 4 LLM Judge Calibration: Cohen's Kappa
# ===========================================================================
def cohens_kappa(labels_a: Sequence[int], labels_b: Sequence[int]) -> dict[str, float]:
    """
    Compute raw agreement (`p_o`), chance agreement (`p_e`), and Cohen's Kappa (`kappa`):
        kappa = (p_o - p_e) / (1 - p_e)
    """
    n = min(len(labels_a), len(labels_b))
    if n == 0:
        return {"raw_agreement": 0.0, "chance_agreement": 0.0, "kappa": 0.0}

    a = list(labels_a[:n])
    b = list(labels_b[:n])
    categories = sorted(set(a) | set(b))

    p_o = sum(1 for x, y in zip(a, b) if x == y) / float(n)
    p_e = sum((a.count(c) / float(n)) * (b.count(c) / float(n)) for c in categories)

    if abs(1.0 - p_e) < 1e-9:
        kappa = 1.0 if p_o == 1.0 else 0.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    return {
        "raw_agreement": round(p_o, 4),
        "chance_agreement": round(p_e, 4),
        "kappa": round(kappa, 4),
    }
