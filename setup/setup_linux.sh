#!/bin/bash

# ============================================
#   Script d'installation - NTL SysToolbox
#   Compatible Debian 13
# ============================================

set -e  # Arrête le script si une commande échoue

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log()     { echo -e "${GREEN}[✔] $1${NC}"; }
warn()    { echo -e "${YELLOW}[!] $1${NC}"; }
error()   { echo -e "${RED}[✘] $1${NC}"; exit 1; }

echo ""
echo "============================================"
echo "   Installation NTL SysToolbox - Debian 13"
echo "============================================"
echo ""

# Vérification Debian
if [ ! -f /etc/debian_version ]; then
    error "Ce script est prévu pour Debian uniquement."
fi

# Mise à jour des paquets
warn "Mise à jour des dépôts APT..."
sudo apt update -y
log "Dépôts mis à jour."

# Installation Python 3
warn "Installation de Python 3..."
sudo apt install -y python3
log "Python 3 installé : $(python3 --version)"

# Installation pip
warn "Installation de pip..."
sudo apt install -y python3-pip
log "pip installé."

# Installation venv
warn "Installation de python3.13-venv..."
sudo apt install -y python3.13-venv
log "venv installé."

# Création de l'environnement virtuel
warn "Création de l'environnement virtuel .venv..."
python3 -m venv .venv
log "Environnement virtuel créé."

# Activation du venv
warn "Activation du venv..."
source .venv/bin/activate
log "Environnement virtuel activé."

# Installation du projet
warn "Installation du projet (pip install -e .)..."
pip install -e .
log "Projet installé."

# Installation MariaDB client
warn "Installation de mariadb-client..."
sudo apt install -y mariadb-client
log "mariadb-client installé."

# Installation des dépendances système MariaDB
warn "Installation de libmariadb3 et libmariadb-dev..."
sudo apt install -y libmariadb3 libmariadb-dev
log "Librairies MariaDB installées."

# Installation des modules Python
warn "Installation des modules Python..."
pip install mariadb
log "mariadb installé."

pip install paramiko
log "paramiko installé."

pip install python-dotenv
log "python-dotenv installé."

pip install requests
log "requests installé."

echo ""
echo "============================================"
echo -e "${GREEN}   Installation terminée avec succès !${NC}"
echo "============================================"
echo ""
warn "Pour activer le venv lors des prochaines sessions :"
echo "   source .venv/bin/activate"
echo ""
warn "Pour lancer l'application :"
echo "   ntl-systoolbox"
echo ""