#python -m pip install psutil typer paramiko
#Distant : python diagnostic.py choose --mode remote
import typer
import mariadb          #MariaDB
import paramiko         #SSH distant (OpenSSH Windows/Linux)
import getpass          #Mot de passe sécurisé
import re               #Gestions des données (Disque/RAM/CPU/Uptime)s
import sys              #Ferme le programme

app = typer.Typer()

@app.command("run")

# ======== FONCTION : BDD ========

def run():
    # Connection parameters
    db_config = {
        'user': 'admin',
        'password': 'admin',
        'host': '172.16.135.60',
        'port': 3306,
        'database': 'diagTest'
    }

    conn = None
    cursor = None

    try:
        # Establish connection
        conn = mariadb.connect(**db_config)
        print("Connected successfully!")

        # Create a cursor
        cursor = conn.cursor()

        # Execute a query
        cursor.execute("SELECT * FROM contacts")
        results = cursor.fetchall()

        # Display results
        for row in results:
            print(row)

    except mariadb.Error as err:
        print(f"Error: {err}")

    finally:
        # Close connection and cursor safely
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# ======== FONCTION : DISTANT SSH (LINUX + WINDOWS) ========
def check_remote_ssh(host: str, user: str, password: str, port: int = 22):
    print(f"\n{'='*60}")
    print(f"DIAGNOSTIC {host}:{port}")
    print(f"{'='*60}")
    
    #Initialisation client SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    #Exécute commande SSH + gère erreurs
    def safe_exec(cmd, timeout=15):
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode('utf-8', errors='ignore').strip()
            err = stderr.read().decode('utf-8', errors='ignore').strip()
            return out if out and not err else "ERREUR"
        except:
            return "ERREUR"
    
    try:
        ssh.connect(host, port=port, username=user, password=password, timeout=10)
        print("SSH connecté !")
        
        #DETECTION AUTOMATIQUE OS
        uname_result = safe_exec('uname -s 2>/dev/null')
        win_reg = safe_exec('reg query "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion" /v ProductName 2>nul')
        cmd_ver = safe_exec('ver 2>/dev/null')
        
        is_windows = "ProductName" in win_reg or "Microsoft Windows" in cmd_ver
        is_linux = "Linux" in uname_result
        
        os_type = "Windows" if is_windows else "Linux" if is_linux else "Windows"
        print(f"Système détecté : {os_type}")
        
        #AFFICHAGE OS
        if is_windows:
            os_name = safe_exec('systeminfo | findstr /B /C:"OS Name" /C:"OS Version" 2>nul')
            if "ERREUR" in os_name:
                os_name = safe_exec('ver')
        else:
            os_name = safe_exec('grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d\'"\' -f2')
        print(f"OS : {os_name}")
        
        #UPTIME
        if is_windows:
            uptime_raw = safe_exec('powershell -c "[math]::Round(((Get-Date)-(Get-CimInstance Win32_OperatingSystem).LastBootUpTime).TotalSeconds)"')
            if uptime_raw != "ERREUR" and uptime_raw.isdigit():
                sec = int(uptime_raw)
                days = sec // 86400
                hours = (sec % 86400) // 3600
                print(f"Uptime : {days}j {hours}h")
            else:
                print("Uptime : ERREUR")
        else:
            uptime_raw = safe_exec('uptime -p')
            print(f"Uptime : {uptime_raw}")
        
        #CPU + RAM Utilisation (%)
        if is_windows:
            cpu_raw = safe_exec('powershell -c "(Get-WmiObject Win32_Processor).LoadPercentage"')
            ram_raw = safe_exec('powershell -c "[math]::Round((1-(Get-WmiObject Win32_OperatingSystem).FreePhysicalMemory/(Get-WmiObject Win32_OperatingSystem).TotalVisibleMemorySize)*100)"')
        else:
            cpu_raw = safe_exec('top -bn1 | grep "%Cpu" | awk \'{print $2}\' | cut -d"%" -f1')
            ram_raw = safe_exec('free | grep "^Mem:" | awk \'{print int($3/$2 * 100)}\'')
        
        print(f"CPU : {cpu_raw if cpu_raw != 'ERREUR' else 'ERREUR'}% d'utilisation")
        print(f"RAM : {ram_raw if ram_raw != 'ERREUR' else 'ERREUR'}% d'utilisation")

        #DISQUE PRINCIPAL C: ou /
        if is_windows:
            disk_wmic = safe_exec('wmic logicaldisk where "DeviceID=\'C:\'" get Size,FreeSpace /value 2>nul', timeout=20)
            if "ERREUR" not in disk_wmic:
                size_match = re.search(r'Size=(\d+)', disk_wmic)
                free_match = re.search(r'FreeSpace=(\d+)', disk_wmic)
                if size_match and free_match:
                    total_bytes = int(size_match.group(1))
                    free_bytes = int(free_match.group(1))
                    used_percent = ((total_bytes - free_bytes) / total_bytes) * 100
                    print(f"Disque C: {used_percent:.1f}% ({total_bytes//(1024**3)} Go)")
                else:
                    print("C: ERREUR parsing")
            else:
                print("C: ERREUR WMIC")
        else:
            disk_raw = safe_exec('df -h / | tail -1 | awk \'{printf "%s (%.0fG total)", $5, $2}\'')
            print(f"Disque /: {disk_raw}")
        
        #SERVICES AD/DNS ou SSID/Bind9
        if is_windows:
            ntds = safe_exec('sc query NTDS 2>nul | findstr "RUNNING"')
            dns = safe_exec('sc query DNS 2>nul | findstr "RUNNING"')
            ntds_status = "ACTIF" if "RUNNING" in ntds else "KO"
            dns_status = "ACTIF" if "RUNNING" in dns else "sKO"
            print(f"NTDS : {ntds_status}")
            print(f"DNS  : {dns_status}")
        else:
            sssd = safe_exec('systemctl is-active sssd 2>/dev/null || echo inactive')
            bind9 = safe_exec('systemctl is-active bind9 2>/dev/null || echo inactive')
            print(f"SSSD  : {'ACTIF' if 'active' in sssd else 'KO'}")
            print(f"BIND9 : {'ACTIF' if 'active' in bind9 else 'KO'}")
        
        print(f"\n{'='*60}")
        print("DIAGNOSTIC TERMINÉ")
        
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        ssh.close()

def run_AD_DNS_OS():
    print(" DIAGNOSTIC COMPLET (Windows Server / Ubuntu)\n")
    host = input("IP/Hostname : ").strip()
    user = input("Utilisateur : ").strip()
    password = getpass.getpass("Mot de passe : ")
    port_input = input("Port SSH [22] : ").strip()
    port = int(port_input) if port_input else 22
    
    check_remote_ssh(host, user, password, port)
