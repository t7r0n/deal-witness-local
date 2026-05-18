from __future__ import annotations

from .models import Deal, EvalCase, Evidence


ACCOUNTS = (
    "Acme",
    "Northwind",
    "Globex",
    "Initech",
    "Umbrella",
    "Soylent",
    "Stark",
    "Wayne",
)


def deals() -> list[Deal]:
    rows: list[Deal] = []
    for idx in range(1, 65):
        account = ACCOUNTS[(idx - 1) % len(ACCOUNTS)]
        risk = "red" if idx % 4 == 1 else "yellow" if idx % 4 == 2 else "green"
        stage = "procurement" if risk == "red" else "legal" if risk == "yellow" else "technical validation"
        rows.append(
            Deal(
                deal_id=f"deal-{idx:04d}",
                account=f"{account}-Q{((idx + 1) % 4) + 1}",
                stage=stage,
                amount=75000 + idx * 9250,
                close_quarter=f"2026-Q{((idx + 1) % 4) + 1}",
                champion=f"{account.lower()}-champion@example.test",
                economic_buyer=f"{account.lower()}-cfo@example.test",
                risk_level=risk,
                evidence_ids=(
                    f"email-{idx:04d}",
                    f"meeting-{idx:04d}",
                    f"call-{idx:04d}",
                    f"crm-{idx:04d}",
                ),
            )
        )
    return rows


def evidence() -> list[Evidence]:
    rows: list[Evidence] = []
    for deal in deals():
        n = int(deal.deal_id.split("-")[1])
        silence = "champion has not replied for 21 days" if deal.risk_level == "red" else "champion replied this week"
        budget = "budget confirmed by finance" if deal.risk_level != "red" else "budget approval missing"
        pricing = f"committed pricing is ${deal.amount:,} with procurement review"
        buyer = f"economic buyer is {deal.economic_buyer}"
        rows.extend(
            [
                Evidence(
                    source_id=f"email-{n:04d}",
                    deal_id=deal.deal_id,
                    kind="email",
                    title=f"{deal.account} pricing thread",
                    body=f"{silence}; {pricing}; requested security addendum.",
                    timestamp=f"2026-04-{(n % 24) + 1:02d}T10:00:00Z",
                    tags=("silence" if deal.risk_level == "red" else "engaged", "pricing"),
                ),
                Evidence(
                    source_id=f"meeting-{n:04d}",
                    deal_id=deal.deal_id,
                    kind="meeting",
                    title=f"{deal.account} QBR notes",
                    body=f"{budget}; close plan targets {deal.close_quarter}; stage is {deal.stage}.",
                    timestamp=f"2026-04-{(n % 24) + 1:02d}T16:00:00Z",
                    tags=("budget", "qbr"),
                ),
                Evidence(
                    source_id=f"call-{n:04d}",
                    deal_id=deal.deal_id,
                    kind="call",
                    title=f"{deal.account} discovery call",
                    body=f"{buyer}; key pain is forecast accuracy; legal path is documented.",
                    timestamp=f"2026-04-{(n % 24) + 1:02d}T18:00:00Z",
                    tags=("buyer", "pain"),
                ),
                Evidence(
                    source_id=f"crm-{n:04d}",
                    deal_id=deal.deal_id,
                    kind="crm_field",
                    title=f"{deal.account} opportunity fields",
                    body=f"risk_level={deal.risk_level}; stage={deal.stage}; amount={deal.amount}; close_quarter={deal.close_quarter}.",
                    timestamp=f"2026-04-{(n % 24) + 1:02d}T20:00:00Z",
                    tags=("crm", deal.risk_level),
                ),
            ]
        )
    return rows


def eval_cases() -> list[EvalCase]:
    questions = (
        ("risk", "Why is this deal trending red?", ("risk", "stage")),
        ("silent", "Which contact has gone silent?", ("champion", "replied")),
        ("budget", "Was budget confirmed in the last QBR?", ("budget",)),
        ("pricing", "What pricing was committed?", ("pricing",)),
        ("buyer", "Who is the economic buyer?", ("economic buyer",)),
    )
    cases: list[EvalCase] = []
    for deal in deals()[:50]:
        key, question, terms = questions[len(cases) % len(questions)]
        cases.append(
            EvalCase(
                case_id=f"{key}-{deal.deal_id}",
                deal_id=deal.deal_id,
                question=question,
                expected_terms=terms,
            )
        )
    return cases
