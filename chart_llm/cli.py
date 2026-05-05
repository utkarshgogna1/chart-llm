"""CLI entry point — `chart-llm <command>`."""

from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="chart-llm: natural-language → Vega-Lite chart generation")


@app.command()
def generate(
    csv: Path = typer.Argument(..., help="Path to input CSV file"),
    question: str = typer.Argument(..., help="Natural-language question about the data"),
    model: str = typer.Option("gemini", help="Model to use: gemini | groq | ollama"),
    output: Path = typer.Option(Path("chart.html"), help="Output HTML path"),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip validation loop"),
    max_retries: int = typer.Option(3, help="Max validation retry attempts"),
) -> None:
    """Generate a Vega-Lite chart from a CSV and a question."""
    # TODO: load df, pick model, call run_pipeline, render HTML
    rprint(f"[yellow]TODO:[/yellow] generate chart for '{question}' using {model}")


@app.command()
def benchmark(
    datasets: Path = typer.Option(Path("benchmarks/datasets"), help="Datasets directory"),
    queries: Path = typer.Option(Path("benchmarks/queries"), help="Queries directory"),
    results: Path = typer.Option(Path("benchmarks/results"), help="Results output directory"),
    max_retries: int = typer.Option(3, help="Max validation retry attempts"),
) -> None:
    """Run the full 3-model benchmark and print a summary table."""
    # TODO: call run_benchmark_sync, display results with Rich Table
    rprint("[yellow]TODO:[/yellow] benchmark not yet implemented")


@app.command("fetch-schema")
def fetch_schema(
    version: str = typer.Option("5.20.1", help="Vega-Lite schema version to download"),
) -> None:
    """Download the Vega-Lite JSON schema for local validation."""
    # TODO: download from https://vega.github.io/schema/vega-lite/v{version}.json
    # TODO: save to chart_llm/validation/vega-lite-schema.json
    rprint(f"[yellow]TODO:[/yellow] fetch schema v{version}")


@app.command("test-model")
def test_model(
    name: str = typer.Argument(..., help="Model name: gemini-flash | llama-70b-groq | llama-8b-local"),
) -> None:
    """Send a smoke-test prompt and display the model response."""
    from chart_llm.models.registry import get_client

    console = Console()
    client = get_client(name)
    prompt = 'Reply with the JSON object {"ok": true} and nothing else.'

    with console.status(f"[bold blue]Querying {name}…[/bold blue]"):
        response = client.generate(system="You are a helpful assistant.", user=prompt)

    table = Table(title=f"test-model: {name}", show_header=False, min_width=50)
    table.add_column("field", style="bold cyan")
    table.add_column("value")
    table.add_row("model name", response.model_name)
    table.add_row("response", response.text.strip())
    table.add_row("latency", f"{response.latency_ms:.1f} ms")
    if response.prompt_tokens is not None:
        table.add_row("prompt tokens", str(response.prompt_tokens))
    if response.completion_tokens is not None:
        table.add_row("completion tokens", str(response.completion_tokens))
    console.print(table)


if __name__ == "__main__":
    app()
