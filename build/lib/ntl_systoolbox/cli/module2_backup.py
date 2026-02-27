from __future__ import annotations

import json
import time
import uuid
import os
import socket
import subprocess
import shutil
import getpass
from pathlib import Path
import typer
from rich.console import Console
import csv
from typing import Optional, List

from ntl_systoolbox.core.paths import get_paths

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(".env", usecwd=True))

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


def _perform_mysqldump(host: str, user: str, password: str, db: str, out: Path, port: int = 3306) -> bool:
    """Run `mysqldump` against a remote MariaDB/MySQL instance.

    Returns True on success, False otherwise.
    """
    if shutil.which("mysqldump") is None:
        console.print("[yellow]mysqldump not found in PATH; cannot perform real dump.[/yellow]")
        return False

    out.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "mysqldump",
        "-h",
        host,
        "-P",
        str(port),
        "-u",
        user,
        f"--password={password}",
        db,
    ]

    try:
        with out.open("wb") as fout:
            proc = subprocess.run(args, stdout=fout, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            console.print(f"[red]mysqldump failed:[/red] {proc.stderr.decode().strip()}")
            return False
        return True
    except Exception as exc:
        console.print(f"[red]Erreur lors de l'exécution de mysqldump:[/red] {exc}")
        return False


def _test_db_connection(host: str, user: str, password: str, db: str, port: int = 3306, timeout: int = 5) -> bool:
    """Test TCP connectivity to host:port and optionally verify credentials using `mysql` client.

    Returns True if the host is reachable and credentials are accepted (if tested), False otherwise.
    """
    # TCP test
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except Exception as exc:
        console.print(f"[red]Connexion TCP vers {host}:{port} impossible:[/red] {exc}")
        return False

    # If mysql client is available, attempt a simple SELECT 1 to verify credentials
    mysql_path = shutil.which("mysql")
    if not mysql_path:
        console.print(f"[yellow]Client 'mysql' introuvable; TCP OK mais impossible de tester les identifiants.[/yellow]")
        return True

    env = os.environ.copy()
    env["MYSQL_PWD"] = password or ""
    args = [mysql_path, "-h", host, "-P", str(port), "-u", user, "-D", db, "-e", "SELECT 1;"]
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True, timeout=10)
        if proc.returncode != 0:
            console.print(f"[red]Échec de la connexion avec les identifiants fournis:[/red] {proc.stderr.strip()}")
            return False
        # success if output contains '1'
        out = proc.stdout.strip()
        if "1" in out.split():
            return True
        console.print(f"[red]Test via client 'mysql': sortie inattendue:[/red] {out}")
        return False
    except Exception as exc:
        console.print(f"[red]Erreur lors du test via client 'mysql':[/red] {exc}")
        return False


@app.command("dump")
def dump_sql():
    """Dump SQL -> écrit un fichier .sql dans sauvegarde/."""
    paths = get_paths()
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out = paths.sauvegarde_dir / f"wms_dump_{ts}.sql"

    # Defaults and env-based credentials
    host = os.environ.get("MYSQL_HOST")
    user = os.environ.get("MYSQL_USER")
    db = os.environ.get("MYSQL_DB")
    port_str = os.environ.get("MYSQL_PORT")
    
    if not all([host, user, db, port_str]):
        console.print("[red]Variables .env manquantes[/red]")
        console.print("MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_DB doivent être définies.")
        return

    port = int(port_str)

    # Mot de passe : demandé au runtime si absent
    password = os.environ.get("MYSQL_PASSWORD")
    if not password:
        password = getpass.getpass("MySQL password: ")
        if not password:
            console.print("[red]Mot de passe manquant. Abandon.[/red]")
            return

    console.print(f"Tentative de dump de {db} sur {host}:{port} en tant que {user}...")
    # test connection before attempting dump
    ok = _test_db_connection(host=host, user=user, password=password, db=db, port=port)
    if not ok:
        console.print(f"[red]Connexion à la base impossible — arrêt du dump.[/red]")
        return
    success = _perform_mysqldump(host=host, user=user, password=password, db=db, out=out, port=port)

    if not success:
        console.print("[yellow]Echec du dump réel — écriture d'un fichier de remplacement (placeholder).[/yellow]")
        _write_dummy_file(out, "-- Fallback: mysqldump failed or not available\n")

    manifest = _write_manifest(out, "dump_sql", {"host": host, "db": db, "note": "remote dump"})
    console.print(f"[green]OK[/green] Dump créé: {out}")
    console.print(f"Manifest: {manifest}")

def _mysql_client_path() -> Optional[str]:
    return shutil.which("mysql")


def _list_tables_mysql_client(host: str, user: str, password: str, db: str, port: int = 3306) -> List[str]:
    """
    Retourne la liste des tables via le client `mysql`.
    """
    mysql_path = _mysql_client_path()
    if not mysql_path:
        console.print("[red]Le client 'mysql' est introuvable (PATH). Impossible de lister les tables.[/red]")
        return []

    env = os.environ.copy()
    env["MYSQL_PWD"] = password or ""
    # -N : pas d'entête, -B : batch (sortie simple)
    args = [mysql_path, "-h", host, "-P", str(port), "-u", user, "-D", db, "-N", "-B", "-e", "SHOW TABLES;"]
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    if proc.returncode != 0:
        console.print(f"[red]Erreur SHOW TABLES:[/red] {proc.stderr.strip()}")
        return []
    tables = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return tables


