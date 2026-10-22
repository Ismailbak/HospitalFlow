"""Recommandation : choix du scénario à partir des résultats de simulation.

Règle unique et explicite :
1. un scénario est **recevable** si aucune de ses unités HDJ ne dépasse le seuil
   d'occupation moyen (`max_occupancy`) et s'il n'allonge pas le délai de réalisation
   du bilan par rapport au statu quo ;
2. parmi les scénarios recevables, on retient le **gain net annuel moyen** le plus
   élevé (le statu quo vaut 0) ;
3. la **robustesse** est la part des tirages Monte Carlo où ce choix reste le meilleur.
"""
from __future__ import annotations

import numpy as np

from hdj.simulation.scenarios import SCENARIO_LABELS, SCENARIOS, STATUS_QUO


def _eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


def _days(x: float) -> str:
    return f"{x:.1f} j".replace(".", ",")


def recommend(results: dict, max_occupancy: float) -> dict:
    scenarios = results["scenarios"]
    sq_delay = scenarios[STATUS_QUO]["kpis"]["mean_delay"]["mean"]

    checks = {}
    for key in SCENARIOS:
        s = scenarios[key]
        worst_unit, worst_occ = max(
            ((name, u["occupancy"]["mean"]) for name, u in s["units"].items()), key=lambda t: t[1]
        )
        checks[key] = {
            "net_gain": s["kpis"]["annual_net_gain"]["mean"],
            "occupancy_ok": key == STATUS_QUO or worst_occ <= max_occupancy,
            "delay_ok": s["kpis"]["mean_delay"]["mean"] <= sq_delay + 1e-9,
            "worst_unit": worst_unit,
            "worst_occupancy": worst_occ,
        }
        checks[key]["admissible"] = checks[key]["occupancy_ok"] and checks[key]["delay_ok"]

    admissible = [k for k in SCENARIOS if checks[k]["admissible"]]
    choice = max(admissible, key=lambda k: (checks[k]["net_gain"], k == STATUS_QUO))
    if checks[choice]["net_gain"] <= 0:
        choice = STATUS_QUO

    runs = np.array([scenarios[k]["net_gain_runs"] for k in admissible])
    best_per_run = np.array(admissible)[runs.argmax(axis=0)]
    robustness = float((best_per_run == choice).mean()) if choice in admissible else 1.0

    reasons = []
    c = checks[choice]
    if choice == STATUS_QUO:
        reasons.append("Aucun scénario de regroupement ne dégage de gain net positif sous les contraintes fixées.")
    else:
        k = scenarios[choice]["kpis"]
        lo, hi = _eur(k["annual_net_gain"]["p10"]), _eur(k["annual_net_gain"]["p90"])
        spread = f" (fourchette {lo} – {hi})" if lo != hi else ""
        reasons.append(f"Gain net estimé de {_eur(c['net_gain'])} par an{spread}.")
        reasons.append(f"{k['converted']['mean']:.0f} épisodes regroupés en HDJ, "
                       f"{k['trips_avoided']['mean']:.0f} venues évitées sur la période.")
        reasons.append(f"Délai de réalisation du bilan : {_days(k['mean_delay']['mean'])} "
                       f"contre {_days(sq_delay)} au statu quo.")
        reasons.append(f"Occupation maximale : {c['worst_occupancy']:.0%} ({c['worst_unit']}).")
    for key in SCENARIOS:
        if key in (choice, STATUS_QUO):
            continue
        ck = checks[key]
        if not ck["occupancy_ok"]:
            reasons.append(f"« {SCENARIO_LABELS[key]} » écarté : {ck['worst_unit']} saturé "
                           f"({ck['worst_occupancy']:.0%} > {max_occupancy:.0%}).")
        elif not ck["delay_ok"]:
            reasons.append(f"« {SCENARIO_LABELS[key]} » écarté : allonge le délai de réalisation du bilan.")
        elif ck["net_gain"] < c["net_gain"]:
            reasons.append(f"« {SCENARIO_LABELS[key]} » moins favorable : {_eur(ck['net_gain'])} par an.")

    return {
        "choice": choice,
        "label": SCENARIO_LABELS[choice],
        "robustness": robustness,
        "checks": checks,
        "reasons": reasons,
        "max_occupancy": max_occupancy,
    }
