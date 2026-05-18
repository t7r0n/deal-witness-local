from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .engine import DealWitness


def create_app() -> FastAPI:
    app = FastAPI(title="Deal Witness Local", version="0.1.0")
    witness = DealWitness()

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "deals": len(witness.deals()), "evidence": len(witness.evidence())}

    @app.post("/ask")
    def ask(arguments: dict[str, Any]) -> dict[str, Any]:
        return witness.ask(str(arguments["question"]), str(arguments["deal_id"])).model_dump()

    @app.post("/tools/{tool_name}")
    def tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return witness.route_tool(tool_name, arguments)

    return app


app = create_app()
