"""Accès aux données filtrées, partagé par toutes les pages (mis en cache par jeu de filtres)."""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from dashboard.params import to_simulation
from hdj.analytics import recommend
from hdj.config import AGE_MAX, AGE_MIN, DEFAULT_MIN_VISITS, DEFAULT_START, DEFAULT_WINDOW_DAYS
from hdj.data import build_episodes, filter_visits, load_visits
from hdj.simulation import run_simulation


def default_filters() -> dict:
    visits = load_visits()
    return {
        "start": DEFAULT_START,
        "end": visits["date"].max().strftime("%Y-%m-%d"),
        "cohorts": [],
        "age": [AGE_MIN, AGE_MAX],
        "window": DEFAULT_WINDOW_DAYS,
        "min_visits": DEFAULT_MIN_VISITS,
    }


def cohort_options() -> list[str]:
    return sorted(load_visits()["cohort"].unique())


def service_options() -> list[str]:
    return sorted(load_visits()["service"].unique())


def date_bounds() -> tuple[str, str]:
    dates = load_visits()["date"]
    return dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d")


@lru_cache(maxsize=32)
def _dataset(start, end, cohorts, age, window, min_visits) -> tuple[pd.DataFrame, pd.DataFrame]:
    visits = filter_visits(load_visits(), start, end, list(cohorts), age)
    return visits, build_episodes(visits, window, min_visits)


def dataset(filters: dict | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    f = {**default_filters(), **(filters or {})}
    return _dataset(f["start"], f["end"], tuple(sorted(f["cohorts"] or [])), tuple(f["age"]),
                    int(f["window"]), int(f["min_visits"]))


def resolved(filters: dict | None) -> dict:
    return {**default_filters(), **(filters or {})}


@lru_cache(maxsize=16)
def _simulate(filters_json: str, params_json: str) -> tuple[dict, dict]:
    filters, params = json.loads(filters_json), json.loads(params_json)
    f = resolved(filters)
    _, episodes = dataset(filters)
    sim, max_occupancy = to_simulation(params)
    results = run_simulation(episodes, sim, f["start"], f["end"])
    return results, recommend(results, max_occupancy)


def simulate(filters: dict | None, params: dict) -> tuple[dict, dict]:
    """Résultats + recommandation, partagés (en cache) entre les étapes Simulation et Décision."""
    return _simulate(json.dumps(resolved(filters), sort_keys=True), json.dumps(params, sort_keys=True))
