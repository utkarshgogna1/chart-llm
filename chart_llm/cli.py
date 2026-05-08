"""CLI entry point — `chart-llm <command>`."""

import difflib
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

app = typer.Typer(help="chart-llm: natural-language → Vega-Lite chart generation")

bench_app = typer.Typer(help="Benchmark commands.")
app.add_typer(bench_app, name="bench")


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
    check_render: bool = typer.Option(False, "--check-render", is_flag=True, help="Add render check as final validation stage (requires --validate)"),
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
        run = generate_validated_spec(client, dataset_ctx, question, max_attempts=max_retries, include_render=check_render)

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


@bench_app.command("run")
def bench_run(
    models: str = typer.Option(
        "gemini-flash,llama-70b-groq,llama-8b-local",
        help="Comma-separated model names",
    ),
    modes: str = typer.Option("baseline,validated", help="Comma-separated modes"),
    max_attempts: int = typer.Option(3, help="Max validation retry attempts"),
    output: Path = typer.Option(
        Path("benchmarks/results/run.jsonl"), help="Output JSONL file"
    ),
    queries_dir: Path = typer.Option(
        Path("benchmarks/queries"), help="Directory containing query JSON files"
    ),
    datasets_dir: Path = typer.Option(
        Path("benchmarks/datasets"), help="Directory containing CSV datasets"
    ),
    no_resume: bool = typer.Option(False, "--no-resume", help="Re-run already-recorded triples"),
) -> None:
    """Run the benchmark across models and modes, appending results to a JSONL file."""
    from chart_llm.eval.runner import run_benchmark as _run

    model_names = [m.strip() for m in models.split(",") if m.strip()]
    mode_list = [m.strip() for m in modes.split(",") if m.strip()]

    console = Console()
    console.print(
        f"[bold blue]Running benchmark:[/bold blue] "
        f"{len(model_names)} model(s) × {len(mode_list)} mode(s)"
    )
    _run(
        model_names=model_names,
        modes=mode_list,
        queries_dir=queries_dir,
        datasets_dir=datasets_dir,
        output_path=output,
        max_attempts=max_attempts,
        resume=not no_resume,
    )
    console.print(f"\n[bold green]✓[/bold green] Results written to [bold]{output}[/bold]")


@bench_app.command("report")
def bench_report(
    input: Path = typer.Option(
        Path("benchmarks/results/run.jsonl"), help="JSONL results file"
    ),
    output: Path = typer.Option(
        Path("benchmarks/results/REPORT.md"), help="Output Markdown report"
    ),
) -> None:
    """Build a Markdown report from a benchmark JSONL file."""
    from chart_llm.eval.report import build_report as _build

    console = Console()
    if not input.exists():
        console.print(f"[bold red]Error:[/bold red] {input} not found.")
        raise typer.Exit(code=1)
    _build(input, output)
    console.print(f"[bold green]✓[/bold green] Report written to [bold]{output}[/bold]")


@bench_app.command("list")
def bench_list(
    queries_dir: Path = typer.Option(
        Path("benchmarks/queries"), help="Directory containing query JSON files"
    ),
) -> None:
    """Pretty-print all benchmark queries as a table."""
    from chart_llm.eval.queries import load_benchmark

    console = Console()
    queries = load_benchmark(queries_dir)
    if not queries:
        console.print("[yellow]No queries found.[/yellow]")
        return

    t = Table(title=f"Benchmark Queries ({len(queries)} total)", show_lines=False)
    t.add_column("id", style="bold cyan")
    t.add_column("dataset")
    t.add_column("difficulty")
    t.add_column("tags")
    t.add_column("question", no_wrap=False)
    for q in queries:
        t.add_row(q.id, q.dataset, q.difficulty, ", ".join(q.tags), q.question)
    console.print(t)


@bench_app.command("inspect")
def bench_inspect(
    query_id: str = typer.Argument(..., help="Query ID to inspect (e.g. sales_003)"),
    input: Path = typer.Option(
        Path("benchmarks/results/smoke.jsonl"), help="JSONL results file"
    ),
    queries_dir: Path = typer.Option(
        Path("benchmarks/queries"), help="Directory containing query JSON files"
    ),
) -> None:
    """Print ground-truth vs predicted spec, mismatches, and unified diff for a query."""
    from chart_llm.eval.queries import load_benchmark
    from chart_llm.eval.runner import BenchmarkRecord

    console = Console()

    if not input.exists():
        console.print(f"[bold red]Error:[/bold red] {input} not found.")
        raise typer.Exit(code=1)

    queries = {q.id: q for q in load_benchmark(queries_dir)}
    if query_id not in queries:
        console.print(f"[bold red]Error:[/bold red] Query {query_id!r} not found in {queries_dir}")
        raise typer.Exit(code=1)

    ground_truth = queries[query_id].ground_truth_spec

    records = []
    for line in input.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = BenchmarkRecord.model_validate_json(line)
            if rec.query_id == query_id:
                records.append(rec)
        except Exception:
            pass

    if not records:
        console.print(f"[yellow]No records found for {query_id!r} in {input}[/yellow]")
        return

    def _normalize_for_diff(spec: dict) -> str:
        stripped = {
            k: v for k, v in spec.items()
            if k not in ("$schema", "title", "description", "data", "datasets")
        }
        return json.dumps(stripped, sort_keys=True, indent=2)

    console.print(f"\n[bold cyan]Ground-truth spec ({query_id}):[/bold cyan]")
    console.print(Syntax(json.dumps(ground_truth, indent=2), "json", theme="monokai"))

    gt_norm = _normalize_for_diff(ground_truth)

    for rec in sorted(records, key=lambda r: (r.model, r.mode)):
        title = f"{rec.model} / {rec.mode}"
        console.rule(f"[bold]{title}[/bold]")

        if rec.final_spec is None:
            console.print(f"[red]No spec generated. Error: {rec.error_message}[/red]")
            continue

        console.print("[bold]Predicted spec:[/bold]")
        console.print(Syntax(json.dumps(rec.final_spec, indent=2), "json", theme="monokai"))

        console.print("\n[bold]Mismatches:[/bold]")
        if rec.correctness.mismatches:
            for m in rec.correctness.mismatches:
                console.print(f"  [red]• {m}[/red]")
        else:
            console.print("  [green](none — correctness.match=True)[/green]")

        pred_norm = _normalize_for_diff(rec.final_spec)
        diff = list(
            difflib.unified_diff(
                gt_norm.splitlines(keepends=True),
                pred_norm.splitlines(keepends=True),
                fromfile="ground-truth (normalized)",
                tofile="predicted (normalized)",
            )
        )
        console.print("\n[bold]Unified diff (normalized, sort_keys):[/bold]")
        if diff:
            console.print(Syntax("".join(diff), "diff", theme="monokai"))
        else:
            console.print("  [green](no diff — specs normalize identically)[/green]")


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
