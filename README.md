# NTL-SysToolbox

Outil CLI Python d'administration système regroupant trois modules : diagnostic, sauvegarde et audit d'obsolescence. L'application propose un menu interactif ou des commandes directes via la ligne de commande.

---

## Prérequis

- Python >= 3.10
- `mysqldump` / `mysql` client installés (pour les modules 2 et 3)
- Accès SSH aux machines distantes (clé privée dans `~/.ssh`)

---

## Installation

```bash
pip install -e .
```

---

## Configuration

Créer un fichier `.env` à la racine du projet (exemple) :

```env
MYSQL_HOST=172.16.135.62
MYSQL_PORT=3306
MYSQL_USER=backup
MYSQL_DB=ntl
# MYSQL_PASSWORD=... (optionnel, sinon demandé à l'exécution)
```

---

## Lancement

**Menu interactif (par défaut) :**

```bash
py -m ntl_systoolbox.main
```

ou, si installé en tant que script :

```bash
ntl-systoolbox
```

**Commandes directes :**

```bash
ntl-systoolbox diag run           # Module 1 - Diagnostic BDD
ntl-systoolbox backup dump        # Module 2 - Dump SQL
ntl-systoolbox backup export-csv  # Module 2 - Export CSV
ntl-systoolbox audit audit-system-ssh ...  # Module 3 - Audit système SSH
```

---

## Modules

### Module 1 — Diagnostic

Permet de diagnostiquer des serveurs locaux ou distants.

- **Test de connexion MariaDB** : vérifie l'accès à une base de données (hôte, port, utilisateur, mot de passe).
- **Diagnostic SSH distant** (Windows Server & Ubuntu) : connexion SSH vers un serveur, détection automatique de l'OS, puis collecte :
  - Uptime
  - CPU et RAM (% d'utilisation)
  - Espace disque principal (`C:` ou `/`)
  - Statut des services critiques : NTDS/DNS (Windows) ou SSSD/BIND9 (Linux)

### Module 2 — Sauvegarde WMS

Sauvegarde de la base de données WMS (MariaDB/MySQL).

- **Dump SQL** (`backup dump`) : exécute `mysqldump` et enregistre le fichier dans `sauvegarde/` avec horodatage (`wms_dump_YYYYMMDD_HHMMSS.sql`).
- **Export CSV** (`backup export-csv`) : liste les tables disponibles, exporte la table choisie en CSV (délimiteur `;`) dans `export/`.

Les paramètres de connexion sont lus depuis le fichier `.env`. Le mot de passe est demandé interactivement si absent.

### Module 3 — Audit d'obsolescence réseau

Audit des systèmes d'un réseau via SSH avec vérification des dates de fin de vie (EOL).

- **Audit système SSH** (`audit audit-system-ssh`) : récupère les informations OS d'une machine distante (Linux ou Windows) et vérifie son statut EOL via l'API [endoflife.date](https://endoflife.date).
- **Scan réseau multithread** (`audit audit-network-ssh-mt`) : scanne un sous-réseau (ex : `192.168.1.0/24`) en parallèle, en interrogeant chaque hôte SSH.
- **Rapport** : génère un fichier JSON horodaté dans `logs/` et permet son export en CSV.
- **Statuts de support** : `supported`, `soon_eol` (< 6 mois), `unsupported`.

---

## Structure du projet

```text
MSPR_DEV_GRP1/
├── src/
│   ├── ntl_systoolbox/
│   │   ├── cli/
│   │   │   ├── app.py            # Point d'entrée Typer, enregistrement des modules
│   │   │   ├── interactive.py    # Menus interactifs
│   │   │   ├── module1_diag.py   # Module 1 - Diagnostic
│   │   │   ├── module2_backup.py # Module 2 - Sauvegarde
│   │   │   ├── module3_audit.py  # Module 3 - Audit EOL
│   │   │   └── logger.py         # Logger centralisé
│   │   ├── core/
│   │   │   ├── paths.py          # Chemins du projet
│   │   │   └── ui.py             # Composants d'interface console
│   │   └── main.py               # Entrée principale
│   └── tests/
│       ├── test_module1_diag.py
│       ├── test_module2_backup.py
│       └── test_module3.py
├── sauvegarde/                   # Dumps SQL générés
├── export/                       # Exports CSV générés
├── logs/                         # Rapports d'audit JSON/CSV
├── setup/
│   └── setup_linux.sh            # Script d'installation Linux
├── .env                          # Configuration base de données
├── pyproject.toml
└── .github/workflows/
    └── python-app.yml            # Pipeline CI/CD
```

---

## Tests

Les tests unitaires se trouvent dans `src/tests/`.

```bash
pytest -v src/tests
```

---

## CI/CD

Le projet utilise **GitHub Actions** (workflow `Python application`) déclenché à chaque push ou pull request sur `main`.

La pipeline :

1. Installe le projet et ses dépendances (dont MariaDB)
2. Crée une base de données de test locale
3. Vérifie la qualité du code avec **flake8**
4. Exécute les tests avec **pytest**
