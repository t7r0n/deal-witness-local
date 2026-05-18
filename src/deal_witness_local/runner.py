from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import duckdb

from .dashboard import render_dashboard
from .engine import DealWitness, data_path
from .models import SuiteSummary, project_root


def output_dir(root: Path | None = None) -> Path:
    path = (root or project_root()) / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_suite_and_write(root: Path | None = None) -> SuiteSummary:
    summary, details = DealWitness(root).run_suite()
    out = output_dir(root)
    (out / "summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    (out / "eval_details.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    (out / "dashboard.html").write_text(render_dashboard(summary, details), encoding="utf-8")
    (out / "report.md").write_text(_report(summary), encoding="utf-8")
    _write_run_store(root, summary)
    return summary


def _write_run_store(root: Path | None, summary: SuiteSummary) -> None:
    runs = (root or project_root()) / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(runs / "deal_witness_runs.duckdb"))
    con.execute(
        """
        create table if not exists runs (
            created_at double,
            deal_count integer,
            groundedness double,
            citation_precision double,
            p95_latency_ms integer,
            pass_gates boolean
        )
        """
    )
    con.execute(
        "insert into runs values (?, ?, ?, ?, ?, ?)",
        [time.time(), summary.deal_count, summary.groundedness, summary.citation_precision, summary.p95_latency_ms, summary.pass_gates],
    )
    con.close()


def _report(summary: SuiteSummary) -> str:
    return f"""# Deal Witness Local Report

- Deals: {summary.deal_count}
- Evidence records: {summary.evidence_count}
- Eval cases: {summary.eval_cases}
- Groundedness: {summary.groundedness:.3f}
- Citation precision: {summary.citation_precision:.3f}
- Recall@1: {summary.recall_at_1:.3f}
- P95 latency: {summary.p95_latency_ms} ms
- Stale citation blocks: {summary.stale_citation_blocks}
- Status: {"PASS" if summary.pass_gates else "FAIL"}
"""


def verify_outputs(root: Path | None = None) -> dict[str, bool]:
    root = root or project_root()
    out = output_dir(root)
    checks = {
        "store_exists": data_path(root).exists(),
        "summary_exists": (out / "summary.json").exists(),
        "details_exists": (out / "eval_details.json").exists(),
        "dashboard_exists": (out / "dashboard.html").exists(),
        "report_exists": (out / "report.md").exists(),
    }
    if checks["summary_exists"]:
        summary = SuiteSummary.model_validate_json((out / "summary.json").read_text(encoding="utf-8"))
        checks.update(
            {
                "groundedness_gate": summary.groundedness >= 0.95,
                "precision_gate": summary.citation_precision >= 0.95,
                "recall_gate": summary.recall_at_1 >= 0.9,
                "latency_gate": summary.p95_latency_ms < 6000,
                "stale_gate": summary.stale_citation_blocks == 0,
                "pass_gates": summary.pass_gates,
            }
        )
    return checks


def benchmark(root: Path | None = None, *, iterations: int = 100) -> dict[str, float | int | bool]:
    min_groundedness = 1.0
    min_precision = 1.0
    max_latency = 0
    all_pass = True
    for _ in range(iterations):
        summary, _details = DealWitness(root).run_suite()
        min_groundedness = min(min_groundedness, summary.groundedness)
        min_precision = min(min_precision, summary.citation_precision)
        max_latency = max(max_latency, summary.p95_latency_ms)
        all_pass = all_pass and summary.pass_gates
    result = {
        "iterations": iterations,
        "min_groundedness": min_groundedness,
        "min_citation_precision": min_precision,
        "max_p95_latency_ms": max_latency,
        "pass_gates": all_pass,
    }
    (output_dir(root) / "benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def export_demo_pack(root: Path | None = None) -> Path:
    root = root or project_root()
    out = output_dir(root)
    if not (out / "summary.json").exists():
        run_suite_and_write(root)
    archive = out / "demo-pack.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("summary.json", "eval_details.json", "dashboard.html", "report.md", "benchmark.json"):
            path = out / name
            if path.exists():
                zf.write(path, arcname=name)
    return archive
