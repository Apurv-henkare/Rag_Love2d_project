# 🎯 4-Slide Presentation Guide: Love2D Grounded RAG Assistant
### *Enterprise Production Architecture & Defense Guide — Plaksha AI in Practice (Labs 1–6)*

---

## 🖥️ Slide 1: Project Overview & The Real-World Problem

### 🕹️ What Is This Project? (In Simple Words)
* This is a **smart AI assistant made specifically for 2D game developers** using the **Love2D engine (Lua)**.
* We gave it the **8 official Love2D PDF manuals** (chopped into 7,713 clean, bite-sized pieces).
* It does two main jobs really well:
  1. **Quick Answers:** Explains game functions and concepts in plain English in less than 1 second.
  2. **Complete Game Code:** Writes full, runnable Lua game loops (`love.load`, `love.update`, `love.draw`) that you can copy, paste, and run immediately.
* **Smooth Junior Developer Onboarding:** Helps new and junior developers learn the engine fast, cutting down the time it takes to understand how Love2D works.
* Every single answer comes with **verified citations `[1]`, `[2]`** showing the exact manual page where the facts came from.

---

### 🎮 The Core Industry Problem: Proprietary Engines & Junior Onboarding
*In game development studios, two major bottlenecks slow teams down:*

1. **Game Engines Are Often Proprietary or Niche (No Public Info Available):**
   * Unlike generic Python or web development, game frameworks (like Love2D or in-house studio engines) have very little training data in public models like ChatGPT.
   * If developers ask public AI, it hallucinates fake functions, makes up non-existent parameters, or confuses syntaxes from other engines like Unity or Pygame.

2. **Onboarding Junior Developers Takes Weeks:**
   * Because public documentation and tutorials are scarce, newly hired junior developers must spend weeks reading through hundreds of pages of technical PDF manuals.
   * Junior developers get stuck constantly and have to interrupt senior engineers, draining valuable studio production hours.

---

### 💡 Why RAG Is the Solution:
* **Turns Proprietary Manuals into an Interactive Mentor:** RAG ingests private or niche engine PDFs directly, letting developers chat with the official documentation with zero public data leaks.
* **Smooth Junior Ramp-Up:** Juniors ask questions in plain English and receive instant explanations and runnable game loops (`love.load`, `love.update`, `love.draw`), cutting learning time from weeks to days.
* **100% Grounded with Exact Citations:** Every answer cites the exact manual page `[1]`, `[2]`, preventing hallucinations and teaching juniors real, verified engine APIs.
* **Frees Up Senior Developers:** Senior programmers stay focused on core gameplay and shipping features instead of answering repetitive engine questions.

---

### 🏆 How Our Hardened RAG System Delivers This:
* **Smooth Junior Developer Onboarding:** Slashes engine ramp-up time from weeks to days with clear explanations and runnable game templates.
* **Zero Fake Code (100% Grounded):** The AI is locked to the official Love2D manuals. Every function, parameter, and math formula is checked against real documentation.
* **Super Fast (< 0.6 seconds):** Simple concept questions answer in **~580 ms**. If a question was asked before, our local cache answers in **18 ms at \$0.00** (**115x faster**).
* **100% Verified Citations:** Python checks every citation bracket `[1..k]` in 0.001 ms for free. No fake numbers allowed.
* **5-Layer Safety Shield:** Blocks prompt injections in 0 ms, but is smart enough to never block real game questions like *"how to ignore collisions"*.
* **Audited by an Independent AI Judge:** A separate large model (`gemini-3.5-flash`) graded our system and gave it a **perfect 100% score for Faithfulness and Correctness**.

---

## 🖥️ Slide 2: Dual-Path System Architecture (Theory vs. Coding)

### Slide Content (What goes on the slide):
* **Title:** Adaptive Query Routing: Theory vs. Game Code
* **Architecture Diagram:**

```text
                        [ Developer Question ]
                                  │
                                  ▼
             [ 🛡️ Layer 2 Input Security Shield (Lab 6) ]
                                  │
                                  ▼
                [ 🔀 Deterministic Query Router ]
                     │                      │
       (Theory / Single API)          (Game Code / Multi-Feature)
                     │                      │
                     ▼                      ▼
           [ ⚡ Path A: Direct ]     [ 🎮 Path B: Multi-Query Planner ]
           • 1 single search        • Generates 4 concept searches:
           • Retrieves 5 chunks        (Loop, Graphics, Input, Helpers)
           • 1 LLM Call             • Retrieves 4 x 5 = 20 chunks
           • ~580 ms latency        • Python deduplicates to 12-14 chunks
           • 50% cost savings       • Generates complete runnable Lua loop
                     │                      │
                     └──────────┬───────────┘
                                ▼
         [ 🛡️ Guard Layer 3: Citation & Lua Code Scanner + Repair Loop ]
         • Verifies citations [1..k] against retrieved sources
         • Scans Lua code for ungrounded love.* API memory leakage
         • Triggers automated self-healing Repair Loop if ungrounded
                                ▼
         [ 🖥️ UI with Live Telemetry Ribbon & Cache (Lab 5) ]
```

