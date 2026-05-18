# Deal Witness Local

Local two-phase grounding harness for revenue-style deal answers.

The project simulates an agent asking questions over CRM, email, meeting, and call evidence. It generates an answer, extracts atomic claims, re-fetches the cited source records, and returns a witnessed answer whose confidence is based on grounded coverage rather than model self-reporting.

## Features

- Deterministic local corpus of 64 synthetic deals with email, meeting, call, and CRM evidence.
- Six intent tools: deal risk, silent champion, budget confirmation, pricing commitment, economic buyer, and pipeline health.
- Two-phase grounding: answer first, then live citation re-fetch and claim coverage scoring.
- Reciprocal-rank fusion across evidence channels for support ranking.
- JSONL tool loop and loopback HTTP API for local agent integration tests.
- Eval suite, verifier, benchmark, static dashboard, and demo-pack export.

## Quickstart

```bash
uv sync --extra dev
uv run deal-witness init-demo --force
uv run deal-witness ask "Why is Acme-Q3 trending red?" --deal-id deal-0001
uv run deal-witness run-suite
uv run deal-witness verify
uv run deal-witness dashboard
```

HTTP API:

```bash
uv run deal-witness serve --host 127.0.0.1 --port 8792
```

JSONL tool loop:

```bash
printf '{"tool":"ask","arguments":{"question":"Why is Acme-Q3 trending red?","deal_id":"deal-0001"}}\n' | uv run deal-witness tool-loop
```

## Validation

```bash
uv run ruff check .
uv run pytest -q
uv run deal-witness run-suite
uv run deal-witness benchmark --iterations 100
uv run deal-witness verify
```

Generated runtime data is excluded from git.
