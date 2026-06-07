"""Multi-agent model for HDJ pathway simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import pandas as pd

from src.data import HospitalData, SimulationConfig

ScenarioName = Literal["status_quo", "optimize_existing", "new_hdj"]


class PathwayMode(str, Enum):
    FRAGMENTED = "fragmented"
    EXISTING_HDJ = "existing_hdj"
    NEW_HDJ = "new_hdj"


@dataclass
class PatientAgent:
    patient_id: str
    specialty: str
    complexity: int
    act_count: int
    coordination_need: float
    is_fragmented: bool
    hdj_eligible: bool
    baseline_wait_days: int
    assigned_mode: PathwayMode = PathwayMode.FRAGMENTED
    simulated_wait_days: int = 0
    revenue_eur: float = 0.0


@dataclass
class HDJAgent:
    hdj_id: str
    name: str
    specialty_focus: str
    daily_slots: int
    rooms: int
    exam_capacity_per_day: int
    assigned_patients: int = 0
    utilization: float = 0.0


@dataclass
class ResourceAgent:
    resource_id: str
    label: str
    capacity: int
    demand: int = 0
    saturation: float = 0.0


@dataclass
class SimulationState:
    patients: list[PatientAgent] = field(default_factory=list)
    hdj_units: list[HDJAgent] = field(default_factory=list)
    resources: list[ResourceAgent] = field(default_factory=list)
    scenario: ScenarioName = "status_quo"
    grouping_rate_applied: float = 0.0


def build_agents(data: HospitalData) -> SimulationState:
    """Instantiate agents from hospital data."""
    patients = [
        PatientAgent(
            patient_id=row.patient_id,
            specialty=row.specialty,
            complexity=int(row.complexity),
            act_count=int(row.act_count),
            coordination_need=float(row.coordination_need),
            is_fragmented=bool(row.is_fragmented),
            hdj_eligible=bool(row.hdj_eligible),
            baseline_wait_days=int(row.baseline_wait_days),
        )
        for row in data.patients.itertuples(index=False)
    ]

    hdj_units = [
        HDJAgent(
            hdj_id=row.hdj_id,
            name=row.name,
            specialty_focus=row.specialty_focus,
            daily_slots=int(row.daily_slots),
            rooms=int(row.rooms),
            exam_capacity_per_day=int(row.exam_capacity_per_day),
        )
        for row in data.hdj_units.itertuples(index=False)
    ]

    resources = [
        ResourceAgent(
            resource_id=row.resource_id,
            label=row.label,
            capacity=int(row.base_capacity),
        )
        for row in data.resources.itertuples(index=False)
    ]

    return SimulationState(patients=patients, hdj_units=hdj_units, resources=resources)


class TriageAgent:
    """Organizational triage: routes patients to pathway modes."""

    def triage(
        self,
        patient: PatientAgent,
        scenario: ScenarioName,
        grouping_rate: float,
        new_hdj_specialty: str | None,
    ) -> PathwayMode:
        if not patient.hdj_eligible:
            return PathwayMode.FRAGMENTED

        if scenario == "status_quo":
            return PathwayMode.FRAGMENTED

        if scenario == "optimize_existing":
            if patient.coordination_need >= grouping_rate:
                return PathwayMode.EXISTING_HDJ
            return PathwayMode.FRAGMENTED

        # new_hdj scenario
        if new_hdj_specialty and patient.specialty == new_hdj_specialty:
            return PathwayMode.NEW_HDJ
        if patient.coordination_need >= grouping_rate * 0.85:
            return PathwayMode.EXISTING_HDJ
        return PathwayMode.FRAGMENTED


class CoordinatorAgent:
    """Schedules patients onto HDJ capacity and computes waits."""

    def assign(
        self,
        state: SimulationState,
        config: SimulationConfig,
        new_hdj_slots: int = 0,
    ) -> None:
        hdj_by_specialty = {h.specialty_focus: h for h in state.hdj_units}
        specialty_demand: dict[str, int] = {}
        new_hdj_demand = 0

        for patient in state.patients:
            if patient.assigned_mode == PathwayMode.EXISTING_HDJ:
                specialty_demand[patient.specialty] = (
                    specialty_demand.get(patient.specialty, 0) + 1
                )
            elif patient.assigned_mode == PathwayMode.NEW_HDJ:
                new_hdj_demand += 1

        days = config.simulation_days
        slot_minutes = config.slot_duration_minutes
        slots_per_day = sum(h.daily_slots for h in state.hdj_units) + new_hdj_slots

        total_hdj_patients = sum(
            1 for p in state.patients if p.assigned_mode != PathwayMode.FRAGMENTED
        )
        load_factor = total_hdj_patients / max(slots_per_day * days, 1)

        for patient in state.patients:
            if patient.assigned_mode == PathwayMode.FRAGMENTED:
                penalty = patient.act_count * 4 + (6 - patient.complexity)
                patient.simulated_wait_days = int(
                    patient.baseline_wait_days + penalty
                )
                patient.revenue_eur = (
                    config.fragmented_tariff_eur * patient.act_count * 0.6
                )
            elif patient.assigned_mode == PathwayMode.EXISTING_HDJ:
                hdj = hdj_by_specialty.get(patient.specialty)
                unit_load = 0.5
                if hdj:
                    demand = specialty_demand.get(patient.specialty, 0)
                    capacity = max(hdj.daily_slots * days, 1)
                    unit_load = min(demand / capacity, 1.5)
                    hdj.assigned_patients += 1
                    hdj.utilization = unit_load

                reduction = 0.45 + 0.15 * patient.coordination_need
                patient.simulated_wait_days = max(
                    3,
                    int(patient.baseline_wait_days * (1 - reduction) + unit_load * 8),
                )
                patient.revenue_eur = config.hdj_tariff_eur * (1 + 0.1 * patient.act_count)
            else:  # NEW_HDJ
                new_load = new_hdj_demand / max(new_hdj_slots * days, 1)
                reduction = 0.55 + 0.2 * patient.coordination_need
                patient.simulated_wait_days = max(
                    2,
                    int(patient.baseline_wait_days * (1 - reduction) + new_load * 5),
                )
                patient.revenue_eur = config.hdj_tariff_eur * (1 + 0.15 * patient.act_count)

        for resource in state.resources:
            if resource.resource_id == "SLOTS":
                resource.demand = total_hdj_patients
                resource.capacity = slots_per_day * days
            elif resource.resource_id == "ROOMS":
                resource.demand = int(total_hdj_patients * 0.35)
                resource.capacity = sum(h.rooms for h in state.hdj_units) * days
            elif resource.resource_id == "EXAMS":
                resource.demand = int(total_hdj_patients * 0.5)
                resource.capacity = (
                    sum(h.exam_capacity_per_day for h in state.hdj_units) * days
                )
            resource.saturation = min(resource.demand / max(resource.capacity, 1), 1.5)


class EvaluatorAgent:
    """Compares scenario outcomes."""

    def summarize(self, state: SimulationState) -> dict:
        patients = state.patients
        n = len(patients)
        fragmented = sum(1 for p in patients if p.assigned_mode == PathwayMode.FRAGMENTED)
        existing = sum(1 for p in patients if p.assigned_mode == PathwayMode.EXISTING_HDJ)
        new_hdj = sum(1 for p in patients if p.assigned_mode == PathwayMode.NEW_HDJ)

        return {
            "total_patients": n,
            "fragmented_pathways": fragmented,
            "existing_hdj_pathways": existing,
            "new_hdj_pathways": new_hdj,
            "avg_wait_days": sum(p.simulated_wait_days for p in patients) / max(n, 1),
            "total_revenue_eur": sum(p.revenue_eur for p in patients),
            "hdj_conversion_rate": (existing + new_hdj) / max(n, 1),
            "max_resource_saturation": max(r.saturation for r in state.resources),
        }


def patients_to_dataframe(state: SimulationState) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "patient_id": p.patient_id,
                "specialty": p.specialty,
                "pathway_mode": p.assigned_mode.value,
                "simulated_wait_days": p.simulated_wait_days,
                "revenue_eur": p.revenue_eur,
                "is_fragmented": p.is_fragmented,
                "hdj_eligible": p.hdj_eligible,
                "coordination_need": p.coordination_need,
            }
            for p in state.patients
        ]
    )


def hdj_to_dataframe(state: SimulationState) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "hdj_id": h.hdj_id,
                "name": h.name,
                "specialty_focus": h.specialty_focus,
                "assigned_patients": h.assigned_patients,
                "utilization": round(h.utilization, 3),
                "daily_slots": h.daily_slots,
            }
            for h in state.hdj_units
        ]
    )


def resources_to_dataframe(state: SimulationState) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "resource_id": r.resource_id,
                "label": r.label,
                "capacity": r.capacity,
                "demand": r.demand,
                "saturation": round(r.saturation, 3),
            }
            for r in state.resources
        ]
    )
