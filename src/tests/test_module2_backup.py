import types
from pathlib import Path

import pytest

import ntl_systoolbox.cli.module2_backup as m2


def _set_min_env(monkeypatch):
    """
    Définit les variables d'environnement minimales
    nécessaires pour éviter que le programme passe
    en mode interactif pendant les tests.
    """
    monkeypatch.setenv("MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_USER", "user")
    monkeypatch.setenv("MYSQL_DB", "db")


def test_mysql_client_path_returns_valid_type():
    """
    Vérifie que la fonction _mysql_client_path()
    retourne soit :
    - None si le client MySQL n'est pas trouvé
    - une chaîne de caractères (str) si le chemin existe
    """
    result = m2._mysql_client_path()
    assert result is None or isinstance(result, str)


def test_write_dummy_file_creates_parent_and_writes(tmp_path: Path):
    """
    Vérifie que _write_dummy_file() :
    - crée les dossiers parents si nécessaire
    - crée bien le fichier cible
    - écrit correctement le contenu dans le fichier
    """
    target = tmp_path / "a" / "b" / "dummy.sql"
    m2._write_dummy_file(target, "hello")

    assert target.exists()
    assert target.read_text(encoding="utf-8") == "hello"


def test_log_artifact_calls_logger(tmp_path: Path, monkeypatch):
    """
    Vérifie que _log_artifact() appelle bien le logger
    avec les métadonnées attendues sur l'artefact.
    """
    artifact = tmp_path / "dump.sql"
    artifact.write_text("abc", encoding="utf-8")

    logged = {}

    def fake_info(msg, **kwargs):
        logged["msg"] = msg
        logged["extra_data"] = kwargs.get("extra", {}).get("extra_data", {})

    monkeypatch.setattr(m2.logger, "info", fake_info)

    m2._log_artifact(artifact, "dump_sql", {"k": "v"})

    assert logged["extra_data"]["kind"] == "dump_sql"
    assert logged["extra_data"]["artifact"] == "dump.sql"
    assert logged["extra_data"]["size_bytes"] == artifact.stat().st_size
    assert logged["extra_data"]["k"] == "v"
    assert "trace_id" in logged["extra_data"]


def test_perform_mysqldump_returns_false_when_mysqldump_missing(monkeypatch, tmp_path: Path):
    """
    Simule l'absence de la commande mysqldump
    et vérifie que _perform_mysqldump() retourne False.
    """
    # On force shutil.which() à dire que mysqldump est introuvable
    monkeypatch.setattr(m2.shutil, "which", lambda name: None)

    out = tmp_path / "out.sql"
    ok = m2._perform_mysqldump("h", "u", "p", "db", out, 3306)

    assert ok is False


def test_perform_mysqldump_success_writes_output(monkeypatch, tmp_path: Path):
    """
    Simule un mysqldump fonctionnel et vérifie que :
    - la fonction retourne True
    - le fichier de sortie est créé
    - le contenu du dump est bien écrit
    """
    # Simule la présence de mysqldump
    monkeypatch.setattr(m2.shutil, "which", lambda name: "/usr/bin/mysqldump")

    # Simule subprocess.run() qui écrit un dump SQL dans stdout
    def fake_run(args, stdout=None, stderr=None, **kwargs):
        stdout.write(b"-- dump --\n")
        return types.SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(m2.subprocess, "run", fake_run)

    out = tmp_path / "dump.sql"
    ok = m2._perform_mysqldump("h", "u", "p", "db", out, 3306)

    assert ok is True
    assert out.exists()
    assert out.read_bytes().startswith(b"-- dump --")


def test_test_db_connection_tcp_fail(monkeypatch):
    """
    Simule un échec de connexion TCP à la base de données.
    Le test vérifie alors que _test_db_connection() retourne False.
    """
    def fake_create_connection(*args, **kwargs):
        raise OSError("no route")

    monkeypatch.setattr(m2.socket, "create_connection", fake_create_connection)

    ok = m2._test_db_connection("h", "u", "p", "db", 3306)
    assert ok is False


def test_test_db_connection_tcp_ok_no_mysql_client(monkeypatch):
    """
    Simule :
    - une connexion TCP réussie
    - l'absence du client mysql

    D'après le comportement attendu dans ton code,
    la fonction doit retourner True dans ce cas.
    """
    class DummySock:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    # Simule une connexion TCP réussie
    monkeypatch.setattr(m2.socket, "create_connection", lambda *a, **k: DummySock())

    # Simule l'absence du client mysql
    monkeypatch.setattr(m2.shutil, "which", lambda name: None)

    ok = m2._test_db_connection("h", "u", "p", "db", 3306)
    assert ok is True


