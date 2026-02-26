import typer
import json
import platform
app = typer.Typer()

@app.command("run")
def run():
    """Audit obsolescence (placeholder)."""
    print("TODO: module 3 audit")


def get_system_audit():
    os_family = platform.system().lower()
    hostname = platform.node()
    architecture = platform.machine()

    # ======================
    # ======= LINUX ========
    # ======================
    if os_family == "linux":
        os_data = {}

        try:
            with open("/etc/os-release") as f:
                for line in f:
                    key, _, value = line.partition("=")
                    os_data[key.strip()] = value.strip().strip('"')
        except Exception:
            pass

        return {
            "hostname": hostname,
            "architecture": architecture,
            "os_family": "linux",
            "distribution": os_data.get("ID"),
            "distribution_name": os_data.get("PRETTY_NAME"),
            "version": os_data.get("VERSION_ID"),
            "kernel_version": platform.release()
        }

    # ======================
    # ====== WINDOWS =======
    # ======================
    elif os_family == "windows":
        try:
            import winreg

            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
                current_build, _ = winreg.QueryValueEx(key, "CurrentBuild")
                ubr, _ = winreg.QueryValueEx(key, "UBR")

            full_build = f"{current_build}.{ubr}"

            return {
                "hostname": hostname,
                "architecture": architecture,
                "os_family": "windows",
                "version": display_version,   # ex: 24H2
                "build": full_build           # ex: 26100.1150
            }

        except Exception:
            return {
                "hostname": hostname,
                "architecture": architecture,
                "os_family": "windows",
                "version": None,
                "build": None
            }

    else:
        return {
            "hostname": hostname,
            "architecture": architecture,
            "os_family": os_family
        }
