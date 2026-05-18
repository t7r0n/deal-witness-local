from __future__ import annotations

from jinja2 import Template

from .models import SuiteSummary


HTML = Template(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Deal Witness Local</title>
  <style>
    :root { color-scheme: light dark; --bg:#f7f8fb; --fg:#162033; --muted:#66728a; --card:#fff; --line:#dde4ef; --a:#1f6f78; --b:#6a8f3f; --w:#a46411; }
    @media (prefers-color-scheme: dark) { :root { --bg:#10141a; --fg:#eef3f8; --muted:#a7b2c1; --card:#181e26; --line:#2c3746; --a:#78c0c8; --b:#a9c46f; --w:#f0bc67; } }
    * { box-sizing: border-box; }
    body { margin:0; background:var(--bg); color:var(--fg); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    header, main { max-width:1180px; margin:auto; padding:28px; }
    h1 { margin:0; font-size:clamp(2rem,4vw,4rem); letter-spacing:0; }
    h2 { margin:0 0 14px; font-size:1.05rem; }
    p { color:var(--muted); max-width:760px; line-height:1.45; }
    .grid { display:grid; gap:16px; }
    .metrics { grid-template-columns:repeat(4,minmax(0,1fr)); }
    .cols { grid-template-columns:1fr 1fr; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:18px; box-shadow:0 10px 24px rgba(20,31,50,.06); }
    .metric strong { display:block; font-size:2rem; color:var(--a); }
    .metric span { color:var(--muted); }
    .bar { height:12px; border-radius:999px; background:color-mix(in srgb,var(--line),var(--card) 35%); overflow:hidden; }
    .bar i { display:block; height:100%; background:var(--b); }
    table { width:100%; border-collapse:collapse; font-size:.9rem; }
    th,td { text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
    th { color:var(--muted); }
    code { color:var(--a); white-space:nowrap; }
    .ok { color:var(--b); font-weight:700; }
    .warn { color:var(--w); font-weight:700; }
    @media (max-width:820px){ header,main{padding:20px}.metrics,.cols{grid-template-columns:1fr} table{font-size:.82rem} }
  </style>
</head>
<body>
  <header>
    <h1>Deal Witness Local</h1>
    <p>Two-phase grounding for revenue-style deal answers: draft claims, re-fetch source records, and score confidence from live witness coverage.</p>
  </header>
  <main class="grid">
    <section class="grid metrics">
      <div class="card metric"><strong>{{ summary.deal_count }}</strong><span>Deals</span></div>
      <div class="card metric"><strong>{{ "%.0f"|format(summary.groundedness * 100) }}%</strong><span>Groundedness</span></div>
      <div class="card metric"><strong>{{ "%.0f"|format(summary.citation_precision * 100) }}%</strong><span>Citation precision</span></div>
      <div class="card metric"><strong>{{ summary.p95_latency_ms }} ms</strong><span>P95 latency</span></div>
    </section>
    <section class="grid cols">
      <div class="card">
        <h2>Evaluation Gates</h2>
        {% for label, value, target in gates %}
        <div style="margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>{{ label }}</span><span class="{{ 'ok' if value >= target else 'warn' }}">{{ value }}</span></div>
          <div class="bar"><i style="width: {{ [100, (value / target * 100)|int]|min }}%"></i></div>
        </div>
        {% endfor %}
      </div>
      <div class="card">
        <h2>Run Summary</h2>
        <p>Evidence records: <strong>{{ summary.evidence_count }}</strong></p>
        <p>Eval cases: <strong>{{ summary.eval_cases }}</strong></p>
        <p>Stale citation blocks: <strong>{{ summary.stale_citation_blocks }}</strong></p>
        <p>Status: <span class="{{ 'ok' if summary.pass_gates else 'warn' }}">{{ 'PASS' if summary.pass_gates else 'FAIL' }}</span></p>
      </div>
    </section>
    <section class="card">
      <h2>Golden Questions</h2>
      <table>
        <thead><tr><th>Case</th><th>Confidence</th><th>Citations</th><th>Recall</th></tr></thead>
        <tbody>
        {% for row in details[:12] %}
          <tr><td><code>{{ row.case.case_id }}</code></td><td>{{ row.confidence }}</td><td>{{ row.citations|join(", ") }}</td><td class="{{ 'ok' if row.recall else 'warn' }}">{{ 'hit' if row.recall else 'miss' }}</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>"""
)


def render_dashboard(summary: SuiteSummary, details: list[dict[str, object]]) -> str:
    gates = [
        ("Groundedness", summary.groundedness, 0.95),
        ("Citation precision", summary.citation_precision, 0.95),
        ("Recall@1", summary.recall_at_1, 0.9),
    ]
    return HTML.render(summary=summary, details=details, gates=gates)
