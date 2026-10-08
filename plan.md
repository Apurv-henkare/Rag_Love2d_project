# Master Plan: Love2D Grounded RAG Project (Phase 1 & Simplified Phase 2)

---

## 1. What Are We Doing and Why? (In Plain English)

Originally, our Love2D Documentation Assistant worked like a **basic prototype**:
- It chopped the PDF manuals into huge 3,000-character blocks (which mixed multiple Lua functions together).
- It called the AI twice for every single question (making simple questions twice as slow).
- It did not save past answers in a cache (so asking the same question again wasted time and API quota).
- It had no safety shield against prompt-hacking, API key leaks, or fake citations.
- It had no ground-truth test benchmark to prove how accurate it actually is.

Our goal is to upgrade the Love2D Assistant into a **clean, production-grade RAG system** and prove its quality in **4 simple, easy-to-explain steps** for the professor.

### Diagram 1: Old Prototype vs. Upgraded Project

```text
+--------------------------------------+      +--------------------------------------+
|      OLD LOVE2D PROJECT (Before)     |      |    UPGRADED LOVE2D PROJECT (After)   |
+--------------------------------------+      +--------------------------------------+
| 1. Giant 3,000-letter chunks         |      | 1. Focused 600-letter chunks with    |
|    (mixes 5 functions together)      |      |    section headers & clean metadata  |
|                                      |      |                                      |
| 2. Includes Table-of-Contents noise  | ---> | 2. Filters out cover/archived pages  |
|                                      |      |                                      |
| 3. Makes 2 slow AI calls per query   |      | 3. Makes 1 fast AI call + SQLite     |
|    with no cache and no cost tracker |      |    cache ($0 & ~80ms on repeat asks) |
|                                      |      |                                      |
| 4. Hopes the AI writes good JSON     |      | 4. Python checks every [1] citation  |
|    and citations                     |      |    and auto-repairs any mistake      |
|                                      |      |                                      |
| 5. Zero security guards & zero       |      | 5. 5-Layer Security Shield + Clean   |
|    benchmark test scores             |      |    4-Step Evaluation Scoreboard      |
+--------------------------------------+      +--------------------------------------+
```

---

## 2. Our Two-Phase Game Plan

* **Phase 1 — Upgrade the Core Code Files & Rebuild `faiss_index/` (COMPLETED ✅):**
  We upgraded all 7 core files (`config.py` $\rightarrow$ `schemas.py` $\rightarrow$ `loader.py` $\rightarrow$ `vectorstore.py` $\rightarrow$ `aip_core/` $\rightarrow$ `chain.py` $\rightarrow$ `app.py` & `capstone.py`) and built the clean 600-character `faiss_index/`.

* **Phase 2 — 4 Clean, Defendable Evaluation Steps (One Step at a Time):**
  We test and prove our system in **4 simple steps** that directly answer the 4 main questions your professor will ask:
  1. I create the script/data for that step.
  2. You run `python run_stepX.py` in your terminal and paste the output here.
  3. I write a clear, plain-English summary guide (`step1.md`, `step2.md`, `step3.md`, `step4.md`) explaining the results and formulas simply.

### Diagram 2: Our Step-by-Step Workflow

```text
==============================================================================
PHASE 1: UPGRADE MAIN CODE FILES & BUILD NEW faiss_index/ (COMPLETED ✅)
==============================================================================

  [config.py] -> [schemas.py] -> [loader.py] -> [vectorstore.py]
       -> [aip_core/] -> [chain.py] -> [app.py & capstone.py]
       -> Built clean 600-char `faiss_index/`!

==============================================================================
SIMPLIFIED PHASE 2: 4 CLEAN, DEFENDABLE STEPS
==============================================================================

  Step 1: The Golden Test Benchmark (The "Exam Paper")
          Create a clean test set of 15 real Love2D questions with gold answers
          (10 Love2D game dev questions + 5 out-of-scope trap questions like C#/Unreal).
          -> You run: python run_step1.py  --->  I write: step1.md
          -> Professor question answered: "Where is your ground-truth test data?"
           |
           v
  Step 2: The Chunking & Search Proof (Before vs. After)
          Run a simple comparison on our benchmark:
          - Old 3,000-char chunks vs. New 600-char chunks
          - Unfiltered vs. Metadata Filtered (`status == 'current'`)
          - BM25 vs. Dense Vector Search
          -> You run: python run_step2.py  --->  I write: step2.md
          -> Professor question answered: "Why 600 chars? Prove it beats 3000."
           |
           v
  Step 3: Grounded Answer & Citation Check
          Run the Love2D bot on the test questions and show:
          1. Factual Love2D questions cite exact manual pages [1], [2] (100% valid).
          2. Coding questions generate runnable Lua callbacks (`love.load/update/draw`).
          3. Out-of-scope questions (C#, Unreal, Cooking) cleanly refuse!
          -> You run: python run_step3.py  --->  I write: step3.md
          -> Professor question answered: "How do you guarantee zero hallucinations?"
           |
           v
  Step 4: Speed, Cost & Security Demo (The "Engineering Spine")
          Show the live production engineering & 5-layer security demo:
          1. Ask a question (1st time): takes ~2s and costs ~$0.0015.
          2. Ask it again (2nd time): SQLite Cache returns it in ~80ms for $0.00!
          3. Test the 5 Guardrails: Prompt injection blocked in 0.5ms ($0.00),
             API keys/emails redacted, spy images blocked, and 0% false alarms
             on normal Love2D questions (like "How to ignore gravity?").
          -> You run: python run_step4.py  --->  I write: step4.md
          -> Professor question answered: "Is it production-ready, fast, and safe?"
==============================================================================
```

