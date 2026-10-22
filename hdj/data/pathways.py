"""Reconstruction des parcours : épisodes de soins, délais entre visites, transitions.

Un **épisode** regroupe les visites d'un même patient tombant dans une fenêtre de
`window_days` jours à partir de la première visite de l'épisode (toutes cohortes
confondues). Un épisode est **convertible en HDJ** s'il comporte au moins
`min_visits` jours de venue distincts : ces venues auraient pu être réunies en une
seule journée d'hospitalisation de jour.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _episode_ids(patients: np.ndarray, dates: np.ndarray, window_days: int) -> np.ndarray:
    window = np.timedelta64(window_days, "D")
    ids = np.empty(len(patients), dtype=np.int64)
    counter, prev_patient, anchor = -1, None, None
    for i, (pid, day) in enumerate(zip(patients, dates)):
        if pid != prev_patient or day - anchor > window:
            counter += 1
            prev_patient, anchor = pid, day
        ids[i] = counter
    return ids


def build_episodes(visits: pd.DataFrame, window_days: int, min_visits: int) -> pd.DataFrame:
    if visits.empty:
        return pd.DataFrame(columns=[
            "episode_id", "patient_id", "start", "end", "span_days", "n_visits", "n_days",
            "n_services", "services", "pattern", "cohort", "age", "eligible",
        ])
    v = visits.sort_values(["patient_id", "date"])
    v = v.assign(episode_id=_episode_ids(v["patient_id"].to_numpy(), v["date"].to_numpy(), window_days))
    episodes = v.groupby("episode_id").agg(
        patient_id=("patient_id", "first"),
        start=("date", "min"),
        end=("date", "max"),
        n_visits=("sejour_id", "size"),
        n_days=("date", "nunique"),
        services=("service", lambda s: tuple(sorted(set(s)))),
        cohort=("cohort", "first"),
        age=("age", "first"),
    ).reset_index()
    episodes["span_days"] = (episodes["end"] - episodes["start"]).dt.days
    episodes["n_services"] = episodes["services"].map(len)
    episodes["pattern"] = episodes["services"].map(" + ".join)
    episodes["eligible"] = episodes["n_days"] >= min_visits
    return episodes


def visit_gaps(visits: pd.DataFrame) -> pd.Series:
    """Délai (jours) entre deux jours de venue consécutifs d'un même patient."""
    days = visits[["patient_id", "date"]].drop_duplicates().sort_values(["patient_id", "date"])
    gaps = days.groupby("patient_id")["date"].diff().dt.days
    return gaps.dropna().astype(int)


def service_transitions(visits: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """Passages service → service suivant, quand la visite suivante est dans la fenêtre."""
    v = visits.sort_values(["patient_id", "date", "sejour_id"])
    nxt = v.groupby("patient_id")[["service", "date"]].shift(-1)
    gap = (nxt["date"] - v["date"]).dt.days
    mask = nxt["service"].notna() & (gap <= window_days)
    return (
        pd.DataFrame({"source": v.loc[mask, "service"], "target": nxt.loc[mask, "service"]})
        .value_counts()
        .rename("count")
        .reset_index()
    )
