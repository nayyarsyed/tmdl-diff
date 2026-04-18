import difflib
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from packaging import version

import questionary
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.columns import Columns
from rich.text import Text

from pbi_detector import get_open_pbi_models
from pbip_parser import compare_models
from semantic_formatter import render_semantic_diff

__version__ = "1.1.1"

app = typer.Typer(
    help="TMDL Diff CLI - compare Power BI TMDL export files and open Power BI instances",
    no_args_is_help=True,
)
console = Console()


def check_for_updates() -> None:
    """Check PyPI for a newer version and notify user if available."""
    try:
        result = subprocess.run(
            ["pip", "index", "versions", "tmdl-diff-cli"],
            capture_output=True,
            text=True,
            timeout=3
        )
        
        if result.returncode == 0:
            # Parse pip output to find available version
            output = result.stdout
            if "Available versions:" in output:
                lines = output.split("\n")
                for line in lines:
                    if "Available versions:" in line:
                        versions_str = line.split("Available versions:")[1].strip()
                        latest = versions_str.split(",")[0].strip()
                        if version.parse(latest) > version.parse(__version__):
                            console.print(
                                Panel(
                                    f"[bold yellow]🎉 New version available: {latest}[/bold yellow]\n\n"
                                    f"Current version: {__version__}\n"
                                    f"Latest version: {latest}\n\n"
                                    f"[cyan]To update, run:[/cyan]\n"
                                    f"[bold green]pip install --upgrade tmdl-diff-cli[/bold green]",
                                    title="⬆️ Update Available",
                                    border_style="yellow"
                                )
                            )
                        break
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # Silently fail if pip is not available or times out
        pass


def version_callback(value: bool) -> None:
    """Show version and check for updates."""
    if value:
        console.print(f"[bold cyan]tmdl-diff[/bold cyan] version [bold green]{__version__}[/bold green]")
        check_for_updates()
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and check for updates",
        is_eager=True,
    ),
) -> None:
    """Main app callback - check for updates on startup."""
    if version:
        version_callback(True)


def load_tmdl_lines(file_path: Path) -> List[str]:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with file_path.open("r", encoding="utf-8", errors="replace") as fp:
        return [line.rstrip("\n") for line in fp.readlines()]


def find_tmdl_files(search_dir: Path = Path.cwd()) -> List[Path]:
    tmdl_files = sorted(search_dir.glob("*.tmdl"))
    pbip_files = sorted(search_dir.glob("*.pbip"))
    return tmdl_files + pbip_files


def compute_diff(file_a: Path, file_b: Path) -> Dict[str, object]:
    left = load_tmdl_lines(file_a)
    right = load_tmdl_lines(file_b)
    diff_lines = list(
        difflib.unified_diff(
            left,
            right,
            fromfile=str(file_a),
            tofile=str(file_b),
            lineterm="",
        )
    )

    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    context = sum(1 for line in diff_lines if line.startswith(" "))

    return {
        "diff": diff_lines,
        "added": added,
        "removed": removed,
        "context": context,
    }


def choose_file(prompt: str, candidates: List[Path]) -> Path:
    if candidates:
        choices = [str(path) for path in candidates] + ["Enter a custom path"]
        selected = questionary.select(prompt, choices=choices).ask()

        if selected == "Enter a custom path":
            custom_path = questionary.text("Enter the full path to a .tmdl or .pbip file:").ask()
            # Strip quotes from the input if present
            custom_path = custom_path.strip('"').strip("'")
            return Path(custom_path).expanduser().resolve()

        return Path(selected)

    file_path = questionary.text(prompt).ask()
    # Strip quotes from the input if present
    file_path = file_path.strip('"').strip("'")
    return Path(file_path).expanduser().resolve()