def _export_table_csv_mysql_client(host: str, user: str, password: str, db: str, table: str, out_csv: Path, port: int = 3306) -> bool:
    """
    Exporte une table au format CSV via le client `mysql` en produisant une sortie tabulée,
    puis conversion en CSV (delimiter=';').
    Note: fonctionne bien pour des cas simples; si tu as des champs avec tabs/newlines,
    la solution "pymysql streaming" est plus robuste.
    """
    mysql_path = _mysql_client_path()
    if not mysql_path:
        console.print("[red]Le client 'mysql' est introuvable (PATH). Impossible d'exporter.[/red]")
        return False

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["MYSQL_PWD"] = password or ""

    # On récupère d'abord les colonnes pour écrire l'entête CSV
    cols_cmd = f"SHOW COLUMNS FROM `{table}`;"
    cols_args = [mysql_path, "-h", host, "-P", str(port), "-u", user, "-D", db, "-N", "-B", "-e", cols_cmd]
    cols_proc = subprocess.run(cols_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    if cols_proc.returncode != 0:
        console.print(f"[red]Erreur SHOW COLUMNS:[/red] {cols_proc.stderr.strip()}")
        return False
    columns = [line.split("\t", 1)[0] for line in cols_proc.stdout.splitlines() if line.strip()]
    if not columns:
        console.print("[red]Impossible de récupérer les colonnes (table vide ou inexistante).[/red]")
        return False

    # Récupère les données en mode batch: colonnes séparées par tab
    data_cmd = f"SELECT * FROM `{table}`;"
    data_args = [mysql_path, "-h", host, "-P", str(port), "-u", user, "-D", db, "-N", "-B", "-e", data_cmd]
    data_proc = subprocess.run(data_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    if data_proc.returncode != 0:
        console.print(f"[red]Erreur SELECT:[/red] {data_proc.stderr.strip()}")
        return False

    # Écriture CSV (séparateur ;)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(columns)
        for line in data_proc.stdout.splitlines():
            # chaque ligne = valeurs séparées par tab
            row = line.split("\t")
            writer.writerow(row)

    return True

@app.command("export-csv")
def export_csv(
    table: Optional[str] = typer.Option(None, "--table", "-t", help="Nom de la table à exporter (si omis: mode interactif)"),
    db: Optional[str] = typer.Option(None, "--db", help="Nom de la base (sinon MYSQL_DB ou saisie)"),
):
    """Export d'une table au format CSV -> écrit dans export/."""
    paths = get_paths()
    export_dir = paths.repo_root / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Defaults and env-based credentials
    host = os.environ.get("MYSQL_HOST")
    user = os.environ.get("MYSQL_USER")
    db = os.environ.get("MYSQL_DB")
    port_str = os.environ.get("MYSQL_PORT")
    
    if not all([host, user, db, port_str]):
        console.print("[red]Variables .env manquantes[/red]")
        console.print("MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_DB doivent être définies.")
        return

    port = int(port_str)

    # Mot de passe : demandé au runtime si absent
    password = os.environ.get("MYSQL_PASSWORD")
    if not password:
        password = getpass.getpass("MySQL password: ")
        if not password:
            console.print("[red]Mot de passe manquant. Abandon.[/red]")
            return

    console.print(f"Connexion à {db} sur {host}:{port} ...")
    ok = _test_db_connection(host=host, user=user, password=password, db=db, port=port)
    if not ok:
        console.print("[red]Connexion à la base impossible — arrêt de l'export.[/red]")
        return

    # Liste des tables
    tables = _list_tables_mysql_client(host=host, user=user, password=password, db=db, port=port)
    if not tables:
        console.print("[red]Aucune table trouvée (ou impossible de les lister).[/red]")
        return

    console.print("\n[bold]Tables disponibles :[/bold]")
    # affichage propre (pas trop long)
    for t in tables[:50]:
        console.print(f" - {t}")
    if len(tables) > 50:
        console.print(f"[yellow]... {len(tables) - 50} autres tables non affichées[/yellow]")

    # Choix table (si non fournie)
    if not table:
        table = console.input("\nNom de la table à exporter > ").strip()

    if not table:
        console.print("[red]Table vide. Abandon.[/red]")
        return

    if table not in tables:
        console.print(f"[red]Table inconnue:[/red] {table}")
        return

    # Export CSV dans export/
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out = export_dir / f"{db}_{table}_{ts}.csv"

    success = _export_table_csv_mysql_client(
        host=host,
        user=user,
        password=password,
        db=db,
        table=table,
        out_csv=out,
        port=port,
    )
    if not success:
        console.print("[red]Export CSV échoué.[/red]")
        return

    manifest = _write_manifest(out, "export_csv", {"host": host, "db": db, "table": table, "note": "mysql client"})
    console.print(f"[green]OK[/green] CSV créé: {out}")
    console.print(f"Manifest: {manifest}")



# --- Fonctions appelées par le menu interactif ---

def interactive_dump_sql() -> None:
    dump_sql()

def interactive_export_csv() -> None:
    export_csv(table=None, db=None)
