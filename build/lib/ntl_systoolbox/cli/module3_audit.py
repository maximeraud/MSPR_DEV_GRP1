import json
import os
import paramiko
from pathlib import Path
import typer
from rich.console import Console
import ipaddress
import socket
import json
from concurrent.futures import ThreadPoolExecutor, as_completed


app = typer.Typer()

# --------------------------
# Détection automatique de la clé SSH
# --------------------------
@app.command("find-ssh-key")
def find_ssh_key() -> str | None:
    """
    Cherche automatiquement une clé privée SSH dans ~/.ssh.
    Retourne le chemin complet ou None si aucune trouvée.
    """
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.exists():
        return None

    # Cherche des clés privées classiques
    for key_name in ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]:
        key_path = ssh_dir / key_name
        if key_path.exists():
            return str(key_path)
    return None

# --------------------------
# run_command_ssh
# --------------------------
@app.command("run-ssh")
def run_command_ssh(host: str, username: str, key_path: str, commands: list[str]) -> dict:
    result = {"host": host, "success": False, "outputs": {}}
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=host, username=username, key_filename=key_path, timeout=10)
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            result["outputs"][cmd] = {"stdout": out, "stderr": err}
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    finally:
        ssh.close()
    return result

# --------------------------
# get_system_audit_ssh
# --------------------------
@app.command("audit-system-ssh")
def get_system_audit_ssh(host: str, username: str, ssh_key: str | None = None) -> dict:
    """
    Récupère les informations système d'un host distant via SSH.
    """
    # Détecte la clé si elle n'est pas fournie
    if ssh_key is None:
        ssh_key = find_ssh_key()
        if ssh_key is None:
            return {"error": "Aucune clé SSH trouvée"}

    commands_linux = ["cat /etc/os-release", "uname -a", "hostname"]
    commands_windows = ["ver", "hostname"]

    # Tentative Linux
    ssh_result = run_command_ssh(host, username, ssh_key, commands_linux)
    system_info = {}

    if ssh_result.get("success"):
        os_release_output = ssh_result["outputs"].get("cat /etc/os-release", {}).get("stdout", "")
        os_data = {}
        for line in os_release_output.splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                os_data[key] = val.strip('"')
        system_info = {
            "hostname": ssh_result["outputs"].get("hostname", {}).get("stdout", ""),
            "os_family": "linux",
            "distribution": os_data.get("ID"),
            "distribution_name": os_data.get("PRETTY_NAME"),
            "version": os_data.get("VERSION_ID"),
            "kernel_version": ssh_result["outputs"].get("uname -a", {}).get("stdout", "")
        }
    else:
        # Tentative Windows
        ssh_result_win = run_command_ssh(host, username, ssh_key, commands_windows)
        if ssh_result_win.get("success"):
            system_info = {
                "hostname": ssh_result_win["outputs"].get("hostname", {}).get("stdout", ""),
                "os_family": "windows",
                "version": ssh_result_win["outputs"].get("ver", {}).get("stdout", "")
            }
        else:
            system_info = {"error": ssh_result.get("error")}

    return system_info


@app.command("audit-network-ssh-mt")
def audit_network_ssh_mt(
    hosts: list[str] | None = None, 
    username: str = None, 
    ssh_key: str | None = None,
    subnet: str | None = None,
    max_workers: int = 25  # nombre de threads
) -> None:
    """
    Audite un réseau via SSH en multithread.
    - hosts : liste d'IP
    - subnet : plage réseau, ex: 192.168.1.0/24
    - Si aucun host ni subnet fourni, scan du /24 autour de l'IP locale
    - Ignore rapidement les machines qui ne répondent pas
    """
    import ipaddress, socket, json
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not username:
        username = typer.prompt("[yellow]Nom d'utilisateur SSH non fourni. Merci de saisir le login :[/yellow]")


    # Détection automatique de la clé SSH
    if ssh_key is None:
        ssh_key = find_ssh_key()
        if ssh_key is None:
            typer.echo(json.dumps([{"error": "Aucune clé SSH trouvée"}], indent=2))
            raise typer.Exit()

    # Génération de la liste d'hôtes
    if not hosts:
        if subnet:
            net = ipaddress.ip_network(subnet, strict=False)
            hosts = [str(ip) for ip in net.hosts()]
        else:
            local_ip = socket.gethostbyname(socket.gethostname())
            network_prefix = ".".join(local_ip.split(".")[:3])
            hosts = [f"{network_prefix}.{i}" for i in range(1, 255)]

    typer.echo(f"[green]Début du scan de {len(hosts)} hôtes...[/green]")

    # Fonction interne pour thread
    def audit_host(host: str) -> dict:
        try:
            typer.echo(f"[blue]Tentative de connexion à {host}...[/blue]")
            info = get_system_audit_ssh(host, username, ssh_key)
            info["host_ip"] = host
            if "error" in info:
                typer.echo(f"[red][ERROR][/red] {host} -> {info['error']}")
            else:
                typer.echo(f"[green][OK][/green] {host} -> Connexion réussie")
            return info
        except Exception as e:
            typer.echo(f"[red][TIMEOUT/ERROR][/red] {host} -> {str(e)}")
            return {"host_ip": host, "error": str(e)}

    # Multithreading
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_host = {executor.submit(audit_host, host): host for host in hosts}
        for future in as_completed(future_to_host):
            results.append(future.result())

    typer.echo("[green]Audit terminé[/green]")
    typer.echo(json.dumps(results, indent=2))

# --- Fonctions appelées par le menu interactif ---

def interactive_audit_system() -> None:
    audit_data = get_system_audit_ssh("172.16.135.61", "user")
    print(json.dumps(audit_data, indent=2))

def interactive_audit_reseau() -> None:
    audit_network_ssh_mt(subnet="172.16.135.0/24")