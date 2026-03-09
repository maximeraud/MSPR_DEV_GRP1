"""
Batterie de tests pour le module d'audit SSH (module3_audit.py)

Tests couverts :
- test_find_ssh_key_found : Vérifie la détection d'une clé SSH présente dans ~/.ssh.
- test_find_ssh_key_not_found : Vérifie le retour None si aucune clé SSH n'est trouvée.
- test_audit_linux : Simule un hôte Linux et vérifie l'extraction correcte des informations système (distribution, version, kernel, hostname).
- test_audit_windows : Simule un hôte Windows (après échec Linux) et vérifie la détection de l'OS et la récupération des informations système (hostname, version).

Chaque test utilise monkeypatch pour isoler les dépendances système ou réseau.
"""

from pathlib import Path
from ntl_systoolbox.cli.module3_audit import find_ssh_key
from ntl_systoolbox.cli.module3_audit import get_system_audit_ssh



def test_find_ssh_key_found(tmp_path, monkeypatch):
    """
    Vérifie que la fonction find_ssh_key détecte une clé SSH
    lorsqu'elle est présente dans le dossier ~/.ssh.
    """

    # Création d'un faux dossier ~/.ssh
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()

    # Création d'une fausse clé SSH
    key_file = ssh_dir / "id_rsa"
    key_file.write_text("fakekey")

    # On remplace Path.home() par notre dossier temporaire
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = find_ssh_key()

    assert result.endswith("id_rsa")

def test_find_ssh_key_not_found(tmp_path, monkeypatch):
    """
    Vérifie que la fonction retourne None
    lorsqu'aucune clé SSH n'est présente.
    """

    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = find_ssh_key()

    assert result is None



def test_audit_linux(monkeypatch):
    """
    Vérifie que la fonction détecte correctement
    un système Linux et extrait les informations.
    """

    fake_result = {
        "success": True,
        "outputs": {
            "cat /etc/os-release": {
                "stdout": 'ID=ubuntu\nPRETTY_NAME="Ubuntu 22.04"\nVERSION_ID="22.04"'
            },
            "uname -a": {
                "stdout": "Linux kernel"
            },
            "hostname": {
                "stdout": "server01"
            }
        }
    }


    monkeypatch.setattr(
        "ntl_systoolbox.cli.module3_audit.run_command_ssh",
        lambda *args, **kwargs: fake_result
    )

    result = get_system_audit_ssh("1.1.1.1", "user", "key")

    assert result["os_family"] == "linux"
    assert result["distribution"] == "ubuntu"


def test_audit_windows(monkeypatch):
    """
    Vérifie que le script détecte Windows
    lorsque les commandes Linux échouent.
    """

    linux_fail = {"success": False}

    windows_ok = {
        "success": True,
        "outputs": {
            "hostname": {"stdout": "WIN01"},
            "ver": {"stdout": "Windows 10"}
        }
    }

    calls = [linux_fail, windows_ok]

    def fake_run(*args, **kwargs):
        return calls.pop(0)

    monkeypatch.setattr("ntl_systoolbox.cli.module3_audit.run_command_ssh", fake_run)

    result = get_system_audit_ssh("1.1.1.1", "user", "key")

    assert result["os_family"] == "windows"
