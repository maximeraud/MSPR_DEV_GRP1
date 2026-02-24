from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
import typer
from rich.console import Console

from ntl_systoolbox.core.paths import get_paths

app = typer.Typer()
console = Console()


def _write_dummy_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_manifest(artifact: Path, kind: str, extra: dict) -> Path:
    manifest = artifact.with_suffix(artifact.suffix + ".manifest.json")
    payload = {
        "trace_id": str(uuid.uuid4()),
        "kind": kind,
        "artifact": str(artifact.name),
        "size_bytes": artifact.stat().st_size if artifact.exists() else 0,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "extra": extra,
    }
    manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


@app.command("dump")
def dump_sql():
    """Dump SQL (placeholder) -> écrit un fichier .sql dans sauvegarde/."""
    paths = get_paths()
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out = paths.sauvegarde_dir / f"wms_dump_{ts}.sql"
    _write_dummy_file(out, "-- TODO mysqldump\nCREATE DATABASE wms;\n")
    manifest = _write_manifest(out, "dump_sql", {"note": "placeholder"})
    console.print(f"[green]OK[/green] Dump créé: {out}")
    console.print(f"Manifest: {manifest}")


@app.command("export-csv")
def export_csv(table: str = typer.Argument(..., help="Nom de la table à exporter")):
    """Export CSV (placeholder) -> écrit un fichier .csv dans sauvegarde/."""
    paths = get_paths()
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out = paths.sauvegarde_dir / f"wms_{table}_{ts}.csv"
    _write_dummy_file(out, "id;name\n1;demo\n")
    manifest = _write_manifest(out, "export_csv", {"table": table, "note": "placeholder"})
    console.print(f"[green]OK[/green] CSV créé: {out}")
    console.print(f"Manifest: {manifest}")


@app.command("list")
def list_local():
    """Liste les artefacts dans sauvegarde/."""
    paths = get_paths()
    files = sorted(paths.sauvegarde_dir.glob("*"))
    if not files:
        console.print("Aucun fichier dans sauvegarde/.")
        return
    for f in files:
        console.print(f"- {f.name}")


@app.command("verify")
def verify(file: str = typer.Argument(..., help="Nom (ou chemin) du fichier à vérifier (placeholder)")):
    """Vérification (placeholder). Pour l’instant: vérifie juste l’existence."""
    p = Path(file)
    if not p.exists():
        # tente dans sauvegarde/
        paths = get_paths()
        p2 = paths.sauvegarde_dir / file
        if p2.exists():
            p = p2

    if not p.exists():
        raise typer.BadParameter(f"Fichier introuvable: {file}")

    console.print(f"[green]OK[/green] Fichier trouvé: {p} (hash à implémenter)")


# --- Fonctions appelées par le menu interactif ---

def interactive_dump_sql() -> None:
    dump_sql()

def interactive_export_csv() -> None:
    table = console.input("Nom de la table > ").strip()
    if not table:
        console.print("[red]Table vide.[/red]")
        return
    export_csv(table=table)

def interactive_verify_file() -> None:
    name = console.input("Nom du fichier à vérifier > ").strip()
    if not name:
        console.print("[red]Nom vide.[/red]")
        return
    verify(name)

def interactive_list_sauvegardes() -> None:
    list_local()