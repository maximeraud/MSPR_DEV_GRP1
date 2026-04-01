from __future__ import annotations

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
from ntl_systoolbox.cli.logger import get_logger

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(".env", usecwd=True))

app = typer.Typer()
console = Console()
logger = get_logger("module2_backup")

def _write_dummy_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _log_artifact(artifact: Path, kind: str, extra: dict) -> None:
    logger.info(
        f"artifact created: {artifact.name}",
        extra={
            "extra_data": {
                "trace_id": str(uuid.uuid4()),
                "kind": kind,
                "artifact": artifact.name,
                "size_bytes": artifact.stat().st_size if artifact.exists() else 0,
                **extra,
            }
        },
    )


def _perform_mysqldump(host: str, user: str, password: str, db: str, out: Path, port: int = 3306) -> bool:
    """Run `mysqldump` against a remote MariaDB/MySQL instance.

    Returns True on success, False otherwise.
    """
    if shutil.which("mysqldump") is None:
        msg = "mysqldump not found in PATH; cannot perform real dump."
        console.print(f"[yellow]{msg}[/yellow]")
        logger.warning(msg)
        return False

    out.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "mysqldump",
        "-h", host,
        "-P", str(port),
        "-u", user,
        f"--password={password}",
        db,
    ]

    try:
        with out.open("wb") as fout:
            proc = subprocess.run(args, stdout=fout, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            err_msg = proc.stderr.decode().strip()
            console.print(f"[red]mysqldump failed:[/red] {err_msg}")
            logger.error(f"mysqldump failed: {err_msg}")
            return False
        logger.info(f"mysqldump réussi: {out.name}")
        return True
    except Exception as exc:
        console.print(f"[red]Erreur lors de l'exécution de mysqldump:[/red] {exc}")
        logger.error(f"Erreur lors de l'exécution de mysqldump: {exc}")
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
        msg = f"Connexion TCP vers {host}:{port} impossible: {exc}"
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return False

    # If mysql client is available, attempt a simple SELECT 1 to verify credentials
    mysql_path = shutil.which("mysql")
    if not mysql_path:
        msg = f"Client 'mysql' introuvable; TCP OK mais impossible de tester les identifiants."
        console.print(f"[yellow]{msg}[/yellow]")
        logger.warning(msg)
        return True

    env = os.environ.copy()
    env["MYSQL_PWD"] = password or ""
    args = [mysql_path, "-h", host, "-P", str(port), "-u", user, "-D", db, "-e", "SELECT 1;"]
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True, timeout=10)
        if proc.returncode != 0:
            err_msg = proc.stderr.strip()
            console.print(f"[red]Échec de la connexion avec les identifiants fournis:[/red] {err_msg}")
            logger.error(f"Échec de la connexion avec les identifiants fournis: {err_msg}")
            return False
        out = proc.stdout.strip()
        if "1" in out.split():
            logger.info(f"Connexion à {db} sur {host}:{port} réussie")
            return True
        msg = f"Test via client 'mysql': sortie inattendue: {out}"
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return False
    except Exception as exc:
        msg = f"Erreur lors du test via client 'mysql': {exc}"
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return False


@app.command("dump")
def dump_sql():
    """Dump SQL -> écrit un fichier .sql dans sauvegarde/."""
    paths = get_paths()
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out = paths.sauvegarde_dir / f"wms_dump_{ts}.sql"

    host = os.environ.get("MYSQL_HOST")
    user = os.environ.get("MYSQL_USER")
    db = os.environ.get("MYSQL_DB")
    port_str = os.environ.get("MYSQL_PORT")

    if not all([host, user, db, port_str]):
        msg = "Variables .env manquantes: MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_DB doivent être définies."
        console.print("[red]Variables .env manquantes[/red]")
        console.print("MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_DB doivent être définies.")
        logger.error(msg)
        return

    port = int(port_str)

    password = os.environ.get("MYSQL_PASSWORD")
    if not password:
        password = getpass.getpass("MySQL password: ")
        if not password:
            msg = "Mot de passe manquant. Abandon du dump."
            console.print("[red]Mot de passe manquant. Abandon.[/red]")
            logger.error(msg)
            return

    logger.info(f"Tentative de dump de {db} sur {host}:{port} en tant que {user}")
    console.print(f"Tentative de dump de {db} sur {host}:{port} en tant que {user}...")

    ok = _test_db_connection(host=host, user=user, password=password, db=db, port=port)
    if not ok:
        msg = "Connexion à la base impossible — arrêt du dump."
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return

    success = _perform_mysqldump(host=host, user=user, password=password, db=db, out=out, port=port)

    if not success:
        msg = "Echec du dump réel — écriture d'un fichier de remplacement (placeholder)."
        console.print(f"[yellow]{msg}[/yellow]")
        logger.warning(msg)
        _write_dummy_file(out, "-- Fallback: mysqldump failed or not available\n")

    _log_artifact(out, "dump_sql", {"host": host, "db": db, "note": "remote dump"})
    console.print(f"[green]OK[/green] Dump créé: {out}")
    logger.info(f"Dump créé: {out}")


def _mysql_client_path() -> Optional[str]:
    return shutil.which("mysql")


