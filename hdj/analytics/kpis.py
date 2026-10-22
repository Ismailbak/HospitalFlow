"""Indicateurs descriptifs de l'activité observée."""
from __future__ import annotations

import pandas as pd


def activity_summary(visits: pd.DataFrame, episodes: pd.DataFrame, window_days: int) -> dict:
    patients = visits["patient_id"].nunique()
    if not patients:
        return {k: 0 for k in (
            "patients", "visits", "visits_per_patient", "multi_service_patients",
            "multi_service_share", "mean_age", "eligible_episodes", "eligible_patients",
            "eligible_share", "groupable_trips",
        )}
    services_per_patient = visits.groupby("patient_id")["service"].nunique()
    eligible = episodes[episodes["eligible"]]
    return {
        "patients": patients,
        "visits": len(visits),
        "visits_per_patient": len(visits) / patients,
        "multi_service_patients": int((services_per_patient >= 2).sum()),
        "multi_service_share": float((services_per_patient >= 2).mean()),
        "mean_age": float(visits.drop_duplicates("patient_id")["age"].mean()),
        "eligible_episodes": len(eligible),
        "eligible_patients": eligible["patient_id"].nunique(),
        "eligible_share": eligible["patient_id"].nunique() / patients,
        # venues évitables : un épisode de n jours de venue devient 1 journée HDJ
        "groupable_trips": int((eligible["n_days"] - 1).sum()),
        "window_days": window_days,
    }


def conversion_potential(episodes: pd.DataFrame) -> pd.DataFrame:
    """Épisodes convertibles par service impliqué (un épisode multi-services compte pour chacun)."""
    eligible = episodes[episodes["eligible"]]
    if eligible.empty:
        return pd.DataFrame(columns=["service", "episodes", "trips_avoided"])
    exploded = eligible.explode("services")
    return (
        exploded.groupby("services")
        .agg(episodes=("episode_id", "nunique"), trips_avoided=("n_days", lambda s: int((s - 1).sum())))
        .reset_index()
        .rename(columns={"services": "service"})
        .sort_values("episodes", ascending=False)
    )


def top_patterns(episodes: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    """Motifs de parcours convertibles les plus fréquents."""
    eligible = episodes[episodes["eligible"]]
    if eligible.empty:
        return pd.DataFrame(columns=["pattern", "episodes", "patients", "mean_days", "median_span"])
    return (
        eligible.groupby("pattern")
        .agg(
            episodes=("episode_id", "size"),
            patients=("patient_id", "nunique"),
            mean_days=("n_days", "mean"),
            median_span=("span_days", "median"),
        )
        .reset_index()
        .sort_values("episodes", ascending=False)
        .head(limit)
    )


def data_quality(visits: pd.DataFrame) -> pd.DataFrame:
    """Couverture des champs clés, par fichier source."""
    return (
        visits.groupby("source_file")
        .agg(
            cohort=("cohort", "first"),
            visits=("sejour_id", "size"),
            patients=("patient_id", "nunique"),
            start=("date", "min"),
            end=("date", "max"),
            with_diagnosis=("diagnosis", lambda s: s.notna().mean()),
            with_ccam=("n_ccam", lambda s: (s > 0).mean()),
            hdj_visits=("unit", lambda s: int((s == "HDJ CONSULTATION").sum())),
        )
        .reset_index()
        .sort_values("start")
    )
