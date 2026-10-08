# Phase 1 — Fix 1: Upgrading `config.py`

**File Modified:** [`config.py`](file:///d:/Python_AIP_second/config.py)

---

## 1. Big Picture: Why Did We Change `config.py`?

Think of `config.py` as the **control panel** for our entire Love2D assistant. Every other file in the project looks here to know:
- How big each text chunk should be
- Which AI models to use
- Where to save the vector database, cache, and trace logs
- What rules to follow for temperature, cost limits, and refusals

In our old `config.py`, several settings were hurting our search quality and missing key features from `Plaksha_AI_in_Practise_modified`. Here is what we fixed and why.

---

## 2. Before vs. After Comparison

```text
+----------------------------------------+----------------------------------------+
|           OLD config.py                |           NEW config.py                |
+----------------------------------------+----------------------------------------+
| CHUNK_SIZE = 3000                      | CHUNK_SIZE = 600                       |
| CHUNK_OVERLAP = 600                    | CHUNK_OVERLAP = 120                    |
| (Blends 4-5 functions into 1 vector)   | (Keeps each function/topic focused)    |
+----------------------------------------+----------------------------------------+
| No filter for Table-of-Contents pages  | ARCHIVED_DOCS = ("00-cover-contents",) |
|                                        | (Marks cover pages as non-current)     |
+----------------------------------------+----------------------------------------+
| Only 1 hardcoded LLM_MODEL             | MODEL_TIERS: SMALL, MAIN, LARGE, EMBED |
|                                        | (Uses LARGE as a separate AI Judge)    |
+----------------------------------------+----------------------------------------+
| No SEED or TEMPERATURE                 | SEED = 42, TEMPERATURE = 0.0           |
| (Answers could change randomly)        | (Repeatable, deterministic answers)    |
+----------------------------------------+----------------------------------------+
| No standardized Refusal phrase         | Exact REFUSAL constant (from Lab 4)    |
+----------------------------------------+----------------------------------------+
| No Cache, Cost, Trace, or Data folders | Added .aip_cache, .aip_traces, data/,  |
|                                        | reports/, PRICES_PER_MTOK & BUDGET_USD |
+----------------------------------------+----------------------------------------+
```

---

## 3. Line-by-Line Plain-English Explanation of Every Change

### Change 1: Shrinking Chunk Size from `3000` to `600` (Lab 3 Good Practice)
* **What we changed:**
  ```python
  CHUNK_SIZE = 600
  CHUNK_OVERLAP = 120
  LEGACY_CHUNK_SIZE = 3000
  LEGACY_CHUNK_OVERLAP = 600
  ```
* **What this means in plain English:**
  - When we chop the Love2D PDF manuals into pieces (chunks), each piece gets turned into a single list of 384 numbers (a vector) representing its meaning.
  - **Why `3000` was bad (Semantic Dilution):** A 3,000-character chunk is almost a full page and a half of text! In a coding manual like Love2D, 3,000 characters often contain 4 or 5 completely different Lua functions (for example, `love.graphics.circle`, `love.graphics.rectangle`, `love.graphics.line`, and `love.graphics.polygon`). When the embedding model turns all 3,000 characters into **one single vector**, it averages all those functions together into a blurry middle ground.
  - **Why `600` with `120` overlap is better:** Lab 3 (`labs/lab3/report.md`) proved that smaller chunks (`400–800` characters) keep each rule or function in its own sharp, focused vector. The `120`-character overlap makes sure we never accidentally cut a sentence or Lua code snippet in half at the edge of a chunk.
  - **Why we kept `LEGACY_CHUNK_SIZE = 3000`:** In Phase 2 (Step 3), our evaluation script will test `3000` vs. `600` side-by-side so we can prove with real numbers how much accuracy improved.

---

### Change 2: Filtering Out Cover & Table-of-Contents Noise (Lab 3 Good Practice)
* **What we changed:**
  ```python
  ARCHIVED_DOCS: tuple[str, ...] = ("00-cover-contents.pdf",)
  ```
* **What this means in plain English:**
  - Your `documents/` folder has 9 PDFs, and the first one (`00-cover-contents.pdf`) is just the book cover and Table of Contents.
  - A Table of Contents mentions every topic name (*"Graphics... Page 40, Physics... Page 90"*) without explaining how any of them work!
  - In the old code, the search engine often grabbed chunks from `00-cover-contents.pdf` because the topic words matched, wasting valuable context slots.
  - By listing `00-cover-contents.pdf` in `ARCHIVED_DOCS`, our loader will tag it as `status: "archived"`, and our search engine will only search real manual chapters (`status: "current"`).

---

### Change 3: Adding Model Tiers — `SMALL`, `MAIN`, `LARGE`, `EMBED` (All Labs)
* **What we changed:**
  ```python
  MODEL_TIERS: dict[str, str] = {
      "SMALL": "gemini-3.1-flash-lite",
      "MAIN": "gemini-3.1-flash-lite",
      "LARGE": "gemini-3.5-flash",
      "EMBED": EMBEDDING_MODEL,
  }
  ```
* **What this means in plain English:**
  - In `Plaksha_AI_in_Practise_modified`, you never use the exact same model for every job:
    - **`SMALL` (`gemini-3.1-flash-lite`):** Fast and cheap, used when extracting data from dozens of support tickets in Labs 1 & 2.
    - **`MAIN` (`gemini-3.1-flash-lite`):** Our main model for answering Love2D user questions (with automatic fallback to `FALLBACK_LLM_MODELS` if the server is busy).
    - **`LARGE` (`gemini-3.5-flash`):** A stronger, separate model used as the **AI Judge** in Lab 4. Why must `LARGE` be different from `MAIN`? Because if a model grades its own answers, it suffers from **Self-Preference Bias** (giving itself high marks even when it makes a mistake!).
    - **`EMBED` (`all-MiniLM-L6-v2`):** Our local HuggingFace model that turns text into 384-number vectors on your computer for free ($0).

---

### Change 4: Adding Token Pricing (`PRICES_PER_MTOK`) & Budget Limit (`BUDGET_USD`)
* **What we changed:**
  ```python
  PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
      "gemini-3.1-flash-lite": (0.30, 2.50),
      "gemini-3.5-flash": (1.50, 9.00),
      ...
  }
  BUDGET_USD = _env_float("AIP_BUDGET_USD", 2.0)
  ```
* **What this means in plain English:**
  - AI providers charge per **1 Million tokens** (where 1 token is roughly $\frac{3}{4}$ of an English word).
  - Each tuple `(0.30, 2.50)` means: **$0.30 per 1M input tokens** (what we send to the AI) and **$2.50 per 1M output tokens** (what the AI writes back).
  - `BUDGET_USD = 2.0` acts as a circuit breaker: if a runaway loop ever tries to spend more than $2.00, the system stops automatically.

---

### Change 5: Adding `SEED = 42` and `TEMPERATURE = 0.0` (Labs 1 & 2)
* **What we changed:**
  ```python
  SEED = 42
  TEMPERATURE = _env_float("AIP_TEMPERATURE", 0.0)
  ```
* **What this means in plain English:**
  - **`TEMPERATURE = 0.0`** turns off random "creativity" so the AI always picks the single most likely, factual word based on the Love2D manual.
  - **`SEED = 42`** locks the random number generator so that when we run experiments or shuffle data, we get the exact same repeatable results every time.

---

### Change 6: Adding the Exact `REFUSAL` Sentence & `MAX_TOOL_CALLS` (Labs 4 & 6)
* **What we changed:**
  ```python
  MAX_TOOL_CALLS = 3
  REFUSAL = "I don't have enough information in the provided sources to answer that."
  ```
* **What this means in plain English:**
  - **`REFUSAL`**: Instead of letting the AI invent 20 different ways to say *"Sorry, I don't know"*, Lab 4 requires one exact, standardized sentence. That way, our Python code can check in 0 milliseconds whether the AI refused or answered!
  - **`MAX_TOOL_CALLS = 3`**: In Lab 6, this stops a hacker prompt from tricking the assistant into searching the database 500 times in a row.

---

### Change 7: Adding Directories for `data/`, `.aip_cache/`, `.aip_traces/`, and `reports/`
* **What we changed:**
  ```python
  DATA_DIR = BASE_DIR / "data"
  CORPUS_DIR = DATA_DIR / "corpus"
  EVAL_DIR = DATA_DIR / "eval"
  ATTACKS_DIR = DATA_DIR / "attacks"
  REPORTS_DIR = BASE_DIR / "reports"
  CACHE_DIR = Path(os.getenv("AIP_CACHE_DIR", BASE_DIR / ".aip_cache"))
  TRACE_DIR = Path(os.getenv("AIP_TRACE_DIR", BASE_DIR / ".aip_traces"))
  ```
* **What this means in plain English:**
  - Sets up the exact folder paths used across `Plaksha_AI_in_Practise_modified` for caching answers (`.aip_cache`), logging step-by-step traces (`.aip_traces`), storing test datasets (`data/`), and saving JSON scorecards (`reports/`).