def render_diff_result(file_a: Path, file_b: Path, diff_data: Dict[str, object]) -> None:
    if not diff_data["diff"]:
        console.print(
            Panel.fit(
                f"No differences found between\n[file]{file_a}[/file]\nand\n[file]{file_b}[/file]",
                title="✅ TMDL Diff Summary",
                subtitle="Files are identical",
            )
        )
        return

    summary = (
        f"Comparing:\n"
        f"  [cyan]1.[/cyan] {file_a.name}\n"
        f"  [cyan]2.[/cyan] {file_b.name}\n"
        f"\n"
        f"[bold green]+ Added lines:[/bold green] {diff_data['added']}\n"
        f"[bold red]- Removed lines:[/bold red] {diff_data['removed']}\n"
        f"[bold blue]  Context lines:[/bold blue] {diff_data['context']}\n"
    )

    diff_preview = "\n".join(diff_data["diff"][:100])
    console.print(Panel.fit(summary, title="📊 TMDL Diff Summary"))
    console.print("\n[bold]Diff preview:[/bold]\n")
    console.print(diff_preview)
    if len(diff_data["diff"]) > 100:
        console.print(f"[dim]...output truncated ({len(diff_data['diff'])} diff lines total)[/dim]")


def extract_tmdl_metadata(file_path: Path) -> Dict[str, object]:
    """Extract metadata for a local TMDL snapshot or a full PBIP project."""
    is_pbip = file_path.suffix.lower() == ".pbip"
    
    metadata = {
        "path": str(file_path),
        "name": file_path.name,
        "type": "PBIP Project" if is_pbip else "TMDL File",
        "size_bytes": file_path.stat().st_size,
        "model_name": None,
        "tables": [],
        "measures": [],
        "preview": [],
        "structure": [],
        "full_model": None
    }

    if is_pbip:
        from pbip_parser import extract_pbip_model
        model_data = extract_pbip_model(file_path)
        if model_data:
            metadata["full_model"] = model_data
            metadata["model_name"] = model_data.get("name")
            
            base_name = file_path.stem
            sem_model_dir = file_path.parent / f"{base_name}.SemanticModel"
            report_dir = file_path.parent / f"{base_name}.Report"
            
            if sem_model_dir.exists():
                metadata["structure"].append(f"📁 {sem_model_dir.name}")
            if report_dir.exists():
                metadata["structure"].append(f"📁 {report_dir.name}")

    lines = load_tmdl_lines(file_path)
    metadata["line_count"] = len(lines)
    metadata["preview"] = lines[:20]

    return metadata


def render_model_info(metadata: Dict[str, object]) -> None:
    table = Table(title=f"Model info for {metadata['name']}")
    table.add_column("Field", style="bold green")
    table.add_column("Value", style="cyan")
    table.add_row("Type", str(metadata["type"]))
    table.add_row("Path", metadata["path"])
    table.add_row("Size", f"{metadata['size_bytes']} bytes")
    
    if metadata.get("model_name"):
        table.add_row("Model name", str(metadata["model_name"]))
    
    console.print(table)

    if metadata.get("full_model"):
        model = metadata["full_model"]
        root_tree = Tree(f"🏗️ [bold blue]Model:[/bold blue] {model.get('name', 'N/A')}")
        
        tables_node = root_tree.add("📁 [bold yellow]Tables[/bold yellow]")
        for t in model.get("tables", []):
            t_name = t.get("name")
            table_node = tables_node.add(f"📊 [bold cyan]{t_name}[/bold cyan]")
            
            if t.get("columns"):
                cols_node = table_node.add("🔹 [bold yellow]Columns[/bold]")
                for col in t["columns"]:
                    cols_node.add(f"[dim]{col}[/dim]")
            
            if t.get("measures"):
                meas_node = table_node.add("🧪 [bold yellow]Measures[/bold green]")
                for meas in t["measures"]:
                    meas_node.add(f"[green]{meas}[/green]")
            
            if t.get("hierarchies"):
                hier_node = table_node.add("🧬 [bold magenta]Hierarchies[/bold magenta]")
                for hier in t["hierarchies"]:
                    hier_node.add(f"[magenta]{hier}[/magenta]")

        console.print("\n[bold]Model Hierarchy:[/bold]")
        console.print(root_tree)
    elif metadata.get("structure"):
        console.print("\n[bold]Project Structure:[/bold]")
        for item in metadata["structure"]:
            console.print(f"[dim]{item}[/dim]")

    console.print("\n[bold]Manifest/File Preview:[/bold]\n")
    console.print("\n".join(metadata["preview"]))


