"""Lecture des extractions « consultations externes » et mise au format visite.

Une ligne des fichiers source = un acte / une cotation. Une **visite** = un séjour
externe (NUM SEJOUR) : une venue d'un patient, un jour, dans une unité.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import pandas as pd

from hdj.config import (
    CACHE_DIR, COHORTS, GENERIC_UNITS, OTHER_SERVICE, RAW_DIR, UNIT_TO_SERVICE, normalize,
)

_SOURCE_COLUMNS = {
    "NUM IPP PATIENT": "patient_id",
    "NUM SEJOUR": "sejour_id",
    "DATE ENTREE SEJ": "date",
    "HEURE ENTREE SEJ": "entry_time",
    "LIBELLE UNITE MVT": "unit",
    "AGE PATIENT ANNEES ENT SEJ": "age",
    "LIBELLE DIAG": "diagnosis",
    "LIBELLE ACTE": "ccam_label",
    "LIBELLE COTATION NGAP": "ngap_label",
}


def _cohort_for(path: Path) -> str:
    name = normalize(path.stem)
    for key, label in COHORTS.items():
        if key in name:
            return label
    return OTHER_SERVICE


def _service_for(unit: str, cohort: str) -> str:
    if unit in GENERIC_UNITS:
        return cohort
    return UNIT_TO_SERVICE.get(unit, OTHER_SERVICE)


def _read_raw(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(raw_dir.glob("*.xlsx")):
        df = pd.read_excel(path, usecols=list(_SOURCE_COLUMNS)).rename(columns=_SOURCE_COLUMNS)
        df["cohort"] = _cohort_for(path)
        df["source_file"] = path.name
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"Aucun fichier .xlsx dans {raw_dir}")
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def _to_visits(rows: pd.DataFrame) -> pd.DataFrame:
    rows = rows.copy()
    rows["has_ccam"] = rows["ccam_label"].notna()
    visits = (
        rows.groupby("sejour_id", as_index=False)
        .agg(
            patient_id=("patient_id", "first"),
            date=("date", "first"),
            entry_time=("entry_time", "first"),
            unit=("unit", "first"),
            age=("age", "first"),
            cohort=("cohort", "first"),
            source_file=("source_file", "first"),
            n_rows=("sejour_id", "size"),
            n_ccam=("has_ccam", "sum"),
            diagnosis=("diagnosis", "first"),
        )
    )
    visits["date"] = pd.to_datetime(visits["date"]).dt.normalize()
    visits["service"] = [_service_for(u, c) for u, c in zip(visits["unit"], visits["cohort"])]
    visits["hour"] = pd.to_datetime(visits["entry_time"]).dt.hour
    visits["weekday"] = visits["date"].dt.dayofweek
    visits["age"] = visits["age"].astype(int)
    return visits.drop(columns="entry_time").sort_values(["patient_id", "date"]).reset_index(drop=True)


@lru_cache(maxsize=1)
def load_visits(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Toutes les visites, avec un cache parquet invalidé si un fichier source change."""
    sources = sorted(raw_dir.glob("*.xlsx"))
    stamp = "|".join(f"{p.name}:{p.stat().st_mtime_ns}" for p in sources)
    cache = CACHE_DIR / f"visits_{hashlib.sha1(stamp.encode()).hexdigest()[:12]}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    visits = _to_visits(_read_raw(raw_dir))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for old in CACHE_DIR.glob("visits_*.parquet"):
        old.unlink()
    visits.to_parquet(cache, index=False)
    return visits


def filter_visits(
    visits: pd.DataFrame,
    start: str | None = None,
    end: str | None = None,
    cohorts: list[str] | None = None,
    age_range: tuple[int, int] | None = None,
) -> pd.DataFrame:
    mask = pd.Series(True, index=visits.index)
    if start:
        mask &= visits["date"] >= pd.Timestamp(start)
    if end:
        mask &= visits["date"] <= pd.Timestamp(end)
    if cohorts:
        mask &= visits["cohort"].isin(cohorts)
    if age_range:
        mask &= visits["age"].between(*age_range)
    return visits[mask]
