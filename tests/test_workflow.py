from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from deal_witness_local.engine import DealWitness, init_store, jsonl_loop
from deal_witness_local.runner import benchmark, export_demo_pack, run_suite_and_write, verify_outputs


def test_ask_returns_witnesses(tmp_path: Path) -> None:
    init_store(tmp_path, force=True)
    answer = DealWitness(tmp_path).ask("Why is Acme-Q3 trending red?", "deal-0001")
    assert answer.confidence >= 0.95
    assert answer.citations
    assert all(citation.deal_id == "deal-0001" for citation in answer.citations)


def test_resource_read_and_unknown_tool(tmp_path: Path) -> None:
    init_store(tmp_path, force=True)
    witness = DealWitness(tmp_path)
    assert witness.route_tool("resources_read", {"source_id": "email-0001"})["ok"] is True
    assert witness.route_tool("unknown", {})["ok"] is False


def test_suite_outputs(tmp_path: Path) -> None:
    init_store(tmp_path, force=True)
    summary = run_suite_and_write(tmp_path)
    assert summary.eval_cases == 50
    assert summary.pass_gates
    assert all(verify_outputs(tmp_path).values())
    assert benchmark(tmp_path, iterations=3)["pass_gates"] is True
    assert export_demo_pack(tmp_path).exists()


def test_jsonl_tool_loop(tmp_path: Path) -> None:
    init_store(tmp_path, force=True)
    request = {"tool": "ask", "arguments": {"question": "What pricing was committed?", "deal_id": "deal-0001"}}
    [line] = jsonl_loop([json.dumps(request)], tmp_path)
    payload = json.loads(line)
    assert payload["confidence"] >= 0.95
    assert payload["citations"]


def test_cli_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "deal_witness_local.cli", "ask", "Who is the economic buyer?", "--deal-id", "deal-0001"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "economic" in result.stdout.lower()
