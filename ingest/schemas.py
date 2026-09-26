"""Pydantic contracts for curriculum data.

`subject` is present on every node even though the pilot ships mathematics
alone. Adding Science later should be an ingest run, not a schema migration.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

NodeLevel = Literal["standard", "indicator"]

# Strand numbers are stable across B7-B9 in the mathematics curriculum.
MATHS_STRANDS: dict[int, str] = {
    1: "Number",
    2: "Algebra",
    3: "Geometry and Measurement",
    4: "Handling Data",
}

# A title is a short functional name for the skill. Anything longer is almost
# certainly exemplar prose bleeding in, which must not be stored.
MAX_TITLE_CHARS = 300


class StrandRef(BaseModel):
    number: int
    title: str | None = None


class Source(BaseModel):
    document: str
    edition: str
    page: int
    retrieved: date


class CurriculumNode(BaseModel):
    """One content standard or indicator from the NaCCA Common Core Programme."""

    model_config = ConfigDict(populate_by_name=True)

    code: str
    subject: str = "mathematics"
    level: NodeLevel
    class_: str = Field(alias="class")
    strand: StrandRef
    sub_strand: StrandRef
    parent: str | None = None
    title: str
    core_competencies: list[str] = Field(default_factory=list)
    source: Source

    @field_validator("code")
    @classmethod
    def code_is_canonical(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"B[789](\.\d+){3,4}", v):
            raise ValueError(f"non-canonical code: {v!r}")
        return v

    @field_validator("title")
    @classmethod
    def title_is_short(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("empty title")
        if len(v) > MAX_TITLE_CHARS:
            raise ValueError(f"title exceeds {MAX_TITLE_CHARS} chars: {v[:60]!r}...")
        return v


class Reject(BaseModel):
    """An extraction the pipeline could not trust. Never dropped silently."""

    page: int
    reason: str
    raw: str
    repaired_to: str | None = None


class Chunk(BaseModel):
    """A passage of openly licensed prose, mapped onto curriculum indicators.

    Provenance is mandatory rather than best-effort: CC BY compliance requires
    an attribution string, and reconstructing one retroactively across thousands
    of chunks is miserable.
    """

    id: str
    subject: str = "mathematics"
    source_id: str
    grade: int
    heading_path: list[str]
    text: str
    url: str
    licence: str
    attribution: str
    retrieved: date
    chunk_index: int
    word_count: int
    indicators: list[str] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def text_is_substantial(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v.split()) < 20:
            raise ValueError("chunk too short to be useful")
        return v

    @field_validator("licence")
    @classmethod
    def licence_is_permissive(cls, v: str) -> str:
        """Guards the corpus against non-commercial material entering by accident."""
        allowed = {"CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-4.0"}
        if v not in allowed:
            raise ValueError(f"licence {v!r} not in permitted set {sorted(allowed)}")
        return v