def _list_tables_mysql_client(host: str, user: str, password: str, db: str, port: int = 3306) -> List[str]:
    """
    Retourne la liste des tables via le client `mysql`.
    """
    mysql_path = _mysql_client_path()
    if not mysql_path:
        msg = "Le client 'mysql' est introuvable (PATH). Impossible de lister les tables."
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return []

    env = os.environ.copy()
    env["MYSQL_PWD"] = password or ""
    args = [mysql_path, "-h", host, "-P", str(port), "-u", user, "-D", db, "-N", "-B", "-e", "SHOW TABLES;"]
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    if proc.returncode != 0:
        err_msg = proc.stderr.strip()
        console.print(f"[red]Erreur SHOW TABLES:[/red] {err_msg}")
        logger.error(f"Erreur SHOW TABLES: {err_msg}")
        return []
    tables = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    logger.info(f"{len(tables)} tables trouvées dans {db}")
    return tables


def _export_table_csv_mysql_client(host: str, user: str, password: str, db: str, table: str, out_csv: Path, port: int = 3306) -> bool:
    """
    Exporte une table au format CSV via le client `mysql` en produisant une sortie tabulée,
    puis conversion en CSV (delimiter=';').
    """
    mysql_path = _mysql_client_path()
    if not mysql_path:
        msg = "Le client 'mysql' est introuvable (PATH). Impossible d'exporter."
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return False

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["MYSQL_PWD"] = password or ""

    cols_cmd = f"SHOW COLUMNS FROM `{table}`;"
    cols_args = [mysql_path, "-h", host, "-P", str(port), "-u", user, "-D", db, "-N", "-B", "-e", cols_cmd]
    cols_proc = subprocess.run(cols_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    if cols_proc.returncode != 0:
        err_msg = cols_proc.stderr.strip()
        console.print(f"[red]Erreur SHOW COLUMNS:[/red] {err_msg}")
        logger.error(f"Erreur SHOW COLUMNS pour {table}: {err_msg}")
        return False
    columns = [line.split("\t", 1)[0] for line in cols_proc.stdout.splitlines() if line.strip()]
    if not columns:
        msg = "Impossible de récupérer les colonnes (table vide ou inexistante)."
        console.print(f"[red]{msg}[/red]")
        logger.error(f"{msg} Table: {table}")
        return False

    data_cmd = f"SELECT * FROM `{table}`;"
    data_args = [mysql_path, "-h", host, "-P", str(port), "-u", user, "-D", db, "-N", "-B", "-e", data_cmd]
    data_proc = subprocess.run(data_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
    if data_proc.returncode != 0:
        err_msg = data_proc.stderr.strip()
        console.print(f"[red]Erreur SELECT:[/red] {err_msg}")
        logger.error(f"Erreur SELECT sur {table}: {err_msg}")
        return False

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(columns)
        for line in data_proc.stdout.splitlines():
            row = line.split("\t")
            writer.writerow(row)

    logger.info(f"Export CSV de la table {table} terminé: {out_csv.name}")
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

    host = os.environ.get("MYSQL_HOST")
    user = os.environ.get("MYSQL_USER")
    db = os.environ.get("MYSQL_DB")
    port_str = os.environ.get("MYSQL_PORT")

    if not all([host, user, db, port_str]):
        msg = "Variables .env manquantes: MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_DB doivent être définies."
        console.print("[red]Variables .env manquantes[/red]")
        console.print("MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_DB doivent être définies.")
        logger.error(msg)
        return

    port = int(port_str)

    password = os.environ.get("MYSQL_PASSWORD")
    if not password:
        password = getpass.getpass("MySQL password: ")
        if not password:
            msg = "Mot de passe manquant. Abandon de l'export."
            console.print("[red]Mot de passe manquant. Abandon.[/red]")
            logger.error(msg)
            return

    logger.info(f"Tentative de connexion à {db} sur {host}:{port} pour export CSV")
    console.print(f"Connexion à {db} sur {host}:{port} ...")

    ok = _test_db_connection(host=host, user=user, password=password, db=db, port=port)
    if not ok:
        msg = "Connexion à la base impossible — arrêt de l'export."
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return

    tables = _list_tables_mysql_client(host=host, user=user, password=password, db=db, port=port)
    if not tables:
        msg = "Aucune table trouvée (ou impossible de les lister)."
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return

    console.print("\n[bold]Tables disponibles :[/bold]")
    for t in tables[:50]:
        console.print(f" - {t}")
    if len(tables) > 50:
        console.print(f"[yellow]... {len(tables) - 50} autres tables non affichées[/yellow]")

    if not table:
        table = console.input("\nNom de la table à exporter > ").strip()

    if not table:
        msg = "Nom de table vide. Abandon."
        console.print(f"[red]{msg}[/red]")
        logger.error(msg)
        return

    if table not in tables:
        msg = f"Table inconnue: {table}"
        console.print(f"[red]Table inconnue:[/red] {table}")
        logger.error(msg)
        return

    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out = export_dir / f"{db}_{table}_{ts}.csv"

    logger.info(f"Début export CSV de la table {table} vers {out.name}")
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
        msg = f"Export CSV de la table {table} échoué."
        console.print("[red]Export CSV échoué.[/red]")
        logger.error(msg)
        return

    _log_artifact(out, "export_csv", {"host": host, "db": db, "table": table, "note": "mysql client"})
    console.print(f"[green]OK[/green] CSV créé: {out}")
    logger.info(f"CSV créé: {out}")


# --- Fonctions appelées par le menu interactif ---

def interactive_dump_sql() -> None:
    dump_sql()

def interactive_export_csv() -> None:
    export_csv(table=None, db=None)
