from __future__ import annotations

import json
import sys
from typing import Annotated

import typer
import uvicorn
from rich.console import Console

from .engine import DealWitness, init_store, jsonl_loop
from .models import project_root
from .runner import benchmark as run_benchmark
from .runner import export_demo_pack, output_dir, run_suite_and_write, verify_outputs

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def init_demo(force: bool = False) -> None:
    console.print_json(json.dumps(init_store(project_root(), force=force)))


@app.command()
def ask(question: str, deal_id: Annotated[str, typer.Option("--deal-id")] = "deal-0001") -> None:
    console.print_json(DealWitness().ask(question, deal_id).model_dump_json())


@app.command()
def resources_read(source_id: str) -> None:
    console.print_json(json.dumps(DealWitness().route_tool("resources_read", {"source_id": source_id})))


@app.command()
def run_suite() -> None:
    console.print_json(run_suite_and_write(project_root()).model_dump_json())


@app.command()
def dashboard() -> None:
    summary = run_suite_and_write(project_root())
    console.print_json(json.dumps({"dashboard": str(output_dir(project_root()) / "dashboard.html"), "pass_gates": summary.pass_gates}))


@app.command()
def verify() -> None:
    checks = verify_outputs(project_root())
    console.print_json(json.dumps(checks))
    if not all(checks.values()):
        raise typer.Exit(1)


@app.command()
def benchmark(iterations: int = 100) -> None:
    console.print_json(json.dumps(run_benchmark(project_root(), iterations=iterations)))


@app.command(name="export-demo-pack")
def export_demo_pack_command() -> None:
    console.print_json(json.dumps({"demo_pack": str(export_demo_pack(project_root()))}))


@app.command(name="tool-loop")
def tool_loop() -> None:
    for line in jsonl_loop(sys.stdin, project_root()):
        print(line)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8792) -> None:
    uvicorn.run("deal_witness_local.server:app", host=host, port=port, reload=False)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