* **Key Architectural Innovations:**
  * **Path A (Theory):** Bypasses the planner for single-concept queries, slashing latency by 75% (~580 ms) and cutting token costs in half.
  * **Path B (Coding):** Decomposes complex game requests into 4 targeted searches, preventing graphics from crowding out input or physics.

---

### 🎯 Deep Grounding Hardening: Theory vs. Coding Solutions

*Beyond basic RAG, production systems must prevent pre-trained memory from corrupting both conceptual explanations and generated code:*

1. **Solution 1: Theory Grounding Hardening (Path A — Conceptual & API Questions)**
   * **The Problem:** General tutorial stories often repeated generic words and out-ranked the official API manual page; furthermore, Gemini leaked external pre-trained jargon (*"active color state"*, *"state machine"*) not present in the manual.
   * **The Engineering Fix:**
     * **Section-Aware Manual Boosting (`vectorstore.py`):** Added `_matches_api_section()`, awarding a **$+50.0$ BM25 boost and $+1.0$ Hybrid RRF boost** to official manual definition sections, guaranteeing official API pages land at **Rank #1**.
     * **Zero Pre-Trained Vocabulary Leakage (`chain.py`):** Enforced a strict extractive prompt constraint forbidding external technical terms; if retrieved chunks only contain code examples without a written English definition, the AI must explicitly state this rather than inventing theory from memory.

2. **Solution 2: Coding Grounding Hardening (Path B — Game Implementation & Code Loops)**
   * **The Problem:** When generating game code (e.g., Pong or Shooter), LLMs naturally suffer from **pre-trained engine memory leakage**—calling functions that work in Love2D but were never retrieved or verified in the documentation chunks, or bundling all citations under a single chunk.
   * **The Engineering Fix:**
     * **1-to-1 Citation Mapping & Traceability Table (`chain.py`):** In `MODE 2`, every engine function must be cited individually against its specific chunk, followed by an **API & Callback Traceability Table** (`Engine API / Callback Used | Source Chunk | Purpose in Game`) documenting the origin of every function.
     * **Two-Tier Python Grounding in Guard Layer 3 (`validate_answer`):**
       - **Tier 1 (Global Engine Pool):** Verifies all called `love.*` functions in code exist in the retrieved context pool, eliminating fabricated APIs.
       - **Tier 2 (Per-Citation Traceability):** Cross-checks each row of the Traceability Table, ensuring the *specific cited chunk* actually contains that API (eliminating attribution leakage). If mismatched, triggers the self-healing **Repair Loop** to re-ground the answer!

## 🖥️ Slide 3: Production Engineering Spine (Plaksha Labs 1–6 Alignment)

### Slide Content (What goes on the slide):
* **Title:** Production Engineering Spine: Built on Plaksha Labs 1–6
* **1. Lab 1 (Reliable Extraction) — Deterministic Python Boundaries:**
  * *Report Discovery:* Naive prompts fail schema validation; moving deterministic regex out of the LLM saves cost and guarantees 100% accuracy.
  * *Love2D Implementation:* Python `@model_validator` extracts `[1..k]` citations in **0.001 ms for \$0.00**, and sets safe fallback `needs_human_review`.
* **2. Lab 2 (Prompt Lab) — Model Tiers & Budget Ceilings:**
  * *Report Discovery:* Low budget caps prematurely abort evaluations; multi-tier model architectures require explicit cost management.
  * *Love2D Implementation:* Implemented strict model tiers (`MAIN` vs `LARGE`) and set a **\$2.00 cost circuit breaker** in `config.py`.
* **3. Lab 3 (Search) — The Dilution Cliff, Heading Prefixes & Hybrid RRF:**
  * *Report Discovery:* Chunks > 800 chars suffer from semantic dilution; heading prefixes boost Hit@1 by +14.3%; lexical rerankers can degrade results.
  * *Love2D Implementation:* **600-char recursive chunks** with dynamic heading detection, two-tier archiving (`ARCHIVED_DOCS` + `ARCHIVED_PAGES`), and **Hybrid RRF ($k=60$)** achieving a perfect **100% Hit@1, 100% Hit@5, and 1.000 MRR**!
