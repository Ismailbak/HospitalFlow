"""Agents de la simulation.

- PatientAgent      : un épisode de soins réel (issu des données) et son devenir.
- HDJUnitAgent      : une unité HDJ, son calendrier de places et son activité de fond.
- TriageAgent       : oriente chaque épisode vers un mode de prise en charge.
- CoordinatorAgent  : ordonnance les journées HDJ, gère saturation, absences et replanification.
- EvaluatorAgent    : agrège les indicateurs d'un scénario.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from hdj.simulation.scenarios import STATUS_QUO, HDJUnitSpec, SimulationParams


class Mode(str, Enum):
    FRAGMENTED = "fragmented"
    EXISTING_HDJ = "existing_hdj"
    NEW_HDJ = "new_hdj"


@dataclass
class PatientAgent:
    episode_id: int
    services: tuple[str, ...]
    request_day: int
    n_visits: int
    n_days: int
    span_days: int
    eligible: bool
    mode: Mode = Mode.FRAGMENTED
    unit: str | None = None
    hdj_day: int | None = None
    wait_days: int | None = None
    replans: int = 0
    fallback: bool = False

    @property
    def trips(self) -> int:
        return 1 if self.mode is not Mode.FRAGMENTED else self.n_days

    @property
    def completion_days(self) -> int:
        """Délai pour réaliser tout le bilan : étalement réel, ou attente de la journée HDJ."""
        return self.wait_days if self.mode is not Mode.FRAGMENTED else self.span_days


class HDJUnitAgent:
    def __init__(self, spec: HDJUnitSpec, horizon: int, day0_weekday: int,
                 rng: np.random.Generator, is_new: bool):
        self.spec = spec
        self.is_new = is_new
        weekdays = (day0_weekday + np.arange(horizon)) % 7
        self.open = np.isin(weekdays, spec.open_weekdays)
        self.capacity = np.where(self.open, spec.places_per_day, 0)
        background = rng.binomial(spec.places_per_day, spec.baseline_occupancy, size=horizon)
        self.background = np.where(self.open, background, 0)
        self.booked = self.background.copy()

    @property
    def name(self) -> str:
        return self.spec.name

    def first_free_day(self, start: int, stop: int) -> int | None:
        start, stop = max(start, 0), min(stop, len(self.capacity))
        free = np.flatnonzero(self.open[start:stop] & (self.booked[start:stop] < self.capacity[start:stop]))
        return int(start + free[0]) if free.size else None

    def book(self, day: int) -> None:
        self.booked[day] += 1

    def occupancy(self, days: int) -> float:
        cap = self.capacity[:days].sum()
        return float(self.booked[:days].sum() / cap) if cap else 0.0

    def saturated_share(self, days: int) -> float:
        open_days = self.open[:days]
        if not open_days.any():
            return 0.0
        return float((self.booked[:days][open_days] >= self.capacity[:days][open_days]).mean())


class TriageAgent:
    """Triage de parcours (pas de diagnostic médical)."""

    def __init__(self, scenario: str, existing: HDJUnitAgent, new_units: list[HDJUnitAgent]):
        self.scenario = scenario
        self.existing = existing
        self.new_units = new_units

    def route(self, patient: PatientAgent) -> list[HDJUnitAgent]:
        """Unités à essayer, par ordre de préférence. Liste vide = parcours fragmenté."""
        if self.scenario == STATUS_QUO or not patient.eligible:
            return []
        candidates = [u for u in self.new_units if u.spec.accepts(patient.services)]
        if self.existing.spec.accepts(patient.services):
            candidates.append(self.existing)
        return candidates


class CoordinatorAgent:
    """Ordonnanceur : première journée libre, replanification en cas de saturation ou d'absence."""

    def __init__(self, params: SimulationParams, rng: np.random.Generator):
        self.lead = params.lead_days
        self.max_wait = params.max_wait_days
        self.no_show = params.no_show_rate
        self.rng = rng

    def schedule(self, patient: PatientAgent, units: list[HDJUnitAgent]) -> None:
        earliest = patient.request_day + self.lead
        deadline = patient.request_day + self.max_wait + 1
        for rank, unit in enumerate(units):
            day = unit.first_free_day(earliest, deadline)
            if day is None:
                continue
            patient.replans += rank  # unités préférées saturées → réorientation
            while True:
                unit.book(day)
                if self.rng.random() >= self.no_show:
                    patient.mode = Mode.NEW_HDJ if unit.is_new else Mode.EXISTING_HDJ
                    patient.unit, patient.hdj_day = unit.name, day
                    patient.wait_days = day - patient.request_day
                    return
                patient.replans += 1
                day = unit.first_free_day(day + 1, deadline)
                if day is None:
                    break
        patient.fallback = bool(units)


class EvaluatorAgent:
    def __init__(self, params: SimulationParams, observed_days: int):
        self.params = params
        self.days = observed_days
        self.years = observed_days / 365.25

    def summarize(self, patients: list[PatientAgent], units: list[HDJUnitAgent]) -> dict:
        p = self.params
        eligible = [x for x in patients if x.eligible]
        converted = [x for x in patients if x.mode is not Mode.FRAGMENTED]
        revenue = sum(
            p.hdj_tariff if x.mode is not Mode.FRAGMENTED else x.n_visits * p.consult_tariff
            for x in patients
        )
        cost = sum(u.spec.places_per_day * u.spec.annual_cost_per_place for u in units if u.is_new) * self.years
        delays = [x.completion_days for x in eligible]
        return {
            "episodes": len(patients),
            "eligible": len(eligible),
            "converted": len(converted),
            "converted_new": sum(x.mode is Mode.NEW_HDJ for x in patients),
            "conversion_rate": len(converted) / len(eligible) if eligible else 0.0,
            "trips": sum(x.trips for x in patients),
            "mean_delay": float(np.mean(delays)) if delays else 0.0,
            "replans": sum(x.replans for x in patients),
            "fallbacks": sum(x.fallback for x in patients),
            "revenue": revenue,
            "cost": cost,
            "annual_revenue": revenue / self.years,
            "annual_cost": cost / self.years,
            "units": {
                u.name: {
                    "occupancy": u.occupancy(self.days),
                    "saturated_share": u.saturated_share(self.days),
                    "is_new": u.is_new,
                    "places": u.spec.places_per_day,
                }
                for u in units
            },
        }
