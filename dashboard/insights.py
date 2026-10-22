"""Phrases « À retenir » : les chiffres clés de chaque étape, en langage courant.

Chaque fonction renvoie une liste de (valeur mise en avant, phrase).
"""
from __future__ import annotations

import pandas as pd

from dashboard import format as fmt
from hdj.analytics import activity_summary, conversion_potential
from hdj.data import visit_gaps
from hdj.simulation import NEW_HDJ, OPTIMIZE_EXISTING, SCENARIO_LABELS, STATUS_QUO

WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _one_in(share: float) -> str:
    return f"1 patient sur {round(1 / share)}" if share > 0 else "Aucun patient"


def activity(visits: pd.DataFrame, episodes: pd.DataFrame) -> list[tuple[str, str]]:
    if visits.empty:
        return []
    s = activity_summary(visits, episodes, 0)
    services = visits["service"].value_counts(normalize=True)
    morning = (visits["hour"] < 12).mean()
    busiest = WEEKDAYS_FR[visits["weekday"].value_counts().idxmax()]
    return [
        (fmt.percent(services.iloc[0]),
         f"des consultations ont lieu en {services.index[0].lower()}, premier service de la période."),
        (fmt.percent(morning),
         f"des patients arrivent le matin ; le {busiest} est le jour le plus chargé."),
        (_one_in(s["multi_service_share"]),
         "est suivi par plusieurs services : c'est là que la coordination se joue."),
    ]


def pathways(visits: pd.DataFrame, episodes: pd.DataFrame, window: int, min_visits: int) -> list[tuple[str, str]]:
    eligible = episodes[episodes["eligible"]]
    if eligible.empty:
        return [("0", f"épisode ne compte {min_visits} venues ou plus en {window} jours avec ces filtres.")]
    s = activity_summary(visits, episodes, window)
    potential = conversion_potential(episodes)
    top = potential.iloc[0]
    gaps = visit_gaps(visits)
    return [
        (fmt.integer(s["eligible_patients"]),
         f"patients ({fmt.percent(s['eligible_share'], 1)}) sont venus au moins {min_visits} fois en {window} jours."),
        (f"{eligible['span_days'].median():.0f} jours",
         "séparent en médiane leur première et leur dernière venue. Une journée HDJ les réunirait en une seule."),
        (fmt.percent(top["episodes"] / len(eligible)),
         f"des épisodes regroupables passent par {top['service'].lower()}."
         + (f" Délai médian entre deux venues, tous patients : {gaps.median():.0f} jours." if len(gaps) else "")),
    ]


def simulation(results: dict, scenario: str) -> list[tuple[str, str]]:
    k = results["scenarios"][scenario]["kpis"]
    base = results["scenarios"][STATUS_QUO]["kpis"]
    eligible = k["eligible"]["mean"]
    existing = results["scenarios"][scenario]["units"]["HDJ existant"]["occupancy"]["mean"]
    before = results["scenarios"][STATUS_QUO]["units"]["HDJ existant"]["occupancy"]["mean"]
    return [
        (f"{fmt.integer(k['converted']['mean'])} / {fmt.integer(eligible)}",
         "épisodes regroupables ont trouvé une journée HDJ dans le délai d'attente maximal."),
        (f"{fmt.decimal(base['mean_delay']['mean'])} → {fmt.decimal(k['mean_delay']['mean'])} j",
         "pour réaliser l'ensemble du bilan, contre l'étalement actuel des consultations."),
        (f"{fmt.percent(before)} → {fmt.percent(existing)}",
         "d'occupation de l'HDJ existant une fois ces patients accueillis."),
    ]


def decision(results: dict, reco: dict) -> list[tuple[str, str]]:
    k = results["scenarios"][reco["choice"]]["kpis"]
    if reco["choice"] == STATUS_QUO:
        best = max((OPTIMIZE_EXISTING, NEW_HDJ), key=lambda s: results["scenarios"][s]["kpis"]["annual_net_gain"]["mean"])
        return [("Statu quo", f"aucune réorganisation n'est rentable et soutenable ; la meilleure, "
                              f"« {SCENARIO_LABELS[best]} », reste en dessous des critères.")]
    return [
        (fmt.euros(k["annual_net_gain"]["mean"]), "de gain net estimé par an, investissement déduit."),
        (fmt.integer(k["trips_avoided"]["mean"]), "venues évitées aux patients sur la période étudiée."),
        (fmt.percent(reco["robustness"]), "des simulations aléatoires aboutissent au même choix."),
    ]
