import math
import re
from collections import Counter
from pathlib import Path
from typing import List, Optional
import numpy as np
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from config import ARCHIVED_PAGES, DOCUMENTS_DIR, EMBEDDING_MODEL, FAISS_INDEX_DIR, RETRIEVER_K, RETRIEVER_MODE
from loader import _is_archived_doc, load_single_pdf_chunks

_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_EMBEDDINGS_SINGLETON: Optional[HuggingFaceEmbeddings] = None


def tokenize(text: str) -> List[str]:
    """
    Tokenizes text into lowercase alphanumeric + underscore words.
    Keeping underscores/dots split cleanly helps match Lua APIs like
    `love.graphics.rectangle` -> ['love', 'graphics', 'rectangle'].
    """
    return _TOKEN_RE.findall(text.lower())


_LOVE_API_RE = re.compile(r"\b(love\.[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?)\b", re.IGNORECASE)


def _matches_api_section(query: str, section: str) -> bool:
    """
    Lab 3 Best Practice — Section-Aware Prioritization:
    Returns True if the query explicitly asks about a Love2D API function
    and `section` is the official manual section header for that API.
    (e.g., query has 'love.graphics.setColor' and section is 'love.graphics.setColor').
    """
    if not section or not query:
        return False
    sec_lower = section.strip().lower()
    apis = _LOVE_API_RE.findall(query)
    for api in apis:
        api_lower = api.strip().lower()
        if api_lower == sec_lower or api_lower in sec_lower or sec_lower in api_lower:
            return True
    return False


