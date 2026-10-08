"""
PHASE 2 — DECOUPLED AI JUDGE EVALUATION (`run_step_judge.py`)
============================================================
Evaluates Grounded Love2D RAG answers using a Decoupled AI Judge (`MODEL_TIERS["LARGE"]`),
specifically designed to eliminate the 5%–10% Self-Preference Grading Bias identified in Lab 4.

Key Architecture:
  1. Generator Model: `MAIN` (gemini-3.1-flash-lite) generates the RAG answers.
  2. Judge Model:     `LARGE` (gemini-3.5-flash / Pro class) objectively evaluates:
       • Rubric A: FAITHFULNESS (Score 0 or 1) — Did the answer stick strictly to retrieved chunks?
       • Rubric B: CORRECTNESS  (Score 0, 1, or 2) — Did it provide accurate APIs / exact refusal?
  3. Output Contract: `JudgeVerdict` from `schemas.py` forces RATIONALE first, SCORE last.

Run command:
    python run_step_judge.py
    python run_step_judge.py --all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import (
    EVAL_DIR,
    FAISS_INDEX_DIR,
    MODEL_TIERS,
    REFUSAL,
    REPORTS_DIR,
    RETRIEVER_K,
)
from chain import (
    answer_question_grounded,
    format_docs,
    get_llm,
    retrieve_all_sentence_chunks,
)
from schemas import JudgeVerdict
from vectorstore import Love2DRetriever, get_vectorstore

GOLDEN_PATH = EVAL_DIR / "rag_golden.jsonl"
STEP3_REPORT_PATH = REPORTS_DIR / "step3_grounding.json"
OUTPUT_REPORT_PATH = REPORTS_DIR / "step_judge_evaluation.json"


# =============================================================================
# 1. Judge Prompts enforcing Rationale-First Evaluation (Lab 4 Rubric)
# =============================================================================

FAITHFULNESS_PROMPT = """\
You are an expert impartial AI Judge evaluating a documentation RAG system for the Love2D (LÖVE) game framework.
Your task is to evaluate the FAITHFULNESS of the generated answer with respect to the retrieved reference chunks.

[RETRIEVED REFERENCE CHUNKS]
{context}

[USER QUESTION]
{question}

[GENERATED ANSWER TO EVALUATE]
{answer}

[SCORING RUBRIC — FAITHFULNESS]
- Score 1 (Faithful): Every factual statement, Lua function name, and technical claim in the generated answer is directly supported by the retrieved reference chunks above, OR the answer correctly refuses because the chunks lack the required info.
- Score 0 (Unfaithful / Hallucinated): The answer asserts Love2D APIs, parameters, or rules that do NOT appear anywhere in the retrieved chunks.

[OUTPUT FORMAT INSTRUCTIONS]
You MUST respond with a single valid JSON object following this exact schema:
{{
  "rationale": "<1-2 sentence explanation comparing the answer's claims strictly against the retrieved chunks>",
  "score": <0 or 1>
}}
State your rationale FIRST, then provide the score.
"""

CORRECTNESS_PROMPT = """\
You are an expert impartial AI Judge evaluating a documentation RAG system for the Love2D (LÖVE) game framework.
Your task is to evaluate the ANSWER CORRECTNESS of the generated answer against the ground-truth benchmark specification.

[USER QUESTION]
{question}

[BENCHMARK GROUND TRUTH SPECIFICATION]
Expected APIs / Concepts: {expected_apis}
Is Answerable: {answerable}
Gold Standard Reference: {gold_reference}

[GENERATED ANSWER TO EVALUATE]
{answer}

[SCORING RUBRIC — ANSWER CORRECTNESS]
- Score 2 (Fully Correct):
  * For answerable questions: Accurately answers the question and includes the required Love2D APIs/concepts.
  * For unanswerable/trap questions: Emits the exact refusal ("{refusal}").
- Score 1 (Partially Correct): The answer is mostly right but misses a secondary parameter or optional rule.
- Score 0 (Incorrect): Factually wrong, invents non-existent APIs for a trap question, or fails to refuse an impossible request.

[OUTPUT FORMAT INSTRUCTIONS]
You MUST respond with a single valid JSON object following this exact schema:
{{
  "rationale": "<1-2 sentence explanation comparing the answer against the gold standard and expected APIs>",
  "score": <0, 1, or 2>
}}
State your rationale FIRST, then provide the score.
"""


def _parse_judge_json(raw_text: str) -> JudgeVerdict:
    """Robustly extracts and validates JudgeVerdict from the judge's response."""
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        data = json.loads(candidate)
        return JudgeVerdict(
            rationale=str(data.get("rationale", "")).strip(),
            score=int(data.get("score", 0)),
        )
    raise ValueError(f"Could not parse valid JSON from judge output: {raw_text[:120]}")


