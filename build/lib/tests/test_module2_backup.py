import json
import types
from pathlib import Path

import pytest

import ntl_systoolbox.cli.module2_backup as m2


def _set_min_env(monkeypatch):
    """Définit un environnement minimal pour éviter le mode interactif."""
    monkeypatch.setenv("MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_USER", "user")
    monkeypatch.setenv("MYSQL_DB", "db")


def test_mysql_client_path_returns_valid_type():
    result = m2._mysql_client_path()
    assert result is None or isinstance(result, str)


def test_write_dummy_file_creates_parent_and_writes(tmp_path: Path):
    target = tmp_path / "a" / "b" / "dummy.sql"
    m2._write_dummy_file(target, "hello")
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "hello"


def test_write_manifest_creates_json(tmp_path: Path):
    artifact = tmp_path / "dump.sql"
    artifact.write_text("abc", encoding="utf-8")

    manifest = m2._write_manifest(artifact, "dump_sql", {"k": "v"})
    assert manifest.exists()

    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["kind"] == "dump_sql"
    assert data["artifact"] == "dump.sql"
    assert data["size_bytes"] == artifact.stat().st_size
    assert data["extra"]["k"] == "v"


def test_perform_mysqldump_returns_false_when_mysqldump_missing(monkeypatch, tmp_path: Path):
    # mysqldump absent
    monkeypatch.setattr(m2.shutil, "which", lambda name: None)

    out = tmp_path / "out.sql"
    ok = m2._perform_mysqldump("h", "u", "p", "db", out, 3306)
    assert ok is False


def test_perform_mysqldump_success_writes_output(monkeypatch, tmp_path: Path):
    # mysqldump présent
    monkeypatch.setattr(m2.shutil, "which", lambda name: "/usr/bin/mysqldump")

    # subprocess.run écrit dans stdout (redirigé vers fichier)
    def fake_run(args, stdout=None, stderr=None, **kwargs):
        # On simule que mysqldump écrit bien dans stdout (un file handle)
        stdout.write(b"-- dump --\n")
        return types.SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(m2.subprocess, "run", fake_run)

    out = tmp_path / "dump.sql"
    ok = m2._perform_mysqldump("h", "u", "p", "db", out, 3306)

    assert ok is True
    assert out.exists()
    assert out.read_bytes().startswith(b"-- dump --")


def test_test_db_connection_tcp_fail(monkeypatch):
    # TCP KO
    def fake_create_connection(*args, **kwargs):
        raise OSError("no route")

    monkeypatch.setattr(m2.socket, "create_connection", fake_create_connection)

    ok = m2._test_db_connection("h", "u", "p", "db", 3306)
    assert ok is False


def test_test_db_connection_tcp_ok_no_mysql_client(monkeypatch):
    # TCP OK
    class DummySock:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False

    monkeypatch.setattr(m2.socket, "create_connection", lambda *a, **k: DummySock())
    # mysql client absent => True (selon ton code)
    monkeypatch.setattr(m2.shutil, "which", lambda name: None)

    ok = m2._test_db_connection("h", "u", "p", "db", 3306)
    assert ok is True


def test_test_db_connection_mysql_client_success(monkeypatch):
    # TCP OK
    class DummySock:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False

    monkeypatch.setattr(m2.socket, "create_connection", lambda *a, **k: DummySock())
    monkeypatch.setattr(m2.shutil, "which", lambda name: "/usr/bin/mysql")

    def fake_run(args, stdout=None, stderr=None, env=None, text=None, timeout=None, **kwargs):
        # Simule "SELECT 1" OK
        return types.SimpleNamespace(returncode=0, stdout="1\n", stderr="")

    monkeypatch.setattr(m2.subprocess, "run", fake_run)

    ok = m2._test_db_connection("h", "u", "p", "db", 3306)
    assert ok is True


def test_list_tables_mysql_client_returns_list(monkeypatch):
    # mysql client présent
    monkeypatch.setattr(m2, "_mysql_client_path", lambda: "/usr/bin/mysql")

    def fake_run(args, stdout=None, stderr=None, env=None, text=None, **kwargs):
        return types.SimpleNamespace(returncode=0, stdout="table1\ntable2\n", stderr="")

    monkeypatch.setattr(m2.subprocess, "run", fake_run)

    tables = m2._list_tables_mysql_client("h", "u", "p", "db", 3306)
    assert tables == ["table1", "table2"]


def test_export_table_csv_mysql_client_writes_csv(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(m2, "_mysql_client_path", lambda: "/usr/bin/mysql")

    # 1er run => SHOW COLUMNS, 2e run => SELECT
    calls = {"n": 0}

    def fake_run(args, stdout=None, stderr=None, env=None, text=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # format attendu : "col\t..." par ligne
            return types.SimpleNamespace(returncode=0, stdout="id\tint\nname\tvarchar\n", stderr="")
        else:
            # SELECT * => lignes tab-separated
            return types.SimpleNamespace(returncode=0, stdout="1\tAlice\n2\tBob\n", stderr="")

    monkeypatch.setattr(m2.subprocess, "run", fake_run)

    out_csv = tmp_path / "t.csv"
    ok = m2._export_table_csv_mysql_client("h", "u", "p", "db", "users", out_csv, 3306)

    assert ok is True
    content = out_csv.read_text(encoding="utf-8")
    # delimiter ';'
    assert "id;name" in content
    assert "1;Alice" in content
    assert "2;Bob" in content


def test_dump_sql_missing_env_exits(monkeypatch, tmp_path: Path):
    # vide l'env => doit sortir sans appeler mysqldump
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.delenv("MYSQL_PORT", raising=False)
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.delenv("MYSQL_DB", raising=False)

    # patch get_paths pour écrire dans tmp
    class DummyPaths:
        sauvegarde_dir = tmp_path
        repo_root = tmp_path

    monkeypatch.setattr(m2, "get_paths", lambda: DummyPaths())

    # empêche getpass de bloquer au cas où
    monkeypatch.setattr(m2.getpass, "getpass", lambda prompt: "x")

    m2.dump_sql()  # ne doit pas crash
    # pas de fichier attendu car env manquante => return direct
    assert list(tmp_path.glob("*.sql")) == []