def test_test_db_connection_mysql_client_success(monkeypatch):
    """
    Simule :
    - une connexion TCP réussie
    - un client mysql présent
    - une commande SQL 'SELECT 1' qui fonctionne

    Vérifie que _test_db_connection() retourne True.
    """
    class DummySock:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    # Simule une connexion réseau OK
    monkeypatch.setattr(m2.socket, "create_connection", lambda *a, **k: DummySock())

    # Simule la présence du client mysql
    monkeypatch.setattr(m2.shutil, "which", lambda name: "/usr/bin/mysql")

    # Simule l'exécution réussie d'une commande SQL
    def fake_run(args, stdout=None, stderr=None, env=None, text=None, timeout=None, **kwargs):
        return types.SimpleNamespace(returncode=0, stdout="1\n", stderr="")

    monkeypatch.setattr(m2.subprocess, "run", fake_run)

    ok = m2._test_db_connection("h", "u", "p", "db", 3306)
    assert ok is True


def test_list_tables_mysql_client_returns_list(monkeypatch):
    """
    Vérifie que _list_tables_mysql_client() retourne
    bien une liste de noms de tables à partir de la sortie du client mysql.
    """
    # Simule un chemin valide vers mysql
    monkeypatch.setattr(m2, "_mysql_client_path", lambda: "/usr/bin/mysql")

    # Simule une sortie contenant deux tables
    def fake_run(args, stdout=None, stderr=None, env=None, text=None, **kwargs):
        return types.SimpleNamespace(returncode=0, stdout="table1\ntable2\n", stderr="")

    monkeypatch.setattr(m2.subprocess, "run", fake_run)

    tables = m2._list_tables_mysql_client("h", "u", "p", "db", 3306)
    assert tables == ["table1", "table2"]


def test_export_table_csv_mysql_client_writes_csv(monkeypatch, tmp_path: Path):
    """
    Vérifie que _export_table_csv_mysql_client() :
    - récupère d'abord les colonnes de la table
    - récupère ensuite les données
    - écrit un fichier CSV avec le séparateur ';'
    """
    monkeypatch.setattr(m2, "_mysql_client_path", lambda: "/usr/bin/mysql")

    # Compteur pour distinguer le 1er appel (SHOW COLUMNS)
    # du 2e appel (SELECT *)
    calls = {"n": 0}

    def fake_run(args, stdout=None, stderr=None, env=None, text=None, **kwargs):
        calls["n"] += 1

        if calls["n"] == 1:
            # Réponse simulée pour SHOW COLUMNS
            # format : nom_colonne \t type
            return types.SimpleNamespace(
                returncode=0,
                stdout="id\tint\nname\tvarchar\n",
                stderr=""
            )
        else:
            # Réponse simulée pour SELECT *
            return types.SimpleNamespace(
                returncode=0,
                stdout="1\tAlice\n2\tBob\n",
                stderr=""
            )

    monkeypatch.setattr(m2.subprocess, "run", fake_run)

    out_csv = tmp_path / "t.csv"
    ok = m2._export_table_csv_mysql_client("h", "u", "p", "db", "users", out_csv, 3306)

    assert ok is True

    content = out_csv.read_text(encoding="utf-8")

    # Vérifie que le CSV a bien été généré avec ';' comme séparateur
    assert "id;name" in content
    assert "1;Alice" in content
    assert "2;Bob" in content


def test_dump_sql_missing_env_exits(monkeypatch, tmp_path: Path):
    """
    Vérifie que dump_sql() s'arrête proprement si les variables
    d'environnement requises sont absentes.

    Le test vérifie aussi qu'aucun fichier .sql n'est généré.
    """
    # Supprime les variables d'environnement nécessaires
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.delenv("MYSQL_PORT", raising=False)
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.delenv("MYSQL_DB", raising=False)

    # Remplace get_paths() pour travailler dans tmp_path
    class DummyPaths:
        sauvegarde_dir = tmp_path
        repo_root = tmp_path
        log_dir = tmp_path

    monkeypatch.setattr(m2, "get_paths", lambda: DummyPaths())

    # Empêche un éventuel blocage si getpass est appelé
    monkeypatch.setattr(m2.getpass, "getpass", lambda prompt: "x")

    # La fonction ne doit pas planter
    m2.dump_sql()

    # Aucun dump ne doit être créé
    assert list(tmp_path.glob("*.sql")) == []