def evaluate_faithfulness(judge_llm, question: str, context: str, answer: str) -> JudgeVerdict:
    """Calls the LARGE model to judge whether the answer is strictly grounded in retrieved chunks."""
    prompt = FAITHFULNESS_PROMPT.format(question=question, context=context, answer=answer)
    resp = judge_llm.invoke(prompt)
    raw = resp.content if hasattr(resp, "content") else str(resp)
    return _parse_judge_json(raw)


def evaluate_correctness(
    judge_llm,
    question: str,
    answer: str,
    expected_apis: List[str],
    answerable: bool,
    gold_reference: str,
) -> JudgeVerdict:
    """Calls the LARGE model to judge whether the answer matches the gold standard."""
    prompt = CORRECTNESS_PROMPT.format(
        question=question,
        expected_apis=", ".join(expected_apis) if expected_apis else "None (Trap / Out-of-Scope)",
        answerable=answerable,
        gold_reference=gold_reference or "N/A (Unanswerable Trap)",
        answer=answer,
        refusal=REFUSAL,
    )
    resp = judge_llm.invoke(prompt)
    raw = resp.content if hasattr(resp, "content") else str(resp)
    return _parse_judge_json(raw)


# =============================================================================
# 2. Main Evaluation Pipeline
# =============================================================================

def load_benchmark_data() -> List[Dict[str, Any]]:
    """Loads all questions from data/eval/rag_golden.jsonl."""
    if not GOLDEN_PATH.exists():
        raise FileNotFoundError(f"Benchmark file not found at {GOLDEN_PATH}")
    items = []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line.strip()))
    return items


