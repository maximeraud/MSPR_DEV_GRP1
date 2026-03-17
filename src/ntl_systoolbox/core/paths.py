from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    sauvegarde_dir: Path
    log_dir: Path

def detect_repo_root() -> Path:
    # Partir du répertoire de travail courant (cwd) pour trouver la racine du
    # projet via "pyproject.toml" ou "sauvegarde/". Cela fonctionne que le
    # package soit installé ou utilisé en développement, à condition de lancer
    # la commande depuis le projet (ou un sous-dossier).
    cur_dir = Path.cwd()
    for parent in [cur_dir] + list(cur_dir.parents):
        if (parent / "pyproject.toml").exists() or (parent / "sauvegarde").exists():
            return parent
    return cur_dir

def get_paths() -> AppPaths:
    root = detect_repo_root()
    sauvegarde = root / "sauvegarde"
    sauvegarde.mkdir(parents=True, exist_ok=True)
    log = root / "log"
    log.mkdir(parents=True, exist_ok=True)
    return AppPaths(repo_root=root, sauvegarde_dir=sauvegarde, log_dir=log)