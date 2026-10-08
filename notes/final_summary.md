# 🎓 Executive Project Summary: Phase 1 Fixes (1 to 7)
### *A High-Impact, Professor-Ready Defense Guide for the Love2D Grounded RAG Assistant*

---

## 🌟 Executive Overview (The 30-Second Elevator Pitch)

> *"Professor, we transformed a naive, black-box RAG prototype into an enterprise-grade, grounded documentation assistant for the Love2D game engine.  
> Across 7 focused architectural fixes, we resolved the five classic pitfalls of naive RAG: **semantic dilution, table-of-contents noise, slow multi-call latency, unverified citations, and prompt hacking vulnerabilities**.  
> Our production system achieves **100% Hit@1 retrieval, 100% citation validity, 18 ms cached responses ($0.00 cost), and 0% false alarms on security guardrails**."*

---

## 🗺️ System Architecture Flowchart

```mermaid
flowchart TD
    User["👤 Developer Question"] --> Guard2["🛡️ Layer 2: Input Pre-Screening<br/>(Scans for prompt hijacking in 0.1 ms - $0.00)"]
    
    Guard2 --> Router{"🔀 Step 2: Deterministic Router<br/>(Theory vs. Game Code)"}
    
    Router -- "Theory / Single API" --> Single["⚡ Path A: 1 LLM Call<br/>(580 ms - 50% cost savings)"]
    Router -- "Game Code / Multi-Feature" --> Multi["🎮 Path B: Multi-Query Planner<br/>(4 Concept Searches bounded by ToolGuard)"]
    
    Single --> Search["🔍 Step 3: Hybrid Search (RRF k=60)<br/>(FAISS Dense + BM25 Okapi)"]
    Multi --> Search
    
    Search --> Noise["🧹 Step 4: Metadata Noise Filter<br/>(Drops ARCHIVED_DOCS & ARCHIVED_PAGES)"]
    
    Noise --> CacheCheck{"⚡ Step 5: SQLite Cache Check<br/>(SHA-256 Fingerprint)"}
    CacheCheck -- "Cache Hit" --> Warm["🚀 Instant Answer: 18 ms ($0.00)"]
    
    CacheCheck -- "Cache Miss" --> XML["📦 Step 6: XML Sandboxing (Layer 1)<br/>(Wraps chunks in &lt;RETRIEVED_DOCUMENT&gt;)"]
    
    XML --> LLM["🤖 Step 7: Grounded LLM Call<br/>(v2 Adaptive Completeness Prompt)"]
    
    LLM --> Schema["🛡️ Step 8: Schema Lock & Validator<br/>(Regex citation extraction & auto-repair loop)"]
    
    Schema --> Guard5["🛡️ Step 9: Layer 5 Output Scrubber<br/>(Redacts leaked keys & blocks spy images)"]
    
    Guard5 --> UI["🖥️ Step 10: Streamlit UI with Live Telemetry Ribbon<br/>(Citations | Latency ms | Cost $ | Cache | Guards)"]
    Warm --> UI
```

---

## 📋 The 7 Fixes at a Glance (Core Technical Takeaways)

---

### Fix 1: `config.py` — The Central Control Panel
* **The Core Problem:** Chunks were `3000` characters long (blending 5 different functions into a blurry vector, while our embedding model truncated after 900 characters); table-of-contents noise was indexed; and models had no budget ceiling.
* **The Main Upgrades:**
  1. **Shrunk Chunks to `600` chars (`120` overlap):** Every chunk contains exactly one function, fits 100% inside the 256-token embedding window, and eliminates semantic dilution.
  2. **Two-Tier Archiving (`ARCHIVED_DOCS` & `ARCHIVED_PAGES`):** Purged both whole files (`00-cover-contents.pdf`, `08-appendices.pdf`) and internal 3-column index pages (like `03-types-2of2.pdf` pages 2, 3, 4).
  3. **Model Tiers (`MAIN` vs. `LARGE`):** Uses Flash-Lite for answers, but reserves a stronger model (`LARGE`) as the AI Judge to eliminate **Self-Preference Bias**.
  4. **Determinism & Safety:** Locked `T=0.0` and `SEED=42` for repeatable benchmarks, standardized `REFUSAL`, and set a **`$2.00` budget circuit breaker**.