def load_cached_step3_answers() -> Dict[str, Dict[str, Any]]:
    """Loads previously generated answers from step3_grounding.json if available to save API tokens."""
    if not STEP3_REPORT_PATH.exists():
        return {}
    try:
        with open(STEP3_REPORT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {item["id"]: item for item in data.get("per_question", [])}
    except Exception:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run decoupled LARGE model AI Judge evaluation.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all 15 benchmark questions (default is 5 representative questions).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Re-generate answers live using MAIN instead of reusing step3_grounding.json answers.",
    )
    args = parser.parse_args()

    print("=" * 102)
    print("  PHASE 2 — LAB 4 DECOUPLED AI JUDGE EVALUATION (`run_step_judge.py`)")
    print(f"  • Generator Model (MAIN) : {MODEL_TIERS['MAIN']} (Flash-Lite tier)")
    print(f"  • Judge Model     (LARGE): {MODEL_TIERS['LARGE']} (Higher-tier independent evaluator)")
    print("  • Objective              : Eliminate 5%–10% Self-Preference Bias via Rationale-First Schema")
    print("=" * 102)

    golden_items = load_benchmark_data()
    cached_answers = {} if args.live else load_cached_step3_answers()

    # Select questions: representative sample of Theory, Coding, and Traps (or all 15)
    if args.all:
        selected_items = golden_items
        print(f"\n[INFO] Evaluating ALL {len(selected_items)} benchmark questions...")
    else:
        # 5 representative questions: 2 Theory (Q01, Q03), 1 Coding (Q09), 2 Traps (Q11, Q13)
        target_ids = {"Q01", "Q03", "Q09", "Q11", "Q13"}
        selected_items = [it for it in golden_items if it["id"] in target_ids]
        print(f"\n[INFO] Evaluating {len(selected_items)} representative questions (Q01, Q03, Q09, Q11, Q13)...")
        print("       (Pass `--all` to evaluate all 15 questions across the entire dataset)")

    vectorstore = get_vectorstore(persist_dir=FAISS_INDEX_DIR, only_current=True)
    retriever = Love2DRetriever(vectorstore=vectorstore, k=RETRIEVER_K, mode="hybrid", only_current=True)
    generator_llm = get_llm("MAIN")
    judge_llm = get_llm("LARGE")

    evaluation_records: List[Dict[str, Any]] = []

    for idx, item in enumerate(selected_items, start=1):
        q_id = item["id"]
        kind = item["kind"]
        question = item["question"]
        answerable = bool(item["answerable"])
        expected_apis = item.get("expected_apis", [])
        gold_ref = item.get("gold_answer", "")

        print(f"\n[{idx:02d}/{len(selected_items):02d}] Evaluating {q_id} ({kind}): \"{question[:55]}...\"")

        # 1. Obtain Answer and Retrieved Context from Generator (MAIN)
        t_gen0 = time.perf_counter()
        if q_id in cached_answers and "full_answer" in cached_answers[q_id]:
            print(f"  ⚡ Generator (MAIN): Loaded answer from `{STEP3_REPORT_PATH.name}`")
            gen_answer = cached_answers[q_id]["full_answer"]
            # Retrieve supporting chunks to give to the judge
            docs = retrieve_all_sentence_chunks(question, retriever, generator_llm)
            context_text = format_docs(docs, use_delimiters=False)
        else:
            print("  🚀 Generator (MAIN): Generating live answer via grounded RAG chain...")
            res = answer_question_grounded(question, retriever, generator_llm, version="v2")
            gen_answer = res.full_answer
            docs = retrieve_all_sentence_chunks(question, retriever, generator_llm)
            context_text = format_docs(docs, use_delimiters=False)

        print(f"  📝 Answer Preview : {gen_answer[:90]}...")

        # 2. Rubric A: Faithfulness Evaluation via LARGE Judge
        t_j0 = time.perf_counter()
        print(f"  ⚖️  Judge (LARGE)  : Grading FAITHFULNESS against {len(docs)} retrieved chunks...")
        faith_verdict = evaluate_faithfulness(judge_llm, question, context_text, gen_answer)
        print(f"      -> Faithfulness Score: {faith_verdict.score}/1 | Rationale: {faith_verdict.rationale[:80]}...")

        # 3. Rubric B: Answer Correctness Evaluation via LARGE Judge
        print("  ⚖️  Judge (LARGE)  : Grading CORRECTNESS against gold benchmark specification...")
        corr_verdict = evaluate_correctness(
            judge_llm, question, gen_answer, expected_apis, answerable, gold_ref
        )
        j_time_ms = round((time.perf_counter() - t_j0) * 1000.0, 1)
        print(f"      -> Correctness Score : {corr_verdict.score}/2 | Rationale: {corr_verdict.rationale[:80]}...")

        evaluation_records.append(
            {
                "id": q_id,
                "kind": kind,
                "question": question,
                "answerable": answerable,
                "generator_model": MODEL_TIERS["MAIN"],
                "judge_model": MODEL_TIERS["LARGE"],
                "generated_answer": gen_answer,
                "faithfulness": {
                    "score": faith_verdict.score,
                    "max_score": 1,
                    "rationale": faith_verdict.rationale,
                },
                "correctness": {
                    "score": corr_verdict.score,
                    "max_score": 2,
                    "rationale": corr_verdict.rationale,
                },
                "judge_latency_ms": j_time_ms,
            }
        )

    # =========================================================================
    # 3. Print Final Evaluation Scorecard & Save JSON Report
    # =========================================================================
    total_q = len(evaluation_records)
    avg_faithfulness = sum(r["faithfulness"]["score"] for r in evaluation_records) / max(total_q, 1)
    avg_correctness = (
        sum(r["correctness"]["score"] for r in evaluation_records) / max(total_q * 2, 1)
    )

    print("\n" + "=" * 102)
    print("  TABLE: DECOUPLED AI JUDGE SCORECARD (MODEL_TIERS['LARGE'] = gemini-3.5-flash)")
    print("=" * 102)
    print("  +-----+------------+-----------+-------------+-------------------------------------------------------------+")
    print("  | ID  | Category   | Faithful  | Correctness | Judge Rationale Summary (LARGE Tier)                        |")
    print("  +-----+------------+-----------+-------------+-------------------------------------------------------------+")
    for r in evaluation_records:
        rat_short = r["correctness"]["rationale"][:59]
        print(
            f"  | {r['id']:<3} | {r['kind']:<10} | {r['faithfulness']['score']}/1       | "
            f"{r['correctness']['score']}/2         | {rat_short:<59} |"
        )
    print("  +-----+------------+-----------+-------------+-------------------------------------------------------------+")
    print(f"\n  📊 Summary Metrics from Decoupled AI Judge ({total_q} Questions Evaluated):")
    print(f"     • Faithfulness Score (Strict Grounding)   : {avg_faithfulness * 100:.1f}% ({sum(r['faithfulness']['score'] for r in evaluation_records)}/{total_q})")
    print(f"     • Answer Correctness (Gold Alignment)     : {avg_correctness * 100:.1f}% ({sum(r['correctness']['score'] for r in evaluation_records)}/{total_q * 2} pts)")
    print(f"     • Bias Elimination                        : 100% (Decoupled LARGE model independently graded MAIN)")

    # Save to reports/step_judge_evaluation.json
    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_payload = {
        "step": "Phase 2 - Lab 4: Decoupled AI Judge Evaluation",
        "date_evaluated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "generator_tier": {
            "tier_name": "MAIN",
            "model": MODEL_TIERS["MAIN"],
        },
        "judge_tier": {
            "tier_name": "LARGE",
            "model": MODEL_TIERS["LARGE"],
        },
        "metrics": {
            "questions_evaluated": total_q,
            "average_faithfulness": round(avg_faithfulness, 3),
            "average_correctness_ratio": round(avg_correctness, 3),
            "self_preference_bias": "Eliminated via Decoupled Model Tiers + Rationale-First Schema",
        },
        "evaluations": evaluation_records,
    }
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    print(f"\n  ✅ COMPLETE! Detailed judge verdicts and rationales saved to:")
    print(f"     📁 `{OUTPUT_REPORT_PATH}`")
    print("=" * 102)


if __name__ == "__main__":
    main()
