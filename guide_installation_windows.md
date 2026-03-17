# Guide d'installation — NTL SysToolbox

> Application CLI Python — Windows 11

---

## Prérequis

### Machine

| Composant | Minimum recommandé |
| --- | --- |
| OS | Windows 11 (64 bits) |
| RAM | 8192 Mo |
| Stockage | 20 Go d'espace libre |
| Réseau | Accès Internet (pour télécharger les dépendances) |
| Droits | Compte avec droits **Administrateur** |

### Logiciels requis

- **Python 3.10+** — à installer manuellement (voir ci-dessous)
- **Git for Windows** — pour cloner le dépôt
- **Visual C++ Build Tools** — requis pour compiler le connecteur MariaDB
- **MariaDB Connector/C** — librairie système pour le module Python `mariadb`

---

## Étape 1 — Installer Python

### Via le site officiel

1. Télécharger l'installeur sur [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Lancer l'installeur
3. ⚠️ **Cocher impérativement** `Add Python to PATH` avant de cliquer sur *Install Now*

Vérifier l'installation dans un terminal PowerShell :

```powershell
python --version
pip --version
```

---

## Étape 2 — Installer Git for Windows

1. Télécharger l'installeur sur [https://git-scm.com/download/win](https://git-scm.com/download/win)
2. Lancer l'installeur en laissant les options par défaut
3. Vérifier l'installation :

```powershell
git --version
```

---

## Étape 3 — Installer Visual C++ Build Tools

Requis pour compiler le module Python `mariadb`.

1. Télécharger **Visual Studio Build Tools** sur [https://visualstudio.microsoft.com/fr/visual-cpp-build-tools/](https://visualstudio.microsoft.com/fr/visual-cpp-build-tools/)
2. Lancer l'installeur
3. Sélectionner **"Développement Desktop en C++"**
4. Cliquer sur **Installer**

---

## Étape 4 — Installer MariaDB Connector/C

Librairie système nécessaire au module Python `mariadb`.

1. Télécharger le connecteur sur [https://mariadb.com/downloads/connectors/](https://mariadb.com/downloads/connectors/)
2. Choisir **Connector/C** → Windows → 64 bits → **MSI Installer**
3. Lancer l'installeur et suivre les étapes (options par défaut)

---

## Étape 5 — Installer MariaDB Client (`mysqldump`)

Pour disposer de la commande `mysqldump` :

1. Télécharger l'installeur MariaDB sur [https://mariadb.org/download/](https://mariadb.org/download/)
2. Choisir **Windows** → **MSI Package**
3. Durant l'installation, sélectionner a minima le composant **Client Programs**
4. ⚠️ Cocher **"Add to PATH"** pour que `mysqldump` soit accessible partout

Vérifier :

```powershell
mysqldump --version
```

---

## Étape 6 — Récupérer le projet

Ouvrir un terminal **PowerShell** et cloner le dépôt :

```powershell
git clone git@github.com:maximeraud/MSPR_DEV_GRP1.git
cd MSPR_DEV_GRP1
```

---

## Étape 7 — Créer et activer l'environnement virtuel

```powershell
python -m venv .venv
.venv\Scripts\activate
```

> ⚠️ Si PowerShell bloque l'activation avec une erreur de politique d'exécution, lancer cette commande d'abord :
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
>
> Puis réessayer `.venv\Scripts\activate`.

Une fois activé, le prompt affiche **`(.venv)`** en début de ligne.

---

## Étape 8 — Installer le projet et ses dépendances

Avec le venv activé, installer le projet :

```powershell
pip install -e .
```

Puis installer les modules Python nécessaires :

```powershell
pip install mariadb
pip install paramiko
pip install python-dotenv
pip install requests
```

---

## Ce que les dépendances Python font

| Module | Rôle |
| --- | --- |
| `mariadb` | Connexion et interaction avec des bases de données MariaDB |
| `paramiko` | Connexions SSH vers des machines distantes |
| `python-dotenv` | Chargement de la configuration depuis un fichier `.env` |
| `requests` | Appels HTTP vers des APIs ou services web |

---

## Lancer l'application

```powershell
ntl-systoolbox
```

Afficher l'aide et les commandes disponibles :

```powershell
ntl-systoolbox --help
```

---

## Sessions suivantes

> ⚠️ L'environnement virtuel **ne s'active pas automatiquement** à chaque ouverture de terminal.

À chaque nouvelle session PowerShell :

```powershell
cd MSPR_DEV_GRP1
.venv\Scripts\activate
ntl-systoolbox
```

---

## Réinitialiser l'installation

Pour repartir de zéro :

```powershell
deactivate                        # Si le venv est actif
Remove-Item -Recurse -Force .venv # Suppression du venv
python -m venv .venv              # Recréation
.venv\Scripts\activate            # Activation
pip install -e .                  # Réinstallation du projet
pip install mariadb paramiko python-dotenv requests
```

---

## Résolution des problèmes courants

| Erreur | Cause | Solution |
| --- | --- | --- |
| `python: command not found` | Python absent du PATH | Réinstaller Python en cochant *Add to PATH* |
| `ntl-systoolbox: command not found` | venv non activé | `.venv\Scripts\activate` |
| `error: Microsoft Visual C++ 14.0 is required` | Build Tools manquants | Installer Visual C++ Build Tools (étape 3) |
| `ModuleNotFoundError: No module named 'mariadb'` | Connector/C manquant | Installer MariaDB Connector/C (étape 4) |
| `cannot be loaded because running scripts is disabled` | Politique PowerShell restrictive | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `mysqldump: command not found` | MariaDB client absent du PATH | Réinstaller MariaDB client en cochant *Add to PATH* |