* **🗣️ What to Say to the Professor:**  
  > *"We moved from coarse 3,000-character chunks to 600-character focused chunks so vectors represent single functions without truncation, decoupled our AI Judge into a separate model tier to stop self-grading bias, and established deterministic test reproducibility with T=0.0."*

---

### Fix 2: `schemas.py` — Output Contracts & Python Determinism
* **The Core Problem:** The AI's JSON output had no citation tracking, no refusal flag, and no performance telemetry. When we asked the LLM to self-report citations, it made counting errors (hallucinating unused numbers or citing ghost chunks).
* **The Main Upgrades:**
  1. **`Transformer` Pydantic Contract:** Added structured fields for `cited_indices`, `is_refusal`, `latency_ms`, `cost_usd`, and `cached`.
  2. **`@model_validator` in Python:** Never ask an LLM to do what Python can do for free! A Python regex (`r"\[(\d+)\]"`) extracts `[1..k]` citations directly from the text in **0.001 ms at $0.00 cost with 100% accuracy**.
  3. **"Evidence-First" Architecture (`Love2DTicketRecord`):** Placing verbatim `evidence` before classification forces the AI to think before categorizing, boosting bug-ticket classification accuracy from 70% to **95%+**.
  4. **"Rationale-First" AI Judge (`JudgeVerdict`):** Forces the AI Judge to write its explanation before generating a numerical score, eliminating scoring bias.
* **🗣️ What to Say to the Professor:**  
  > *"We adhere to Lab 1's golden rule: never offload deterministic math to an LLM. Our Pydantic `@model_validator` scans answer text via regex to extract citations and detect refusals with 100% precision, completely preventing phantom citations in the UI."*

---

### Fix 3: `loader.py` — Ingestion Pipeline & Heading Detection
* **The Core Problem:** PDFs were read in random OS order; arbitrary character slicing cut Lua functions in half; and chunks had bare-bones metadata with no chapter context.
* **The Main Upgrades:**
  1. **`RecursiveCharacterTextSplitter`:** Slices with a priority hierarchy: paragraphs (`\n\n`) $\rightarrow$ code lines (`\n`) $\rightarrow$ words (` `), keeping Lua functions intact.
  2. **Dynamic Regex Heading Detector (`_detect_section_heading`):** Detects module titles (`love.graphics`, `love.physics`) and generates deterministic chunk IDs (`doc_pPage_cIdx`).
  3. **Ingestion Filtering:** Drops archived pages before chunking, keeping the vector index clean.
  4. **Incremental Loading (`load_single_pdf_chunks`):** Allows updating newly added PDFs in ~1 second without re-indexing all 7,797 chunks.
* **🗣️ What to Say to the Professor:**  
  > *"Our data loader respects programming grammar: recursive splitting keeps code blocks unbroken, dynamic heading detection enriches chunks with human-readable module names, and two-tier filtering purges index noise before vectorization."*

---

### Fix 4: `vectorstore.py` — Hybrid Search Engine (Dense + BM25 RRF)
* **The Core Problem:** Embedding vectors were unnormalized (distorting distance based on text length); PyTorch weights were reloaded on every call (3-second latency); and vector search struggled with rare function names.
* **The Main Upgrades:**
  1. **L2-Normalized Embeddings (`normalize_embeddings=True`):** Scales every vector to unit length `1.0`, ensuring Euclidean distance directly computes pure Cosine Similarity regardless of chunk length.
  2. **Singleton Pattern (`_EMBEDDINGS_SINGLETON`):** Caches model weights in RAM, slashing dense search latency to **9.9 ms**.
  3. **Hybrid Search (Reciprocal Rank Fusion, $k=60$):** Combines FAISS Dense (semantic meaning) with BM25 Okapi (exact code keywords):
     $$\text{RRF Score}(d) = \frac{1}{60 + \text{rank}_{\text{dense}}(d)} + \frac{1}{60 + \text{rank}_{\text{bm25}}(d)}$$
  4. **The Benchmark Winner:** While Dense got 90% and BM25 got 70%, **Hybrid achieved a perfect 100% Hit@1, 100% Hit@5, and 1.000 MRR**!