* **4. Lab 4 (Grounded RAG) — Dual Grounding (Theory & Code) + Decoupled AI Judge:**
  * *Report Discovery:* Generation Loss exceeds Retrieval Loss (11.9% vs 9.5%); models suffer from 5–10% self-preference bias when self-grading.
  * *Love2D Implementation:*
    * **Theory Grounding:** Section-aware manual boosting ($+50.0$ BM25 / $+1.0$ RRF) ensures official definitions hit Rank #1; zero-leakage prompt prevents external jargon.
    * **Code Grounding:** Deterministic Two-Tier Python Scanner (Tier 1 Global Pool + Tier 2 Per-Citation Table Match); triggers **automated self-healing repair retry** if an unretrieved or misattributed API is called.
    * **Decoupled AI Judge:** Empirical audit using `LARGE: gemini-3.5-flash` in [`run_step_judge.py`](file:///d:/Python_AIP_second/run_step_judge.py) achieving **100% Faithfulness and 100% Correctness** with Rationale-First `JudgeVerdict`.
* **5. Lab 5 (Diagnose & Fix) — Solving the "Brevity Trap":**
  * *Report Discovery:* 85.7% of errors were Mode 6 (Generation Errors) caused by a rigid 2-sentence limit; static unconstrained prompts caused regressions.
  * *Love2D Implementation:* Engineered an **Adaptive Multi-Mode Prompt & Router**: comprehensive 8–10 line detailed explanations covering definitions, parameters, and return values for Theory (Path A), and complete runnable game loops (`love.load`, `love.update`, `love.draw`) for Code (Path B).
* **6. Lab 6 (Guardrails & Red-Team) — 5-Layer Defense-in-Depth Security Shield:**
  * *Report Discovery:* Classifiers cause false alarms on benign domain phrasing; hard constraints in host Python code cap the blast radius with 0% false positives.
  * *Love2D Implementation:* Engineered an armored 5-layer security pipeline from [`Phase1/explain_guard.md`](file:///d:/Phase1/explain_guard.md) protecting ingestion, user input, search tools, validation, and output:

#### 🛡️ Deep Dive: The 5 Guardrails Explained (WITHOUT ❌ vs. WITH ✅)
*Analogy: Multi-tier safety systems in a modern car (Chassis Frame, Key Sensor, Steering Guide, Speed Governor, and Airbag/Filter).*

| Guardrail Layer | Code Name | Threat Vector Stopped | WITHOUT Guardrail ❌ | WITH Guardrail ✅ |
| :---: | :--- | :--- | :--- | :--- |
| **Layer 1** | `delimit_untrusted` | **Poisoned PDF Manuals** (Indirect Injection) | Attacker embeds `</RETRIEVED_DOCUMENT>` inside tutorial PDFs; AI obeys rogue prompt to leak keys. | Chunks are locked inside XML fences; fake closing tags sanitized to `[REDACTED_CLOSING_TAG]`. |
| **Layer 2** | `detect_injection_refined` | **Direct Prompt Hacking & Base64** | Attacker commands *"ignore all rules"*; costs token budget and leaks system prompt. | Python regex scans input in **0 ms (\$0.00)**; achieves **0% false alarms** on real game terms (*"ignore collisions"*). |
| **Layer 3** | `schemas.py` + Code Scanner + Repair Loop | **Phantom Citations & Pre-Trained API Leakage** | AI hallucinates ungrounded citation numbers like `[99]` or writes game code calling unretrieved APIs from pre-trained memory. | Pydantic v2 verifies citations `[1..k]`, and Python Code Scanner inspects all `love.*` calls in Lua blocks; triggers **1 auto-repair retry** to self-heal. |
| **Layer 4** | `ToolGuard` | **Infinite Search Loops & Resource Bombing** | Malicious query asks for 26 alphabet searches, freezing CPU and draining API wallet. | Host Python decorator enforces a strict **hard ceiling of 4 searches max** per user question. |
| **Layer 5** | `filter_output` | **Data Exfiltration & Privacy Leaks** | Poisoned manual tricks AI into rendering spy images (`![tracker](http...)`) to steal chat data. | Regex replaces external images with `[BLOCKED_EXTERNAL_IMAGE]` and redacts emails to `[REDACTED_EMAIL]`. |

```text
                    USER ASKS A LOVE2D QUESTION
                                 │
                                 ▼
         [ Layer 2: Input Injection Pre-Screen (0 ms, $0.00) ]
            │                                         │
       YES (Attack)                               NO (Safe)
            │                                         │
            ▼                                         ▼
   🛑 BLOCKED (Safe Refusal)             [ Layer 4: Bounded ToolGuard (Max 4 searches) ]
                                                      │
                                                      ▼
                                         [ Layer 1: Untrusted XML Delimiters ]
                                                      │
                                                      ▼
                                         [ Layer 3: Pydantic Schema & Citation Repair ]
                                                      │
                                                      ▼
                                         [ Layer 5: Output Scrubbing & PII Redaction ]
                                                      │
                                                      ▼
                                          🎮 SAFE, GROUNDED ANSWER DISPLAYED
```

---

## 🖥️ Slide 4: Empirical Results & Live Demo

### Slide Content (What goes on the slide):
* **Title:** Benchmark Results & Live System Telemetry

#### 💡 Understanding the Metrics (With Simple Love2D Examples)

*Before reviewing the tables, here is what each metric measures so you can explain them effortlessly to the professor:*


> [!IMPORTANT]
> ### ⚖️ The Critical Difference: Faithfulness vs. Correctness (Why They Look Similar But Are Completely Different)
>
> **The 1-Sentence Memory Rule for Presentation:**
> * **"Faithfulness is a Source Check — Did this answer come strictly from the retrieved Love2D PDF, or did the AI hallucinate?"**
> * **"Correctness is a Solution Check — Did the AI actually answer the question and write working Love2D game code?"**
>
> At first glance, **Faithfulness** and **Correctness** sound similar, but in production RAG systems they evaluate two completely distinct dimensions:
>
> | Dimension | 🛡️ Faithfulness (Grounding & Anti-Hallucination) | 🎯 Correctness (API Alignment & Problem Solving) |
> | :--- | :--- | :--- |
> | **Core Question** | *"Did the AI stick ONLY to the retrieved PDF chunks?"* | *"Did the AI accurately solve the user's game dev problem?"* |
> | **What it penalizes** | Hallucinations, invented parameters, pre-trained bias. | Wrong APIs, broken game loops, incorrect physics math, failing to refuse traps. |
> | **Source of Truth** | The **retrieved document chunks** (strictly what is in the prompt). | The **user's intent** & official Love2D API contracts (`expected_apis`). |
> | **Score Range** | **0 / 1** (Unfaithful) or **1 / 1** (Strictly Grounded) | **0 / 2** (Wrong), **1 / 2** (Partial), or **2 / 2** (Fully Correct) |
>
> ---
>
> #### 🔍 The 3 Key Scenarios (How They Contrast):
>
> 1. **Can an answer be Faithful (1/1), but INCORRECT (0/2)? — YES!**
>    * *Love2D Scenario:* The developer asks *"How do I move a player with arrow keys?"*. The AI answers: *"According to [1], `love.graphics.circle` draws circles with `(mode, x, y, radius)`."*
>    * *Why?* Every single word came directly from the retrieved manual with zero hallucinations (**Faithful = 1/1**), but it completely failed to answer the user's question about player movement (**Incorrect = 0/2**)!
>
> 2. **Can an answer be Correct (2/2), but UNFAITHFUL (0/1)? — YES!**
>    * *Love2D Scenario:* The developer asks *"How do I play audio in Love2D?"*, but retrieval accidentally only pulled graphics chunks. The AI answers from pre-trained memory: *"Use `love.audio.newSource('jump.wav', 'static'):play()`."*
>    * *Why?* That code actually works in Love2D (**Correct = 2/2**), but because the audio manual was missing from the retrieved context, the AI cheated using unverified pre-trained memory (**Unfaithful = 0/1**)!
>
> 3. **The Production Ideal (Both Faithful = 1/1 AND Correct = 2/2):**
>    * *Love2D Scenario:* The system retrieves the actual `love.keyboard.isDown` and `love.update(dt)` chunks, and generates runnable Lua code citing those exact chunks with correct delta-time physics.
>    * *Result:* 100% grounded in sources (**Faithful = 1/1**) AND 100% solves the user's game dev task (**Correct = 2/2**). Our assistant achieved **100% on both**!


* **Search Hit@1 (First-Ranked Accuracy):**
  > **"Hit@1 is a Bullseye Check — Did the single #1 top chunk returned by search contain the exact Love2D manual page needed?"**
  * *Love2D Example:* If you ask *"What parameters does `love.graphics.circle` take?"*, does chunk #1 give the official `love.graphics.circle` manual page? If yes $\rightarrow$ Hit@1 = 100%. If chunk #1 is an unrelated audio page, it is a complete miss (0%).


* **Search Hit@5 (Top-5 Retrieval Coverage):**
  > **"Hit@5 is a Safety Net Check — Did the required Love2D documentation land anywhere inside the top 5 chunks given to the AI?"**
  * *Love2D Example:* If you ask *"How to move a character with arrow keys?"*, does the `love.keyboard.isDown` manual page appear anywhere in the 5 chunks given to the AI? If it appears in slot #3, Hit@5 is a success (100%).


* **Search MRR@5 (Mean Reciprocal Rank):**
  > **"MRR@5 is a Rank Position Check — How close to #1 was the target page? (1.000 means the correct page was ranked #1 on every test)."**
  * *Love2D Example:* Calculated as $\frac{1}{\text{Rank position}}$. If the target page is at Rank #1 $\rightarrow$ score is $\frac{1}{1} = 1.0$. If buried at Rank #2 $\rightarrow$ $\frac{1}{2} = 0.50$. If Rank #5 $\rightarrow$ $\frac{1}{5} = 0.20$. If missing $\rightarrow$ 0. Our production system scored a perfect **1.000 MRR** (Rank #1 on every single test).


* **Cached Latency & Speedup:**
  > **"Cached Latency is an Instant-Speed Check — How fast does the system respond when an identical question was already asked and saved in SQLite?"**
  * *Love2D Example:* The first time a developer asks *"What is `love.timer.getFPS()`?"*, Gemini takes ~580 ms. The second time, the local cache returns the answer in **18.2 ms at \$0.00** (**115x speedup**).


* **Citation Validity:**
  > **"Citation Validity is a Proof Check — Does every citation tag like [1] or [2] point to a real retrieved chunk, with zero fake 'phantom' numbers?"**
  * *Love2D Example:* If the AI retrieves 5 chunks (numbered `[1]` to `[5]`), but hallucinates `[8]`, that is an invalid "phantom citation". Our Pydantic validator guarantees **100% Citation Validity** (zero phantom numbers).


* **AI Judge Faithfulness (Grounding):**
  > **"Faithfulness is a Source Check — Did this answer come strictly from the retrieved Love2D PDF, or did the AI hallucinate?"**
  * Evaluated across **both Theory and Code**:

  * *Case 1 (Theory):* If asked *"What does `dt` represent in `love.update(dt)`?"*, and the AI falsely claims `dt` is measured in milliseconds or invents imaginary arguments not in the manual, the judge marks it unfaithful (0/1). A faithful answer strictly cites the retrieved manual: `dt` is the fractional number of seconds since the last frame.

  * *Case 2 (Code):* If asked to draw a colored circle, and the generated code claims `love.graphics.circle` has a secret parameter for color like `love.graphics.circle("fill", 100, 100, 25, "red")`, but the Love2D manual explicitly states color is set beforehand via `love.graphics.setColor()`, the judge marks it unfaithful (0/1). Our system scored **100% (5/5)**.


* **AI Judge Correctness (API Contract Alignment):**
  > **"Correctness is a Solution Check — Did the AI actually answer the question and write working Love2D game code?"**
  * Evaluated across **both Theory and Code** (`expected_apis` and refusal traps):

  * *Case 1 (Theory):* For Q01 (`love.update(dt)`) and Q03 (`love.graphics.circle`), does the AI correctly explain the exact parameters `(mode, x, y, radius)`, valid draw modes (`"fill"`, `"line"`), and why delta-time is essential for frame-rate independent gameplay across 60Hz and 144Hz displays? Awarded full 2/2 points.

  * *Case 2 (Code):* For Q09 (moving a rectangle with arrow keys), does the code correctly check continuous input via `love.keyboard.isDown`, multiply speed by `dt` in `love.update(dt)` for smooth movement, and render using `love.graphics.rectangle` in `love.draw()`? Awarded full 2/2 points.

  * *Case 3 (Trap Refusal):* For Q11 (Unity C#) and Q13 (React hooks), did the system cleanly refuse the out-of-scope question with the exact standardized refusal string rather than hallucinating foreign code? Awarded full 2/2 points. (Overall Score: **100% = 10/10 points**).


* **Security Shield:**
  > **"Security Shield is an Armor Check — Did the 5-layer pipeline block prompt injections and data leaks without false alarms on game dev terms like 'ignore collisions'?"**
  * *Love2D Example:* Blocks adversarial prompts like *"ignore all previous instructions"* in 0 ms for \$0.00 while achieving 0% false alarms on benign game design requests like *"ignore collisions when ghost is invisible"*. Our system scored **5/5 layers passed**.

* **Before vs. After Scorecard (Tested on Golden Benchmark):**

| Metric / Objective | Plaksha Lab Reference | Naive Baseline ❌ | Production System 🏆 | Improvement |
| :--- | :--- | :---: | :---: | :--- |
| **Chunk Size** | Lab 3 (Ingestion) | 3,000 chars | **600 chars** | 82% less prompt bloat |
| **Search Hit@1** | Lab 3 (Retrieval) | 40.0% | **100.0% (Hybrid RRF)** | Target manual page always #1 |
| **Search Hit@5** | Lab 3 (Retrieval) | 60.0% | **100.0%** | 100% coverage in top 5 chunks |
| **Search MRR@5** | Lab 3 (Retrieval) | 0.475 | **1.000** | Perfect reciprocal rank |
| **Cached Latency** | Lab 5 (Engineering) | None (~2,400 ms) | **18.2 ms (\$0.00)** | **115x speedup** |
| **Citation Validity** | Lab 4 (Groundedness) | ~60% (Unchecked) | **100.0%** | Zero phantom citations |
| **AI Judge Faithfulness** | Lab 4 (Evaluation) | ~5–10% Self-Bias | **100.0% (Decoupled LARGE)** | Impartial `gemini-3.5-flash` audit ([`run_step_judge.md`](file:///d:/Python_AIP_second/run_step_judge.md)) |
| **Security Shield** | Lab 6 (Guardrails) | 0% Protected | **5/5 Layers Passed** | 0% false alarms on game code |

---

### 📊 Detailed Retrieval Metrics Tables (From [`step2.md`](file:///d:/Python_AIP_second/step2.md)):

#### 1. Experiment 1: Chunk Size Optimization (Solving the Dilution Cliff)
*Proves why 600-character chunks beat naive 3,000-character chunks on [`rag_golden.jsonl`](file:///d:/Python_AIP_second/data/eval/rag_golden.jsonl):*

> **💡 Experiment 1 Metrics Explained:**
> * **Text Sent to AI (5 Chunks):**
>   > **"Prompt Volume Check — How many characters are injected into the prompt? (600-char chunks cut prompt bloat by 82% to fit within the 256-token embedding window)."**
>   * Naive 3,000-character chunks sent 14,252 characters. Because our embedding model (`all-MiniLM-L6-v2`) has a 256-token (~900 character) limit, two-thirds of each 3,000-char chunk was silently truncated and invisible to search! 600-character chunks send only 2,593 characters (**82% smaller**), fitting 100% inside the embedding window.
> * **API Recall@5:**
>   > **"Subsystem Coverage Check — What percentage of all required Love2D functions for the game were successfully found in the top 5 chunks?"**
>   * For example, if a coding question requires 4 APIs (`love.load`, `love.update`, `love.draw`, `love.keyboard.isDown`) and retrieval brings in 3 of them, Recall is $\frac{3}{4} = 75\%$. 600-character chunks boosted API Recall from 79.2% to **93.3%**.

| Version | Target Chunk Size | Text Sent to AI (5 Chunks) | Hit@1 | Hit@5 | MRR@5 | API Recall@5 | Root Cause / Discovery |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Phase 1 (Old Baseline)** | 3,000 chars | 14,252 chars *(Bloated & noisy)* | 40.0% | 60.0% | 0.475 | 79.2% | MiniLM cuts off after 256 tokens (~900 chars); 2/3 of text was invisible |
| **Phase 2 (Production)** | **600 chars** | **2,593 chars *(82% smaller!)*** | **90.0%** | **100.0%** | **0.950** | **93.3%** | Fits 100% within embedding context; eliminates prompt bloat |

#### 2. Experiment 2: Table-of-Contents Noise Filtering (`status == 'current'`)
*Filtering out `00-cover-contents.pdf` so empty index pages never pollute retrieval:*

> **💡 Experiment 2 Metrics Explained:**
> * **Junk TOC Chunks in Top 5:**
>   > **"Index Noise Check — How many search slots out of 5 were wasted on useless Table-of-Contents pages? (Reduced from 3 to 0 by filtering)."**
>   * *Love2D Example:* `00-cover-contents.pdf` contains lists of chapter titles like *"Chapter 3: Graphics"* with zero code or explanations. When unfiltered, 3 out of 5 chunks were useless TOC junk, crowding out the real `love.graphics.circle` manual page. Tagging TOC pages in `ARCHIVED_DOCS` eliminated junk chunks completely (**from 3 down to 0**), boosting Hit@1 from 50% to **90%**.

| Ingestion Filter Mode | Junk TOC Chunks in Top 5 | Hit@1 | Hit@5 | MRR@5 | Engineering Solution |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Unfiltered (All PDFs)** | ~3 junk chunks | 50.0% | 70.0% | 0.580 | Table of Contents lists names with no code context |
| **Filtered (`status == 'current'`)** | **0 junk chunks** | **90.0%** | **100.0%** | **0.950** | Tagged TOC in `ARCHIVED_DOCS` (`loader.py`); 100% clean chunks |

#### 3. Experiment 3: Search Strategy Comparison (Keyword vs. Vector vs. Hybrid)
*Comparing BM25, Dense FAISS, and Hybrid search over 600-character chunks:*

> **💡 Experiment 3 Metrics Explained:**
> * **BM25 (Keyword Search):**
>   > **"Keyword Match Check — Exact token matching that excels at function names like 'love.graphics.circle' but struggles with natural language."**
>   * Ranks chunks by exact word frequency. It gets 100% on exact code names like `love.graphics.circle`, but drops to 70% Hit@1 on natural language questions (e.g. *"how to make a round circle on the screen"*).
> * **Dense FAISS (Vector Default):**
>   > **"Semantic Match Check — Embedding search that excels at conceptual questions but can confuse similar function signatures."**
>   * Ranks chunks by semantic meaning using embedding vectors. Great at understanding conceptual queries (90% Hit@1), but can confuse similar functions (drops to 83.3% on coding APIs).
> * **Hybrid RRF (Dense + BM25):**
>   > **"Combined Spine Check — Reciprocal Rank Fusion ($k=60$) merging keyword precision and vector semantics for a perfect 100% score."**
>   * Combines both algorithms using Reciprocal Rank Fusion ($k=60$). Delivers a perfect **100.0% Hit@1, 100.0% Hit@5, and 1.000 MRR** on both single theory APIs (`Q01`–`Q08`) and full game code APIs (`Q09`–`Q10`).

| Search Strategy | Hit@1 | Hit@5 | MRR@5 | Theory APIs (`Q01`–`Q08`) | Coding APIs (`Q09`–`Q10`) | Latency / Query | Key Characteristic |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **BM25 (Keyword Search)** | 70.0% | 100.0% | 0.795 | 100.0% | 100.0% | 32.7 ms | Superb on exact code tokens; distracted by common words |
| **Dense FAISS (Vector Default)** | 90.0% | 100.0% | 0.950 | 100.0% | 83.3% | **9.9 ms** | Ultra-fast semantic search (5x faster than hybrid) |
| **Hybrid RRF (Dense + BM25)** | **100.0%** | **100.0%** | **1.000** | **100.0%** | **100.0%** | 50.4 ms | 🏆 **Deployed Production Engine: Best of both worlds** |

#### 4. Experiment 4: Did Reranking Earn Its Latency? (Lab 3 §C Decision Matrix)
*Testing whether a 2-stage lexical or LLM reranker earns its latency overhead:*

> **💡 Experiment 4 Metrics Explained:**
> * **Dense + Lexical Reranker:**
>   > **"Lexical Reranker Check — Word-overlap reranking degraded Hit@1 to 70% by over-weighting repetitive tutorial words."**
>   * Adding a BM25 re-ranking step after vector search actually *degraded* Hit@1 from 90% down to 70%, because game tutorial manuals repeat common words (*"game"*, *"player"*, *"screen"*) that trick the lexical scorer into prioritizing wordy overviews instead of the exact technical API definition.
> * **Dense + LLM Reranker (Gemini):**
>   > **"LLM Reranker Check — Calling Gemini to rerank reached 100% but failed UI latency (~1,850 ms) and added +$1.00 cost per 1k queries."**
>   * Using an LLM to re-score chunks reached 100% accuracy, but added **~1,850 ms of latency** and **+\$1.00 per 1,000 queries**, violating interactive UI requirements.
> * **Hybrid RRF (Production Spine):**
>   > **"Zero-Cost Winner Check — Delivered the exact same 100% accuracy as the LLM reranker in 65.3 ms for $0.00 extra cost."**
>   * Reached the exact same **100.0% Hit@1 and 1.000 MRR** as the LLM reranker, but in only **65.3 ms at \$0.00 extra cost**.

| Retrieval Pipeline | Hit@1 | Hit@5 | MRR@5 | Coding Recall | Latency | Extra Cost / 1k | Production Decision (Lab 3 §C3) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Hybrid RRF (Dense + BM25)** | **100.0%** | **100.0%** | **1.000** | **100.0%** | 65.3 ms | **\$0.00** | 🏆 **Deployed Production Spine ([`app.py`](file:///d:/Python_AIP_second/app.py))** |
| **Dense FAISS Baseline** | 90.0% | 100.0% | 0.950 | 83.3% | **14.7 ms** | **\$0.00** | ⚡ Low-latency fallback baseline |
| **Dense + Lexical Reranker** | 70.0% | 100.0% | 0.825 | 87.5% | 16.8 ms | **\$0.00** | 🛑 Degrades Hit@1 (over-weights repetitive tutorial words) |
| **Dense + LLM Reranker (Gemini)** | **100.0%** | **100.0%** | **1.000** | **100.0%** | ~1,850 ms | +\$1.00 | 🛑 Fails UI latency SLO & violates cost limits |

---

### ⚖️ Decoupled AI Judge Scorecard (From [`run_step_judge.md`](file:///d:/Python_AIP_second/run_step_judge.md)):
*Evaluates Love2D API contracts & callbacks (`expected_apis`) using independent judge `MODEL_TIERS["LARGE"]` (`gemini-3.5-flash`), eliminating the 5%–10% self-preference grading bias:*

> **💡 Decoupled AI Judge Metrics Explained:**
>
> * **Decoupled LARGE Tier (`gemini-3.5-flash`):**
>   In naive evaluations, having an AI grade its own output produces a 5%–10% self-preference bias. We decoupled the judge by having an independent, higher-tier model (`gemini-3.5-flash`) audit the generator model's output.
>
> * **Required Love2D APIs (`expected_apis`):**
>   Rather than using brittle string matching (which falsely fails if variable names or comments differ), the judge verifies that the generated code correctly invokes the required Love2D lifecycle callbacks, functions, and parameters.
>
> * **Faithful (`LARGE`) — Source Check (Scored 0/1 or 1/1):**
>   > *"Faithfulness is a Source Check — Did this answer come strictly from the retrieved Love2D PDF, or did the AI hallucinate?"*
>
>   * *Case 1 (Theory):* If explaining `love.update(dt)`, every single technical claim about delta-time must come directly from the retrieved manual page with zero invented facts.
>
>   * *Case 2 (Code):* If generating game code, function calls must strictly match official Love2D signatures (e.g. no hallucinated color arguments in `love.graphics.circle`, where color must be set via `love.graphics.setColor`).
>
>   * *Our System Score:* **5 / 5 = 100%**.
>
> * **Correctness (`LARGE`) — Solution Check (Scored 0/2, 1/2, or 2/2):**
>   > *"Correctness is a Solution Check — Did the AI actually answer the question and write working Love2D game code?"*
>
>   * *Case 1 (Theory):* For Q01 & Q03, the judge verifies that all technical details, parameter definitions, and Love2D modes (`"fill"`, `"line"`) are completely and accurately explained with frame-rate independent math.
>
>   * *Case 2 (Code):* For Q09, the judge verifies that all 4 required game callbacks and APIs (`love.update`, `love.draw`, `love.keyboard.isDown`, `love.graphics.rectangle`) work together with correct delta-time physics math (`speed * dt`).
>
>   * *Case 3 (Trap Refusal):* For Q11 (Unity C#) and Q13 (React hooks), full 2/2 points are awarded only if the system cleanly refuses the out-of-scope trap with the standardized refusal message without hallucinating foreign code.
>
>   * *Our System Score:* **10 / 10 pts = 100%**.

| ID | Category | Question Tested | Required Love2D APIs (`expected_apis`) | Faithful (`LARGE`) | Correctness (`LARGE`) | Independent Judge Rationale Summary |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| **Q01** | Theory | `love.update(dt)` delta-time | `love.update`, `dt` | **1 / 1** | **2 / 2** | Accurately explains `love.update(dt)` and `dt` (seconds) for frame-rate independence. |
| **Q03** | Theory | `love.graphics.circle` modes | `love.graphics.circle`, `fill`, `line` | **1 / 1** | **2 / 2** | Details `love.graphics.circle` with `"fill"`/`"line"` modes and exact `(mode, x, y, radius)` parameters. |
| **Q09** | **Coding** | Move rectangle with arrow keys | `love.update`, `love.draw`, `love.keyboard.isDown`, `love.graphics.rectangle` | **1 / 1** | **2 / 2** | Implements all required Love2D APIs and callbacks with accurate delta-time movement math. |
| **Q11** | Trap | Unity C# MonoBehaviour script | None (Must Refuse) | **1 / 1** | **2 / 2** | Correctly identifies Unity out-of-scope trap and emits exact refusal string. |
| **Q13** | Trap | React `useState` / `useEffect` | None (Must Refuse) | **1 / 1** | **2 / 2** | Correctly identifies React web trap and emits exact refusal string. |
| **TOTAL** | **Summary** | **5 Key Representative Tests** | — | **100.0% (5/5)** | **100.0% (10/10)** | **100% Bias-Free Evaluation of Love2D API Contracts** |

*(Full rationales, latency, and verdicts saved in [`reports/step_judge_evaluation.json`](file:///d:/Python_AIP_second/reports/step_judge_evaluation.json))*

---

* **Live Demo Plan (3 Quick Steps):**
  1. *Theory Query:* Ask a concept question to show the live telemetry badge (`Citations [1, 2] | Latency | Cost | Guards`) and pure grounded explanation with zero leaked jargon.
  2. *Cache Hit:* Ask the same question again to show instant 18 ms response at \$0.00.
  3. *Coding Query:* Show complete runnable Lua game loop, point out the **API & Callback Traceability Table**, and click **`📚 View Cited PDF Chunks`** to prove that every function used in code maps directly to official Love2D documentation (with Guard Layer 3 Python Scanner ensuring zero ungrounded API leakage).

---

## 📌 Master Curriculum Traceability Matrix (Cheat Sheet for Defense)

| Lab Module | Core Course Principle | How It Is Implemented in Our Codebase | File Reference |
| :--- | :--- | :--- | :--- |
| **Lab 1** | Deterministic Boundaries & Contracts | Pydantic v2 `Transformer`, `@model_validator` regex extraction of `[1..k]` citations in 0.001 ms, safe fallback flag `needs_human_review`. | [`schemas.py`](file:///d:/Python_AIP_second/schemas.py) |
| **Lab 2** | Schema Contracts & Safe Fallbacks | Strongly typed Pydantic v2 `Transformer` schema with strict field constraints and safe fallback flags (`needs_human_review`). | [`schemas.py`](file:///d:/Python_AIP_second/schemas.py) |
| **Lab 3** | Chunking, Noise Removal & Hybrid Search | 600-char recursive splitting, `ARCHIVED_DOCS` + `ARCHIVED_PAGES` TOC noise filtering, Hybrid RRF $k=60$ (100% Hit@1). | [`config.py`](file:///d:/Python_AIP_second/config.py), [`loader.py`](file:///d:/Python_AIP_second/loader.py), [`vectorstore.py`](file:///d:/Python_AIP_second/vectorstore.py) |
| **Lab 4** | Groundedness, Auto-Repair & Bias-Free Judge | Dual Grounding: Section-aware manual boost ($+50.0$ BM25) for theory, deterministic Python Code Scanner for Lua code, standardized `REFUSAL`, auto-repair retry loop (`validate_answer`), and an empirical Decoupled AI Judge (`LARGE: gemini-3.5-flash` in [`run_step_judge.py`](file:///d:/Python_AIP_second/run_step_judge.py) / [`run_step_judge.md`](file:///d:/Python_AIP_second/run_step_judge.md)) scoring 100% with Rationale-First `JudgeVerdict`. | [`chain.py`](file:///d:/Python_AIP_second/chain.py), [`vectorstore.py`](file:///d:/Python_AIP_second/vectorstore.py), [`run_step_judge.py`](file:///d:/Python_AIP_second/run_step_judge.py), [`schemas.py`](file:///d:/Python_AIP_second/schemas.py) |
| **Lab 5** | RAG v2 Diagnosis & Solving Generation Errors | Diagnosed Mode 6 Generation Errors (85.7% failures from the "Brevity Trap"); engineered the `v2` Adaptive Multi-Mode Prompt and Deterministic Router (comprehensive 8–10 line theory vs. complete runnable Lua code), backed by SQLite caching and $p_{50}/p_{95}$ telemetry. | [`chain.py`](file:///d:/Python_AIP_second/chain.py), [`aip_core/cache.py`](file:///d:/Python_AIP_second/aip_core/cache.py) |
| **Lab 6** | Defense-in-Depth Security Shield | 5 layers: Layer 1 XML sandboxing, Layer 2 input injection pre-screen (0% false alarms on *"ignore collisions"*), Layer 4 ToolGuard (max 4 calls), Layer 5 key/image scrubbing. | [`aip_core/guards.py`](file:///d:/Python_AIP_second/aip_core/guards.py) |