def render_hierarchical_comparison(diff: Dict[str, Any]) -> None:
    """Render a side-by-side hierarchical tree comparison."""
    if "error" in diff:
        console.print(f"[red]{diff['error']}[/red]")
        return

    # Header and Legend
    legend = (
        "Legend: [bold bright_green][+] Added[/bold bright_green] | "
        "[bold bright_red][-] Removed[/bold bright_red] | "
        "[bold yellow]Modified[/bold yellow] | "
        "[italic dim]Unchanged[/italic dim]"
    )
    console.print(Panel(legend, title="🎨 Comparison Legend", border_style="blue"))

    tree_left = Tree(f"🏗️ [bold bright_red]Left Model:[/bold bright_red] {diff['model_a_name']}")
    tree_right = Tree(f"🏗️ [bold bright_green]Right Model:[/bold bright_green] {diff['model_b_name']}")

    tables_left = tree_left.add("📁 [bold yellow]Tables[/bold yellow]")
    tables_right = tree_right.add("📁 [bold yellow]Tables[/bold yellow]")

    for t_name, t_diff in diff["tables"].items():
        status = t_diff["status"]
        
        if status == "removed":
            node_l = tables_left.add(f"📊 [bold bright_red][-] {t_name}[/bold bright_red]")
            _add_table_to_tree(node_l, t_diff["data_a"], "bold bright_red")
            tables_right.add(f"📊 [italic dim grey50](Deleted) {t_name}[/italic dim grey50]")
            
        elif status == "added":
            node_r = tables_right.add(f"📊 [bold bright_green][+] {t_name}[/bold bright_green]")
            _add_table_to_tree(node_r, t_diff["data_b"], "bold bright_green")
            tables_left.add(f"📊 [italic dim grey50](New) {t_name}[/italic dim grey50]")
            
        elif status == "modified":
            node_l = tables_left.add(f"📊 [bold yellow]{t_name}[/bold yellow]")
            node_r = tables_right.add(f"📊 [bold yellow]{t_name}[/bold yellow]")
            
            # Columns Comparison
            all_cols = sorted(list(set(t_diff["data_a"]["columns"]) | set(t_diff["data_b"]["columns"])))
            if all_cols:
                cl = node_l.add("🔹 [bold blue]Columns[bold blue]")
                cr = node_r.add("🔹 [bold blue]Columns[bold blue]")
                for c in all_cols:
                    if c in t_diff["columns"]["removed"]:
                        cl.add(f"[bold bright_red][-] {c}[/bold bright_red]")
                        cr.add(f"[italic dim grey50]...[/italic dim grey50]")
                    elif c in t_diff["columns"]["added"]:
                        cl.add(f"[italic dim grey50]...[/italic dim grey50]")
                        cr.add(f"[bold bright_green][+] {c}[/bold bright_green]")
                    else:
                        cl.add(f"[italic dim grey50]{c}[/italic dim grey50]")
                        cr.add(f"[italic dim grey50]{c}[/italic dim grey50]")
            
            # Measures Comparison
            all_meas = sorted(list(set(t_diff["data_a"]["measures"]) | set(t_diff["data_b"]["measures"])))
            if all_meas:
                ml = node_l.add("🧪 [bold blue]Measures[/bold blue]")
                mr = node_r.add("🧪 [bold blue]Measures[/bold blue]")
                for m in all_meas:
                    if m in t_diff["measures"]["removed"]:
                        ml.add(f"[bold bright_red][-] {m}[/bold bright_red]")
                        mr.add(f"[italic dim grey50]...[/italic dim grey50]")
                    elif m in t_diff["measures"]["added"]:
                        ml.add(f"[italic dim grey50]...[/italic dim grey50]")
                        mr.add(f"[bold bright_green][+] {m}[/bold bright_green]")
                    else:
                        ml.add(f"[italic dim grey50]{m}[/italic dim grey50]")
                        mr.add(f"[italic dim grey50]{m}[/italic dim grey50]")
        
        else: # identical
            node_l = tables_left.add(f"📊 [italic dim grey50]{t_name}[/italic dim grey50]")
            node_r = tables_right.add(f"📊 [italic dim grey50]{t_name}[/italic dim grey50]")
            _add_table_to_tree(node_l, t_diff["data_a"], "italic dim grey50")
            _add_table_to_tree(node_r, t_diff["data_b"], "italic dim grey50")

    console.print(Panel("📊 [bold]Side-by-Side Model Comparison[/bold]", expand=True, border_style="bright_magenta"))
    console.print(Columns([tree_left, tree_right], padding=(0, 8), equal=True))


