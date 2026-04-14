from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import difflib

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def _get_change_preview(file_path_a, file_path_b, max_lines=5):
    """Get a preview of what changed between two files."""
    try:
        with open(file_path_a, 'r', encoding='utf-8', errors='ignore') as f:
            lines_a = f.readlines()
        with open(file_path_b, 'r', encoding='utf-8', errors='ignore') as f:
            lines_b = f.readlines()
        
        # Get unified diff
        diff_lines = list(difflib.unified_diff(lines_a, lines_b, lineterm='', n=1))
        
        # Show first few changes
        preview_lines = []
        for line in diff_lines[3:max_lines+3]:  # Skip header lines
            if line.startswith('+') and not line.startswith('+++'):
                preview_lines.append(f"[green]{line[:80]}[/green]")
            elif line.startswith('-') and not line.startswith('---'):
                preview_lines.append(f"[red]{line[:80]}[/red]")
        
        return preview_lines if preview_lines else None
    except Exception:
        return None


def render_semantic_diff(file_a, file_b, changes):
    """
    Render a professional, detailed semantic diff of model changes.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    from_path = Path(file_a)
    to_path = Path(file_b)
    
    console.print("\n")
    console.print(
        Panel.fit(
            f"[bold cyan]📊 Power BI Model Comparison[/bold cyan]\n"
            f"[dim]Generated: {timestamp}[/dim]",
            title="TMDL Semantic Diff",
        )
    )
    
    console.print(f"\n[bold]Comparing:[/bold]")
    console.print(f"  [cyan]From:[/cyan] {from_path.name}")
    console.print(f"  [cyan]To:  [/cyan] {to_path.name}")
    
    # Count total changes
    total_changes = sum(len(v) for v in changes.values())
    console.print(f"\n[bold cyan]Total Changes: {total_changes}[/bold cyan]\n")
    
    # Tables section
    if changes.get("tables_added") or changes.get("tables_removed") or changes.get("tables_modified"):
        console.print("[bold green]📋 TABLES & STRUCTURES[/bold green]")
        
        if changes.get("tables_added"):
            console.print("[green]✓ Added:[/green]")
            for table in changes["tables_added"]:
                console.print(f"   [green]▪[/green] {table['name']}")
        
        if changes.get("tables_removed"):
            console.print("[red]✗ Removed:[/red]")
            for table in changes["tables_removed"]:
                console.print(f"   [red]▪[/red] {table['name']}")
        
        if changes.get("tables_modified"):
            console.print("[yellow]~ Modified:[/yellow]")
            for table in changes["tables_modified"]:
                name = table['name']
                console.print(f"   [yellow]▪[/yellow] {name}")
                
                # Show change preview if available
                base_a = from_path.stem
                base_b = to_path.stem
                sem_a = from_path.parent / f"{base_a}.SemanticModel" / name
                sem_b = from_path.parent / f"{base_b}.SemanticModel" / name
                
                if sem_a.exists() and sem_b.exists():
                    preview = _get_change_preview(sem_a, sem_b, max_lines=3)
                    if preview:
                        for line in preview:
                            console.print(f"      {line}")
        
        console.print()
    
    # Relationships section
    if changes.get("relationships_added") or changes.get("relationships_removed") or changes.get("relationships_modified"):
        console.print("[bold yellow]🔗 RELATIONSHIPS[/bold yellow]")
        
        if changes.get("relationships_added"):
            console.print("[green]✓ Added[/green]")
        
        if changes.get("relationships_removed"):
            console.print("[red]✗ Removed[/red]")
        
        if changes.get("relationships_modified"):
            console.print("[yellow]~ Modified[/yellow]")
        
        console.print()
    
    # Summary
    summary_parts = []
    if changes.get("tables_added"):
        summary_parts.append(f"[green]{len(changes['tables_added'])} added[/green]")
    if changes.get("tables_removed"):
        summary_parts.append(f"[red]{len(changes['tables_removed'])} removed[/red]")
    if changes.get("tables_modified"):
        summary_parts.append(f"[yellow]{len(changes['tables_modified'])} modified[/yellow]")
    if changes.get("relationships_added"):
        summary_parts.append(f"[green]{len(changes['relationships_added'])} relationship(s) added[/green]")
    if changes.get("relationships_removed"):
        summary_parts.append(f"[red]{len(changes['relationships_removed'])} relationship(s) removed[/red]")
    if changes.get("relationships_modified"):
        summary_parts.append(f"[yellow]{len(changes['relationships_modified'])} relationship(s) modified[/yellow]")
    
    if summary_parts:
        console.print(
            Panel.fit(
                " • ".join(summary_parts),
                title="Summary",
            )
        )
    else:
        console.print("[dim]✅ No changes detected - models are identical.[/dim]")
    
    console.print()
