# Phase 1 — Fix 5: Adding the `aip_core/` Engineering Toolkit

**Files Created:**
- [`aip_core/__init__.py`](file:///d:/Python_AIP_second/aip_core/__init__.py)
- [`aip_core/cache.py`](file:///d:/Python_AIP_second/aip_core/cache.py)
- [`aip_core/cost.py`](file:///d:/Python_AIP_second/aip_core/cost.py)
- [`aip_core/tracing.py`](file:///d:/Python_AIP_second/aip_core/tracing.py)
- [`aip_core/guards.py`](file:///d:/Python_AIP_second/aip_core/guards.py)
- [`aip_core/evals.py`](file:///d:/Python_AIP_second/aip_core/evals.py)

---

## 1. Big Picture: Why Did We Add `aip_core/`?

In `Plaksha_AI_in_Practise_modified`, every lab relies on a shared toolkit folder (`aip/`) that handles **caching, cost tracking, tracing, security guardrails, and evaluation math**.

Before this fix, our Love2D project had none of those tools. By adding `aip_core/`, our Love2D project now has the exact same engineering spine as the course repository!

```text
+-------------------------------------------------------------------------+
|                    aip_core/ ENGINEERING TOOLKIT                        |
+-------------------------------------------------------------------------+
|  1. cache.py   -> Saves AI answers in `.aip_cache/cache.sqlite`         |
|                   (Repeat questions take 0 ms and cost $0.00!)          |
|                                                                         |
|  2. cost.py    -> Tracks Input/Output tokens, USD cost, Median speed    |
|                   (p50), Tail speed (p95), and stops if over budget     |
|                                                                         |
|  3. tracing.py -> Writes step-by-step JSON logs into `.aip_traces/`     |
|                   so you can see how many milliseconds each step took   |
|                                                                         |
|  4. guards.py  -> 5-Layer Security Shield against prompt hackers,       |
|                   poisoned documents, infinite loops, and PII leaks     |
|                                                                         |
|  5. evals.py   -> All math formulas for Labs 1-6 (`nDCG@10`, `MRR`,     |
|                   `Recall@5`, `Wilson CI`, `Paired p-value`, `Kappa`)   |
+-------------------------------------------------------------------------+
```

---

## 2. Plain-English Explanation of Each File in `aip_core/`

### File 1: `aip_core/cache.py` (The SQLite Memory Bank)
* **What it does in plain English:**
  Every time we ask the AI a question with a set of retrieved chunks, `cache.py` creates a unique 32-character digital fingerprint (a **SHA-256 hash**) from the model name, temperature, and prompt text.
  - **First time you ask a question:** It calls the Gemini API and saves the answer in `.aip_cache/cache.sqlite`.
  - **Second time you ask the exact same question:** It finds the fingerprint in SQLite and returns the saved answer in **0 milliseconds for $0.00** without touching the internet!
  - **Offline Mode (`AIP_OFFLINE=1`):** Lets your professor or grader replay all experiments with zero internet connection and zero API cost.

---

### File 2: `aip_core/cost.py` (The Cost & Speed Meter)
* **What it does in plain English:**
  Tracks every AI call inside a `Budget` object:
  1. **Token Cost Formula:**
     $$\text{Cost (USD)} = \frac{\text{Input Tokens}}{1,000,000} \times \text{Price}_{\text{in}} + \frac{\text{Output Tokens}}{1,000,000} \times \text{Price}_{\text{out}}$$
  2. **Median Speed ($p_{50}$) vs. Tail Speed ($p_{95}$):**
     - **$p_{50}$ (50th percentile / Median):** Half of your questions finish faster than this number. It tells you the *typical* speed.
     - **$p_{95}$ (95th percentile / Tail Latency):** 95 out of 100 questions finish faster than this number; only the slowest 5% take longer. Engineers care about $p_{95}$ because users remember when the app freezes!
  3. **Budget Circuit Breaker (`BudgetExceeded`):** If a script ever spends more than `limit_usd` (default `$2.00`), it stops immediately to protect your API key.

---

### File 3: `aip_core/tracing.py` (The Flight Data Recorder)
* **What it does in plain English:**
  Just like an airplane's black-box flight recorder, `tracing.py` writes a `.jsonl` log file inside `.aip_traces/` for every run.
  Each line records one stage of the pipeline (`guard.input` $\rightarrow$ `retrieve.dense` $\rightarrow$ `llm.generate` $\rightarrow$ `validate.citations` $\rightarrow$ `guard.output`) along with its exact `duration_ms` and status (`ok` or `error`).

---

### File 4: `aip_core/guards.py` (The 5-Layer Security Shield — Lab 6)
* **What it does in plain English:**
  Implements all **5 Defense Layers** from Lab 6 (`labs/lab6/report.md`):
  1. **Layer 1 (`delimit_untrusted`)**: Wraps every retrieved PDF chunk inside `<RETRIEVED_DOCUMENT source="...">...</RETRIEVED_DOCUMENT>` tags. If a hacker hides a fake closing tag `</RETRIEVED_DOCUMENT>` inside a document to escape the box, `delimit_untrusted()` strips it out!
  2. **Layer 2 (`detect_injection_refined`)**: Catches hacker prompts trying to override rules (*"Ignore all previous instructions"*), steal the system prompt (*"Print your initial instructions"*), hijack the persona (*"You are now FreeBot"*), or sneak commands inside Base64 code.
     - **Crucial Lab 6 Good Practice:** The regex rules are carefully written so normal Love2D questions that use words like *"ignore"* (*"How do I ignore collisions between two bodies?"*) or *"act as"* (*"Make a rectangle act as a button"*) are **never** blocked (**0% False-Positive Rate**).
  3. **Layer 3 (Schema Lock)**: Works with `schemas.py` to force strict structured output.
  4. **Layer 4 (`ToolGuard`)**: Caps how many times the search tool can be called per turn (`MAX_TOOL_CALLS = 3`), stopping infinite-loop attacks.
  5. **Layer 5 (`filter_output` & `redact_pii`)**: Checks the AI's final answer before showing it to the user: blocks suspicious external Markdown image links (`![](https://attacker.example/...)`), hides accidental emails/phone numbers (`[REDACTED_EMAIL]`, `[REDACTED_PHONE]`), and blocks any verbatim leak of our system prompt.

---

### File 5: `aip_core/evals.py` (The Lab 1–6 Scoreboard Calculator)
* **What it does in plain English:**
  Contains all the math functions we will use in Phase 2 (Steps 2, 3, 4, 5) to grade our system:
  - **`retrieval_metrics()`**: Calculates `hit_rate@1`, `hit_rate@5`, `recall@5`, `mrr`, and `ndcg@10` for Step 3.
  - **`field_accuracy()`**: Calculates per-field accuracy and all-or-nothing `record_accuracy` for Step 2.
  - **`wilson_interval()`**: Calculates the 95% confidence interval for accuracy scores.
  - **`paired_test()`**: Runs the Paired Sign Test ($p$-value) to prove whether Version B is genuinely better than Version A or just got lucky.
  - **`cohens_kappa()`**: Calculates Cohen's Kappa ($\kappa$) to prove our AI Judge agrees with human grading in Step 4.