def _add_table_to_tree(parent_node: Any, table_data: Dict[str, Any], style: str) -> None:
    """Helper to add table structure to a tree node with a specific style."""
    if table_data.get("columns"):
        cols_node = parent_node.add(f"🔹 [{style}]Columns[/{style}]")
        for col in table_data["columns"]:
            cols_node.add(f"[{style}]{col}[/{style}]")
    
    if table_data.get("measures"):
        meas_node = parent_node.add(f"🧪 [{style}]Measures[/{style}]")
        for meas in table_data["measures"]:
            meas_node.add(f"[{style}]{meas}[/{style}]")
    
    if table_data.get("hierarchies"):
        hier_node = parent_node.add(f"🧬 [{style}]Hierarchies[/{style}]")
        for hier in table_data["hierarchies"]:
            hier_node.add(f"[{style}]{hier}[/{style}]")


@app.command(name="info")
def info_file(
    file_path: Path = typer.Argument(..., exists=True, help="Path to the .tmdl or .pbip file to inspect."),
) -> None:
    """Show metadata for a local TMDL/PBIP snapshot file."""
    metadata = extract_tmdl_metadata(file_path)
    render_model_info(metadata)


@app.command(name="list")
def list_models() -> None:
    """List open Power BI Desktop instances and local .tmdl/.pbip snapshots."""
    open_models = get_open_pbi_models()
    tmdl_files = find_tmdl_files()

    if open_models:
        table = Table(title="Open Power BI Models")
        table.add_column("Name", style="bold green")
        table.add_column("Port")
        table.add_column("Workspace Path", style="dim")
        for model in open_models:
            table.add_row(model["name"], model["port"], model.get("workspace", "n/a"))
        console.print(table)
    else:
        console.print("[yellow]No open Power BI Desktop instances found.[/yellow]")

    if tmdl_files:
        from datetime import datetime

        table = Table(title="Local TMDL / PBIP Files")
        table.add_column("File", style="bold cyan")
        table.add_column("Modified", style="dim")
        for path in tmdl_files:
            modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(sep=" ", timespec="seconds")
            table.add_row(str(path.name), modified)
        console.print(table)
    else:
        console.print("[yellow]No .tmdl or .pbip files found in the current directory.[/yellow]")


@app.command(name="diff")
def diff_files(
    file_a: Path = typer.Argument(..., exists=True, help="Path to the first .tmdl or .pbip file."),
    file_b: Path = typer.Argument(..., exists=True, help="Path to the second .tmdl or .pbip file."),
) -> None:
    """Compare two TMDL/PBIP export files and print a detailed semantic diff."""
    if file_a.suffix.lower() == '.pbip' and file_b.suffix.lower() == '.pbip':
        diff_data = compare_models(file_a, file_b)
        render_hierarchical_comparison(diff_data)
    else:
        diff_data = compute_diff(file_a, file_b)
        render_diff_result(file_a, file_b, diff_data)


