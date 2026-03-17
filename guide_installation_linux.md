# Guide d'installation — NTL SysToolbox
>
> Application CLI Python — Debian 13

---

## Prérequis

### Machine virtuelle

| Composant | Minimum recommandé |
| --- | --- |
| OS | Debian 13 (Trixie) |
| RAM | 512 Mo |
| Stockage | 2 Go d'espace libre |
| Réseau | Accès Internet (pour télécharger les dépendances) |
| Droits | Accès `sudo` obligatoire |

### Logiciels requis sur la VM

- **`git`** — pour cloner le dépôt du projet
- **`sudo`** — pour installer les paquets système

Vérifier que `git` est installé :

```bash
git --version
```

Si non installé :

```bash
sudo apt install git
```

---

## Récupérer le projet

Cloner le dépôt sur la machine :

```bash
git clone git@github.com:maximeraud/MSPR_DEV_GRP1.git
cd MSPR_DEV_GRP1
```

---

## Installation via le script `setup/setup_linux.sh`

### Rendre le script exécutable

```bash
chmod +x setup/setup_linux.sh
```

### Lancer le script

```bash
bash setup/setup_linux.sh
```

Le script s'occupe de tout automatiquement. Il affiche la progression à chaque étape et s'arrête immédiatement en cas d'erreur.

---

## Ce que le script installe et pourquoi

### 1. Python 3

```bash
sudo apt install python3
```

Langage dans lequel est développée l'application. Debian 13 fournit **Python 3.13** dans ses dépôts officiels.

---

### 2. pip

```bash
sudo apt install python3-pip
```

Gestionnaire de paquets Python, nécessaire pour installer les dépendances du projet.

---

### 3. python3.13-venv

```bash
sudo apt install python3.13-venv
```

Module permettant de créer des **environnements virtuels Python**. Requis par Debian 13 qui protège l'installation Python système contre les modifications extérieures.

---

### 4. Environnement virtuel `.venv`

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Crée un environnement Python isolé dans le dossier `.venv/`. Cela permet d'installer les dépendances du projet **sans affecter le système**, et d'éviter les conflits entre paquets.

---

### 5. Installation du projet

```bash
pip install -e .
```

Installe le projet `ntl-systoolbox` en mode éditable à partir du fichier `pyproject.toml`. Cela enregistre la commande `ntl-systoolbox` dans le venv et rend le projet importable en Python.

---

### 6. MariaDB client

```bash
sudo apt install mariadb-client
```

Fournit l'outil `mysqldump` et les utilitaires en ligne de commande MariaDB/MySQL. Nécessaire pour les fonctionnalités de **sauvegarde de bases de données** de l'application.

---

### 7. Librairies système MariaDB

```bash
sudo apt install libmariadb3 libmariadb-dev
```

Librairies C nécessaires à la compilation et au fonctionnement du connecteur Python `mariadb`. Sans elles, le module Python ne peut pas s'installer correctement.

---

### 8. Module Python `mariadb`

```bash
pip install mariadb
```

Connecteur Python officiel pour MariaDB. Permet à l'application de **se connecter et d'interagir avec des bases de données MariaDB**.

---

### 9. Module Python `paramiko`

```bash
pip install paramiko
```

Librairie Python pour les connexions **SSH**. Utilisée par l'application pour se connecter à des machines distantes et exécuter des commandes à distance.

---

### 10. Module Python `python-dotenv`

```bash
pip install python-dotenv
```

Permet de charger des variables d'environnement depuis un fichier `.env`. Utilisé pour gérer la **configuration de l'application** (identifiants, hôtes, ports…) sans les mettre en dur dans le code.

---

### 11. Module Python `requests`

```bash
pip install requests
```

Librairie HTTP pour Python. Permet à l'application d'effectuer des **appels vers des APIs ou services web**.

---

## Après l'installation

### Lancer l'application

```bash
source .venv/bin/activate
ntl-systoolbox
```

### Afficher l'aide et les commandes disponibles

```bash
ntl-systoolbox --help
```

---

## Sessions suivantes

> ⚠️ L'environnement virtuel **ne s'active pas automatiquement** à chaque ouverture de terminal.

À chaque nouvelle session, activer le venv avant d'utiliser l'application :

```bash
cd MSPR_DEV_GRP1
source .venv/bin/activate
ntl-systoolbox
```

---

## Réinitialiser l'installation

Pour repartir de zéro (supprimer et recréer l'environnement virtuel) :

```bash
deactivate          # Si le venv est actif
rm -rf .venv        # Suppression du venv
bash setup/setup_linux.sh          # Réinstallation complète
```

---

## Résolution des problèmes courants

| Erreur | Cause | Solution |
| --- | --- | --- |
| `command not found: ntl-systoolbox` | venv non activé | `source .venv/bin/activate` |
| `externally-managed-environment` | Installation hors venv | Utiliser le venv via `setup.sh` |
| `No module named 'mariadb'` | Librairies système manquantes | `sudo apt install libmariadb3 libmariadb-dev` |
| `sudo: command not found` | Droits insuffisants | Ajouter l'utilisateur au groupe `sudo` |
| `pip: command not found` | pip non installé | `sudo apt install python3-pip` |
