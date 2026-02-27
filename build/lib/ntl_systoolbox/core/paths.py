from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    sauvegarde_dir: Path

def detect_repo_root() -> Path:
    # Heuristique robuste: remonter depuis le fichier du module pour trouver
    # "sauvegarde/" ou "pyproject.toml" (fonctionne même si l'app est lancée
    # depuis un autre working directory).
    cur_dir = Path(__file__).resolve().parent
    for parent in [cur_dir] + list(cur_dir.parents):
        if (parent / "pyproject.toml").exists() or (parent / "sauvegarde").exists():
            return parent
    return cur_dir

def get_paths() -> AppPaths:
    root = detect_repo_root()
    sauvegarde = root / "sauvegarde"
    sauvegarde.mkdir(parents=True, exist_ok=True)
    return AppPaths(repo_root=root, sauvegarde_dir=sauvegarde)