@app.command(name="status")
def status_files(
    file_a: Path = typer.Argument(..., exists=True, help="Path to the first .tmdl or .pbip file."),
    file_b: Path = typer.Argument(..., exists=True, help="Path to the second .tmdl or .pbip file."),
) -> None:
    """Show whether two TMDL export files differ."""
    diff_data = compute_diff(file_a, file_b)
    if diff_data["diff"]:
        console.print(
            Panel.fit(
                f"Files differ:\n[file]{file_a.name}[/file]\n[file]{file_b.name}[/file]\n\n"
                f"Added lines: {diff_data['added']}\n"
                f"Removed lines: {diff_data['removed']}",
                title="⚠️ TMDL Status",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"Files are identical:\n[file]{file_a.name}[/file]\n[file]{file_b.name}[/file]",
                title="✅ TMDL Status",
            )
        )


@app.command(name="compare")
def compare_interactive() -> None:
    """Interactively choose two local files to compare."""
    open_models = get_open_pbi_models()
    if open_models:
        console.print("[bold blue]Detected open Power BI models. You can export them to .tmdl and compare the exported snapshots.[/bold blue]\n")
        for model in open_models:
            console.print(f"- {model['name']} (port {model['port']})\n  workspace: {model.get('workspace', 'n/a')}")
        console.print(
            "[yellow]Note: this tool compares exported TMDL/PBIP files. Open models are listed for reference, but you must select saved snapshot files for comparison.[/yellow]\n"
        )

    available_files = find_tmdl_files()
    if available_files:
        file_a = choose_file("Select the first file to compare:", available_files)
        file_b = choose_file("Select the second file to compare:", available_files)

        if file_a == file_b:
            console.print("[red]Please select two different files to compare.[/red]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]No .tmdl or .pbip files were found in the current directory.[/yellow]")
        file_a = choose_file("Enter the path to the first TMDL/PBIP file:", [])
        file_b = choose_file("Enter the path to the second TMDL/PBIP file:", [])

    if file_a.suffix.lower() == '.pbip' and file_b.suffix.lower() == '.pbip':
        diff_data = compare_models(file_a, file_b)
        render_hierarchical_comparison(diff_data)
    else:
        diff_data = compute_diff(file_a, file_b)
        render_diff_result(file_a, file_b, diff_data)


@app.command(name="compare-open")
def compare_open_instances() -> None:
    """Choose two detected Power BI Desktop instances and inspect their workspaces."""
    open_models = get_open_pbi_models()
    if not open_models:
        console.print("[red]No open Power BI Desktop instances detected.[/red]")
        console.print("Open Power BI Desktop and load a model, then try again.")
        raise typer.Exit(1)

    choices = [f"{model['name']} (port {model['port']}) - {model.get('workspace', 'workspace unknown')}" for model in open_models]
    selected = questionary.checkbox(
        "Select exactly 2 open Power BI models to compare:",
        choices=choices,
        validate=lambda x: True if len(x) == 2 else "Please select exactly 2 models."
    ).ask()

    if not selected:
        console.print("[red]Operation cancelled.[/red]")
        raise typer.Exit(1)

    selected_models = [open_models[choices.index(choice)] for choice in selected]
    console.print("\n[bold green]Selected open models:[/bold green]")
    for model in selected_models:
        console.print(f"- {model['name']} (port {model['port']})\n  workspace: {model['workspace']}")

    console.print(
        "\n[yellow]To compare these models, export each model to a .tmdl/.pbip file and then run `tmdl-diff diff file1.tmdl file2.tmdl`.[/yellow]"
    )


if __name__ == "__main__":
    app()
