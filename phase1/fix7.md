# Phase 1 — Fix 7: Upgrading `app.py` (Streamlit UI) & `capstone.py` (CLI)

**Files Modified:**
- [`app.py`](file:///d:/Python_AIP_second/app.py)
- [`capstone.py`](file:///d:/Python_AIP_second/capstone.py)

---

## 1. Big Picture: Why Did We Change `app.py` and `capstone.py`?

`app.py` (your Streamlit web app) and `capstone.py` (your terminal app) are the **front doors** that users interact with.

In our old `app.py` and `capstone.py`:
1. Both files had a long `negative_cues` list trying to guess whether the AI refused a question.
2. Neither file showed the new engineering telemetry from our upgraded pipeline: which chunks `[1, 2]` were cited, how many milliseconds the response took, how much it cost in dollars, whether it came from the SQLite cache (`0 ms`, `$0.00`), or whether the 5 security guards passed.

We upgraded both files so they use our clean `response.is_refusal` flag from `schemas.py` and display live engineering metrics right on screen!

---

## 2. Before vs. After Comparison

```text
+----------------------------------------+----------------------------------------+
|       OLD app.py & capstone.py         |       NEW app.py & capstone.py         |
+----------------------------------------+----------------------------------------+
| Guessed if the AI refused by checking  | Uses the clean `response.is_refusal`   |
| 9 hardcoded strings (`negative_cues`)  | switch computed in `schemas.py`        |
+----------------------------------------+----------------------------------------+
| Did not show citations, latency, cost, | Displays a clean badge below every     |
| cache hits, or security guard status   | answer:                                |
|                                        | `Citations: [1, 2] | Latency: 640 ms |`|
|                                        | `Cost: $0.0004 | Guards: 5/5 Passed`   |
+----------------------------------------+----------------------------------------+
| No sidebar showing session budget or   | Streamlit sidebar shows Live Calls,    |
| $p_{50} / p_{95}$ speed                | Cache Hits, $p_{50}/p_{95}$ Latency,   |
|                                        | and Total Spend in USD                 |
+----------------------------------------+----------------------------------------+
```

---

## 3. What Happens When You Run `streamlit run app.py` Now?

Because you deleted the old `faiss_index/` folder earlier, the very first time you run:

```bash
streamlit run app.py
```

1. `load_rag_pipeline()` calls `get_vectorstore()` in `vectorstore.py`.
2. It sees that `faiss_index/` does not exist yet, so it automatically calls `get_document_chunks(DOCUMENTS_DIR, only_current=True)` in `loader.py`.
3. It reads your Love2D PDFs, filters out `00-cover-contents.pdf` (`status="archived"`), chops Chapters `01`–`08` into **600-character recursive chunks (`strategy="recursive"`)**, embeds them with L2-normalized `all-MiniLM-L6-v2` vectors, and saves the brand-new **`faiss_index/`** folder to disk!
4. From then on, every future startup loads the saved `faiss_index/` from disk in under 1 second.
