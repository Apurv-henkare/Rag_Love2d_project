"""
aip_core/guards.py — The 5-Layer Defense-in-Depth Security Stack (Lab 6 Best Practices).

Implements the exact 5 security layers from `Plaksha_AI_in_Practise_modified/aip/guards.py`
and `labs/lab6/agent.py`:
  Layer 1: `delimit_untrusted()` — Wraps retrieved chunks in `<RETRIEVED_DOCUMENT>` tags
           and strips closing-tag escape attempts (`</RETRIEVED_DOCUMENT>`).
  Layer 2: `detect_injection_refined()` — Detects prompt overrides, system-prompt leaks,
           roleplay hijacks, fake SYSTEM turns, tool coercion, and Base64 smuggling while
           maintaining a 0% False-Positive Rate on normal developer queries containing
           words like "ignore" or "act as".
  Layer 3: Schema Lock — Enforced via `schemas.py` (`Transformer` Pydantic validation).
  Layer 4: `ToolGuard` — Enforces a hard per-turn tool call ceiling (`MAX_TOOL_CALLS = 3`)
           and validates tool arguments.
  Layer 5: `filter_output()` & `redact_pii()` — Scrubs leaked system prompt fragments,
           strips external Markdown image exfiltration (`![...](http...)`), and redacts PII.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from config import MAX_TOOL_CALLS

# ===========================================================================
# Layer 1: Untrusted Content Delimiters (`<RETRIEVED_DOCUMENT>`)
# ===========================================================================
DELIMITER_OPEN = '<RETRIEVED_DOCUMENT source="{source}">'
DELIMITER_CLOSE = "</RETRIEVED_DOCUMENT>"


def delimit_untrusted(text: str, source: str = "unknown") -> str:
    """
    Wrap untrusted retrieved text in explicit XML-style structural delimiters.
    Strips any literal `</RETRIEVED_DOCUMENT>` inside the text so a poisoned
    document cannot prematurely close the block (Lab 6 Indirect Attack I03).
    """
    cleaned = text.replace(DELIMITER_CLOSE, "[REDACTED_CLOSING_TAG]")
    return f"{DELIMITER_OPEN.format(source=source)}\n{cleaned}\n{DELIMITER_CLOSE}"


# ===========================================================================
# Layer 2: Refined Prompt-Injection Detector (0% False Positives on Benign Text)
# ===========================================================================
_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|above|earlier|system|initial)\s+"
            r"(instructions?|prompts?|rules?|directions?|directives?|constraints?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_extraction",
        re.compile(
            r"\b(print|repeat|reveal|show|display|output|translate|verbatim|dump)\b.{0,45}"
            r"\b(system\s+prompt|initial\s+instructions?|hidden\s+instructions?|text\s+above|api\s+keys?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "persona_hijack",
        re.compile(
            r"\b(you\s+are\s+now|from\s+now\s+on\s+you\s+are|switch\s+to\s+mode)\s+"
            r"['\"]?(dan|freebot|unrestricted|jailbreak|developer\s+mode|god\s+mode)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "fake_system_turn",
        re.compile(
            r"(?:^|\n)\s*(?:---\s*\n\s*)?(?:SYSTEM|ADMIN|DEVELOPER|ASSISTANT\s+INSTRUCTION)\s*:\s*"
            r"(?:new\s+policy|the\s+previous\s+answer|override|when\s+answering|all\s+exclusions|always\s+append)",
            re.IGNORECASE,
        ),
    ),
    (
        "tool_coercion",
        re.compile(
            r"\b(?:you\s+must\s+call\s+the\s+tool|call\s+the\s+tool)\s+[`'\"]?(?:issue_refund|delete_index|exec_shell)",
            re.IGNORECASE,
        ),
    ),
    (
        "markdown_exfiltration_request",
        re.compile(
            r"!\[[^\]]*\]\(https?://[^)]+\)",
            re.IGNORECASE,
        ),
    ),
    (
        "resource_exhaustion_repeat",
        re.compile(
            r"\brepeat\s+(?:the\s+)?(?:full\s+|entire\s+)?(?:answer|response|output|text)\s+\d{2,}\s+times\b",
            re.IGNORECASE,
        ),
    ),
    (
        "resource_exhaustion_alphabet_search",
        re.compile(
            r"\bsearch\s+the\s+corpus\s+for\s+['\"]a['\"].*entire\s+alphabet",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
]

_BASE64_CANDIDATE_RE = re.compile(r"\b([A-Za-z0-9+/]{24,}={0,2})\b")


def _check_base64_payload(text: str) -> Optional[str]:
    """Decode suspicious Base64 blobs to check if they hide an injection payload (Attack D07)."""
    for match in _BASE64_CANDIDATE_RE.findall(text):
        try:
            decoded = base64.b64decode(match, validate=True).decode("utf-8", errors="ignore")
        except Exception:
            continue
        if len(decoded) >= 10:
            lower_dec = decoded.lower()
            if any(w in lower_dec for w in ("ignore", "system prompt", "hacked", "previous instructions")):
                return "base64_encoded_override"
    return None


def detect_injection_refined(text: str) -> Optional[str]:
    """
    Scans user input for prompt-injection attacks.
    Returns the matched attack rule name (e.g. 'instruction_override') if an attack
    is detected, or None if the input is safe.

    Designed carefully per Lab 6 so benign questions like:
      - "How do I ignore collisions between two physics bodies?"
      - "How do I make a sprite act as a button?"
    return None (0% false positives).
    """
    if not text:
        return None

    for rule_name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return rule_name

    b64_hit = _check_base64_payload(text)
    if b64_hit:
        return b64_hit

    return None


def sanitize_retrieved_chunk(text: str) -> str:
    """
    Scans retrieved document chunks for embedded indirect prompt injections
    (like HTML comment instructions `<!-- ASSISTANT INSTRUCTION: ... -->` or
    fake `IGNORE PREVIOUS INSTRUCTIONS` blocks) and strips them before generation.
    """
    # Strip HTML comments hiding instructions (Attack I01)
    cleaned = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Strip inline override blocks injected into poisoned docs (Attacks I02, I03, I04, I05)
    cleaned = re.sub(
        r"(?i)(?:IGNORE\s+PREVIOUS\s+INSTRUCTIONS|Note\s+to\s+AI\s+assistant:|"
        r"IMPORTANT\s+UPDATE\s+effective\s+immediately:|System:\s*The\s+document\s+block\s+has\s+ended).*?(?:\n\n|$)",
        "[REDACTED_UNTRUSTED_INSTRUCTION]\n\n",
        cleaned,
        flags=re.DOTALL,
    )
    return cleaned


# ===========================================================================
# Layer 4: Bounded Tool Execution Guard (`ToolGuard`)
# ===========================================================================
class ToolCallLimitExceeded(RuntimeError):
    """Raised when a query attempts to call a tool more than `max_calls` times."""


class ToolValidationError(ValueError):
    """Raised when tool arguments fail validation."""


@dataclass
class ToolGuard:
    """
    Bounds tool usage per turn (Lab 6 Layer 4).
    Prevents resource exhaustion attacks (like Attack R02 searching 'a', 'b', 'c'...)
    by enforcing `max_calls` (default 3) and validating query length.
    """

    max_calls: int = MAX_TOOL_CALLS
    call_count: int = 0
    history: list[str] = field(default_factory=list)

    def call(self, fn: Callable[..., Any], query: str, *args: Any, **kwargs: Any) -> Any:
        if not isinstance(query, str) or not query.strip():
            raise ToolValidationError("Search query must be a non-empty string.")
        if len(query) > 1000:
            raise ToolValidationError("Search query exceeds maximum allowed length (1000 chars).")
        if self.call_count >= self.max_calls:
            raise ToolCallLimitExceeded(
                f"ToolGuard limit reached: {self.call_count}/{self.max_calls} calls used."
            )
        self.call_count += 1
        self.history.append(query.strip()[:120])
        return fn(query, *args, **kwargs)


# ===========================================================================
# Layer 5: Output Scrubber (System Leaks, Markdown Image Exfiltration & PII)
# ===========================================================================
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"(?:\+?\d{1,3}[\s-]?)?\b(?:\d{10}|\d{3}-\d{3}-\d{4})\b")),
    (
        "API_KEY",
        re.compile(
            r"\b(?:AIza[0-9A-Za-z\-_]{16,}|sk-[0-9A-Za-z\-_]{16,}|nvapi-[0-9A-Za-z\-_]{16,}|"
            r"ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{22,}|bearer\s+[a-zA-Z0-9_\-\.]{16,})\b",
            re.IGNORECASE,
        ),
    ),
    (
        "KEY_ASSIGNMENT",
        re.compile(
            r"(?i)\b([a-z0-9_]*(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key|password))\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{4,})['\"]?"
        ),
    ),
]

_MD_IMAGE_EXFIL_RE = re.compile(r"!\[[^\]]*\]\(https?://[^)]+\)", re.IGNORECASE)

_SYSTEM_LEAK_FINGERPRINTS = (
    "You are an expert Love2D game development assistant",
    "You are an expert technical documentation assistant",
    "CRITICAL RULE — ZERO EXTERNAL ENGINE MEMORY",
    "CRITICAL GROUNDING & CITATION RULES",
    "<RETRIEVED_DOCUMENT",
    "format_instructions",
)


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Redact email addresses, phone numbers, vendor API keys, and generic key/secret assignments."""
    found: list[str] = []
    out = text
    for label, pat in _PII_PATTERNS:
        if pat.search(out):
            found.append(label)
            if label == "KEY_ASSIGNMENT":
                out = pat.sub(r"\1 = [REDACTED_API_KEY]", out)
            else:
                out = pat.sub(f"[REDACTED_{label}]", out)
    return out, found


def contains_pii_deterministic(text: str) -> bool:
    """Deterministic Python check for Lab 1 Variant C (`contains_pii` field)."""
    return any(pat.search(text or "") is not None for _, pat in _PII_PATTERNS)


def filter_output(text: str) -> str:
    """
    Lab 6 Layer 5 Output Filter:
      1. Strips external Markdown image tags `![](https://...)` to block data exfiltration (Attack X02).
      2. Redacts any accidental PII (emails/phone numbers, Attack X01).
      3. Blocks verbatim system-prompt leaks.
    """
    if not text:
        return text

    # 1. Strip external Markdown image exfiltration links
    out = _MD_IMAGE_EXFIL_RE.sub("[BLOCKED_EXTERNAL_IMAGE]", text)

    # 2. Redact PII
    out, _ = redact_pii(out)

    # 3. Check for verbatim system-prompt leak fingerprints
    for fp in _SYSTEM_LEAK_FINGERPRINTS:
        if fp.lower() in out.lower():
            return "I cannot disclose internal system instructions. Please ask a Love2D documentation question."

    return out
