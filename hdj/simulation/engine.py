"""Moteur de simulation : rejoue les épisodes réels dans chaque scénario, en Monte Carlo.

Sources d'aléa (par tirage) : date de demande (± `arrival_jitter_days`), activité de
fond de chaque HDJ (binomiale sur `baseline_occupancy`), absences (`no_show_rate`).
Les trois scénarios d'un même tirage partagent la même graine (nombres aléatoires
communs), ce qui rend leurs écarts directement comparables.
"""
from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd

from hdj.simulation.agents import (
    CoordinatorAgent, EvaluatorAgent, HDJUnitAgent, PatientAgent, TriageAgent,
)
from hdj.simulation.scenarios import (
    NEW_HDJ, SCENARIO_LABELS, SCENARIOS, STATUS_QUO, SimulationParams,
)

_AGGREGATED = (
    "episodes", "eligible", "converted", "converted_new", "conversion_rate", "trips",
    "mean_delay", "replans", "fallbacks", "annual_revenue", "annual_cost",
    "annual_revenue_delta", "annual_net_gain", "trips_avoided",
)


def _band(values) -> dict:
    arr = np.asarray(values, dtype=float)
    return {"mean": float(arr.mean()), "p10": float(np.percentile(arr, 10)), "p90": float(np.percentile(arr, 90))}


def _run_once(scenario: str, episodes: pd.DataFrame, params: SimulationParams, seed: int,
              day0: pd.Timestamp, observed_days: int, horizon: int):
    rng = np.random.default_rng(seed)
    existing = HDJUnitAgent(params.existing, horizon, day0.dayofweek, rng, is_new=False)
    new_units = (
        [HDJUnitAgent(spec, horizon, day0.dayofweek, rng, is_new=True) for spec in params.new_units]
        if scenario == NEW_HDJ else []
    )
    start_days = (episodes["start"] - day0).dt.days.to_numpy()
    if scenario != STATUS_QUO and params.arrival_jitter_days:
        j = params.arrival_jitter_days
        start_days = np.clip(start_days + rng.integers(-j, j + 1, size=len(start_days)), 0, None)

    patients = [
        PatientAgent(int(e.episode_id), e.services, int(d), int(e.n_visits), int(e.n_days),
                     int(e.span_days), bool(e.eligible))
        for e, d in zip(episodes.itertuples(index=False), start_days)
    ]
    triage = TriageAgent(scenario, existing, new_units)
    coordinator = CoordinatorAgent(params, rng)
    for patient in sorted(patients, key=lambda x: x.request_day):
        units = triage.route(patient)
        if units:
            coordinator.schedule(patient, units)

    units = [existing, *new_units]
    kpis = EvaluatorAgent(params, observed_days).summarize(patients, units)
    calendars = {u.name: (u.booked[:observed_days], u.capacity[:observed_days]) for u in units}
    delays = [p.completion_days for p in patients if p.eligible]
    return kpis, calendars, delays


def run_simulation(episodes: pd.DataFrame, params: SimulationParams,
                   start: str | pd.Timestamp, end: str | pd.Timestamp) -> dict:
    """Résultat JSON-sérialisable (stockable tel quel côté dashboard)."""
    day0, last = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    observed_days = max((last - day0).days + 1, 1)
    years = observed_days / 365.25
    horizon = observed_days + params.max_wait_days + params.lead_days + params.arrival_jitter_days + 7
    episodes = episodes[(episodes["start"] >= day0) & (episodes["start"] <= last)]
    weeks = pd.date_range(day0, periods=observed_days, freq="D").to_period("W").start_time

    raw = {s: [] for s in SCENARIOS}
    for run in range(params.runs):
        for scenario in SCENARIOS:
            raw[scenario].append(_run_once(scenario, episodes, params, params.seed + run,
                                           day0, observed_days, horizon))

    baseline = [k for k, _, _ in raw[STATUS_QUO]]
    results = {}
    for scenario in SCENARIOS:
        runs = []
        for (k, _, _), base in zip(raw[scenario], baseline):
            delta = (k["revenue"] - base["revenue"]) / years
            runs.append({
                **k,
                "annual_revenue_delta": delta,
                "annual_net_gain": delta - k["annual_cost"],
                "trips_avoided": base["trips"] - k["trips"],
            })
        unit_names = list(runs[0]["units"])
        units = {}
        for name in unit_names:
            booked = np.mean([cal[name][0] for _, cal, _ in raw[scenario]], axis=0)
            capacity = raw[scenario][0][1][name][1]
            weekly = pd.DataFrame({"week": weeks, "booked": booked, "capacity": capacity}).groupby("week").sum()
            weekly = weekly[weekly["capacity"] > 0]
            first = runs[0]["units"][name]
            units[name] = {
                "is_new": first["is_new"],
                "places": first["places"],
                "occupancy": _band([r["units"][name]["occupancy"] for r in runs]),
                "saturated_share": _band([r["units"][name]["saturated_share"] for r in runs]),
                "weekly": {
                    "week": [w.strftime("%Y-%m-%d") for w in weekly.index],
                    "occupancy": (weekly["booked"] / weekly["capacity"]).round(4).tolist(),
                },
            }
        results[scenario] = {
            "label": SCENARIO_LABELS[scenario],
            "kpis": {key: _band([r[key] for r in runs]) for key in _AGGREGATED},
            "net_gain_runs": [r["annual_net_gain"] for r in runs],
            "units": units,
            "delays": raw[scenario][0][2],
        }

    return {
        "meta": {
            "start": day0.strftime("%Y-%m-%d"),
            "end": last.strftime("%Y-%m-%d"),
            "observed_days": observed_days,
            "years": years,
            "params": asdict(params),
        },
        "scenarios": results,
    }
