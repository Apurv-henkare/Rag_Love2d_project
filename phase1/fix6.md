# Phase 1 — Fix 6: Upgrading `chain.py`

**File Modified:** [`chain.py`](file:///d:/Python_AIP_second/chain.py)

---

## 1. Big Picture: Why Did We Change `chain.py`?

`chain.py` is the **brain** of your Love2D project. It takes the user's question, searches `faiss_index/`, formats the chunks into a prompt, calls the Gemini AI, and parses the final answer.

In our old `chain.py`, there were **5 major weaknesses** that we fixed using the lessons from Labs 1, 2, 4, 5, and 6 of `Plaksha_AI_in_Practise_modified`:

```text
+----------------------------------------+----------------------------------------+
|             OLD chain.py               |             NEW chain.py               |
+----------------------------------------+----------------------------------------+
| Made 2 AI calls on EVERY question      | Python checks if it's a single-topic   |
| (even simple theory questions!)        | question -> skips Call #1 (saves 50%   |
|                                        | time & cost!). Only uses the planner   |
|                                        | (capped at 3 searches) for full games. |
+----------------------------------------+----------------------------------------+
| Unnumbered context headers & no        | Formats chunks as `[1]`, `[2]`, `[3]`  |
| `<RETRIEVED_DOCUMENT>` security tags   | wrapped inside `<RETRIEVED_DOCUMENT>`  |
|                                        | tags after scrubbing poisoned text     |
+----------------------------------------+----------------------------------------+
| No Python check for whether citations  | `validate_answer()` in Python checks   |
| `[1]..[n]` exist or are in bounds      | every `[n]` is between `1` and `n`.    |
|                                        | If invalid -> 1 automatic repair retry |
|                                        | -> safe fallback to `REFUSAL` (`1.000` |
|                                        | Citation Validity guaranteed!)         |
+----------------------------------------+----------------------------------------+
| Rigid prompt rules                     | Supports `v1` (brief baseline) and     |
|                                        | `v2` (**Adaptive Completeness**: crisp |
|                                        | for theory, complete callbacks for     |
|                                        | coding) + Partial Refusal support      |
+----------------------------------------+----------------------------------------+
| No SQLite cache, no cost meter, no     | Integrated with `aip_core`: SQLite     |
| trace logs, and no security guards     | cache (`0 ms` / `$0`), `Budget` cost,  |
|                                        | `.aip_traces/`, and all 5 guard layers |
+----------------------------------------+----------------------------------------+
```

---

## 2. Step-by-Step Flow Inside Our New `chain.py`

```text
  USER QUESTION
       |
       v
+-------------------------------------------------------------------------+
| STAGE 1: INPUT SECURITY GUARD (Layer 2: detect_injection_refined)       |
|   - Checks if the user is trying to hack the prompt.                    |
|   - If blocked -> Returns safe refusal immediately in 0 ms for $0.00!   |
+-------------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------------+
| STAGE 2: DETERMINISTIC ROUTER & BOUNDED SEARCH (Layer 4: ToolGuard)     |
|   - Single-topic question? -> Searches FAISS directly (skips Call #1!)  |
|   - Full game build? -> Generates up to 3 search lines (`max_calls=3`)  |
|   - Scrubs chunks & wraps them in `<RETRIEVED_DOCUMENT>` (Layer 1)      |
|   - Numbers them `[1]`, `[2]`, ..., `[n]`                               |
+-------------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------------+
| STAGE 3: SQLITE CACHE CHECK (`aip_core/cache.py`)                       |
|   - Checks if `(question + chunk_ids)` is already in `cache.sqlite`.    |
|   - If found -> Returns cached answer in 0 ms for $0.00!                |
+-------------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------------+
| STAGE 4: GROUNDED AI CALL (`v2` Adaptive Prompt + Layer 3 Schema Lock)  |
|   - Simple theory question -> 2-4 concise sentences with `[1]` tags.    |
|   - Coding question -> Complete ```lua code + callbacks with `[1]` tags.|
|   - Unanswerable -> Exact `REFUSAL` sentence (or Partial Refusal).      |
+-------------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------------+
| STAGE 5: PYTHON CITATION VALIDATOR & AUTO-REPAIR (`validate_answer`)    |
|   - Did the AI cite at least one `[n]`? Is every `1 <= n <= len(docs)`? |
|   - If NO -> Sends exact error back to AI for 1 automatic repair retry! |
|   - If still broken -> Falls back safely to `REFUSAL` (`1.000` valid!)  |
+-------------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------------+
| STAGE 6: OUTPUT FILTER (Layer 5) + SAVE TO CACHE & BUDGET LEDGER        |
|   - Scrubs any external image links, PII, or system prompt leaks.       |
|   - Saves verified answer to SQLite cache and logs cost/latency/trace.  |
+-------------------------------------------------------------------------+
```

---

## 3. Plain-English Explanation of Every Key Function in `chain.py`

### 1. Deterministic Router (`_needs_multi_query_planner`) — Lab 1 & Lab 2 Good Practice
* **What it does:**
  In the old `chain.py`, even if you asked a tiny question like *"What is `love.load`?"*, it made a separate AI call (`translate_query_to_search_concepts`) just to repeat the question back!
  Now, a fast Python check (`_needs_multi_query_planner`) checks if you are asking to build a multi-feature game (like *"Build a Pong game"*).
  - For normal theory or API questions, it **skips Call #1 completely**, cutting response time and token cost in half!
  - For full game builds, it runs the planner capped at `MAX_TOOL_CALLS = 3` (`ToolGuard`).

### 2. Numbered & Delimited Chunks (`format_docs`) — Lab 4 & Lab 6 Good Practice
* **What it does:**
  - Cleans each chunk with `sanitize_retrieved_chunk()` (removing hidden HTML comment instructions).
  - Numbers each chunk `[1]`, `[2]`, ..., `[n]` with its PDF source and page number.
  - Wraps each chunk in `<RETRIEVED_DOCUMENT source="...">...</RETRIEVED_DOCUMENT>` so the AI treats it strictly as data, never as commands.

### 3. `get_prompt_template(version="v2")` — Lab 4 & Lab 5 Good Practice
* **What it does:**
  - Enforces **Zero External Engine Memory** (only use Love2D functions shown in the retrieved chunks).
  - Requires **inline numbered citations (`[1]`, `[2]`)** on every factual claim.
  - Enforces the **Exact `REFUSAL` string** (and **Partial Refusal** when a 2-part question is only half-covered by the manual).
  - Supports both `version="v1"` (strict 2–3 sentence brevity baseline) and `version="v2"` (**Adaptive Completeness**: concise for simple theory questions, complete callbacks & parameters for coding/multi-part questions) so in Phase 2 (Step 5) we can compare `v1` vs. `v2`!

### 4. Deterministic Citation Validator & Repair Loop (`validate_answer`) — Lab 4 Good Practice
* **What it does:**
  Before showing any answer to the user, Python checks:
  1. Is the answer non-empty?
  2. If it is not a refusal, does it have at least one `[n]` citation?
  3. Is every cited number `[n]` between `1` and the actual number of retrieved chunks (`len(docs)`)? (For example, if we gave the AI 5 chunks and it cites `[8]`, Python flags it as an out-of-bounds hallucination!)
  - If any check fails, `chain.py` automatically sends the exact error back to the AI for **1 repair retry**. If the retry still fails, it falls back to `REFUSAL`—guaranteeing **100% (`1.000`) Citation Validity**.
