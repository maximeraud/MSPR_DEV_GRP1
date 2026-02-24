from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    sauvegarde_dir: Path

def detect_repo_root() -> Path:
    # Heuristique simple: remonter jusqu'à trouver "sauvegarde/" ou "pyproject.toml"
    cur = Path.cwd().resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / "pyproject.toml").exists() or (parent / "sauvegarde").exists():
            return parent
    return cur

def get_paths() -> AppPaths:
    root = detect_repo_root()
    sauvegarde = root / "sauvegarde"
    sauvegarde.mkdir(parents=True, exist_ok=True)
    return AppPaths(repo_root=root, sauvegarde_dir=sauvegarde)