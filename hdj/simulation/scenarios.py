"""Définition des scénarios et de leurs paramètres.

Aucune valeur métier par défaut : tarifs, capacités, coûts et paramètres d'organisation
doivent être fournis (par l'utilisateur, à partir des données de l'établissement).
"""
from __future__ import annotations

from dataclasses import dataclass

STATUS_QUO = "status_quo"
OPTIMIZE_EXISTING = "optimize_existing"
NEW_HDJ = "new_hdj"
SCENARIOS = (STATUS_QUO, OPTIMIZE_EXISTING, NEW_HDJ)

SCENARIO_LABELS = {
    STATUS_QUO: "Statu quo",
    OPTIMIZE_EXISTING: "Optimisation de l'existant",
    NEW_HDJ: "Création de HDJ",
}
SCENARIO_DESCRIPTIONS = {
    STATUS_QUO: "Parcours actuels observés : une venue par consultation.",
    OPTIMIZE_EXISTING: "Les épisodes convertibles sont regroupés dans la capacité libre de l'HDJ existant.",
    NEW_HDJ: "Un ou plusieurs HDJ dédiés absorbent les épisodes de leurs spécialités, l'existant prend le reste.",
}

WEEKDAYS = (0, 1, 2, 3, 4)


@dataclass(frozen=True)
class HDJUnitSpec:
    name: str
    places_per_day: int
    services: tuple[str, ...] | None = None   # None = toutes spécialités acceptées
    baseline_occupancy: float = 0.0           # part des places déjà prise par l'activité actuelle
    annual_cost_per_place: float = 0.0        # coût de fonctionnement (nouvelles places uniquement)
    open_weekdays: tuple[int, ...] = WEEKDAYS

    def accepts(self, services: tuple[str, ...]) -> bool:
        return self.services is None or any(s in self.services for s in services)


@dataclass(frozen=True)
class SimulationParams:
    existing: HDJUnitSpec
    consult_tariff: float             # € par consultation externe
    hdj_tariff: float                 # € par journée HDJ
    lead_days: int                    # délai minimal pour organiser une journée HDJ
    max_wait_days: int                # au-delà, le coordinateur renonce : parcours fragmenté
    no_show_rate: float               # absence non prévenue → créneau perdu, replanification
    arrival_jitter_days: int          # incertitude sur la date de demande (± jours)
    new_units: tuple[HDJUnitSpec, ...] = ()
    runs: int = 30                    # tirages Monte Carlo (réglage technique)
    seed: int = 42
