"""
run_step1.py — Phase 2, Step 1: Build & Verify `data/eval/rag_golden.jsonl`
Directly from `faiss_index/` ("The Exam Paper")

What this script does:
1. Loads your actual `faiss_index/` from disk (`get_vectorstore(only_current=True)`).
2. For all 10 Love2D questions (`Q01`-`Q10`), searches `faiss_index/` and scans the
   indexed chunks for the exact target `love.*` APIs to pull the real `relevant_docs`,
   `gold_pages`, and `gold_chunk_ids` directly from `faiss_index/`.
3. For Coding questions (`Q09`-`Q10`), stores `expected_apis` (only checking that the
   required `love.*` API functions are used, since exact-matching full code is impossible).
4. For Out-of-Scope / Fake API Trap questions (`Q11`-`Q15`), sets `relevant_docs = []`
   and `answerable = False` (must trigger exact refusal).
5. Saves `data/eval/rag_golden.jsonl` and `reports/step1_benchmark.json`.

Run with:
    python run_step1.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from config import ARCHIVED_DOCS, CHUNK_OVERLAP, CHUNK_SIZE, DOCUMENTS_DIR, EVAL_DIR, REPORTS_DIR, RETRIEVER_K
from chain import _normalize_search_query
from vectorstore import extract_docs_from_faiss, get_retriever, get_vectorstore

GOLDEN_PATH = EVAL_DIR / "rag_golden.jsonl"

# Base specification of our 15 benchmark questions.
# `relevant_docs` and `gold_chunk_ids` are populated directly from `faiss_index/`!
RAW_BENCHMARK_SPECS = [
    # ------------------------------------------------------------------
    # Group A: 8 Love2D Theory / API Questions (Q01 - Q08)
    # ------------------------------------------------------------------
    {
        "id": "Q01",
        "kind": "theory",
        "answerable": True,
        "question": "What does love.update(dt) do and why is dt important?",
        "api_anchors": ["love.update", "dt"],
        "expected_apis": ["love.update", "dt"],
    },
    {
        "id": "Q02",
        "kind": "theory",
        "answerable": True,
        "question": "When is love.load() called and what is it used for in a Love2D game?",
        "api_anchors": ["love.load"],
        "expected_apis": ["love.load"],
    },
    {
        "id": "Q03",
        "kind": "theory",
        "answerable": True,
        "question": "How do I draw a filled or outlined circle on the screen using love.graphics.circle?",
        "api_anchors": ["love.graphics.circle"],
        "expected_apis": ["love.graphics.circle", "fill", "line"],
    },
    {
        "id": "Q04",
        "kind": "theory",
        "answerable": True,
        "question": "What arguments does love.graphics.rectangle take to draw a rectangle?",
        "api_anchors": ["love.graphics.rectangle"],
        "expected_apis": ["love.graphics.rectangle", "width", "height"],
    },
    {
        "id": "Q05",
        "kind": "theory",
        "answerable": True,
        "question": "What is the difference between static and stream in love.audio.newSource?",
        "api_anchors": ["love.audio.newSource", "SourceType"],
        "expected_apis": ["static", "stream"],
    },
    {
        "id": "Q06",
        "kind": "theory",
        "answerable": True,
        "question": "How do I check if a keyboard key is held down in Love2D?",
        "api_anchors": ["love.keyboard.isDown"],
        "expected_apis": ["love.keyboard.isDown"],
    },
    {
        "id": "Q07",
        "kind": "theory",
        "answerable": True,
        "question": "How do I create a Box2D physics world using love.physics.newWorld?",
        "api_anchors": ["love.physics.newWorld"],
        "expected_apis": ["love.physics.newWorld"],
    },
    {
        "id": "Q08",
        "kind": "theory",
        "answerable": True,
        "question": "How do I change the game window title using love.window.setTitle?",
        "api_anchors": ["love.window.setTitle"],
        "expected_apis": ["love.window.setTitle"],
    },
    # ------------------------------------------------------------------
    # Group B: 2 Love2D Coding Questions (Q09 - Q10) -> Check ONLY APIs!
    # ------------------------------------------------------------------
    {
        "id": "Q09",
        "kind": "coding",
        "answerable": True,
        "question": "Write Lua code to move a rectangle on screen using arrow keys and delta time dt in love.update and draw it in love.draw.",
        "api_anchors": ["love.keyboard.isDown", "love.graphics.rectangle", "love.update"],
        "expected_apis": ["love.update", "love.draw", "love.keyboard.isDown", "love.graphics.rectangle"],
    },
    {
        "id": "Q10",
        "kind": "coding",
        "answerable": True,
        "question": "Write Lua code to load an audio sound file in love.load and play it in Love2D.",
        "api_anchors": ["love.audio.newSource", "love.audio.play"],
        "expected_apis": ["love.load", "love.audio.newSource", "play"],
    },
    # ------------------------------------------------------------------
    # Group C: 5 Out-of-Scope / Fake API Traps (Q11 - Q15) -> Must Refuse!
    # ------------------------------------------------------------------
    {
        "id": "Q11",
        "kind": "out_of_scope",
        "answerable": False,
        "question": "How do I write a C# MonoBehaviour script with Rigidbody in Unity?",
        "api_anchors": [],
        "expected_apis": [],
    },
    {
        "id": "Q12",
        "kind": "out_of_scope",
        "answerable": False,
        "question": "How do I create a 3D vehicle physics controller in Unreal Engine using C++?",
        "api_anchors": [],
        "expected_apis": [],
    },
    {
        "id": "Q13",
        "kind": "out_of_scope",
        "answerable": False,
        "question": "How do I manage component state using useState and useEffect hooks in React?",
        "api_anchors": [],
        "expected_apis": [],
    },
    {
        "id": "Q14",
        "kind": "out_of_scope",
        "answerable": False,
        "question": "What is the best recipe and oven temperature for baking sourdough pasta at home?",
        "api_anchors": [],
        "expected_apis": [],
    },
    {
        "id": "Q15",
        "kind": "out_of_scope",
        "answerable": False,
        "question": "How do I call love.graphics.draw3DRaytracedMesh() to enable hardware raytracing in Love2D?",
        "api_anchors": [],
        "expected_apis": [],
    },
]


def main() -> None:
    print("=" * 92)
    print("  PHASE 2 — STEP 1: BUILDING & VERIFYING `rag_golden.jsonl` DIRECTLY FROM `faiss_index/`")
    print("=" * 92)

    # 1. Load active FAISS index and extract all stored chunks
    vs = get_vectorstore(only_current=True)
    retriever = get_retriever(vs, k=RETRIEVER_K, mode="dense")
    indexed_chunks = extract_docs_from_faiss(vs, only_current=True)

    # 2. Build each golden record by querying `faiss_index` and matching `api_anchors`
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    golden_records: list[dict] = []

    for spec in RAW_BENCHMARK_SPECS:
        qid = spec["id"]
        question = spec["question"]
        answerable = spec["answerable"]
        anchors = spec["api_anchors"]

        if not answerable:
            golden_records.append(
                {
                    "id": qid,
                    "kind": spec["kind"],
                    "answerable": False,
                    "question": question,
                    "relevant_docs": [],
                    "gold_chunk_ids": [],
                    "gold_pages": [],
                    "expected_apis": [],
                }
            )
            continue

        # Retrieve top-5 chunks from FAISS for this question (normalized just like chain.py)
        norm_q = _normalize_search_query(question)
        top_hits = retriever.invoke(norm_q)

        # Keep hits from `faiss_index` that contain at least one target API anchor
        # (or also scan full `indexed_chunks` for exact API anchor matches)
        matched_chunks = [
            d for d in top_hits
            if any(a.lower() in d.page_content.lower() for a in anchors)
        ]
        if not matched_chunks:
            matched_chunks = [
                d for d in indexed_chunks
                if any(a.lower() in d.page_content.lower() for a in anchors)
            ][:5]

        # Extract unique PDF filenames, chunk_ids, and (source, page) pairs in rank order
        rel_docs: list[str] = []
        gold_chunk_ids: list[str] = []
        gold_pages: list[str] = []

        for d in matched_chunks:
            src = d.metadata.get("source", "Unknown.pdf")
            cid = d.metadata.get("chunk_id", "")
            page = d.metadata.get("page", "?")
            if src not in rel_docs:
                rel_docs.append(src)
            if cid and cid not in gold_chunk_ids:
                gold_chunk_ids.append(cid)
            page_tag = f"{src}:p{page}"
            if page_tag not in gold_pages:
                gold_pages.append(page_tag)

        golden_records.append(
            {
                "id": qid,
                "kind": spec["kind"],
                "answerable": True,
                "question": question,
                "relevant_docs": rel_docs,
                "gold_chunk_ids": gold_chunk_ids[:5],
                "gold_pages": gold_pages[:5],
                "expected_apis": spec["expected_apis"],
            }
        )

    # Save to `data/eval/rag_golden.jsonl`
    GOLDEN_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in golden_records) + "\n",
        encoding="utf-8",
    )

    # 3. Print Summary Table of All 15 Golden Questions (with real `faiss_index` sources!)
    by_kind = Counter(r["kind"] for r in golden_records)
    print(f"\n[1] Saved {len(golden_records)} Golden Questions to `{GOLDEN_PATH.relative_to(GOLDEN_PATH.parents[2])}`:")
    print(f"    • Group A (Theory / API)   : {by_kind['theory']} questions (Q01 - Q08)")
    print(f"    • Group B (Lua Coding)     : {by_kind['coding']} questions (Q09 - Q10) -> Graded ONLY on `expected_apis`!")
    print(f"    • Group C (Out-of-Scope)   : {by_kind['out_of_scope']} questions (Q11 - Q15) -> Must trigger exact REFUSAL!")

    print("\n  [VERIFIED GOLDEN BENCHMARK TABLE — POPULATED DIRECTLY FROM `faiss_index/`]:")
    print("  +-----+--------------+-----------------------------------+----------------------------+------------------------+")
    print("  | ID  | Group / Kind | Checked APIs (`expected_apis`)    | PDFs in `faiss_index/`     | Top Gold Page in FAISS |")
    print("  +-----+--------------+-----------------------------------+----------------------------+------------------------+")
    for r in golden_records:
        qid = r["id"]
        kind = r["kind"]
        apis_str = ", ".join(r["expected_apis"]) if r["expected_apis"] else "REFUSAL (Out-of-Scope)"
        if len(apis_str) > 33:
            apis_str = apis_str[:30] + "..."
        docs_str = ", ".join(d.replace(".pdf", "") for d in r["relevant_docs"]) or "None (Must Refuse)"
        if len(docs_str) > 26:
            docs_str = docs_str[:23] + "..."
        top_page = r["gold_pages"][0] if r["gold_pages"] else "—"
        print(f"  | {qid:<3} | {kind:<12} | {apis_str:<33} | {docs_str:<26} | {top_page:<22} |")
    print("  +-----+--------------+-----------------------------------+----------------------------+------------------------+")

    # 4. Print `faiss_index/` Inventory per PDF
    pdf_files = sorted(DOCUMENTS_DIR.glob("*.pdf"))
    chunks_by_pdf = Counter(c.metadata.get("source", "Unknown") for c in indexed_chunks)
    avg_chunk_len = round(
        sum(len(c.page_content) for c in indexed_chunks) / max(len(indexed_chunks), 1), 1
    )
    archived_in_index = sum(
        1 for c in indexed_chunks if c.metadata.get("source") in ARCHIVED_DOCS
    )

    print(f"\n[2] `faiss_index/` Chunk Inventory:")
    print(f"    • Total Active Chunks (`status='current'`) : {len(indexed_chunks):,} chunks")
    print(f"    • Chunk Config                             : {CHUNK_SIZE} chars (overlap {CHUNK_OVERLAP}, avg {avg_chunk_len} chars)")
    print(f"    • Archived Cover Noise (`00-cover...`)     : {archived_in_index} chunks in index (Filtered out!)")

    print("\n  +----------------------------+---------------+------------------------------------------+")
    print("  | PDF Filename               | Status        | Indexed Chunks in `faiss_index/`         |")
    print("  +----------------------------+---------------+------------------------------------------+")
    for pdf_path in pdf_files:
        name = pdf_path.name
        is_arch = name in ARCHIVED_DOCS or "ARCHIVED" in name.upper()
        status_str = "archived" if is_arch else "current"
        cnt = chunks_by_pdf.get(name, 0)
        note = "(Filtered out - Table of Contents noise)" if is_arch else f"{cnt:,} chunks indexed"
        print(f"  | {name:<26} | {status_str:<13} | {note:<40} |")
    print("  +----------------------------+---------------+------------------------------------------+")

    # 5. Save JSON Report (`reports/step1_benchmark.json`)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "step1_benchmark.json"
    report_payload = {
        "step": "step1_golden_benchmark",
        "golden_file": str(GOLDEN_PATH.relative_to(GOLDEN_PATH.parents[2])),
        "total_questions": len(golden_records),
        "counts_by_kind": dict(by_kind),
        "faiss_total_chunks": len(indexed_chunks),
        "faiss_avg_chunk_chars": avg_chunk_len,
        "archived_chunks_in_index": archived_in_index,
        "chunks_per_pdf": dict(chunks_by_pdf),
        "questions": golden_records,
    }
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    print("\n" + "=" * 92)
    print(f"  ✅ STEP 1 COMPLETE! Golden dataset saved to: {GOLDEN_PATH}")
    print(f"  ✅ Scorecard saved to                      : {report_path}")
    print("=" * 92)


if __name__ == "__main__":
    main()
