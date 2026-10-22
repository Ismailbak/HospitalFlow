"""Chemins, référentiels et valeurs par défaut."""
from __future__ import annotations

import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CACHE_DIR = ROOT / "data" / "cache"

# Cohorte = fichier d'extraction (la population de patients ciblée par la requête).
# Clé : mot-clé recherché dans le nom de fichier (sans accents, minuscules).
COHORTS: dict[str, str] = {
    "infectieux": "Infectiologie",
    "endocrino": "Endocrinologie-diabétologie",
    "gastro": "Gastro-entérologie",
    "hematologie": "Hématologie-oncologie",
    "medecine_interne": "Médecine interne",
    "neuro": "Neurologie",
}

# Service = unité où la consultation a réellement eu lieu (LIBELLE UNITE MVT).
# Les unités génériques (MEDECINE CONSULTATIONS EXTERNES) prennent le nom de la cohorte.
GENERIC_UNITS = {"MEDECINE CONSULTATIONS EXTERNES", "CONSULTATION AMBULATOIRE"}
UNIT_TO_SERVICE: dict[str, str] = {
    "INFECTIO CONS": "Infectiologie",
    "DERMATOLOGIE CONSULTATION": "Dermatologie",
    "CONSULTATION GASTROENTEROLOGIE": "Gastro-entérologie",
    "CHIRURGIE VISCERALE CONSULTATION": "Chirurgie viscérale",
    "ONCOLOGIE CONSULTATION": "Hématologie-oncologie",
    "NEPHROLOGIE CONSULTATION": "Néphrologie",
    "CARDIOLOGIE CONSULTATION": "Cardiologie",
    "CONSULTATION NEUROLOGIE": "Neurologie",
    "CONSULT EXT URGENCES": "Urgences",
    "UHCD MEDURG": "Urgences",
    "URGENCE GYNECO OBSTE": "Gynéco-obstétrique",
    "CONSULTATION GYNECO-OBS": "Gynéco-obstétrique",
    "OBSTETRIQUE SUITES DE COUCHE (HISTORIQUE)": "Gynéco-obstétrique",
    "CONSULTATION IRM": "Imagerie",
    "CONSULTATION ECHOGRAPHIE": "Imagerie",
    "SERVICE IMAGERIE": "Imagerie",
    "HDJ CONSULTATION": "HDJ",
}
OTHER_SERVICE = "Autres"

AGE_MIN, AGE_MAX = 0, 100
DEFAULT_START = "2024-01-01"  # les fichiers 2020-2023 ne couvrent que 2 cohortes

# Paramètres d'analyse des parcours
DEFAULT_WINDOW_DAYS = 30   # visites regroupables si elles tombent dans cette fenêtre
DEFAULT_MIN_VISITS = 2     # nb minimal de jours de venue pour qu'un épisode soit convertible


def normalize(text: str) -> str:
    """Minuscules sans accents — pour des correspondances robustes sur les libellés."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()