---

## 3. How `documents/`, `faiss_index/`, and `data/` Work Together

1. **`documents/` is the Textbook:** Holds the official Love2D manual PDFs (`00-cover-contents.pdf` to `08-appendices.pdf`).
2. **`faiss_index/` is the Searchable Index Card Box:** Holds the 600-character chunks (`status == "current"`) and their L2-normalized 384-dimensional vectors (`all-MiniLM-L6-v2`).
3. **`data/eval/love2d_golden.jsonl` is the Exam Paper:** Holds our 15 benchmark questions (10 answerable Love2D questions + 5 out-of-scope trap questions) that we use across Steps 1, 2, 3, and 4.

---

## 4. Detailed Summary Table of Phase 2 (Steps 1 to 4)

| Step | What We Build & Test | Command You Run | What I Explain in `stepX.md` (In Simple Plain English) |
| :--- | :--- | :--- | :--- |
| **Step 1**<br>*The Golden Benchmark* | Creates `data/eval/love2d_golden.jsonl` (10 real Love2D questions covering graphics, physics, callbacks, audio, input + 5 out-of-scope traps like C#, Unity, Unreal, Cooking, Python) and verifies every question against our PDFs. | `python run_step1.py` | - Why every AI system needs a Golden Benchmark ("Exam Paper")<br>- Breakdown of the 10 Love2D questions & expected PDF sources<br>- Why we include 5 Unanswerable / Out-of-Scope trap questions |
| **Step 2**<br>*Chunking & Search Proof* | Compares **Old `3000`-char chunks** (with cover-page noise) vs. **New `600`-char chunks** (`status == 'current'`), and compares **`BM25`** vs. **`Dense`** search on the 10 Love2D questions. | `python run_step2.py` | - What **Semantic Dilution** is and why `600` chars beats `3000` chars<br>- How filtering out `00-cover-contents.pdf` removes Table-of-Contents noise<br>- Simple explanation & math for **`Hit Rate@1`**, **`Hit Rate@5`**, and **`MRR`** |
| **Step 3**<br>*Grounded Answers & Citations* | Runs the Grounded RAG chain on the benchmark to measure:<br>1. **Citation Validity (`[1]`, `[2]`)**<br>2. **Refusal Accuracy** on the 5 trap questions<br>3. **Adaptive Prompting** (concise theory vs. complete Lua code) | `python run_step3.py` | - How Python's `validate_answer()` guarantees **100% (`1.000`) Citation Validity** with auto-repair<br>- **Refusal Recall** & **Refusal Precision** explained simply<br>- How the bot answers Love2D questions vs. refuses C#/Unity |
| **Step 4**<br>*Speed, Cost & 5 Security Guards* | Tests:<br>1. **Live Call vs. SQLite Cache Hit** (`~2200 ms` / `$0.0015` $\rightarrow$ `~80 ms` / `$0.00`)<br>2. **Budget Circuit Breaker** & **JSONL Traces**<br>3. **All 5 Security Guardrails** (Direct Injection, Poisoned PDF, API Key Redaction, Spy Image, and Benign `"ignore"` Control) | `python run_step4.py` | - How SHA-256 SQLite caching saves 100% of API cost on repeat asks<br>- Token cost math & Median ($p_{50}$) vs. Tail ($p_{95}$) speed<br>- Plain-English guide to all **5 Guardrails** (`100%` attacks blocked, `0%` false alarms) |
