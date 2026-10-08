# Phase 1 — Fix 4: Upgrading `vectorstore.py`

**File Modified:** [`vectorstore.py`](file:///d:/Python_AIP_second/vectorstore.py)

---

## 1. Big Picture: Why Did We Change `vectorstore.py`?

`vectorstore.py` is the **search engine** of your Love2D project. It takes the 600-character recursive chunks from `loader.py`, turns them into 384-number vectors using `all-MiniLM-L6-v2`, saves them inside `faiss_index/`, and searches them whenever a user asks a question.

Following the exact empirical conclusion of **Lab 3 (`labs/lab3/report.md`)** in `Plaksha_AI_in_Practise_modified`:
1. **Default Production Retriever = Pure Dense Vector Search (`mode="dense"`):**
   - In Lab 3, once chunks were sized properly (`600` chars with `120` overlap using `recursive` splitting), **Pure Dense Search (`mode="dense"`) was the overall winner** (`nDCG@10 = 0.8527`, `latency = 1.41 ms`, `$0` cost), beating both BM25 (`0.701`) and Hybrid RRF (`0.8180`).
   - Why did Pure Dense beat Hybrid in Lab 3? Because Dense vectors capture conceptual meaning cleanly, whereas BM25 sometimes pulls up distractor chunks that happen to repeat common words, dragging down the Hybrid average!
2. **L2-Normalized Embeddings (`normalize_embeddings=True`):**
   - Ensures every 384-number vector has a unit length of `1.0`, so FAISS similarity search computes pure Cosine Similarity.
3. **Metadata Filtering (`status == "current"`):**
   - Automatically filters out `00-cover-contents.pdf` (Table-of-Contents noise) and any `ARCHIVED` trap documents both when building `faiss_index/` and when searching.
4. **Optional `bm25` and `hybrid` Modes Kept for Step 3 Sweeps:**
   - So in Phase 2 (Step 3), our evaluation script can test `dense` vs. `bm25` vs. `hybrid` side-by-side and prove with numbers why `dense` is our default!

---

## 2. How Our Default `dense` Search Works (In Plain English)

```text
  USER QUESTION: "How do I draw a rectangle in Love2D?"
                         |
                         v
+-------------------------------------------------------------------------+
| STEP 1: TURN QUESTION INTO A 384-NUMBER UNIT VECTOR (Length = 1.0)      |
|   - Uses `all-MiniLM-L6-v2` with `normalize_embeddings=True`            |
+-------------------------------------------------------------------------+
                         |
                         v
+-------------------------------------------------------------------------+
| STEP 2: PURE DENSE SEARCH IN FAISS (`mode="dense"` — Lab 3 Winner)      |
|   - Compares the question vector against all 600-char recursive chunks  |
|   - Filters for `status == "current"` (skips 00-cover-contents noise)   |
|   - Returns Top 5 matching chunks in ~1.5 milliseconds at $0 cost!      |
+-------------------------------------------------------------------------+
```

---

## 3. Before vs. After Comparison

```text
+----------------------------------------+----------------------------------------+
|          OLD vectorstore.py            |          NEW vectorstore.py            |
+----------------------------------------+----------------------------------------+
| Reloaded `HuggingFaceEmbeddings` every | Caches a single `HuggingFaceEmbeddings`|
| time `get_embeddings()` was called     | in memory (`_EMBEDDINGS_SINGLETON`)    |
| without `normalize_embeddings=True`    | with `normalize_embeddings=True`       |
+----------------------------------------+----------------------------------------+
| No metadata filtering (`status`)       | Enforces `status == "current"` both    |
|                                        | when building `faiss_index/` and when  |
|                                        | searching                              |
+----------------------------------------+----------------------------------------+
| No way to compare Dense vs BM25 vs     | Default is **`mode="dense"`** (Lab 3   |
| Hybrid in Lab 3                        | winner!), and also supports `bm25` and |
|                                        | `hybrid` for the Step 3 sweep table    |
+----------------------------------------+----------------------------------------+
```

---

## 4. Plain-English Explanation of Every Change in `vectorstore.py`

### Change 1: L2-Normalized Embeddings (`normalize_embeddings=True`)
* **What we changed:**
  ```python
  _EMBEDDINGS_SINGLETON = HuggingFaceEmbeddings(
      model_name=EMBEDDING_MODEL,
      encode_kwargs={"normalize_embeddings": True},
  )
  ```
* **What this means in plain English:**
  - Every chunk is turned into an arrow (vector) pointing in a 384-dimensional space.
  - **`normalize_embeddings=True`** scales every arrow so its length is exactly **`1.0`**.
  - When all arrows have length `1.0`, comparing two arrows only checks the **angle (direction)** between them (**Cosine Similarity**), so a long paragraph and a short sentence about the exact same Love2D function point in the exact same spot!

### Change 2: Metadata Filter (`only_current=True`) in `get_vectorstore()`
* **What we changed:**
  - Before building `faiss_index/`, `get_vectorstore()` filters `chunks` to keep only `chunk.metadata.get("status", "current") == "current"`.
  - That guarantees `00-cover-contents.pdf` (Table of Contents noise) is never stored inside your live `faiss_index/`.

### Change 3: Default `mode="dense"` in `Love2DRetriever` and `get_retriever()`
* **What we changed:**
  ```python
  def get_retriever(
      vectorstore: FAISS,
      k: int = RETRIEVER_K,
      mode: str = "dense",
  ):
  ```
* **Why `mode="dense"` is the default:**
  - Matches the Lab 3 Report (`labs/lab3/report.md`) winning architecture: **Breadcrumb-enriched chunks + Pure Dense retrieval + `status: current` metadata filtering**, with no slow reranker in live interactive chat.
  - We also kept `mode="bm25"` and `mode="hybrid"` inside `Love2DRetriever` (initializing BM25 only when those modes are requested) so our Step 3 experiment script can benchmark all three methods cleanly.
