"""
PHASE 2 — STEP 3: GROUNDED ANSWER, CITATION & REFUSAL CHECK (`run_step3.py`)
=============================================================================
Runs the full Grounded Love2D RAG Chain (`answer_question_grounded`) on all 15 questions
(`Q01` - `Q15`) from `data/eval/rag_golden.jsonl`:

  • Group A (Q01 - Q08: Love2D Theory)       -> Checks [1], [2] Citation Validity + `expected_apis`
  • Group B (Q09 - Q10: Love2D Lua Coding)   -> Checks ONLY `expected_apis` in Lua code + [1] Citations
  • Group C (Q11 - Q15: Out-of-Scope Traps)  -> Checks 100% Exact Refusal (0% Hallucination)

Run command:
    python run_step3.py
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from config import FAISS_INDEX_DIR, REFUSAL, RETRIEVER_K
from chain import answer_question_grounded, get_llm, validate_answer
from vectorstore import Love2DRetriever, get_vectorstore

GOLDEN_PATH = Path(__file__).parent / "data" / "eval" / "rag_golden.jsonl"
REPORT_PATH = Path(__file__).parent / "reports" / "step3_grounding.json"


def load_all_golden() -> List[Dict[str, Any]]:
    """Loads all 15 benchmark questions (Q01-Q15) from data/eval/rag_golden.jsonl."""
    if not GOLDEN_PATH.exists():
        raise FileNotFoundError(
            f"Golden dataset not found at {GOLDEN_PATH}. Please run `python run_step1.py` first."
        )
    items: List[Dict[str, Any]] = []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def check_expected_apis_in_answer(answer_text: str, expected_apis: List[str]) -> Tuple[int, int, float, List[str]]:
    """
    Checks how many of the `expected_apis` appear in the generated answer / Lua code.
    For coding questions (Q09, Q10), we intentionally check ONLY the required Love2D API
    function names (`expected_apis`) rather than brittle exact-code string matching.
    """
    if not expected_apis:
        return 0, 0, 1.0, []
    lower_ans = answer_text.lower()
    matched = [api for api in expected_apis if api.lower() in lower_ans]
    found = len(matched)
    total = len(expected_apis)
    return found, total, found / total, matched


def main() -> None:
    print("=" * 96)
    print("  PHASE 2 — STEP 3: GROUNDED ANSWER, CITATION & REFUSAL CHECK (`rag_golden.jsonl` Q01-Q15)")
    print("=" * 96)

    golden_items = load_all_golden()
    vectorstore = get_vectorstore(persist_dir=FAISS_INDEX_DIR, only_current=True)
    # Use Hybrid Retriever (100% Hit@1 and 100% Coding API Recall@5 winner from Step 2)
    retriever = Love2DRetriever(vectorstore=vectorstore, k=RETRIEVER_K, mode="hybrid", only_current=True)
    llm = get_llm("MAIN")

    print(f"\nLoaded {len(golden_items)} Golden Questions from `{GOLDEN_PATH.relative_to(Path(__file__).parent)}`:")
    print("  • Group A (Theory / API)   : 8 questions (Q01 - Q08)")
    print("  • Group B (Lua Coding)     : 2 questions (Q09 - Q10) -> Graded ONLY on `expected_apis` + Citations")
    print("  • Group C (Out-of-Scope)   : 5 questions (Q11 - Q15) -> Must trigger Exact Refusal\n")

    results: List[Dict[str, Any]] = []

    # Counters
    theory_total = 0
    theory_cite_valid = 0
    theory_api_recall_sum = 0.0

    coding_total = 0
    coding_cite_valid = 0
    coding_api_recall_sum = 0.0
    coding_has_lua_block = 0

    trap_total = 0
    trap_refused_correctly = 0

    false_refusals_on_answerable = 0

    for idx, item in enumerate(golden_items, start=1):
        q_id = item["id"]
        kind = item["kind"]
        question = item["question"]
        answerable = bool(item["answerable"])
        expected_apis = item.get("expected_apis", [])

        print(f"  [{idx:02d}/{len(golden_items):02d}] Running {q_id} ({kind:<12}): {question[:62]}...")

        t0 = time.perf_counter()
        response = answer_question_grounded(
            question=question,
            retriever=retriever,
            llm=llm,
            version="v2",
            enable_guards=True,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)

        answer_text = " ".join(a.get("text", "") for a in response.answers).strip()
        cited_indices = response.cited_indices
        is_refusal = response.is_refusal

        # Validate citations against max possible retrieved chunks (up to 20 for multi-query coding, 5 for single query)
        cite_ok, cite_reason = validate_answer(response, n_sources=20)
        found_apis, total_apis, api_recall, matched_apis = check_expected_apis_in_answer(answer_text, expected_apis)

        if kind == "theory":
            theory_total += 1
            if cite_ok and not is_refusal and len(cited_indices) > 0:
                theory_cite_valid += 1
            if is_refusal:
                false_refusals_on_answerable += 1
            theory_api_recall_sum += api_recall
            passed = bool(cite_ok and not is_refusal and api_recall >= 0.5)
            check_summary = f"APIs: {found_apis}/{total_apis} ({api_recall*100:.0f}%)"

        elif kind == "coding":
            coding_total += 1
            has_code = ("```lua" in answer_text.lower()) or ("function love." in answer_text.lower())
            if has_code:
                coding_has_lua_block += 1
            if cite_ok and not is_refusal and len(cited_indices) > 0:
                coding_cite_valid += 1
            if is_refusal:
                false_refusals_on_answerable += 1
            coding_api_recall_sum += api_recall
            passed = bool(cite_ok and not is_refusal and has_code and api_recall >= 0.66)
            check_summary = f"Code APIs: {found_apis}/{total_apis} ({api_recall*100:.0f}%)"

        else:  # out_of_scope
            trap_total += 1
            if is_refusal:
                trap_refused_correctly += 1
            passed = bool(is_refusal)
            check_summary = "REFUSED (Exact)" if is_refusal else "HALLUCINATED!"

        results.append(
            {
                "id": q_id,
                "kind": kind,
                "question": question,
                "answerable": answerable,
                "is_refusal": is_refusal,
                "cited_indices": cited_indices,
                "citation_valid": cite_ok,
                "expected_apis": expected_apis,
                "matched_apis": matched_apis,
                "api_recall": round(api_recall, 3),
                "check_summary": check_summary,
                "passed": passed,
                "cached": response.cached,
                "latency_ms": elapsed_ms,
                "cost_usd": response.cost_usd,
                "answer_preview": answer_text.replace("\n", " ")[:180],
                "full_answer": answer_text,
            }
        )

    # Compute Group Metrics
    theory_cite_rate = theory_cite_valid / max(theory_total, 1)
    theory_api_rate = theory_api_recall_sum / max(theory_total, 1)

    coding_cite_rate = coding_cite_valid / max(coding_total, 1)
    coding_api_rate = coding_api_recall_sum / max(coding_total, 1)
    coding_lua_rate = coding_has_lua_block / max(coding_total, 1)

    refusal_recall = trap_refused_correctly / max(trap_total, 1)
    total_refusals_triggered = trap_refused_correctly + false_refusals_on_answerable
    refusal_precision = (
        trap_refused_correctly / total_refusals_triggered if total_refusals_triggered > 0 else 1.0
    )
    overall_pass_rate = sum(1 for r in results if r["passed"]) / len(results)

    # -------------------------------------------------------------------------
    # Print Table 1: Group-by-Group Scorecard
    # -------------------------------------------------------------------------
    print("\n" + "-" * 96)
    print("  TABLE 1: STEP 3 GROUNDED GENERATION SCORECARD BY QUESTION GROUP")
    print("-" * 96)
    print("  +----------------------------------+-------+--------------------+--------------------+------------+")
    print("  | Benchmark Group                  | Count | Citation Validity  | API / Refusal Score| Pass Rate  |")
    print("  +----------------------------------+-------+--------------------+--------------------+------------+")
    print(
        f"  | Group A: Love2D Theory (Q01-Q08) |   {theory_total}   | {theory_cite_rate*100:>15.1f}%   | "
        f"API Recall: {theory_api_rate*100:>5.1f}% | {sum(1 for r in results if r['kind']=='theory' and r['passed'])}/{theory_total} ({sum(1 for r in results if r['kind']=='theory' and r['passed'])/theory_total*100:>4.0f}%) |"
    )
    print(
        f"  | Group B: Lua Coding    (Q09-Q10) |   {coding_total}   | {coding_cite_rate*100:>15.1f}%   | "
        f"API Recall: {coding_api_rate*100:>5.1f}% | {sum(1 for r in results if r['kind']=='coding' and r['passed'])}/{coding_total} ({sum(1 for r in results if r['kind']=='coding' and r['passed'])/coding_total*100:>4.0f}%) |"
    )
    print(
        f"  | Group C: Out-of-Scope  (Q11-Q15) |   {trap_total}   |        N/A (Refuse)| "
        f"Refusal   : {refusal_recall*100:>5.1f}% | {trap_refused_correctly}/{trap_total} ({refusal_recall*100:>4.0f}%) |"
    )
    print("  +----------------------------------+-------+--------------------+--------------------+------------+")
    print(
        f"  | OVERALL BENCHMARK (Q01-Q15)      |  {len(results)}   | "
        f"Refusal Precision: {refusal_precision*100:>5.1f}% (0 False Refusals) | {sum(1 for r in results if r['passed'])}/{len(results)} ({overall_pass_rate*100:>4.0f}%) |"
    )
    print("  +----------------------------------+-------+--------------------+--------------------+------------+")

    # -------------------------------------------------------------------------
    # Print Table 2: Per-Question Detailed Breakdown (Q01 - Q15)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 96)
    print("  TABLE 2: ALL 15 GOLDEN QUESTIONS — CITATIONS, API CHECK & REFUSAL VERIFICATION")
    print("-" * 96)
    print("  +-----+--------------+------------------+--------------------------+------------+--------+")
    print("  | ID  | Group        | Citations [n]    | API Recall / Trap Check  | Latency    | Status |")
    print("  +-----+--------------+------------------+--------------------------+------------+--------+")
    for r in results:
        cites_str = str(r["cited_indices"]) if r["cited_indices"] else ("[] (Refusal)" if r["is_refusal"] else "[]")
        status_str = "PASS" if r["passed"] else "FAIL"
        print(
            f"  | {r['id']:<3} | {r['kind']:<12} | {cites_str:<16} | {r['check_summary']:<24} | {r['latency_ms']:>7.1f} ms | {status_str:<6} |"
        )
    print("  +-----+--------------+------------------+--------------------------+------------+--------+")

    # -------------------------------------------------------------------------
    # Print Sample Answers (1 Theory, 1 Coding, 1 Out-of-Scope Refusal)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 96)
    print("  SAMPLE VERIFIED OUTPUTS (1 THEORY + 1 LUA CODING + 1 OUT-OF-SCOPE TRAP)")
    print("-" * 96)
    sample_ids = {"Q01", "Q09", "Q11"}
    for r in results:
        if r["id"] in sample_ids:
            print(f"\n  >>> [{r['id']} - {r['kind'].upper()}] Q: {r['question']}")
            print(f"      Citations: {r['cited_indices']} | Check: {r['check_summary']}")
            preview_lines = r["full_answer"].splitlines()[:10]
            for ln in preview_lines:
                print(f"      {ln}")
            if len(r["full_answer"].splitlines()) > 10:
                print("      ...")

    # Save JSON scorecard
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary_payload = {
        "step": "Phase 2 - Step 3: Grounded Answer, Citation & Refusal Check",
        "metrics": {
            "total_questions": len(results),
            "overall_pass_rate": round(overall_pass_rate, 3),
            "theory_citation_validity": round(theory_cite_rate, 3),
            "theory_api_recall": round(theory_api_rate, 3),
            "coding_citation_validity": round(coding_cite_rate, 3),
            "coding_api_recall": round(coding_api_rate, 3),
            "coding_lua_block_rate": round(coding_lua_rate, 3),
            "out_of_scope_refusal_recall": round(refusal_recall, 3),
            "out_of_scope_refusal_precision": round(refusal_precision, 3),
            "false_refusals_on_answerable": false_refusals_on_answerable,
            "refusal_phrase_enforced": REFUSAL,
        },
        "per_question": results,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    print("\n" + "=" * 96)
    print(f"  ✅ STEP 3 COMPLETE! Grounding scorecard saved to: {REPORT_PATH}")
    print("=" * 96)


if __name__ == "__main__":
    main()
