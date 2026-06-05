"""Synthetic hospital pathway data and configuration for HDJ simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
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
    """User-adjustable simulation parameters."""

    patient_volume_multiplier: float = 1.0
    room_capacity_multiplier: float = 1.0
    slot_duration_minutes: int = 30
    grouping_rate: float = 0.35
    fragmented_tariff_eur: float = 180.0
    hdj_tariff_eur: float = 420.0
    simulation_days: int = 30
    random_seed: int = 42


@dataclass
class HospitalData:
    """Container for synthetic hospital datasets."""

    patients: pd.DataFrame
    hdj_units: pd.DataFrame
    resources: pd.DataFrame
    specialties: pd.DataFrame
    config: SimulationConfig = field(default_factory=SimulationConfig)


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_synthetic_data(config: SimulationConfig | None = None) -> HospitalData:
    """Generate realistic synthetic ambulatory / HDJ pathway data."""
    config = config or SimulationConfig()
    rng = _rng(config.random_seed)
    n_patients = int(500 * config.patient_volume_multiplier)

    specialty_weights = np.array([0.22, 0.20, 0.18, 0.15, 0.25])
    specialty_weights /= specialty_weights.sum()

    patient_ids = [f"P{i:04d}" for i in range(1, n_patients + 1)]
    specialties = rng.choice(SPECIALTIES, size=n_patients, p=specialty_weights)
    complexity = rng.integers(1, 6, size=n_patients)
    act_counts = rng.integers(1, 6, size=n_patients)
    visit_frequency = rng.integers(1, 13, size=n_patients)
    coordination_need = rng.uniform(0.2, 1.0, size=n_patients).round(2)
    fragmented = rng.random(n_patients) < (0.55 - 0.05 * (complexity - 3))

    base_wait = rng.integers(8, 45, size=n_patients)
    wait_days = (base_wait + act_counts * 3 + (1 - coordination_need) * 10).astype(int)

    patients = pd.DataFrame(
        {
            "patient_id": patient_ids,
            "specialty": specialties,
            "complexity": complexity,
            "act_count": act_counts,
            "visit_frequency_per_year": visit_frequency,
            "coordination_need": coordination_need,
            "is_fragmented": fragmented,
            "baseline_wait_days": wait_days,
            "hdj_eligible": (
                (act_counts >= 2)
                & (coordination_need >= 0.45)
                & fragmented
            ),
        }
    )

    hdj_units = pd.DataFrame(
        {
            "hdj_id": ["HDJ_A", "HDJ_B", "HDJ_C"],
            "name": ["HDJ Oncologie", "HDJ Cardio-Diabète", "HDJ Néphrologie"],
            "specialty_focus": ["oncologie", "cardiologie", "nephrologie"],
            "daily_slots": (
                np.array([18, 22, 14]) * config.room_capacity_multiplier
            ).astype(int),
            "rooms": (
                np.array([4, 5, 3]) * config.room_capacity_multiplier
            ).astype(int),
            "exam_capacity_per_day": (
                np.array([12, 15, 10]) * config.room_capacity_multiplier
            ).astype(int),
        }
    )

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


def load_hospital_data(
    source: str = "synthetic",
    config: SimulationConfig | None = None,
    **kwargs: Any,
) -> HospitalData:
    """
    Load hospital data. Currently supports synthetic data only.
    Future: plug anonymized PMSI / CCAM / consultation extracts here.
    """
    if source == "synthetic":
        return generate_synthetic_data(config)
    raise ValueError(f"Unknown data source: {source}")
