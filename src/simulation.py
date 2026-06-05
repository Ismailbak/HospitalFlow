"""Scenario execution engine for HDJ multi-agent simulation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.agents import (
    CoordinatorAgent,
    EvaluatorAgent,
    PathwayMode,
    ScenarioName,
    TriageAgent,
    build_agents,
    hdj_to_dataframe,
    patients_to_dataframe,
    resources_to_dataframe,
)
from src.data import HospitalData, SimulationConfig


@dataclass
class ScenarioResult:
    scenario: ScenarioName
    summary: dict
    patients: pd.DataFrame
    hdj_units: pd.DataFrame
    resources: pd.DataFrame
    new_hdj_specialty: str | None = None
    new_hdj_slots: int = 0


def _identify_new_hdj_candidate(data: HospitalData) -> str:
    """Pick specialty with highest HDJ conversion potential."""
    ranked = data.specialties.sort_values(
        ["conversion_potential", "fragmented_count"],
        ascending=False,
    )
    return str(ranked.iloc[0]["specialty"])


def run_scenario(
    data: HospitalData,
    scenario: ScenarioName,
    config: SimulationConfig | None = None,
) -> ScenarioResult:
    """Run a single organizational scenario."""
    config = config or data.config
    state = build_agents(data)
    state.scenario = scenario
    state.grouping_rate_applied = config.grouping_rate

    triage = TriageAgent()
    coordinator = CoordinatorAgent()
    evaluator = EvaluatorAgent()

    new_hdj_specialty: str | None = None
    new_hdj_slots = 0

    if scenario == "new_hdj":
        new_hdj_specialty = _identify_new_hdj_candidate(data)
        eligible = data.patients[
            (data.patients["specialty"] == new_hdj_specialty)
            & data.patients["hdj_eligible"]
        ]
        new_hdj_slots = max(12, int(len(eligible) / max(config.simulation_days, 1) * 1.2))

    for patient in state.patients:
        patient.assigned_mode = triage.triage(
            patient,
            scenario=scenario,
            grouping_rate=config.grouping_rate,
            new_hdj_specialty=new_hdj_specialty,
        )

    coordinator.assign(state, config, new_hdj_slots=new_hdj_slots)
    summary = evaluator.summarize(state)

    if scenario == "new_hdj":
        summary["proposed_hdj_specialty"] = new_hdj_specialty
        summary["proposed_hdj_daily_slots"] = new_hdj_slots

    return ScenarioResult(
        scenario=scenario,
        summary=summary,
        patients=patients_to_dataframe(state),
        hdj_units=hdj_to_dataframe(state),
        resources=resources_to_dataframe(state),
        new_hdj_specialty=new_hdj_specialty,
        new_hdj_slots=new_hdj_slots,
    )


def run_all_scenarios(
    data: HospitalData,
    config: SimulationConfig | None = None,
) -> dict[str, ScenarioResult]:
    """Run status quo, optimize existing, and new HDJ scenarios."""
    config = config or data.config
    scenarios: list[ScenarioName] = [
        "status_quo",
        "optimize_existing",
        "new_hdj",
    ]
    return {
        scenario: run_scenario(data, scenario, config)
        for scenario in scenarios
    }
