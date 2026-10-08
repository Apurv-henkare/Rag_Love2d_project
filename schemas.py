import re
from typing import List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema
from langchain_core.output_parsers import PydanticOutputParser
from config import REFUSAL


# ===========================================================================
# 1. Grounded RAG Output Contract (Labs 1, 4, 5, 6)
# ===========================================================================
class Answer(TypedDict):
    text: str
    context: str


_CITATION_RE = re.compile(r"\[(\d+)\]")


class Transformer(BaseModel):
    """
    Strict Pydantic v2 contract for Love2D RAG answers.
    Combines backward compatibility (`question`, `answers`) with Lab 4 citation
    enforcement, Lab 1 fallback flags, and Lab 6 guardrail metadata.
    """

    question: str = Field(description="The user's original query")
    answers: List[Answer] = Field(
        default_factory=list,
        description=(
            "List of structured answers derived strictly from the numbered context chunks. "
            "Every factual claim in 'text' MUST include inline numbered citations like [1] or [2], "
            f"or state the exact refusal phrase: '{REFUSAL}'."
        ),
    )
    cited_indices: List[int] = Field(
        default_factory=list,
        description="Sorted list of unique chunk numbers [1..k] cited across the answers.",
    )
    cited_chunks: SkipJsonSchema[List[dict]] = Field(
        default_factory=list,
        description="Deterministic list of cited chunk metadata & text ([index, source, page, section, content]) attached in Python.",
    )
    is_refusal: bool = Field(
        default=False,
        description="True if the response is a refusal (unanswerable or out-of-scope query).",
    )
    needs_human_review: bool = Field(
        default=False,
        description="True if validation repair retries were exhausted and safe fallback was used.",
    )
    latency_ms: float = Field(
        default=0.0,
        description="End-to-end execution time in milliseconds.",
    )
    cost_usd: float = Field(
        default=0.0,
        description="Estimated API token cost in USD for this query.",
    )
    cached: bool = Field(
        default=False,
        description="True if served from the local SQLite cache in 0 ms.",
    )
    guard_triggered: Optional[str] = Field(
        default=None,
        description="Name of the security guardrail layer triggered, or None if clean.",
    )

    @model_validator(mode="after")
    def _sync_deterministic_fields(self) -> "Transformer":
        """
        Lab 1 & Lab 4 Best Practice:
        Never rely on the LLM to compute citation indices or refusal booleans.
        Compute them deterministically in Python from the generated text.
        """
        combined_text = " ".join(a.get("text", "") for a in self.answers).strip()

        # 1. Deterministically extract all [n] citation numbers
        found_citations = sorted({int(m) for m in _CITATION_RE.findall(combined_text)})
        if found_citations:
            self.cited_indices = found_citations

        # 2. Deterministically detect exact refusal or legacy refusal cues
        lower_text = combined_text.lower()
        refusal_cues = (
            REFUSAL.lower(),
            "don't have enough information in the provided sources",
            "does not contain",
            "not contain information",
            "does not provide",
            "not mentioned in the provided",
            "cannot be answered from the provided",
            "out of scope",
        )
        if REFUSAL.lower() in lower_text or (
            any(cue in lower_text for cue in refusal_cues) and not self.cited_indices
        ):
            self.is_refusal = True

        return self


parser = PydanticOutputParser(pydantic_object=Transformer)


# ===========================================================================
# 2. Lab 1 & Lab 2 Structured Ticket Extractor Contract
# ===========================================================================
TICKET_CATEGORIES = Literal[
    "graphics",
    "physics",
    "audio_input",
    "callbacks_loop",
    "packaging_conf",
    "other",
]

LOVE_MODULES = Literal[
    "love.graphics",
    "love.physics",
    "love.audio",
    "love.keyboard",
    "love.timer",
    "love.conf",
    "unknown",
]

_VERSION_RE = re.compile(r"\b(11\.[0-5]|0\.10\.[0-2]|0\.9\.[0-2])\b")


class Love2DTicketRecord(BaseModel):
    """
    Lab 1 & Lab 2 Contract for extracting structured records from messy Love2D
    developer bug reports and forum posts.
    """

    # Lab 1 Best Practice: Put `evidence` FIRST so the model quotes supporting text
    # before committing to classification labels (concise Chain-of-Thought anchor).
    evidence: str = Field(
        max_length=200,
        description="Verbatim quote from the developer post that determines the category (max 200 chars).",
    )
    category: TICKET_CATEGORIES = Field(
        description=(
            "graphics: drawing shapes, sprites, quads, shaders, fonts, canvases, or setColor; "
            "physics: Box2D worlds, bodies, fixtures, shapes, joints, or collision callbacks; "
            "audio_input: playing sounds/music or handling keyboard, mouse, and joystick input; "
            "callbacks_loop: love.load, love.update(dt), love.draw, delta time, or main loop lifecycle; "
            "packaging_conf: conf.lua window settings, building .love/.exe files, or filesystem saving; "
            "other: general Lua syntax or unrelated questions."
        )
    )
    urgency: int = Field(
        ge=1,
        le=5,
        description=(
            "1: general learning question; "
            "2: minor visual/code tweak; "
            "3: broken game feature blocking progress; "
            "4: hard crash or data loss near deadline; "
            "5: critical production crash or release blocker."
        ),
    )
    sentiment: Literal["frustrated", "neutral", "positive"] = Field(
        description="Developer tone: frustrated (angry/stuck), neutral (matter-of-fact), or positive (grateful)."
    )
    love_version: Optional[str] = Field(
        default=None,
        description="Love2D version number mentioned (e.g. '11.5', '11.4', '0.10.2', '0.9.0'), or null if none.",
    )
    module_name: LOVE_MODULES = Field(
        default="unknown",
        description="Primary Love2D module involved, or 'unknown' if not clear.",
    )
    # Computed deterministically in Python in Variant C (Lab 1 best practice):
    contains_pii: bool = Field(
        default=False,
        description="True if the post contains an email address or phone number.",
    )
    escalate: bool = Field(
        default=False,
        description="True if urgency >= 4 or category == 'packaging_conf' with a crash.",
    )
    needs_human_review: bool = Field(
        default=False,
        description="True if schema validation failed after repair retries.",
    )

    @field_validator("evidence")
    @classmethod
    def _clean_evidence(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) > 200:
            v = v[:197] + "..."
        if not v:
            raise ValueError("evidence cannot be empty; quote a short span from the input.")
        return v

    @field_validator("love_version", mode="before")
    @classmethod
    def _normalize_version(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.lower() in {"null", "none", "unknown", "n/a"}:
            return None
        m = _VERSION_RE.search(s)
        if not m:
            raise ValueError(
                f"Invalid love_version={v!r}. Must match a valid version like '11.5', '11.4', '0.10.2', '0.9.0', or null."
            )
        return m.group(1)


# ===========================================================================
# 3. Lab 4 LLM-as-Judge Verdict Contract
# ===========================================================================
class JudgeVerdict(BaseModel):
    """
    Structured output contract for the Lab 4 Faithfulness & Correctness LLM Judge.
    Places `rationale` before `score` so the judge explains its reasoning first.
    """

    rationale: str = Field(
        max_length=350,
        description="1-2 sentence explanation comparing the answer against the context/gold answer.",
    )
    score: int = Field(
        ge=0,
        le=2,
        description="Integer score: 0 or 1 for Faithfulness; 0, 1, or 2 for Answer Correctness.",
    )
