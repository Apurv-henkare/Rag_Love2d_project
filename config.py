import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ===========================================================================
# 1. Directories (Main Project + Plaksha_AI_in_Practise_modified Structure)
# ===========================================================================
BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "documents"
FAISS_INDEX_DIR = BASE_DIR / "faiss_index"

# Data & Evaluation Directories (Labs 1-6)
DATA_DIR = BASE_DIR / "data"
CORPUS_DIR = DATA_DIR / "corpus"
EVAL_DIR = DATA_DIR / "eval"
ATTACKS_DIR = DATA_DIR / "attacks"
REPORTS_DIR = BASE_DIR / "reports"

# Engineering Spine Directories (SQLite Cache & JSONL Traces)
CACHE_DIR = Path(os.getenv("AIP_CACHE_DIR", BASE_DIR / ".aip_cache"))
TRACE_DIR = Path(os.getenv("AIP_TRACE_DIR", BASE_DIR / ".aip_traces"))

for _d in (CACHE_DIR, TRACE_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ===========================================================================
# 2. API Keys & Runtime Flags
# ===========================================================================
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(int(default))).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


CACHE_ENABLED = _env_bool("AIP_CACHE", True)
OFFLINE_MODE = _env_bool("AIP_OFFLINE", False)
BUDGET_USD = _env_float("AIP_BUDGET_USD", 2.0)

# ===========================================================================
# 3. Model Tiers & Configurations (Plaksha_AI_in_Practise_modified Style)
# ===========================================================================
# Never hard-code a single model everywhere:
#   SMALL -> fast, low-cost tier for high-volume extraction (Labs 1 & 2)
#   MAIN  -> default tier for grounded RAG generation (Labs 4, 5, 6)
#   LARGE -> separate model for LLM-as-Judge (prevents self-preference bias)
#   EMBED -> local HuggingFace embedding model (all-MiniLM-L6-v2, 384-dim)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "gemini-3.1-flash-lite"
FALLBACK_LLM_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.1-pro",
    "gemini-3.8-flash",
]
LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
LLM_REASONING_EFFORT = "minimal"
LLM_MAX_TOKENS = 4096

MODEL_TIERS: dict[str, str] = {
    "SMALL": "gemini-3.1-flash-lite",
    "MAIN": "gemini-3.1-flash-lite",
    "LARGE": "gemini-3.5-flash",
    "EMBED": EMBEDDING_MODEL,
}


def resolve_model(name_or_tier: str | None = None) -> str:
    """Resolve 'SMALL' / 'MAIN' / 'LARGE' / 'EMBED' into a concrete model name."""
    if name_or_tier is None:
        return MODEL_TIERS["MAIN"]
    key = name_or_tier.strip().upper()
    return MODEL_TIERS.get(key, name_or_tier)


# Token pricing per 1 Million tokens (input_usd, output_usd) for the Budget ledger
FREE_PREFIXES: tuple[str, ...] = ("local/", "all-MiniLM", "ollama/")
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini-3.1-flash-lite": (0.30, 2.50),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.1-pro": (1.25, 5.00),
    "all-MiniLM-L6-v2": (0.00, 0.00),
}

# ===========================================================================
# 4. Reproducibility, Chunking, Retrieval & Grounding Settings (Labs 1-6)
# ===========================================================================
SEED = 42
TEMPERATURE = _env_float("AIP_TEMPERATURE", 0.0)

# Lab 3 Best Practice:
# Replaced the old 3000-char chunks (which suffered from severe semantic dilution)
# with focused 600-char recursive chunks + 120-char overlap.
CHUNK_SIZE = 600
CHUNK_OVERLAP = 120

# Kept for Step 3 (Lab 3) comparison sweep to prove why 600 beats 3000:
LEGACY_CHUNK_SIZE = 3000
LEGACY_CHUNK_OVERLAP = 600

# Lab 3 Metadata Filtering:
# Exclude table-of-contents / cover noise, category indexes, and any *-ARCHIVED* documents at query time.
ARCHIVED_DOCS: tuple[str, ...] = (
    "00-cover-contents.pdf",
    "05-categories.pdf",
    "08-appendices.pdf",
)

# Specific page numbers to archive per document (e.g. internal section index / TOC pages):
ARCHIVED_PAGES: dict[str, list[int]] = {
    "02-types-1of2.pdf": [2, 3, 4],
    "03-types-2of2.pdf": [2, 3, 4],
    "04-other-pages.pdf": [2, 3],
    "05-categories.pdf": [2],
    "06-modules.pdf": [2, 3, 4],
    "07-tutorials.pdf": [2],
}

# Retriever & Guardrail settings
# Production Retriever Mode: 'hybrid' combines Dense FAISS (semantic understanding)
# and BM25 Okapi (exact technical identifier match for CamelCase APIs like love.graphics.drawCyberPortal)
# via Reciprocal Rank Fusion (RRF, k=60).
RETRIEVER_MODE = os.getenv("AIP_RETRIEVER_MODE", "hybrid")
RETRIEVER_K = 5
MAX_TOOL_CALLS = 4

# Lab 4 Standardized Exact Refusal String
REFUSAL = "I don't have enough information in the provided sources to answer that."
