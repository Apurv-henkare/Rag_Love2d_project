# 📝 Fix 3: Upgrading `loader.py` (The Document Ingestion & Chunking Pipeline)
*Student Revision & Defense Notes — Plaksha AI in Practice*

---

## 1. The Big Picture: What is `loader.py`?
`loader.py` is the **data factory** of our RAG system. It is responsible for:
1. Opening the Love2D manual PDFs in `documents/` using PyMuPDF (`fitz`).
2. Extracting text page-by-page.
3. Filtering out noise (covers, tables of contents, index pages).
4. Tagging every page with rich metadata (module heading, page number, status, unique chunk ID).
5. Slicing the raw text into clean, semantically intact chunks using LangChain's `RecursiveCharacterTextSplitter`.

If `loader.py` creates poor, noisy, or broken chunks, the vector search engine will fail—garbage in, garbage out!

---

## 2. Before vs. After Summary Table

| Feature / Logic | OLD `loader.py` (Naive / Broken) ❌ | NEW `loader.py` (Production Hardened) ✅ |
| :--- | :--- | :--- |
| **PDF Loading Order** | `folder_path.glob("*.pdf")` (Unsorted, random OS order) | **`sorted(folder_path.glob("*.pdf"))` (Deterministic `00` to `08`)** |
| **Chunking Algorithm** | Naive character splitting (`chunk_size=3000`) | **`RecursiveCharacterTextSplitter` (`chunk_size=600`, `overlap=120`)** |
| **Table-of-Contents Noise** | Ingested `00-cover-contents.pdf` and internal index pages | **Filters whole docs (`ARCHIVED_DOCS`) and pages (`ARCHIVED_PAGES`)** |
| **Chunk Metadata** | Bare minimum: only `source` and `page` | **6 Rich Fields: `source`, `doc_id`, `page`, `section`, `status`, `chunk_id`** |
| **Section Heading Detection** | None | **Regex detector (`_detect_section_heading`) tags `love.graphics`, etc.** |
| **Chunking Strategies** | Hardcoded to one rigid format | **Supports 4 strategies: `fixed`, `sliding`, `recursive`, `breadcrumb`** |
| **Incremental PDF Loading** | Missing (rebuilding 1 PDF required re-reading all 9) | **`load_single_pdf_chunks()` enables ~1-second auto-sync in `vectorstore.py`** |

---

## 3. Deep Dive into Every Fix with Positive & Negative Examples

---

### Fix 3.1: Recursive Semantic Chunking (`600` chars, `120` overlap)

#### ❌ Negative Example (What Broke in the Old Code):
* **Old Settings:** `CHUNK_SIZE = 3000`, `CHUNK_OVERLAP = 600` using naive slicing.
* **The Failure (Cutting Code in Half & Semantic Dilution):**
  1. A naive 3,000-character slice sliced text at arbitrary character boundaries, often cutting a Lua function declaration in half.
  2. Blended 4 to 5 different Love2D functions into a single chunk, creating a blurry vector average.
  3. The local embedding model (`all-MiniLM-L6-v2`) only embeds the first **256 tokens (~900 characters)** and cut off the remaining 2,100 characters!

#### ✅ Positive Example (How the NEW Fix Solves It):
* **New Settings:** `CHUNK_SIZE = 600`, `CHUNK_OVERLAP = 120`, `strategy = "recursive"`.
* **How `RecursiveCharacterTextSplitter` Works:**
  It splits text using a priority hierarchy of separators:
  ```python
  separators = ["\n\n", "\n", " ", ""]
  ```
  1. First, it tries to split on double newlines (`\n\n`) to keep full paragraphs intact.
  2. If a paragraph is too long, it splits on single newlines (`\n`) to keep code blocks and lists intact.
  3. If a line is still too long, it splits on spaces (` `) to keep complete words intact.
* **The Result:** Every chunk contains a **single, unbroken concept or function**, with an overlap of 120 characters ensuring function headers are never orphaned.

---

### Fix 3.2: Two-Tier Noise Filtering (`status = "archived"` vs. `"current"`)

#### ❌ Negative Example (What Broke in the Old Code):
* In the old `loader.py`, all pages from all PDFs were treated equally.
* `00-cover-contents.pdf` (master Table of Contents) and Pages 2–4 of `03-types-2of2.pdf` (3-column function index lists) were sliced into chunks and saved to FAISS.
* When a user asked *"How do I draw shapes?"*, BM25 keyword search retrieved the Table of Contents because the word `love.graphics` appeared 50 times in a row!
* The LLM received a chunk with zero code and zero explanation.

#### ✅ Positive Example (How the NEW Fix Solves It):
* `loader.py` implements two-tier metadata classification:
  ```python
  def _is_archived_page(filename: str, page_number: int) -> bool:
      if _is_archived_doc(filename):
          return True
      if page_number in ARCHIVED_PAGES.get(filename, []):
          return True
      return False
  ```
