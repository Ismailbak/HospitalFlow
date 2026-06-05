"""KPI calculations and scenario recommendation scoring."""

from __future__ import annotations

import pandas as pd

from src.data import SCENARIO_LABELS, HospitalData
from src.simulation import ScenarioResult, run_all_scenarios


def build_comparison_table(results: dict[str, ScenarioResult]) -> pd.DataFrame:
    """Aggregate scenario summaries into a comparison table."""
    rows = []
    for scenario, result in results.items():
        s = result.summary
        rows.append(
            {
                "scenario": scenario,
                "scenario_label": SCENARIO_LABELS.get(scenario, scenario),
                "avg_wait_days": round(s["avg_wait_days"], 1),
                "hdj_conversion_rate": round(s["hdj_conversion_rate"] * 100, 1),
                "total_revenue_eur": round(s["total_revenue_eur"], 0),
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


def recommend_scenario(results: dict[str, ScenarioResult]) -> dict:
    """
    Score scenarios and return a governance-friendly recommendation.
    Weights: wait reduction, revenue, conversion, saturation penalty.
    """
    baseline = results["status_quo"].summary
    scores: dict[str, float] = {}

    for scenario, result in results.items():
        s = result.summary
        wait_gain = baseline["avg_wait_days"] - s["avg_wait_days"]
        revenue_gain = s["total_revenue_eur"] - baseline["total_revenue_eur"]
        conversion_gain = s["hdj_conversion_rate"] - baseline["hdj_conversion_rate"]
        saturation_penalty = max(0, s["max_resource_saturation"] - 0.85) * 50

        score = (
            wait_gain * 2.0
            + revenue_gain / 5000
            + conversion_gain * 40
            - saturation_penalty
        )
        scores[scenario] = score

    best = max(scores, key=scores.get)
    best_result = results[best]

    reasons = []
    if best == "status_quo":
        reasons.append(
            "Les gains organisationnels ne compensent pas le risque de saturation "
            "ou le coût de reconfiguration."
        )
    elif best == "optimize_existing":
        reasons.append(
            "L'optimisation des HDJ existants réduit les délais et améliore la "
            "valorisation sans investissement structurel majeur."
        )
    else:
        specialty = best_result.summary.get("proposed_hdj_specialty", "N/A")
        reasons.append(
            f"La spécialité '{specialty}' présente un volume fragmenté suffisant "
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
        "reasons": reasons,
        "proposed_hdj_specialty": best_result.new_hdj_specialty,
        "proposed_hdj_slots": best_result.new_hdj_slots,
    }


def run_full_analysis(
    data: HospitalData,
) -> dict:
    """Run all scenarios and produce dashboard-ready outputs."""
    results = run_all_scenarios(data, data.config)
    return {
        "results": results,
        "comparison": build_comparison_table(results),
        "deltas": compute_baseline_delta(results),
        "conversion_opportunity": specialty_conversion_opportunity(
            data, results["status_quo"]
        ),
        "recommendation": recommend_scenario(results),
    }
