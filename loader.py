import re
from pathlib import Path
from typing import List
import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from config import ARCHIVED_DOCS, ARCHIVED_PAGES, CHUNK_OVERLAP, CHUNK_SIZE, DOCUMENTS_DIR

# Regex patterns to detect Love2D manual chapters, module headers, or API function titles
_HEADING_PATTERNS = [
    re.compile(r"^(love\.[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?)\b"),
    re.compile(r"^(Chapter\s+\d+[:\.\s].+)$", re.IGNORECASE),
    re.compile(r"^(\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9\s\-_/()]{2,60})$"),
    re.compile(r"^([A-Z][A-Za-z0-9\s\-_/:]{3,50})$"),
]

# Fallback readable section names per PDF filename stem
_DEFAULT_SECTION_BY_STEM = {
    "00-cover-contents": "Cover & Table of Contents",
    "01-getting-started": "Getting Started",
    "02-callbacks": "Love2D Callbacks",
    "03-lua-basics": "Lua Programming Basics",
    "04-graphics": "Graphics & Drawing (love.graphics)",
    "05-physics": "Physics Engine (love.physics)",
    "06-modules": "Core Love2D Modules",
    "07-advanced": "Advanced Topics & Shaders",
    "08-appendix": "Appendix & Reference",
}


def _detect_section_heading(page_text: str, current_heading: str) -> str:
    """
    Scans the top lines of a PDF page to detect if a new Love2D module,
    chapter, or section heading starts on this page. If none is found,
    carries forward the `current_heading` from the previous page.
    """
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    for line in lines[:8]:
        # Skip pure page numbers or very long paragraph lines
        if line.isdigit() or len(line) > 75:
            continue
        for pat in _HEADING_PATTERNS:
            m = pat.match(line)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) >= 4:
                    return candidate
    return current_heading


def _is_archived_doc(filename: str) -> bool:
    """
    Lab 3 Metadata Filtering:
    Returns True if the file is in ARCHIVED_DOCS (like 00-cover-contents.pdf)
    or contains 'ARCHIVED' in its filename.
    """
    if filename in ARCHIVED_DOCS or "ARCHIVED" in filename.upper():
        return True
    return False


def _is_archived_page(filename: str, page_number: int) -> bool:
    """
    Lab 3 Metadata Filtering:
    Returns True if the entire file is archived (via ARCHIVED_DOCS or 'ARCHIVED' in name)
    or if this specific page_number is listed in ARCHIVED_PAGES (e.g. 03-types-2of2.pdf pages 2, 3, 4).
    """
    if _is_archived_doc(filename):
        return True
    if page_number in ARCHIVED_PAGES.get(filename, []):
        return True
    return False


def load_pdf_documents(folder_path: Path = DOCUMENTS_DIR) -> List[Document]:
    """
    Loads all PDF files from the specified directory and extracts text into Document objects.
    Tags every page with:
      - source: PDF filename (e.g., '06-modules.pdf')
      - doc_id: PDF stem (e.g., '06-modules')
      - page: 1-based page number
      - section: Detected chapter/module heading on that page
      - status: 'current' (real chapters) or 'archived' (cover/table-of-contents noise)
    """
    documents: List[Document] = []
    pdf_files = sorted(folder_path.glob("*.pdf"))

    if not pdf_files:
        print(f"Warning: No PDF files found in {folder_path}")
        return documents

    for pdf_path in pdf_files:
        try:
            stem = pdf_path.stem
            status = "archived" if _is_archived_doc(pdf_path.name) else "current"
            current_heading = _DEFAULT_SECTION_BY_STEM.get(stem, stem)

            with fitz.open(str(pdf_path)) as doc:
                total_pages = len(doc)
                print(f"Reading '{pdf_path.name}' ({total_pages} pages, status={status})...")
                for page_number, page in enumerate(doc):
                    text = page.get_text("text") or ""
                    if text.strip():
                        current_heading = _detect_section_heading(text, current_heading)
                        page_num = page_number + 1
                        page_status = "archived" if _is_archived_page(pdf_path.name, page_num) else "current"
                        documents.append(
                            Document(
                                page_content=text,
                                metadata={
                                    "source": str(pdf_path.name),
                                    "doc_id": stem,
                                    "page": page_num,
                                    "section": current_heading,
                                    "status": page_status,
                                },
                            )
                        )
                    if (page_number + 1) % 100 == 0 or (page_number + 1) == total_pages:
                        print(f"  -> Processed {page_number + 1}/{total_pages} pages of '{pdf_path.name}'")
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")

    return documents