* **Tier 1 (Whole Document):** Files in `ARCHIVED_DOCS` (`00-cover-contents.pdf`, `08-appendices.pdf`) are marked `status = "archived"`.
* **Tier 2 (Specific Page Numbers):** Pages in `ARCHIVED_PAGES` (e.g. `03-types-2of2.pdf` pages 2, 3, 4) are marked `status = "archived"`.
* **At Ingestion Time (`get_document_chunks`):**
  ```python
  if only_current:
      docs = [d for d in docs if d.metadata.get("status", "current") == "current"]
  ```
  Archived pages are discarded before chunking, keeping the vector database 100% clean!

---

### Fix 3.3: Dynamic Section Heading Detection (`_detect_section_heading`)

#### ❌ Negative Example (What Broke in the Old Code):
* The old loader only stored `{"source": "06-modules.pdf", "page": 444}`.
* When the chunk reached the prompt or the UI, neither the AI nor the user knew which chapter or module the text belonged to unless the word was explicitly repeated inside the chunk.

#### ✅ Positive Example (How the NEW Fix Solves It):
* `loader.py` uses regex patterns to scan the top 8 lines of every page:
  ```python
  _HEADING_PATTERNS = [
      re.compile(r"^(love\.[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?)\b"),
      re.compile(r"^(Chapter\s+\d+[:\.\s].+)$", re.IGNORECASE),
      re.compile(r"^(\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9\s\-_/()]{2,60})$"),
      re.compile(r"^([A-Z][A-Za-z0-9\s\-_/:]{3,50})$"),
  ]
  ```
* When Page 444 is scanned, it detects: `section = "love.graphics"`.
* If a page has no new heading, it automatically carries forward the `current_heading` from the previous page.
* **The Chunk Metadata:**
  ```python
  {
      "source": "06-modules.pdf",
      "doc_id": "06-modules",
      "page": 444,
      "section": "love.graphics",
      "status": "current",
      "chunk_id": "06-modules_p444_c6235"
  }
  ```
* In the Streamlit UI, the citation drawer can show: **`[06-modules.pdf > Section: love.graphics | Page 444]`**!

---

### Fix 3.4: Multi-Strategy Chunking (`split_documents`) for Benchmark Sweeps

#### 💡 Why This Was Built (Lab 3 Best Practice):
In academic evaluation, you cannot simply assert: *"600-character recursive chunking is best."* You must prove it scientifically against other strategies!

`loader.py` supports **4 distinct chunking strategies**:
1. **`fixed`:** Strict character slicing with zero overlap (`chunk_overlap=0`).
2. **`sliding`:** Character slicing with overlap (`chunk_overlap=120`).
3. **`recursive` (Default):** Paragraph- and sentence-aware recursive splitting.
4. **`breadcrumb`:** Prepends a context header `[Source > Section | Page]` to the top of every chunk before embedding.

* **Benchmark Result (from Step 2):**  
  `recursive` chunking at 600 characters achieved **100% Hit@5 and 0.950 MRR**, vastly outperforming naive fixed chunking (`40.0% Hit@1, 0.475 MRR`).

---

### Fix 3.5: Incremental Single-PDF Splitting (`load_single_pdf_chunks`)

#### ❌ Negative Example (What Broke in the Old Code):
* If you dropped a single new PDF (e.g. `community_tutorial.pdf`) into `documents/`, the old code had to re-read and re-embed all 9 PDF manuals from scratch.
* On CPU, re-embedding 7,797 chunks took 5 to 10 minutes!

#### ✅ Positive Example (How the NEW Fix Solves It):
* `load_single_pdf_chunks(pdf_path: Path)` loads and splits **only the single newly added PDF**.
* In `vectorstore.py`, `_sync_incremental_pdfs()` uses this function to incrementally embed only the new chunks into the existing FAISS index in **~1 second** without rebuilding the database!

---

## 4. What to Tell Your Professor on Demo Day:
> *"In Fix 3, we redesigned `loader.py` from a naive PDF reader into an enterprise data ingestion pipeline:  
> 1. We adopted `RecursiveCharacterTextSplitter` with 600-char chunks and 120-char overlap, preserving code blocks and paragraph boundaries while respecting the 256-token limit of our embedding model.  
> 2. We implemented two-tier noise filtering (`ARCHIVED_DOCS` and `ARCHIVED_PAGES`) to purge both whole-file and internal index pages at loading time.  
> 3. We built a dynamic regex heading detector that tags every chunk with its module title (`love.graphics`, `love.physics`), generating deterministic chunk IDs (`doc_pPage_cIdx`).  
> 4. We enabled multi-strategy chunking (`fixed`, `sliding`, `recursive`, `breadcrumb`) to empirically validate our chunking parameters in our Lab 3 benchmark sweeps."*