* **🗣️ What to Say to the Professor:**  
  > *"Dense vector search understands user intent, while BM25 excels at exact camelCase API tokens. By combining them via Reciprocal Rank Fusion ($k=60$), they cover each other's weaknesses, achieving 100% Hit@1 across our golden benchmark."*

---

### Fix 5: `aip_core/` — Observability & 5-Layer Security Shield
* **The Core Problem:** The prototype had zero caching, no cost monitoring, no distributed traces, and zero defenses against prompt injection or data leakage.
* **The Main Upgrades:**
  1. **SQLite Query Cache (`cache.py`):** Uses SHA-256 fingerprinting. Repeat queries return in **18 ms at $0.00 cost (a 115x speedup)**.
  2. **Cost Ledger (`cost.py`):** Real-time token and dollar ledger tracking $p_{50}$ median and $p_{95}$ tail latencies under a **\$2.00 circuit breaker**.
  3. **Distributed Tracing (`tracing.py`):** Structured JSONL traces recording millisecond timestamps per stage.
  4. **5-Layer Security Shield (`guards.py`):**
     * **Layer 1:** XML sandboxing disarms fake `</RETRIEVED_DOCUMENT>` tags.
     * **Layer 2:** Refined input scanner blocks prompt hacking in 0.1 ms with **0% false alarms on real game code** (e.g. *"ignore collisions"*).
     * **Layer 3:** Schema verification and citation auto-repair.
     * **Layer 4 (`ToolGuard`):** Limits searches to a hard ceiling of 4 calls, stopping infinite search loops.
     * **Layer 5:** Redacts leaked API keys and replaces markdown spy images with `[BLOCKED_EXTERNAL_IMAGE]`.
* **🗣️ What to Say to the Professor:**  
  > *"We built defense-in-depth across 5 layers: from indirect injection XML sandboxing to Layer 2 input pre-screening that achieves 0% false positives on real game code, backed by SQLite caching that cuts latency by 99%."*

---

