"""Hospital pathway data built entirely from user inputs."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

SPECIALTIES = [
    "oncologie",
    "cardiologie",
    "diabetologie",
    "nephrologie",
    "douleur_chronique",
]

SCENARIO_LABELS = {
    "status_quo": "Statu quo",
    "optimize_existing": "Optimisation HDJ existants",
    "new_hdj": "Création nouveau HDJ",
}


@dataclass
class SimulationConfig:
    """All simulation parameters — every value must come from user input."""

    total_patients: int = 0
    fragmentation_pct: float = 0.0
    hdj_eligible_pct: float = 0.0
    avg_wait_days: int = 0
    avg_act_count: int = 2
    slot_duration_minutes: int = 30
    grouping_rate: float = 0.35
    fragmented_tariff_eur: float = 0.0
    hdj_tariff_eur: float = 0.0
    simulation_days: int = 30
    focus_specialty: str | None = None
    hdj_unit_count: int = 1
    hdj_total_beds: int = 0
    hdj_daily_slots: int = 0
    hdj_exam_capacity_per_day: int = 0
    hdj_setup_cost_per_slot: float = 0.0


@dataclass
class HospitalData:
    """Container for hospital datasets derived from user inputs."""

    patients: pd.DataFrame
    hdj_units: pd.DataFrame
    resources: pd.DataFrame
    specialties: pd.DataFrame
    config: SimulationConfig = field(default_factory=SimulationConfig)


def _split_evenly(total: int, parts: int) -> list[int]:
    """Split an integer total evenly across parts (deterministic)."""
    if parts <= 0:
        return []
    base, remainder = divmod(int(total), parts)
    return [base + (1 if i < remainder else 0) for i in range(parts)]


def build_hdj_units(config: SimulationConfig) -> pd.DataFrame:
    """Build HDJ units by splitting user-entered capacity across their units."""
    n_units = max(1, int(config.hdj_unit_count))
    focus = config.focus_specialty or SPECIALTIES[0]
    daily_slots = _split_evenly(config.hdj_daily_slots, n_units)
    rooms = _split_evenly(config.hdj_total_beds, n_units)
    exams = _split_evenly(config.hdj_exam_capacity_per_day, n_units)

    return pd.DataFrame(
        {
            "hdj_id": [f"HDJ_{i + 1}" for i in range(n_units)],
            "name": [f"HDJ {focus.replace('_', ' ').title()} — unité {i + 1}" for i in range(n_units)],
            "specialty_focus": [focus] * n_units,
            "daily_slots": daily_slots,
            "rooms": rooms,
            "exam_capacity_per_day": exams,
        }
    )


def build_patients(config: SimulationConfig) -> pd.DataFrame:
    """Build patient rows deterministically from user-entered clinical indicators."""
    if not config.focus_specialty:
        raise ValueError("La spécialité à analyser est obligatoire.")
    if config.total_patients <= 0:
        raise ValueError("Le nombre de patients doit être supérieur à 0.")

    n = int(config.total_patients)
    n_frag = min(n, round(n * config.fragmentation_pct / 100))
    n_eligible = min(n_frag, round(n * config.hdj_eligible_pct / 100))
    acts = max(1, int(config.avg_act_count))
    base_wait = max(1, int(config.avg_wait_days))

    rows = []
    for i in range(n):
        is_fragmented = i < n_frag
        hdj_eligible = is_fragmented and i < n_eligible
        rows.append(
            {
                "patient_id": f"P{i + 1:04d}",
                "specialty": config.focus_specialty,
                "complexity": 3,
                "act_count": acts if is_fragmented else max(1, acts - 1),
                "visit_frequency_per_year": 6,
                "coordination_need": 0.75 if hdj_eligible else 0.35,
                "is_fragmented": is_fragmented,
                "baseline_wait_days": base_wait + (10 if is_fragmented else 0),
                "hdj_eligible": hdj_eligible and acts >= 2,
            }
        )

    return pd.DataFrame(rows)


def build_hospital_data(config: SimulationConfig) -> HospitalData:
    """Assemble a full hospital dataset from user configuration only."""
    patients = build_patients(config)
    hdj_units = build_hdj_units(config)

    resources = pd.DataFrame(
        {
            "resource_id": ["SLOTS", "ROOMS", "EXAMS"],
            "label": ["Créneaux journaliers", "Salles", "Examens supports"],
            "unit": ["créneaux/j", "salles", "examens/j"],
            "base_capacity": [
                int(hdj_units["daily_slots"].sum()),
                int(hdj_units["rooms"].sum()),
                int(hdj_units["exam_capacity_per_day"].sum()),
            ],
        }
    )

    specialty_stats = (
        patients.groupby("specialty", as_index=False)
        .agg(
            patient_count=("patient_id", "count"),
            fragmented_count=("is_fragmented", "sum"),
            hdj_eligible_count=("hdj_eligible", "sum"),
            avg_wait_days=("baseline_wait_days", "mean"),
            avg_act_count=("act_count", "mean"),
            avg_coordination=("coordination_need", "mean"),
        )
    )
    specialty_stats["fragmentation_rate"] = (
        specialty_stats["fragmented_count"] / specialty_stats["patient_count"]
    ).round(3)
    specialty_stats["conversion_potential"] = (
        specialty_stats["hdj_eligible_count"] / specialty_stats["patient_count"]
    ).round(3)

    return HospitalData(
        patients=patients,
        hdj_units=hdj_units,
        resources=resources,
        specialties=specialty_stats,
        config=config,
    )


def load_hospital_data(config: SimulationConfig) -> HospitalData:
    """Load hospital data from user configuration."""
    return build_hospital_data(config)