def split_documents(
    documents: List[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    strategy: str = "recursive",
    add_breadcrumbs: bool = False,
) -> List[Document]:
    """
    Splits loaded documents into smaller overlapping chunks using `RecursiveCharacterTextSplitter`
    (`strategy='recursive'` by default at 600 chars, 120 overlap).

    Supported strategies (for Lab 3 sweeps in Step 3):
      - 'fixed':      Strict character slicing with 0 overlap
      - 'sliding':    Character slicing with overlap
      - 'recursive':  Paragraph/sentence-aware slicing (Default)
      - 'breadcrumb': Paragraph/sentence-aware slicing + prepended [Source > Section | Page] header
    """
    if strategy == "fixed":
        splitter = CharacterTextSplitter(
            separator="",
            chunk_size=chunk_size,
            chunk_overlap=0,
        )
        use_breadcrumbs = False
    elif strategy == "sliding":
        splitter = CharacterTextSplitter(
            separator="",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        use_breadcrumbs = False
    elif strategy == "breadcrumb":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        use_breadcrumbs = True
    else:
        # Default strategy: 'recursive'
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        use_breadcrumbs = add_breadcrumbs

    raw_chunks = splitter.split_documents(documents)
    enriched_chunks: List[Document] = []

    for idx, chunk in enumerate(raw_chunks):
        meta = dict(chunk.metadata)
        src = meta.get("source", "Unknown.pdf")
        doc_id = meta.get("doc_id", Path(src).stem)
        page = meta.get("page", "?")
        section = meta.get("section", doc_id)
        meta["chunk_id"] = f"{doc_id}_p{page}_c{idx}"

        content = chunk.page_content.strip()
        if use_breadcrumbs:
            breadcrumb = f"[Source: {src} > Section: {section} | Page {page}]"
            if not content.startswith("[Source:"):
                content = f"{breadcrumb}\n{content}"

        enriched_chunks.append(Document(page_content=content, metadata=meta))

    return enriched_chunks


def get_document_chunks(
    folder_path: Path = DOCUMENTS_DIR,
    only_current: bool = True,
) -> List[Document]:
    """
    Convenience function that loads and splits all documents in one step.
    By default (`only_current=True`), filters out archived/cover noise
    (`00-cover-contents.pdf`) and splits using `strategy='recursive'`.
    """
    print(f"Loading documents from: {folder_path}...")
    docs = load_pdf_documents(folder_path)
    total_pages = len(docs)

    if only_current:
        docs = [d for d in docs if d.metadata.get("status", "current") == "current"]
        filtered_out = total_pages - len(docs)
        print(
            f"Loaded {total_pages} total pages -> Kept {len(docs)} 'current' pages "
            f"(filtered out {filtered_out} archived/table-of-contents pages)."
        )
    else:
        print(f"Loaded {total_pages} pages (including archived pages).")

    print(
        f"Splitting into chunks (CHUNK_SIZE={CHUNK_SIZE}, CHUNK_OVERLAP={CHUNK_OVERLAP}, "
        f"strategy='recursive')..."
    )
    chunks = split_documents(docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, strategy="recursive")
    print(f"Created {len(chunks)} recursive text chunks.")
    return chunks


def load_single_pdf_chunks(pdf_path: Path) -> List[Document]:
    """
    Loads and splits a single newly added PDF file so `vectorstore.py` can
    auto-sync new PDFs into `faiss_index/` in ~1 second without rebuilding the whole index.
    """
    pages: List[Document] = []
    stem = pdf_path.stem
    status = "archived" if _is_archived_doc(pdf_path.name) else "current"
    current_heading = _DEFAULT_SECTION_BY_STEM.get(stem, stem)

    with fitz.open(str(pdf_path)) as doc:
        for page_number, page in enumerate(doc):
            text = page.get_text("text") or ""
            if text.strip():
                current_heading = _detect_section_heading(text, current_heading)
                page_num = page_number + 1
                page_status = "archived" if _is_archived_page(pdf_path.name, page_num) else "current"
                pages.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": str(pdf_path.name),
                            "doc_id": stem,
                            "page": page_num,
                            "section": current_heading,
                            "status": page_status,
                        },
                    )
                )
    if not pages:
        return []
    return split_documents(pages, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, strategy="recursive")

