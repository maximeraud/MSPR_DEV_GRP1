import json
import os
from ntl_systoolbox.core.paths import detect_repo_root
import paramiko
from pathlib import Path
import typer
from rich.console import Console
import ipaddress
import socket
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from datetime import datetime



EOL_API = "https://endoflife.date/api"
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
    """
    Exécute une liste de commandes sur un hôte distant via SSH.
    Retourne un dictionnaire avec les sorties et le statut.
    """
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
def get_system_audit_ssh(host: str, username: str, ssh_key: str | None = None, host_ip: str | None = None) -> dict:
    """
    Récupère les informations système d'un host distant via SSH.
    Peut prendre un paramètre optionnel host_ip pour préciser l'adresse IP.
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

    if host_ip:
        system_info["host_ip"] = host_ip
    # Enrichit le résultat avec EOL
    return enrich_with_eol(system_info)


@app.command("audit-network-ssh-mt")
def audit_network_ssh_mt(
    hosts: list[str] | None = None, 
    username: str = None, 
    ssh_key: str | None = None,
    subnet: str | None = None,
    max_workers: int = 25,  # nombre de threads
    network: str | None = None
) -> None:
    """"
    - hosts : liste d'IP
    - subnet : plage réseau, ex: 192.168.1.0/24
    - Si aucun host ni subnet fourni, scan du /24 autour de l'IP locale
    - Ignore rapidement les machines qui ne répondent pas
    - network : paramètre optionnel pour préciser le réseau à auditer
    """
    import ipaddress, socket, json
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not username:
        username = typer.prompt("Nom d'utilisateur SSH non fourni. Merci de saisir le login :")


    # Détection automatique de la clé SSH
    if ssh_key is None:
        ssh_key = find_ssh_key()
        if ssh_key is None:
            typer.echo(json.dumps([{"error": "Aucune clé SSH trouvée"}], indent=2))
            raise typer.Exit()

    # Génération de la liste d'hôtes
   
    if not hosts:
        if network:
            net = ipaddress.ip_network(network, strict=False)
            hosts = [str(ip) for ip in net.hosts()]
        elif subnet:
            net = ipaddress.ip_network(subnet, strict=False)
            hosts = [str(ip) for ip in net.hosts()]
        else:
            local_ip = socket.gethostbyname(socket.gethostname())
            network_prefix = ".".join(local_ip.split(".")[:3])
            hosts = [f"{network_prefix}.{i}" for i in range(1, 255)]
    typer.echo(f"Début du scan de {len(hosts)} hôtes...")

    # Fonction interne pour thread
    def audit_host(host: str) -> dict:
        try:
            typer.echo(f"Tentative de connexion à {host}...")
            info = get_system_audit_ssh(host, username, ssh_key)
            info["host_ip"] = host
            typer.echo(json.dumps(info, indent=2, ensure_ascii=False))
            if "error" in info:
                typer.echo(f"[ERROR] {host} -> {info['error']}")
            else:
                typer.echo(f"[OK] {host} -> Connexion réussie")
            return info
        except Exception as e:
            typer.echo(f"[TIMEOUT/ERROR] {host} -> {str(e)}")
            return {"host_ip": host, "error": str(e)}

    # Multithreading
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_host = {executor.submit(audit_host, host): host for host in hosts}
        for future in as_completed(future_to_host):
            results.append(future.result())
        
        typer.echo("Audit terminé")
        
            # Filtrer les machines où la connexion a fonctionné
        successful_results = [r for r in results if 'error' not in r]
        if successful_results:
            typer.echo("\nRésultats des machines connectées :")
            typer.echo(json.dumps(successful_results, indent=2, ensure_ascii=False))
            generate_report(successful_results)
        else:
            typer.echo("Aucune machine connectée avec succès.")

#### EN TEST - FONCTIONS DE TRAITEMENT DES CYCLES EOL (END OF LIFE) ####

@app.command("fetch-eol")
def fetch_eol_data(product):
    """
    Récupère les cycles EOL pour un produit donné via l'API endoflife.date.
    Retourne une liste de cycles.
    """

    url = f"{EOL_API}/{product}.json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []

def find_eol(product, version):
    """
    Cherche les informations EOL pour un produit et une version.
    Retourne un dictionnaire avec cycle, eol et release.
    """
    data = fetch_eol_data(product)
    print(f"[DEBUG EOL] product={product}, version={version}, data={data}")

    for item in data:
        cycle = item.get("cycle")

        if cycle and version.startswith(cycle):
            return {
                "cycle": cycle,
                "eol": item.get("eol"),
                "release": item.get("releaseDate")
            }

    return None

def calculate_support_status(eol_date):
    """
    Calcule le statut de support en fonction de la date EOL.
    Retourne 'supported', 'soon_eol', 'unsupported' ou 'unknown'.
    """

    if not eol_date:
        return "unknown"

    today = datetime.today()
    eol = datetime.strptime(eol_date, "%Y-%m-%d")

    days_left = (eol - today).days

    if days_left < 0:
        return "unsupported"

    elif days_left < 180:
        return "soon_eol"

    else:
        return "supported"
    
def enrich_with_eol(system_info):
    """
    Enrichit le dictionnaire system_info avec les informations EOL et support_status.
    Retourne le dictionnaire enrichi.
    """
    os_family = system_info.get("os_family")
    distribution = system_info.get("distribution")
    version = system_info.get("version")

    product = distribution if distribution else os_family

    eol_info = find_eol(product, version)

    if not eol_info:
        system_info["eol"] = None   
        system_info["support_status"] = "unknown"
        return system_info

    system_info["eol"] = eol_info["eol"]
    system_info["support_status"] = calculate_support_status(eol_info["eol"])

    return system_info



def get_logs_dir():
    """
    Retourne le chemin absolu du dossier logs à la racine du projet.
    """
    root = detect_repo_root()
    logs_dir = os.path.join(root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def generate_report(results, filename="audit_report.json"):
    """
    Génère un rapport JSON des résultats d'audit.
    Le fichier est sauvegardé sous filename.
    """

    logs_dir = get_logs_dir()
    filename = os.path.join(logs_dir, "audit_report.json")
    report = {
        "scan_date": datetime.today().isoformat(),
        "hosts": results
    }
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Rapport généré : {filename}")

@app.command("export-audit-csv")
def export_audit_report_csv() -> None:
    """
    Exporte le rapport audit_report.json en CSV dans le dossier logs.
    """
    import csv
    logs_dir = get_logs_dir()
    json_file = os.path.join(logs_dir, "audit_report.json")
    csv_file = os.path.join(logs_dir, "audit_report.csv")
    if not os.path.exists(json_file):
        print("Aucun rapport audit_report.json trouvé.")
        return
    with open(json_file, "r") as f:
        report = json.load(f)
    hosts = report.get('hosts', [])
    with open(csv_file, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["IP", "Hostname", "OS", "Version", "EOL", "Support", "Kernel"])
        for host in hosts:
            writer.writerow([
                host.get('host_ip', 'N/A'),
                host.get('hostname', 'N/A'),
                host.get('distribution_name', host.get('os_family', 'N/A')),
                host.get('version', 'N/A'),
                host.get('eol', 'N/A'),
                host.get('support_status', 'N/A'),
                host.get('kernel_version', 'N/A')
            ])
    print(f"Rapport exporté en CSV : {csv_file}")

@app.command("show-audit-report")
def show_audit_report() -> None:
    """
    Affiche le rapport audit_report.json de façon visuelle (console).
    """
    logs_dir = get_logs_dir()
    filename = os.path.join(logs_dir, "audit_report.json")
    if not os.path.exists(filename):
        print("Aucun rapport audit_report.json trouvé.")
        return
    with open(filename, "r") as f:
        report = json.load(f)
    print("\n===== Rapport Audit Visuel =====")
    print(f"Date du scan : {report.get('scan_date')}")
    for host in report.get('hosts', []):
        print("------------------------------")
        print(f"IP : {host.get('host_ip', 'N/A')}")
        print(f"Hostname : {host.get('hostname', 'N/A')}")
        print(f"OS : {host.get('distribution_name', host.get('os_family', 'N/A'))}")
        print(f"Version : {host.get('version', 'N/A')}")
        print(f"EOL : {host.get('eol', 'N/A')}")
        print(f"Support : {host.get('support_status', 'N/A')}")
        print(f"Kernel : {host.get('kernel_version', 'N/A')}")
    print("==============================\n")

# --- Fonctions appelées par le menu interactif ---

def interactive_audit_system() -> None:
    """
    Lance un audit système SSH interactif sur une machine prédéfinie.
    Affiche le résultat en JSON.
    """
    ip = typer.prompt("Adresse IP de la machine à auditer (ex: 192.168.1.10)")
    username = typer.prompt("Nom d'utilisateur SSH")
    audit_data = get_system_audit_ssh(ip, username)
    print(json.dumps(audit_data, indent=2))

def interactive_audit_reseau() -> None:
    """
    Lance un audit réseau SSH multithread sur un subnet prédéfini.
    Affiche les résultats.
    """
    subnet = typer.prompt("Plage réseau à auditer (ex: 192.168.1.0/24)")
    audit_network_ssh_mt(subnet=subnet)