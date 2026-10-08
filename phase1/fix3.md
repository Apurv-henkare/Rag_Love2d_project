# Phase 1 — Fix 3: Upgrading `loader.py`

**File Modified:** [`loader.py`](file:///d:/Python_AIP_second/loader.py)

---

## 1. Big Picture: Why Did We Change `loader.py`?

`loader.py` opens your 9 Love2D PDFs (`00-cover-contents.pdf` through `08-appendix.pdf`), reads the text off every page, and slices that text into chunks for the vector database (`faiss_index/`).

We upgraded `loader.py` based on **Lab 3 (`labs/lab3/report.md`)** of `Plaksha_AI_in_Practise_modified`:
1. **Default Strategy = `recursive` (`CHUNK_SIZE = 600`, `CHUNK_OVERLAP = 120`):**
   Uses `RecursiveCharacterTextSplitter` to split cleanly on paragraphs and sentences at 600 characters with 120 characters of overlap (instead of the old 3,000-character blocks).
2. **Table-of-Contents Noise Filtered Out (`status = "archived"` vs `"current"`):**
   Marks `00-cover-contents.pdf` as `status = "archived"` and drops it by default (`only_current=True`) so the search engine only indexes the real Love2D manual chapters (`01` through `08`).
3. **Rich Metadata on Every Chunk:**
   Tracks `source`, `doc_id`, `page`, `section` (`_detect_section_heading`), `status`, and a unique `chunk_id` (`05-physics_p18_c114`) inside `chunk.metadata`.
4. **Supports All 4 Chunking Styles (`fixed`, `sliding`, `recursive`, `breadcrumb`)** so we can compare them in Phase 2 (Step 3).

---

## 2. Before vs. After Comparison

```text
+----------------------------------------+----------------------------------------+
|            OLD loader.py               |            NEW loader.py               |
+----------------------------------------+----------------------------------------+
| Read PDF files in random folder order  | Sorts PDFs cleanly (`00` through `08`) |
+----------------------------------------+----------------------------------------+
| Only saved `source` and `page` in      | Saves 6 metadata fields:               |
| metadata                               | - `source` ('05-physics.pdf')          |
|                                        | - `doc_id` ('05-physics')              |
|                                        | - `page` (18)                          |
|                                        | - `section` ('love.physics')           |
|                                        | - `status` ('current' or 'archived')   |
|                                        | - `chunk_id` ('05-physics_p18_c42')    |
+----------------------------------------+----------------------------------------+
| Indexed `00-cover-contents.pdf` noise  | Tags `00-cover-contents.pdf` as        |
| into `faiss_index/`                    | `status="archived"` and filters it out |
|                                        | by default (`only_current=True`)       |
+----------------------------------------+----------------------------------------+
| Used 3,000-char chunks (600 overlap)   | Uses 600-char `recursive` chunks       |
|                                        | (120 overlap) by default               |
+----------------------------------------+----------------------------------------+
```
