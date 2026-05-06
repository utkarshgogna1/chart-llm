"""CLI entry point — `chart-llm <command>`."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="chart-llm: natural-language → Vega-Lite chart generation")


def _print_dataset_summary(console: Console, dataset_ctx) -> None:
    t = Table(
        title=f"Dataset: [bold]{dataset_ctx.name}[/bold] ({dataset_ctx.row_count:,} rows)",
        show_lines=False,
    )
    t.add_column("column", style="bold cyan")
    t.add_column("dtype")
    t.add_column("sample values", no_wrap=False)
    t.add_column("unique", justify="right")
    t.add_column("null", justify="right")
    for col in dataset_ctx.column_schema:
        t.add_row(
            col.name, col.dtype, ", ".join(col.sample_values),
            str(col.n_unique), str(col.n_null),
        )
    console.print(t)


@app.command()
def generate(
    csv: Path = typer.Argument(..., help="Path to input CSV file"),
    question: str = typer.Argument(..., help="Natural-language question about the data"),
    model: str = typer.Option("gemini-flash", help="Model: gemini-flash | llama-70b-groq | llama-8b-local"),
    output: Path = typer.Option(Path("chart.html"), help="Output HTML path (rendering in Prompt 7)"),
    max_retries: int = typer.Option(3, help="Max validation retry attempts"),
    validate: bool = typer.Option(False, "--validate", is_flag=True, help="Run validation + retry loop"),
) -> None:
    """Generate a Vega-Lite spec from a CSV and a natural-language question."""
    from chart_llm.models.registry import get_client
    from chart_llm.pipeline.dataset import build_dataset_context

    console = Console()
    dataset_ctx = build_dataset_context(csv)
    _print_dataset_summary(console, dataset_ctx)

    client = get_client(model)

    if not validate:
        from chart_llm.pipeline.generate import generate_spec
        with console.status(f"[bold blue]Generating with {model}…[/bold blue]"):
            result = generate_spec(client, dataset_ctx, question)
        console.print("\n[bold green]Generated Vega-Lite spec:[/bold green]")
        console.print_json(json.dumps(result.spec, indent=2))
        stats = Table(show_header=False, box=None, padding=(0, 1))
        stats.add_column("field", style="bold cyan")
        stats.add_column("value")
        stats.add_row("model", result.model_name)
        stats.add_row("latency", f"{result.latency_ms:.0f} ms")
        if result.prompt_tokens is not None:
            stats.add_row("prompt tokens", str(result.prompt_tokens))
        if result.completion_tokens is not None:
            stats.add_row("completion tokens", str(result.completion_tokens))
        console.print(stats)
        console.print("\n[dim]Run with --validate to enable the validation + retry loop.[/dim]")
        return

    # ── Validated path ────────────────────────────────────────────────────────
    from chart_llm.pipeline.retry import generate_validated_spec

    with console.status(f"[bold blue]Generating with {model} (validation on)…[/bold blue]"):
        run = generate_validated_spec(client, dataset_ctx, question, max_attempts=max_retries)

    console.print()
    for attempt in run.attempts:
        val = attempt.validation
        if val.ok:
            body = "[bold green]✓ All validation checks passed[/bold green]"
            border = "green"
        else:
            lines = [f"[bold red]✗ Failed at stage: {val.stage_failed}[/bold red]"]
            for err in val.errors:
                lines.append(f"  [yellow][{err.code}][/yellow] {err.path}")
                lines.append(f"    {err.message}")
                if err.suggestion:
                    lines.append(f"    [dim]→ {err.suggestion}[/dim]")
            body = "\n".join(lines)
            border = "red"
        console.print(Panel(
            body,
            title=f"Attempt {attempt.attempt_number} / {len(run.attempts)}",
            border_style=border,
            expand=False,
        ))

    if run.succeeded:
        console.print("\n[bold green]Final spec:[/bold green]")
        console.print_json(json.dumps(run.final_spec, indent=2))
    else:
        console.print(
            f"\n[bold red]Generation failed after {len(run.attempts)} attempt(s).[/bold red]"
        )

    tok = run.total_tokens
    tok_str = f"{tok.total:,}" if tok.total else "n/a"
    console.print(
        f"\n[dim]Attempts: {len(run.attempts)} | "
        f"Latency: {run.total_latency_ms:.0f} ms | "
        f"Tokens: {tok_str} | "
        f"Stop: {run.stop_reason}[/dim]"
    )


@app.command()
def render(
    spec_file: Path = typer.Argument(..., help="Path to a saved JSON spec file"),
    csv: Path = typer.Argument(..., help="Path to the source CSV"),
    out: Path = typer.Option(Path("chart.html"), help="Output path (.html, .png, or .svg)"),
    expected_data_name: str = typer.Option("table", help="Expected data.name value in the spec"),
    scale: float = typer.Option(2.0, help="Scale factor for PNG output"),
) -> None:
    """Render a Vega-Lite spec + CSV to HTML, PNG, or SVG."""
    from chart_llm.pipeline.dataset import build_dataset_context
    from chart_llm.rendering import RenderError, render_to_html, render_to_png, render_to_svg

    console = Console()
    spec = json.loads(spec_file.read_text())
    dataset_ctx = build_dataset_context(csv)

    suffix = out.suffix.lower()
    try:
        if suffix == ".png":
            data = render_to_png(spec, dataset_ctx.df, expected_data_name, scale=scale)
            out.write_bytes(data)
        elif suffix == ".svg":
            svg = render_to_svg(spec, dataset_ctx.df, expected_data_name)
            out.write_text(svg, encoding="utf-8")
        else:
            html = render_to_html(spec, dataset_ctx.df, expected_data_name)
            out.write_text(html, encoding="utf-8")
    except RenderError as exc:
        console.print(f"[bold red]Render error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"[bold green]✓[/bold green] Chart written to [bold]{out}[/bold]")


@app.command()
def benchmark(
    datasets: Path = typer.Option(Path("benchmarks/datasets"), help="Datasets directory"),
    queries: Path = typer.Option(Path("benchmarks/queries"), help="Queries directory"),
    results: Path = typer.Option(Path("benchmarks/results"), help="Results output directory"),
    max_retries: int = typer.Option(3, help="Max validation retry attempts"),
) -> None:
    """Run the full 3-model benchmark and print a summary table."""
    from rich import print as rprint
    rprint("[yellow]TODO:[/yellow] benchmark not yet implemented")


@app.command("fetch-schema")
def fetch_schema(
    version: str = typer.Option("5.20.1", help="Vega-Lite schema version to download"),
) -> None:
    """Download the Vega-Lite JSON schema for local validation."""
    from chart_llm.validation.schema import fetch_schema as _fetch

    console = Console()
    with console.status(f"[bold blue]Downloading Vega-Lite v{version} schema…[/bold blue]"):
        path = _fetch(version=version)
    console.print(f"[bold green]✓[/bold green] Schema cached at [bold]{path}[/bold]")


@app.command("validate")
def validate_cmd(
    spec_file: Path = typer.Argument(..., help="Path to a saved JSON spec file"),
    csv: Path = typer.Argument(..., help="Path to the source CSV"),
    expected_data_name: str = typer.Option("table", help="Expected data.name value"),
) -> None:
    """Run the full validation pipeline against a saved spec and print results."""
    from chart_llm.pipeline.dataset import build_dataset_context
    from chart_llm.validation.pipeline import run_validation

    console = Console()
    spec = json.loads(spec_file.read_text())
    dataset_ctx = build_dataset_context(csv)
    result = run_validation(spec, dataset_ctx, expected_data_name)

    if result.ok:
        console.print("[bold green]✓ Spec passed all validation checks.[/bold green]")
        return

    console.print(f"[bold red]✗ Validation failed at stage: {result.stage_failed}[/bold red]\n")
    for err in result.errors:
        console.print(f"  [yellow][{err.code}][/yellow] {err.path}")
        console.print(f"    {err.message}")
        if err.suggestion:
            console.print(f"    [dim]→ {err.suggestion}[/dim]")
    raise typer.Exit(code=1)


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
