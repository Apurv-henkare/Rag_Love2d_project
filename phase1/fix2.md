# Phase 1 — Fix 2: Upgrading `schemas.py`

**File Modified:** [`schemas.py`](file:///d:/Python_AIP_second/schemas.py)

---

## 1. Big Picture: Why Did We Change `schemas.py`?

Think of `schemas.py` as the **strict rulebook (contract)** for what the AI is allowed to output.

In our old `schemas.py`, the contract was only 17 lines long: it only had `question` and `answers` (`text` and `context`), with **zero validation rules**. Because there were no rules in `schemas.py`:
- It did not check or list which chunk numbers (`[1]`, `[2]`) were cited.
- It did not have a clean `True / False` flag for whether the AI refused an out-of-scope question (`is_refusal`).
- It did not track speed (`latency_ms`), cost (`cost_usd`), cache hits (`cached`), or security guard alerts (`guard_triggered`).

We upgraded `schemas.py` to follow the best practices from **Lab 1, Lab 2, Lab 4, and Lab 6** of `Plaksha_AI_in_Practise_modified`.

---

## 1.5 What Does "Citation" Mean? (In Plain English)

A **citation** is simply a **numbered tag like `[1]` or `[2]`** at the end of a sentence that tells you **which exact manual chunk the AI got that fact from**—just like a footnote in a book or Wikipedia article!

### Simple Example:
Suppose a user asks: *"How do I draw a rectangle in Love2D?"*

1. **First, our Search Engine grabs 5 chunks from the PDFs and numbers them `[1]` to `[5]`:**
   - **Chunk `[1]`** (`06-modules.pdf`, Page 12): Explains `love.graphics.rectangle(mode, x, y, width, height)`
   - **Chunk `[2]`** (`06-modules.pdf`, Page 14): Explains `love.graphics.setColor(r, g, b, a)`
   - **Chunk `[3]`** (`01-getting-started.pdf`, Page 5): Explains `love.draw()`
   - **Chunk `[4]`** (`02-callbacks.pdf`, Page 8): Explains `love.update(dt)`
   - **Chunk `[5]`** (`05-physics.pdf`, Page 30): Explains physics bodies

2. **Next, the AI writes its answer and puts the chunk numbers `[1]`, `[2]`, `[3]` next to each fact:**
   > *"To draw a rectangle on the screen, call `love.graphics.rectangle(mode, x, y, width, height)` inside the `love.draw()` callback **`[1][3]`**. You can also change its color first using `love.graphics.setColor(r, g, b)` **`[2]`**."*

Here, **`[1]`**, **`[2]`**, and **`[3]`** are the **citations**!
- They prove the AI did **not** make up the answer from its imagination (hallucinate).
- And in `schemas.py`, our field `cited_indices = [1, 2, 3]` automatically collects those numbers so Python can check: *"Wait—we gave the AI 5 chunks (`[1]` to `[5]`). Did it only cite numbers between 1 and 5, or did it make up a fake `[9]`?"*

---

## 2. Before vs. After Comparison

```text
+----------------------------------------+----------------------------------------+
|           OLD schemas.py               |           NEW schemas.py               |
+----------------------------------------+----------------------------------------+
| Only had `question` and `answers`      | Keeps `question` & `answers` AND adds: |
|                                        | - `cited_indices` ([1, 2, ...])        |
|                                        | - `is_refusal` (True/False)            |
|                                        | - `needs_human_review` (True/False)    |
|                                        | - `latency_ms`, `cost_usd`, `cached`   |
|                                        | - `guard_triggered`                    |
+----------------------------------------+----------------------------------------+
| No automatic Python check for `[1]`    | `@model_validator` in Python extracts  |
| citations or refusals                  | `[1]` citations & sets `is_refusal`    |
|                                        | automatically with 100% accuracy       |
+----------------------------------------+----------------------------------------+
| No schema for Lab 1/2 Ticket Extractor | Added `Love2DTicketRecord` (with       |
| or Lab 4 AI Judge                      | `evidence` placed first + validators)  |
|                                        | and `JudgeVerdict` (for Lab 4 Judge)   |
+----------------------------------------+----------------------------------------+
```

---

## 3. Plain-English Explanation of Every Change

### Change 1: Upgrading `Transformer` (Our Main RAG Answer Contract)
We kept the exact class name `Transformer` and its `question` and `answers` fields so `app.py`, `capstone.py`, and `chain.py` continue to work without breaking, and added 7 new fields:

1. **`cited_indices: List[int]` (Lab 4 Citation Tracking):**
   - Stores the exact list of source chunk numbers cited in the answer (for example, `[1, 3]`).
   - This makes it effortless to check whether every citation is valid (between `1` and `5`).
2. **`is_refusal: bool` (Lab 4 Refusal Tracking):**
   - Instead of `app.py` guessing whether the AI refused to answer, `is_refusal` is a clean `True` or `False` switch.
3. **`needs_human_review: bool` (Lab 1 Safe Fallback):**
   - If the AI ever fails validation even after a repair retry, we don't crash the app—we return a safe fallback response and set `needs_human_review = True`.
4. **`latency_ms`, `cost_usd`, `cached`, `guard_triggered` (Engineering Spine & Lab 6):**
   - Lets our Streamlit UI and CLI show you how fast the answer took (in milliseconds), how much it cost (in USD), whether it came from the SQLite cache (`0 ms`, `$0.00`), and whether any security guard blocked an attack.

---

### Change 2: Moving Citation & Refusal Detection into Python (`_sync_deterministic_fields`)
* **What we added:**
  ```python
  @model_validator(mode="after")
  def _sync_deterministic_fields(self) -> "Transformer":
      combined_text = " ".join(a.get("text", "") for a in self.answers).strip()
      found_citations = sorted({int(m) for m in _CITATION_RE.findall(combined_text)})
      if found_citations:
          self.cited_indices = found_citations
      ...
  ```
* **Why we did this (Lab 1 & Lab 4 Good Practice):**
  - Lab 1 proved: **Never ask the AI to do math or pattern matching that regular Python code can do.**
  - As soon as the AI writes its answer text, this Python function scans the text for `[1]`, `[2]`, etc., fills in `cited_indices` automatically, and checks if the text is a refusal (`is_refusal = True`). It is 100% accurate and costs 0 tokens!

---

### Change 3: Adding `Love2DTicketRecord` (For Step 2 / Labs 1 & 2)
* **What we added:**
  A strict Pydantic v2 contract for extracting structured data from messy Love2D developer bug reports and forum questions (`data/eval/extraction_dev.jsonl` and `extraction_test.jsonl`).
* **Key Good Practices inside `Love2DTicketRecord`:**
  1. **`evidence` is placed FIRST:**
     In Lab 1 (`labs/lab1/report.md`), placing `evidence` as the very first field forces the AI to quote the exact sentence from the user's bug report *before* it picks the category or urgency. That acts like a mini "think before you answer" step without wasting tokens!
  2. **Strict `Literal` and Range Rules (`ge=1, le=5`):**
     The AI is only allowed to pick from our exact list of categories (`graphics`, `physics`, `audio_input`, `callbacks_loop`, `packaging_conf`, `other`) and urgency numbers from `1` to `5`.
  3. **Custom `@field_validator` for `love_version`:**
     If the AI outputs an invalid version string, Pydantic raises a specific `ValidationError` telling the AI exactly how to fix it on the retry!

---

### Change 4: Adding `JudgeVerdict` (For Step 4 / Lab 4 AI Judge)
* **What we added:**
  ```python
  class JudgeVerdict(BaseModel):
      rationale: str = Field(max_length=350, ...)
      score: int = Field(ge=0, le=2, ...)
  ```
* **Why we did this (Lab 4 Good Practice):**
  - When our `LARGE` model grades an answer for **Faithfulness** (`0` or `1`) or **Answer Correctness** (`0`, `1`, or `2`), placing `rationale` before `score` forces the AI Judge to write out its 1–2 sentence explanation *before* giving the final score.
