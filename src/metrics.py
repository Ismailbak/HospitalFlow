"""KPI calculations and scenario recommendation scoring."""

from __future__ import annotations

import pandas as pd

from src.data import SCENARIO_LABELS, HospitalData, SimulationConfig
from src.simulation import ScenarioResult, run_all_scenarios


def _fmt_eur(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def scenario_investment(result: ScenarioResult, config: SimulationConfig) -> float:
    if result.scenario != "new_hdj":
        return 0.0
    slots = result.new_hdj_slots or int(result.summary.get("proposed_hdj_daily_slots", 12))
    return slots * config.hdj_setup_cost_per_slot


def build_comparison_table(
    results: dict[str, ScenarioResult],
    config: SimulationConfig,
) -> pd.DataFrame:
    """Aggregate scenario summaries into a comparison table."""
    baseline_rev = results["status_quo"].summary["total_revenue_eur"]
    rows = []
    for scenario, result in results.items():
        s = result.summary
        investment = scenario_investment(result, config)
        revenue = s["total_revenue_eur"]
        revenue_delta = revenue - baseline_rev
        rows.append(
            {
                "scenario": scenario,
                "scenario_label": SCENARIO_LABELS.get(scenario, scenario),
                "avg_wait_days": round(s["avg_wait_days"], 1),
                "hdj_conversion_rate": round(s["hdj_conversion_rate"] * 100, 1),
                "total_revenue_eur": round(revenue, 0),
                "revenue_delta_eur": round(revenue_delta, 0),
                "investment_eur": round(investment, 0),
                "net_gain_eur": round(revenue_delta - investment, 0),
                "fragmented_pathways": s["fragmented_pathways"],
                "existing_hdj_pathways": s["existing_hdj_pathways"],
                "new_hdj_pathways": s.get("new_hdj_pathways", 0),
                "max_saturation": round(s["max_resource_saturation"] * 100, 1),
            }
        )
    return pd.DataFrame(rows)


def specialty_conversion_opportunity(
    data: HospitalData,
    status_quo_result: ScenarioResult,
) -> pd.DataFrame:
    """Identify specialties with highest HDJ conversion opportunity."""
    patients = status_quo_result.patients
    eligible = patients[patients["hdj_eligible"]]

    by_specialty = (
        eligible.groupby("specialty", as_index=False)
        .agg(
            eligible_patients=("patient_id", "count"),
            avg_wait=("simulated_wait_days", "mean"),
            avg_coordination=("coordination_need", "mean"),
        )
    )

    totals = (
        patients.groupby("specialty", as_index=False)
        .agg(total_patients=("patient_id", "count"))
    )

    merged = totals.merge(by_specialty, on="specialty", how="left").fillna(0)
    merged["conversion_share_pct"] = (
        merged["eligible_patients"] / merged["total_patients"] * 100
    ).round(1)
    merged["avg_wait"] = merged["avg_wait"].round(1)
    merged["avg_coordination"] = merged["avg_coordination"].round(2)
    merged = merged.sort_values("conversion_share_pct", ascending=False)
    return merged


def compute_baseline_delta(
    results: dict[str, ScenarioResult],
) -> pd.DataFrame:
    """Compute deltas vs status quo for each scenario."""
    baseline = results["status_quo"].summary
    rows = []
    for scenario, result in results.items():
        s = result.summary
        rows.append(
            {
                "scenario_label": SCENARIO_LABELS.get(scenario, scenario),
                "wait_delta_days": round(
                    s["avg_wait_days"] - baseline["avg_wait_days"], 1
                ),
                "revenue_delta_eur": round(
                    s["total_revenue_eur"] - baseline["total_revenue_eur"], 0
                ),
                "conversion_delta_pct": round(
                    (s["hdj_conversion_rate"] - baseline["hdj_conversion_rate"]) * 100,
                    1,
                ),
                "saturation_delta_pct": round(
                    (s["max_resource_saturation"] - baseline["max_resource_saturation"])
                    * 100,
                    1,
                ),
            }
        )
    return pd.DataFrame(rows)


def recommend_scenario(
    results: dict[str, ScenarioResult],
    data: HospitalData,
) -> dict:
    """
    Recommend the scenario with the best net gain vs statu quo.
    Prefer creating a new HDJ when it beats optimisation on net value,
    especially if existing capacity is saturated (>= 85 %).
    """
    baseline = results["status_quo"].summary
    config = data.config
    focus = config.focus_specialty
    scores: dict[str, float] = {}
    net_gains: dict[str, float] = {}

    for scenario, result in results.items():
        s = result.summary
        wait_gain = baseline["avg_wait_days"] - s["avg_wait_days"]
        revenue_gain = s["total_revenue_eur"] - baseline["total_revenue_eur"]
        investment = scenario_investment(result, config)
        net_revenue_gain = revenue_gain - investment
        net_gains[scenario] = net_revenue_gain
        conversion_gain = s["hdj_conversion_rate"] - baseline["hdj_conversion_rate"]
        saturation_penalty = max(0, s["max_resource_saturation"] - 0.85) * 50

        score = (
            wait_gain * 2.0
            + net_revenue_gain / 5000
            + conversion_gain * 40
            - saturation_penalty
        )
        scores[scenario] = score

    optimize = results["optimize_existing"]
    optimize_net = net_gains["optimize_existing"]
    new_net = net_gains["new_hdj"]
    optimize_sat = optimize.summary["max_resource_saturation"]
    new_sat = results["new_hdj"].summary["max_resource_saturation"]
    marginal_new_vs_opt = new_net - optimize_net

    if optimize_net <= 0 and new_net <= 0:
        best = "status_quo"
    elif new_net > optimize_net and new_net > 0:
        best = "new_hdj"
    elif optimize_net > 0:
        best = "optimize_existing"
    elif new_net > 0:
        best = "new_hdj"
    else:
        best = "status_quo"

    # Saturated existing capacity: favour a new unit if it is net-positive vs optimise.
    if optimize_sat >= 0.85 and marginal_new_vs_opt > 0:
        best = "new_hdj"

    best_result = results[best]
    specialty_label = focus or best_result.summary.get("proposed_hdj_specialty", "N/A")

    reasons = []
    if best == "status_quo":
        reasons.append(
            "Aucune reconfiguration n'améliore le gain net : les coûts ou la saturation "
            "l'emportent sur les bénéfices attendus."
        )
        reasons.append(
            "Le statu quo évite un investissement structurel "
            "(gain net des autres scénarios ≤ 0 €)."
        )
    elif best == "optimize_existing":
        reasons.append(
            f"Gain net estimé : {_fmt_eur(optimize_net)} € vs statu quo "
            f"(revenus supplémentaires, sans ouvrir de nouvelle unité)."
        )
        reasons.append(
            "L'optimisation des HDJ existants offre le meilleur rapport "
            "bénéfice / investissement dans votre configuration."
        )
        if marginal_new_vs_opt < 0:
            reasons.append(
                f"Créer un nouveau HDJ coûterait {_fmt_eur(abs(marginal_new_vs_opt))} € de gain net "
                f"de plus que l'optimisation — investissement non rentable."
            )
        if optimize_sat >= 0.85:
            reasons.append(
                f"Saturation des HDJ existants : {optimize_sat * 100:.0f} % — "
                "surveiller la capacité même avec cette recommandation."
            )
    else:
        invest = scenario_investment(best_result, config)
        reasons.append(
            f"Gain net estimé : {_fmt_eur(new_net)} € vs statu quo "
            f"(dont −{_fmt_eur(invest)} € d'investissement structurel)."
        )
        if marginal_new_vs_opt > 0:
            reasons.append(
                f"Création d'un nouveau HDJ : +{_fmt_eur(marginal_new_vs_opt)} € de gain net "
                f"vs optimiser l'existant ({_fmt_eur(optimize_net)} €)."
            )
        if optimize_sat >= 0.85:
            reasons.append(
                f"Les HDJ existants sont saturés ({optimize_sat * 100:.0f} %) "
                f"contre {new_sat * 100:.0f} % avec une unité dédiée."
            )
        reasons.append(
            f"La spécialité « {specialty_label} » présente un volume fragmenté suffisant "
            "pour justifier un nouveau HDJ dédié."
        )

    if best_result.summary["max_resource_saturation"] > 0.9:
        reasons.append(
            "Attention : saturation élevée des ressources — prioriser le lissage capacitaire."
        )

    return {
        "recommended_scenario": best,
        "recommended_label": SCENARIO_LABELS.get(best, best),
        "scores": {SCENARIO_LABELS.get(k, k): round(v, 2) for k, v in scores.items()},
        "net_gains_eur": {
            SCENARIO_LABELS.get(k, k): round(v, 0) for k, v in net_gains.items()
        },
        "reasons": reasons,
        "proposed_hdj_specialty": focus or best_result.new_hdj_specialty,
        "proposed_hdj_slots": best_result.new_hdj_slots,
    }


def run_full_analysis(
    data: HospitalData,
) -> dict:
    """Run all scenarios and produce dashboard-ready outputs."""
    results = run_all_scenarios(data, data.config)
    return {
        "results": results,
        "comparison": build_comparison_table(results, data.config),
        "deltas": compute_baseline_delta(results),
        "conversion_opportunity": specialty_conversion_opportunity(
            data, results["status_quo"]
        ),
        "recommendation": recommend_scenario(results, data),
    }