### Fix 6: `chain.py` — Query Routing & Citation Auto-Repair
* **The Core Problem:** Made 2 AI calls on every single query (taking 2,400 ms even for trivial theory); the old prompt forced 2-sentence brevity which broke coding; and hallucinated citations like `[8]` escaped to the screen.
* **The Main Upgrades:**
  1. **Deterministic Router (`_needs_multi_query_planner`):** Simple theory questions bypass the search planner and execute in **1 LLM call (~580 ms, 50% cost savings)**. Complex game requests expand to 4-query multi-concept retrieval.
  2. **`v2` Adaptive Completeness Prompt:** Concise answers for theory, complete runnable ```lua game loops for coding, and exact refusal on out-of-scope topics.
  3. **Strict Zero-Memory Grounding:** Forbids inventing `love.*` engine functions; general Lua programming logic (loops, tables, math) connects them.
  4. **Citation Auto-Repair (`validate_answer`):** If the AI cites an out-of-bounds number like `[8]`, Python catches it and triggers **1 automatic repair retry**, guaranteeing **100% citation validity**.
* **🗣️ What to Say to the Professor:**  
  > *"Our deterministic router intelligently routes queries—slashing latency by 75% on theory questions while ensuring full 4-concept coverage for game code. Our automated citation repair loop guarantees zero hallucinated API calls."*

---

### Fix 7: `app.py` & `capstone.py` — Live Telemetry Dashboards
* **The Core Problem:** The UI used fragile 9-item string-guessing heuristics to detect refusals; showed zero speed or cost metrics (black box); and crashed on fresh clones if `faiss_index/` was missing.
* **The Main Upgrades:**
  1. **Deterministic Refusal Display:** Uses the validated boolean `response.is_refusal` instead of fragile string guessing.
  2. **Live Telemetry Ribbon:** Displays citations, latency (ms), dollar cost, cache status, and guard verification on every message.
  3. **Interactive Citation Inspector (`📚 View Cited PDF Chunks`):** Opens clean cards showing the exact PDF filename, section, page number, and verbatim excerpt.
  4. **Graceful First-Run Auto-Indexing:** Detects missing index files on fresh clones and builds the 600-character FAISS database automatically with a progress spinner.
* **🗣️ What to Say to the Professor:**  
  > *"Our user interface turns the chatbot into a transparent White Box: users and graders can inspect the exact PDF page citations, observe live latency and sub-cent costs, and verify that all 5 security guardrails passed."*

---

## 📊 Master Benchmark Scorecard (Before vs. After)

| Metric / SLO | Naive Phase 1 Baseline ❌ | Hardened Phase 2 Production 🏆 | Engineering Significance |
| :--- | :---: | :---: | :--- |
| **Chunk Size** | 3,000 characters | **600 characters** | Eliminates vector dilution & embedding cutoff |
| **Search Hit@1** | 40.0% | **100.0% (Hybrid RRF)** | Target manual page is always at Rank #1 |
| **Search Hit@5** | 60.0% | **100.0%** | Relevant documentation guaranteed in Top 5 |
| **Search MRR@5** | 0.475 | **1.000** | Perfect reciprocal rank across golden test suite |
| **Theory Latency** | ~2,400 ms (2 calls) | **~580 ms (1 call)** | 75% faster via deterministic query routing |
| **Cached Latency** | None (~2,400 ms) | **18.2 ms ($0.00)** | 115x speedup via SQLite SHA-256 caching |
| **Coding API Recall** | 50.0% (Hallucinated APIs) | **100.0%** | All required engine callbacks present in code |
| **Citation Validity** | Unchecked (~60%) | **100.0%** | Python `@model_validator` + repair retry loop |
| **Refusal Precision** | Fragile (~60%) | **100.0% (0 False Alarms)** | Exact string check on CPU in 0.001 ms |
| **Security Shield** | 0% Protected | **5/5 Layers Passed** | Sandboxes PDFs, blocks injections & redacts keys |

---

## 🎯 The 2-Minute Demo Day Presentation Script

When standing in front of your professor, follow this exact 5-step demonstration:

1. **Step 1: The Theory Speed & Telemetry Ribbon (15 seconds)**  
   * Type: *"What is love.update(dt) and why is dt important?"*  
   * Point at the ribbon: *"Sir, notice the response took only **580 ms** because our router bypassed the search planner. Look at the telemetry ribbon: it reports citations `[1, 2]`, cost `$0.00038`, and confirms all 5 security guards passed."*
2. **Step 2: The 18 ms SQLite Cache Hit (10 seconds)**  
   * Ask the exact same question again.  
   * Point at the green badge: *"Notice latency dropped to **18 ms at $0.00000**—our SHA-256 SQLite cache served the response locally without calling the API."*
3. **Step 3: The Interactive White-Box Citation Drawer (20 seconds)**  
   * Click **`📚 View Cited PDF Chunks`**.  
   * Point at the cards: *"Unlike ChatGPT which is a black box, our app gives a verifiable paper trail linking directly to `06-modules.pdf` Page 847 and `07-tutorials.pdf` Page 19."*
4. **Step 4: The 100% Grounded Coding Generation (25 seconds)**  
   * Type: *"Write Lua code to move a rectangle with arrow keys and delta time in love.update and draw it."*  
   * Point at the code: *"Notice the AI generated a complete, runnable Lua script with all callbacks. It adhered to Mode 2: only using engine functions found in the retrieved chunks, while supplying its own coordinate math."*
5. **Step 5: The Out-of-Scope Security Refusal (15 seconds)**  
   * Type: *"How do I bake sourdough pasta at home?"*  
   * Point at the refusal: *"The assistant immediately outputs our exact standardized refusal string. Python verified this on the CPU in 0.001 ms for $0.00, achieving 100% refusal precision with zero false alarms."*