class SimpleBM25Okapi:
    """
    Pure-Python Okapi BM25 implementation (k1=1.5, b=0.75).
    Used automatically if `rank_bm25` is not installed in the active environment,
    guaranteeing BM25 and Hybrid RRF retrieval always work out-of-the-box.
    """

    def __init__(self, corpus_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus_tokens)
        self.doc_len = [len(doc) for doc in corpus_tokens]
        self.avgdl = (sum(self.doc_len) / self.corpus_size) if self.corpus_size else 1.0
        self.doc_freqs: List[Counter] = []
        df: Counter = Counter()

        for doc in corpus_tokens:
            frequencies = Counter(doc)
            self.doc_freqs.append(frequencies)
            for token in frequencies.keys():
                df[token] += 1

        self.idf = {}
        for word, freq in df.items():
            self.idf[word] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query_tokens: List[str]) -> np.ndarray:
        scores = np.zeros(self.corpus_size, dtype=np.float64)
        for q in query_tokens:
            if q not in self.idf:
                continue
            idf_val = self.idf[q]
            for i, freq_map in enumerate(self.doc_freqs):
                tf = freq_map.get(q, 0)
                if tf > 0:
                    denom = tf + self.k1 * (1.0 - self.b + self.b * (self.doc_len[i] / self.avgdl))
                    scores[i] += idf_val * (tf * (self.k1 + 1.0)) / denom
        return scores


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Initializes and returns the local HuggingFace Embeddings instance (`all-MiniLM-L6-v2`).
    Uses L2 normalization (`normalize_embeddings=True`) so vector dot-products
    and distances correspond directly to Cosine Similarity (Lab 3 best practice).
    """
    global _EMBEDDINGS_SINGLETON
    if _EMBEDDINGS_SINGLETON is None:
        _EMBEDDINGS_SINGLETON = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            encode_kwargs={"normalize_embeddings": True},
        )
    return _EMBEDDINGS_SINGLETON


def _sync_incremental_pdfs(
    vectorstore: FAISS,
    persist_dir: Path = FAISS_INDEX_DIR,
    docs_dir: Path = DOCUMENTS_DIR,
    only_current: bool = True,
) -> FAISS:
    """
    Checks if any PDFs were added to or deleted from `documents/` since `faiss_index/`
    was saved, and incrementally embeds ONLY the new PDF(s) (or removes deleted ones)
    in ~1 second without rebuilding the entire 36 MB index.
    """
    if not docs_dir.exists():
        return vectorstore

    disk_pdfs = {
        p.name
        for p in docs_dir.glob("*.pdf")
        if not (only_current and _is_archived_doc(p.name))
    }
    docstore_dict = getattr(vectorstore.docstore, "_dict", {})
    indexed_pdfs = {
        d.metadata.get("source")
        for d in docstore_dict.values()
        if isinstance(d, Document) and d.metadata.get("source")
    }

    added_pdfs = sorted(disk_pdfs - indexed_pdfs)
    removed_pdfs = sorted(indexed_pdfs - disk_pdfs)
    changed = False

    for pdf_name in added_pdfs:
        pdf_path = docs_dir / pdf_name
        new_chunks = load_single_pdf_chunks(pdf_path)
        if only_current:
            new_chunks = [c for c in new_chunks if c.metadata.get("status", "current") == "current"]
        if new_chunks:
            vectorstore.add_documents(new_chunks)
            changed = True
            print(f"[Auto-Sync] Embedded new PDF '{pdf_name}' ({len(new_chunks)} chunks) into FAISS index!")

    if removed_pdfs:
        ids_to_delete = [
            doc_id
            for doc_id, d in docstore_dict.items()
            if isinstance(d, Document) and d.metadata.get("source") in removed_pdfs
        ]
        if ids_to_delete:
            vectorstore.delete(ids_to_delete)
            changed = True
            print(f"[Auto-Sync] Removed deleted PDF(s) {removed_pdfs} ({len(ids_to_delete)} chunks) from FAISS index!")

    if changed:
        vectorstore.save_local(str(persist_dir))
        print(f"[Auto-Sync] Saved updated FAISS index to: {persist_dir}")

    return vectorstore


def get_vectorstore(
    chunks: Optional[List[Document]] = None,
    persist_dir: Path = FAISS_INDEX_DIR,
    only_current: bool = True,
) -> FAISS:
    """
    Retrieves the FAISS vector store. If a saved index exists locally, it loads it
    and auto-syncs any newly added or deleted PDFs from `documents/`.
    Otherwise, it filters for `status == 'current'` chunks, builds a new vector store,
    and saves it locally to `faiss_index/`.
    """
    embeddings = get_embeddings()

    # Check if a cached FAISS index already exists on disk
    index_file = persist_dir / "index.faiss"
    if index_file.exists():
        print(f"Loading existing FAISS index from: {persist_dir}...")
        vs = FAISS.load_local(
            str(persist_dir),
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )
        return _sync_incremental_pdfs(vs, persist_dir=persist_dir, only_current=only_current)

    # Build new index if chunks provided
    if not chunks:
        raise ValueError(
            f"No existing index found at {persist_dir}, and no document chunks were provided to build one."
        )

    if only_current:
        before_count = len(chunks)
        chunks = [c for c in chunks if c.metadata.get("status", "current") == "current"]
        if before_count != len(chunks):
            print(f"Metadata filter (`status='current'`): kept {len(chunks)}/{before_count} chunks.")

    batch_size = 64
    total_chunks = len(chunks)
    print(f"Generating L2-normalized local embeddings and building FAISS index for {total_chunks} chunks...")

    vectorstore = FAISS.from_documents(embedding=embeddings, documents=chunks[:batch_size])
    print(f"Embedded {min(batch_size, total_chunks)}/{total_chunks} chunks")

    for i in range(batch_size, total_chunks, batch_size):
        batch = chunks[i : i + batch_size]
        vectorstore.add_documents(batch)
        print(f"Embedded {min(i + batch_size, total_chunks)}/{total_chunks} chunks")

    # Cache index locally for instant future startups
    persist_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(persist_dir))
    print(f"Saved FAISS index to: {persist_dir}")

    return vectorstore


def extract_docs_from_faiss(vectorstore: FAISS, only_current: bool = True) -> List[Document]:
    """
    Extracts all stored Document chunks from a loaded FAISS vectorstore's docstore.
    Ensures every chunk has a deterministic `chunk_id` and filters for `status == 'current'`
    when `only_current=True`.
    """
    raw_docs = list(getattr(vectorstore.docstore, "_dict", {}).values())
    docs: List[Document] = []
    for idx, d in enumerate(raw_docs):
        if not isinstance(d, Document):
            continue
        src_name = d.metadata.get("source", "")
        page_num = d.metadata.get("page", 0)
        if only_current and (
            d.metadata.get("status", "current") != "current"
            or _is_archived_doc(src_name)
            or page_num in ARCHIVED_PAGES.get(src_name, [])
        ):
            continue
        if "chunk_id" not in d.metadata:
            src_stem = Path(src_name or "doc").stem
            d.metadata["chunk_id"] = f"{src_stem}_p{page_num}_c{idx}"
        docs.append(d)
    return docs


class Love2DRetriever:
    """
    Plaksha_AI_in_Practise_modified Style Retriever supporting:
      1. 'dense':  FAISS L2-normalized vector similarity search
      2. 'bm25':   Lexical Okapi BM25 exact keyword search (great for Lua API names)
      3. 'hybrid': Reciprocal Rank Fusion (RRF) combining Dense + BM25:
                   score(d) = 1 / (rrf_k + rank_dense(d)) + 1 / (rrf_k + rank_bm25(d))
    """

    def __init__(
        self,
        vectorstore: FAISS,
        k: int = RETRIEVER_K,
        mode: str = "dense",
        rrf_k: int = 60,
        only_current: bool = True,
    ):
        self.vectorstore = vectorstore
        self.k = k
        self.mode = mode.lower()
        self.rrf_k = rrf_k
        self.only_current = only_current
        self.chunks: List[Document] = extract_docs_from_faiss(vectorstore, only_current=only_current)

        # Initialize BM25 only when needed for Lab 3 comparison sweeps ('bm25' or 'hybrid')
        self.bm25 = None
        if self.mode in {"bm25", "hybrid"} and self.chunks:
            tokenized_corpus = [tokenize(c.page_content) for c in self.chunks]
            try:
                from rank_bm25 import BM25Okapi  # type: ignore

                self.bm25 = BM25Okapi(tokenized_corpus)
            except ImportError:
                self.bm25 = SimpleBM25Okapi(tokenized_corpus)

    def _search_dense(self, query: str, top_n: int) -> List[Document]:
        raw_hits = self.vectorstore.similarity_search(query, k=top_n * 2)
        filtered: List[Document] = []
        direct_matches: List[Document] = []
        standard_matches: List[Document] = []

        for rank_idx, doc in enumerate(raw_hits):
            src_name = doc.metadata.get("source", "")
            page_num = doc.metadata.get("page", 0)
            if self.only_current and (
                doc.metadata.get("status", "current") != "current"
                or _is_archived_doc(src_name)
                or page_num in ARCHIVED_PAGES.get(src_name, [])
            ):
                continue
            doc_copy = Document(page_content=doc.page_content, metadata=dict(doc.metadata))
            doc_copy.metadata["retriever"] = "dense"
            if _matches_api_section(query, doc.metadata.get("section", "")):
                direct_matches.append(doc_copy)
            else:
                standard_matches.append(doc_copy)

        combined = direct_matches + standard_matches
        for rank_idx, doc_copy in enumerate(combined[:top_n], start=1):
            doc_copy.metadata["rank"] = rank_idx
            filtered.append(doc_copy)
        return filtered

    def _search_bm25(self, query: str, top_n: int) -> List[Document]:
        if not self.bm25 or not self.chunks:
            return []
        q_tokens = tokenize(query)
        scores = np.asarray(self.bm25.get_scores(q_tokens), dtype=np.float64)
        for idx, chunk in enumerate(self.chunks):
            if _matches_api_section(query, chunk.metadata.get("section", "")):
                scores[idx] += 50.0  # Dominant boost for official API definition chunk

        top_indices = np.argsort(-scores)[:top_n]
        results: List[Document] = []
        for rank_idx, idx in enumerate(top_indices):
            orig = self.chunks[int(idx)]
            doc_copy = Document(page_content=orig.page_content, metadata=dict(orig.metadata))
            doc_copy.metadata["retriever"] = "bm25"
            doc_copy.metadata["bm25_score"] = float(scores[int(idx)])
            doc_copy.metadata["rank"] = rank_idx + 1
            results.append(doc_copy)
        return results

    def _rerank_candidates(self, query: str, candidates: List[Document], top_n: int) -> List[Document]:
        """
        Lab 3 Part C — Second-Stage Reranker:
        Takes an initial pool of candidate chunks (k=20) from Stage 1 retrieval and
        applies fine-grained cross-scoring:
          1. Exact query phrase & Lua API signature matches
          2. Query term coverage (set intersection of distinct search tokens)
          3. Query token density across the chunk
          4. Stage 1 dense vector rank discount
        Returns the top-n reranked chunks.
        """
        if not candidates:
            return []

        q_tokens = tokenize(query)
        q_set = set(q_tokens)
        q_lower = query.lower().strip()
        scored: List[Tuple[float, Document]] = []

        for rank_0, doc in enumerate(candidates):
            text_lower = doc.page_content.lower()
            doc_tokens = tokenize(text_lower)
            doc_set = set(doc_tokens)

            # 1. Query token coverage (fraction of user query terms present)
            coverage = len(q_set & doc_set) / max(len(q_set), 1)

            # 2. Exact phrase bonus (e.g., exact API or phrase match)
            phrase_bonus = 2.5 if q_lower in text_lower else 0.0

            # 2b. Official API section match bonus (Lab 3 Best Practice)
            section_bonus = 10.0 if _matches_api_section(query, doc.metadata.get("section", "")) else 0.0

            # 3. Frequency density of query tokens in chunk
            term_freq = sum(doc_tokens.count(t) for t in q_set) / max(len(doc_tokens), 1)

            # 4. Stage 1 rank prior (preserves vector similarity signal)
            rank_prior = 1.0 / (rank_0 + 6)

            total_score = (coverage * 3.0) + phrase_bonus + section_bonus + (term_freq * 2.0) + rank_prior
            scored.append((total_score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        reranked: List[Document] = []
        for new_rank, (s, orig) in enumerate(scored[:top_n], start=1):
            doc_copy = Document(page_content=orig.page_content, metadata=dict(orig.metadata))
            doc_copy.metadata["retriever"] = "rerank"
            doc_copy.metadata["rerank_score"] = round(s, 4)
            doc_copy.metadata["rank"] = new_rank
            reranked.append(doc_copy)
        return reranked

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Document]:
        top_k = k or self.k
        # Default Lab 3 Winner: Pure Dense Vector Search ('dense')
        if self.mode == "dense":
            return self._search_dense(query, top_k)
        if self.mode == "bm25":
            return self._search_bm25(query, top_k)

        # Lab 3 Part C: Two-stage retrieval with second-stage reranker
        if self.mode == "rerank":
            pool = max(top_k * 4, 20)
            candidates = self._search_dense(query, pool)
            return self._rerank_candidates(query, candidates, top_n=top_k)

        # Optional for Lab 3 Sweep comparison: 'hybrid' — Reciprocal Rank Fusion (RRF)
        pool = max(top_k * 4, 20)
        dense_hits = self._search_dense(query, pool)
        bm25_hits = self._search_bm25(query, pool)

        rrf_scores: dict[str, float] = {}
        doc_by_key: dict[str, Document] = {}

        for rank_0, doc in enumerate(dense_hits):
            key = doc.metadata.get("chunk_id") or f"{doc.metadata.get('source')}_{doc.metadata.get('page')}_{doc.page_content[:60]}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (self.rrf_k + rank_0 + 1)
            doc_by_key[key] = doc

        for rank_0, doc in enumerate(bm25_hits):
            key = doc.metadata.get("chunk_id") or f"{doc.metadata.get('source')}_{doc.metadata.get('page')}_{doc.page_content[:60]}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (self.rrf_k + rank_0 + 1)
            if key not in doc_by_key:
                doc_by_key[key] = doc

        # Ensure direct section matches in corpus are included even if cut off by pool
        for chunk in self.chunks:
            if _matches_api_section(query, chunk.metadata.get("section", "")):
                key = chunk.metadata.get("chunk_id") or f"{chunk.metadata.get('source')}_{chunk.metadata.get('page')}_{chunk.page_content[:60]}"
                doc_by_key[key] = chunk
                rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0  # Dominant boost

        sorted_keys = sorted(rrf_scores.keys(), key=lambda k_id: -rrf_scores[k_id])[:top_k]
        fused_docs: List[Document] = []
        for final_rank, key in enumerate(sorted_keys, start=1):
            doc = doc_by_key[key]
            doc_copy = Document(page_content=doc.page_content, metadata=dict(doc.metadata))
            doc_copy.metadata["retriever"] = "hybrid_rrf"
            doc_copy.metadata["rrf_score"] = round(rrf_scores[key], 5)
            doc_copy.metadata["rank"] = final_rank
            fused_docs.append(doc_copy)

        return fused_docs

    def invoke(self, query: str, config: Optional[dict] = None) -> List[Document]:
        """LangChain Runnable compatibility: delegate invoke() to retrieve()."""
        return self.retrieve(query)


def get_retriever(
    vectorstore: FAISS,
    k: int = RETRIEVER_K,
    mode: str = RETRIEVER_MODE,
):
    """
    Returns a LangChain-compatible Runnable retriever configured with top-k neighbors.
    Defaults to `mode=RETRIEVER_MODE` ('hybrid' — Dense FAISS + Sparse BM25 via RRF),
    while also supporting 'dense' and 'bm25' for comparative sweeps.
    """
    love2d_retriever = Love2DRetriever(vectorstore=vectorstore, k=k, mode=mode)
    return RunnableLambda(love2d_retriever.retrieve)
