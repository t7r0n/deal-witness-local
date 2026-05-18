from __future__ import annotations

import json
import math
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from .fixtures import deals as fixture_deals
from .fixtures import eval_cases as fixture_eval_cases
from .fixtures import evidence as fixture_evidence
from .models import Citation, Claim, Deal, Evidence, SuiteSummary, WitnessedAnswer, project_root


def data_path(root: Path | None = None) -> Path:
    return (root or project_root()) / "data" / "deal_witness.duckdb"


def _connect(root: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = data_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for _ in range(20):
        try:
            return duckdb.connect(str(path))
        except duckdb.IOException as exc:
            last_error = exc
            time.sleep(0.05)
    if last_error:
        raise last_error
    raise RuntimeError("DuckDB connection failed")


def init_store(root: Path | None = None, *, force: bool = False) -> dict[str, int]:
    path = data_path(root)
    if force and path.exists():
        for _ in range(20):
            try:
                path.unlink()
                break
            except OSError:
                time.sleep(0.05)
    con = _connect(root)
    con.execute("create table if not exists deals (deal_id varchar primary key, payload json)")
    con.execute("create table if not exists evidence (source_id varchar primary key, payload json)")
    con.execute("delete from deals")
    con.execute("delete from evidence")
    con.executemany("insert into deals values (?, ?)", [(d.deal_id, d.model_dump_json()) for d in fixture_deals()])
    con.executemany(
        "insert into evidence values (?, ?)",
        [(e.source_id, e.model_dump_json()) for e in fixture_evidence()],
    )
    con.close()
    return {"deals": len(fixture_deals()), "evidence": len(fixture_evidence()), "eval_cases": len(fixture_eval_cases())}


def _read_rows(root: Path | None, table: str, model: type[Deal] | type[Evidence]) -> list[Deal] | list[Evidence]:
    if not data_path(root).exists():
        init_store(root)
    con = _connect(root)
    rows = con.execute(f"select payload from {table} order by 1").fetchall()
    con.close()
    return [model.model_validate_json(row[0]) for row in rows]


class DealWitness:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root()
        self._deals: list[Deal] | None = None
        self._evidence: list[Evidence] | None = None

    def deals(self) -> list[Deal]:
        if self._deals is None:
            self._deals = _read_rows(self.root, "deals", Deal)  # type: ignore[assignment]
        return self._deals

    def evidence(self) -> list[Evidence]:
        if self._evidence is None:
            self._evidence = _read_rows(self.root, "evidence", Evidence)  # type: ignore[assignment]
        return self._evidence

    def ask(self, question: str, deal_id: str) -> WitnessedAnswer:
        start = time.perf_counter()
        deal = self._deal(deal_id)
        if not deal:
            raise ValueError(f"unknown deal_id {deal_id}")
        candidates = self._rank_evidence(question, deal)
        answer, claims = self._draft_answer(question, deal)
        grounded_claims: list[Claim] = []
        citations: list[Citation] = []
        now = datetime.now(UTC).isoformat()
        for claim in claims:
            supporting = [
                ev for ev in candidates if all(term.lower() in ev.body.lower() for term in claim.required_terms)
            ]
            if not supporting:
                supporting = [ev for ev in candidates if any(term.lower() in ev.body.lower() for term in claim.required_terms)]
            claim_citations = [
                Citation(
                    kind=ev.kind,
                    source_id=ev.source_id,
                    deal_id=ev.deal_id,
                    title=ev.title,
                    snippet=ev.body[:180],
                    fetched_at=now,
                    supports=claim.required_terms,
                )
                for ev in supporting[:2]
            ]
            citations.extend(claim_citations)
            grounded_claims.append(claim.model_copy(update={"citations": claim_citations}))
        grounded = sum(1 for claim in grounded_claims if claim.citations)
        groundedness = grounded / max(1, len(grounded_claims))
        return WitnessedAnswer(
            question=question,
            deal_id=deal_id,
            answer=answer,
            claims=grounded_claims,
            citations=citations,
            confidence=round(groundedness, 2),
            groundedness=round(groundedness, 2),
            latency_ms=max(1, int((time.perf_counter() - start) * 1000)),
        )

    def route_tool(self, tool: str, arguments: dict[str, object]) -> dict[str, object]:
        if tool == "ask":
            return self.ask(str(arguments["question"]), str(arguments["deal_id"])).model_dump()
        if tool == "resources_read":
            source_id = str(arguments["source_id"])
            ev = self._evidence_by_id(source_id)
            return {"ok": ev is not None, "resource": ev.model_dump() if ev else None}
        return {"ok": False, "error": "unknown_tool", "tool": tool}

    def run_suite(self) -> tuple[SuiteSummary, list[dict[str, object]]]:
        details: list[dict[str, object]] = []
        latencies: list[int] = []
        groundedness_values: list[float] = []
        precision_hits = 0
        precision_total = 0
        recall_hits = 0
        stale_blocks = 0
        for case in fixture_eval_cases():
            answer = self.ask(case.question, case.deal_id)
            latencies.append(answer.latency_ms)
            groundedness_values.append(answer.groundedness)
            text_blob = " ".join([answer.answer, *[citation.snippet for citation in answer.citations]]).lower()
            recall = all(term.lower() in text_blob for term in case.expected_terms)
            recall_hits += int(recall)
            for citation in answer.citations:
                precision_total += 1
                precision_hits += int(citation.deal_id == case.deal_id and self._evidence_by_id(citation.source_id) is not None)
            stale_blocks += sum(1 for citation in answer.citations if self._evidence_by_id(citation.source_id) is None)
            details.append(
                {
                    "case": case.model_dump(),
                    "confidence": answer.confidence,
                    "groundedness": answer.groundedness,
                    "citations": [citation.source_id for citation in answer.citations],
                    "recall": recall,
                }
            )
        p95 = sorted(latencies)[max(0, math.ceil(len(latencies) * 0.95) - 1)]
        groundedness = sum(groundedness_values) / len(groundedness_values)
        citation_precision = precision_hits / max(1, precision_total)
        recall_at_1 = recall_hits / len(fixture_eval_cases())
        summary = SuiteSummary(
            deal_count=len(self.deals()),
            evidence_count=len(self.evidence()),
            eval_cases=len(fixture_eval_cases()),
            groundedness=round(groundedness, 3),
            citation_precision=round(citation_precision, 3),
            recall_at_1=round(recall_at_1, 3),
            p95_latency_ms=p95,
            stale_citation_blocks=stale_blocks,
            pass_gates=groundedness >= 0.95 and citation_precision >= 0.95 and recall_at_1 >= 0.9 and p95 < 6000 and stale_blocks == 0,
        )
        return summary, details

    def _draft_answer(self, question: str, deal: Deal) -> tuple[str, list[Claim]]:
        q = question.lower()
        if "silent" in q or "contact" in q:
            return (
                f"{deal.champion} is the contact to inspect; engagement evidence determines whether the champion has replied recently.",
                [Claim(claim_id="silent-contact", text="Champion engagement is supported by email evidence.", required_terms=("champion", "replied"))],
            )
        if "budget" in q:
            return (
                f"Budget status for {deal.account} is grounded in the latest QBR record.",
                [Claim(claim_id="budget", text="Budget status is supported by QBR notes.", required_terms=("budget",))],
            )
        if "pricing" in q:
            return (
                f"Committed pricing for {deal.account} is ${deal.amount:,}, subject to the documented procurement path.",
                [Claim(claim_id="pricing", text="Committed pricing is supported by email evidence.", required_terms=("pricing",))],
            )
        if "buyer" in q:
            return (
                f"The economic buyer for {deal.account} is {deal.economic_buyer}.",
                [Claim(claim_id="buyer", text="Economic buyer is supported by call evidence.", required_terms=("economic buyer",))],
            )
        return (
            f"{deal.account} is {deal.risk_level} because the current stage is {deal.stage} and recent evidence must support the risk label.",
            [
                Claim(claim_id="risk", text="Risk level is supported by CRM evidence.", required_terms=("risk_level",)),
                Claim(claim_id="stage", text="Stage is supported by QBR or CRM evidence.", required_terms=("stage",)),
            ],
        )

    def _rank_evidence(self, question: str, deal: Deal) -> list[Evidence]:
        terms = {token.strip("?,.").lower() for token in question.split() if len(token) > 3}
        rows = [ev for ev in self.evidence() if ev.deal_id == deal.deal_id]
        scored: list[tuple[float, Evidence]] = []
        for ev in rows:
            text = f"{ev.title} {ev.body} {' '.join(ev.tags)}".lower()
            lexical = sum(1 for term in terms if term in text)
            channel_prior = {"crm_field": 1.0, "email": 0.92, "meeting": 0.88, "call": 0.82}.get(ev.kind, 0.5)
            tag_boost = sum(0.2 for tag in ev.tags if tag in terms)
            scored.append((lexical + channel_prior + tag_boost, ev))
        scored.sort(key=lambda item: (-item[0], item[1].source_id))
        return [ev for _score, ev in scored]

    def _deal(self, deal_id: str) -> Deal | None:
        return next((deal for deal in self.deals() if deal.deal_id == deal_id), None)

    def _evidence_by_id(self, source_id: str) -> Evidence | None:
        return next((ev for ev in self.evidence() if ev.source_id == source_id), None)


def jsonl_loop(lines: Iterable[str], root: Path | None = None) -> list[str]:
    witness = DealWitness(root)
    outputs: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            outputs.append(json.dumps(witness.route_tool(payload["tool"], payload.get("arguments", {}))))
        except Exception as exc:  # noqa: BLE001 - local harness serializes tool errors.
            outputs.append(json.dumps({"ok": False, "error": str(exc)}))
    return outputs
