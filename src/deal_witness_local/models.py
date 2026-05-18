from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    source_id: str
    deal_id: str
    title: str
    snippet: str
    fetched_at: str
    supports: tuple[str, ...]


class Claim(BaseModel):
    claim_id: str
    text: str
    required_terms: tuple[str, ...]
    citations: list[Citation] = Field(default_factory=list)


class WitnessedAnswer(BaseModel):
    question: str
    deal_id: str
    answer: str
    claims: list[Claim]
    citations: list[Citation]
    confidence: float
    groundedness: float
    latency_ms: int


class Deal(BaseModel):
    model_config = ConfigDict(frozen=True)

    deal_id: str
    account: str
    stage: str
    amount: int
    close_quarter: str
    champion: str
    economic_buyer: str
    risk_level: str
    evidence_ids: tuple[str, ...]


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    deal_id: str
    kind: str
    title: str
    body: str
    timestamp: str
    tags: tuple[str, ...]


class EvalCase(BaseModel):
    case_id: str
    deal_id: str
    question: str
    expected_terms: tuple[str, ...]


class SuiteSummary(BaseModel):
    deal_count: int
    evidence_count: int
    eval_cases: int
    groundedness: float
    citation_precision: float
    recall_at_1: float
    p95_latency_ms: int
    stale_citation_blocks: int
    pass_gates: bool
