"""Paramètres de simulation saisis par l'utilisateur : définition, validation, conversion.

Aucune valeur métier par défaut. Les saisies sont conservées dans le navigateur (store `sim-params`).
"""
from __future__ import annotations

from dataclasses import dataclass

from hdj.simulation import HDJUnitSpec, SimulationParams


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    help: str
    unit: str | None = None
    min: float = 0
    max: float | None = None
    step: float = 1
    source: str | None = None


GROUPS: list[tuple[str, str, list[Field]]] = [
    ("HDJ existant", "La capacité dans laquelle les épisodes peuvent être regroupés aujourd'hui.", [
        Field("ex_places", "Places par jour", "Patients que l'HDJ peut accueillir par jour ouvré.",
              min=1, source="Encadrement de l'HDJ"),
        Field("ex_occ", "Occupation actuelle", "Part moyenne des places déjà prise par l'activité actuelle.",
              unit="%", max=100, source="Encadrement de l'HDJ"),
    ]),
    ("Valorisation", "Ce que rapporte une venue dans chaque organisation.", [
        Field("consult", "Tarif d'une consultation", "Recette moyenne d'une consultation externe.",
              unit="€", step=0.01, source="DIM"),
        Field("hdj", "Tarif d'une journée HDJ", "Recette moyenne d'une journée d'hospitalisation de jour.",
              unit="€", step=0.01, source="DIM"),
    ]),
    ("Organisation", "Les règles que suit l'agent coordinateur pour planifier les journées.", [
        Field("lead", "Délai d'organisation", "Temps minimal entre la demande et la journée HDJ.", unit="jours"),
        Field("maxwait", "Attente maximale", "Au-delà, le patient reste en parcours classique.", unit="jours", min=1),
        Field("noshow", "Taux d'absence", "Patients qui ne se présentent pas : la place est perdue, "
              "la journée est replanifiée.", unit="%", max=100, step=0.5),
        Field("jitter", "Incertitude sur la demande", "Imprécision (±) sur la date à laquelle la journée "
              "aurait été demandée.", unit="± jours"),
    ]),
    ("Décision", "Le critère qui écarte un scénario.", [
        Field("maxocc", "Seuil d'occupation acceptable", "Au-delà, une unité est jugée saturée et le "
              "scénario n'est pas recommandé.", unit="%", min=1, max=100),
    ]),
]

REQUIRED = [f for _, _, fields in GROUPS for f in fields]
NEW_UNIT_COST = Field("place_cost", "Coût annuel par place créée",
                      "Personnel, locaux et équipement, rapportés à une place et à une année.",
                      unit="€", step=100, source="Contrôle de gestion")
RUN_OPTIONS = [10, 30, 50, 100]
DEFAULT_RUNS = 30  # réglage technique, pas une donnée de l'établissement

# Toutes les clés saisissables, pour remplir / vider le formulaire
LIST_KEYS = ("ex_services", "a_services", "b_services")
ALL_KEYS = (*(f.key for f in REQUIRED), *LIST_KEYS, "a_places", "b_places", "place_cost", "runs")

# Jeux de démonstration — valeurs FICTIVES, choisies pour que chaque jeu aboutisse à une organisation
# différente. Ils servent à présenter l'outil, jamais à décider.
_DEMO_BASE = {"ex_places": 10, "ex_occ": 70, "consult": 30, "hdj": 600, "lead": 3, "maxwait": 30,
              "noshow": 8, "jitter": 5, "maxocc": 90, "runs": DEFAULT_RUNS}
PRESETS: dict[str, dict] = {
    "status_quo": {
        "label": "Statu quo",
        "story": "La journée HDJ rapporte moins que les consultations qu'elle remplace : rien n'est rentable.",
        "values": {**_DEMO_BASE, "hdj": 50},
    },
    "optimize_existing": {
        "label": "Optimisation de l'existant",
        "story": "L'HDJ existant a de la place libre : il absorbe les épisodes sans saturer.",
        "values": _DEMO_BASE,
    },
    "new_hdj": {
        "label": "Création de HDJ",
        "story": "L'HDJ existant est trop petit et sature : un HDJ d'infectiologie dédié prend le relais.",
        "values": {**_DEMO_BASE, "ex_places": 2, "a_services": ["Infectiologie"], "a_places": 4, "place_cost": 20000},
    },
}


def preset_values(name: str | None) -> dict:
    """Valeurs complètes du formulaire pour un jeu de démonstration (None = formulaire vide)."""
    values = PRESETS[name]["values"] if name else {"runs": DEFAULT_RUNS}
    return {k: values.get(k, [] if k in LIST_KEYS else None) for k in ALL_KEYS}


def matching_preset(params: dict | None) -> str | None:
    """Nom du jeu de démonstration si les paramètres saisis lui sont strictement identiques."""
    p = params or {}
    for name in PRESETS:
        expected = preset_values(name)
        if all((p.get(k) or ([] if k in LIST_KEYS else None)) == v for k, v in expected.items()):
            return name
    return None


def _unit_defined(p: dict, name: str) -> bool:
    return bool(p.get(f"{name}_services")) and bool(p.get(f"{name}_places"))


def missing(params: dict | None) -> list[str]:
    p = params or {}
    out = [f.label for f in REQUIRED if p.get(f.key) is None]
    for name in ("a", "b"):
        if p.get(f"{name}_services") and not p.get(f"{name}_places"):
            out.append(f"Places de l'HDJ {name.upper()}")
        if p.get(f"{name}_places") and not p.get(f"{name}_services"):
            out.append(f"Spécialités de l'HDJ {name.upper()}")
    if any(_unit_defined(p, n) for n in ("a", "b")) and p.get("place_cost") is None:
        out.append(NEW_UNIT_COST.label)
    return out


def has_new_units(params: dict) -> bool:
    return any(_unit_defined(params, n) for n in ("a", "b"))


def to_simulation(params: dict) -> tuple[SimulationParams, float]:
    """(paramètres du moteur, seuil d'occupation) — à n'appeler que si `missing()` est vide."""
    p = params
    new_units = tuple(
        HDJUnitSpec(f"HDJ {n.upper()}", int(p[f"{n}_places"]), tuple(p[f"{n}_services"]), 0.0, float(p["place_cost"]))
        for n in ("a", "b") if _unit_defined(p, n)
    )
    sim = SimulationParams(
        existing=HDJUnitSpec("HDJ existant", int(p["ex_places"]), tuple(p.get("ex_services") or ()) or None,
                             p["ex_occ"] / 100),
        new_units=new_units,
        consult_tariff=float(p["consult"]), hdj_tariff=float(p["hdj"]),
        lead_days=int(p["lead"]), max_wait_days=int(p["maxwait"]), no_show_rate=p["noshow"] / 100,
        arrival_jitter_days=int(p["jitter"]), runs=int(p.get("runs") or DEFAULT_RUNS),
    )
    return sim, p["maxocc"] / 100
