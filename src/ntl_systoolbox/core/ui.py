from __future__ import annotations
from typing import List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel

console = Console()

def header(title: str) -> None:
    console.print(Panel.fit(f"[bold]{title}[/bold]", border_style="cyan"))

def choose(title: str, options: List[Tuple[str, str]], allow_back: bool = True) -> Optional[str]:
    """
    options: [(key, label), ...]
    Retourne la key choisie, ou None si retour.
    """
    header(title)
    for k, label in options:
        console.print(f"  [bold]{k}[/bold] - {label}")
    if allow_back:
        console.print("  [bold]0[/bold] - Retour")

    while True:
        choice = console.input("\nChoix > ").strip()
        if allow_back and choice == "0":
            return None
        if any(choice == k for k, _ in options):
            return choice
        console.print("[red]Choix invalide.[/red] Réessaie.")