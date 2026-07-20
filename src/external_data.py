"""Load and summarize CHU external-consultation extracts for app priors & charts."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "documents" / "data"

# App specialty → Excel file(s). Empty list = no extract (manual only).
SPECIALTY_EXTRACT_FILES: dict[str, list[str]] = {
    "oncologie": ["Données_Externes_Hématologie_et_Oncologie_A.xlsx"],
    "diabetologie": [
        "Données_Externes_Endocrino_et_diabéto_2020_2023_A.xlsx",
        "Données_Externes_Endocrino_et_diabéto_A.xlsx",
    ],
    "cardiologie": [],
    "nephrologie": [],
    "douleur_chronique": [],
}

# Labels for hospital-wide demand ranking (all extracts).
EXTRACT_LABELS: dict[str, str] = {
    "infectieux": "Infectieux",
    "gastro": "Gastro / chir. viscérale",
    "hemato_onco": "Hémato / oncologie",
    "endocrino": "Endocrino / diabéto",
    "med_interne": "Médecine interne",
    "neuro": "Neurologie",
}

_DOW_FR = {
    "Monday": "Lundi",
    "Tuesday": "Mardi",
    "Wednesday": "Mercredi",
    "Thursday": "Jeudi",
    "Friday": "Vendredi",
    "Saturday": "Samedi",
    "Sunday": "Dimanche",
}
_DOW_ORDER = list(_DOW_FR.values())


def _extract_key_from_filename(name: str) -> str:
    n = name.lower()
    if "infect" in n:
        return "infectieux"
    if "gastro" in n:
        return "gastro"
    if "hémat" in n or "hemat" in n:
        return "hemato_onco"
    if "endocrino" in n:
        return "endocrino"
    if "interne" in n:
        return "med_interne"
    if "neuro" in n:
        return "neuro"
    return "other"


def _norm_ngap(raw: object) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return "MISSING"
    c = str(raw).upper().replace(" ", "")
    if c.startswith("CS"):
        return "CS"
    if c.startswith("APC"):
        return "APC"
    if c.startswith("APU"):
        return "APU"
    if c.startswith("G"):
        return "G"
    if c.startswith("MCS"):
        return "MCS"
    if c in {"", "NAN", "NONE"}:
        return "MISSING"
    return "OTHER"


def _metabolic_mask(series: pd.Series) -> pd.Series:
    lib = series.fillna("").astype(str)
    return lib.str.contains(
        r"Diabète|diabète|Hypoglycémie|hypoglycémie|Hypokali",
        case=False,
        regex=True,
    )


@dataclass
class SpecialtyPriors:
    """Suggested wizard defaults + chart payloads for one app specialty."""

    specialty: str
    has_data: bool = False
    n_rows: int = 0
    n_patients: int = 0
    n_sejours: int = 0
    period_start: str | None = None
    period_end: str | None = None
    mean_age: float = 0.0
    median_age: float = 0.0
    visits_per_patient: float = 1.0
    pct_repeat: float = 0.0
    suggested_patients: int = 0
    suggested_fragmentation_pct: float = 80.0
    suggested_hdj_eligible_pct: float = 30.0
    suggested_avg_acts: int = 3
    metabolic_patients: int = 0
    metabolic_pct: float = 0.0
    cross_specialty_patients: int = 0
    note: str = ""
    arrival_by_dow: dict[str, int] = field(default_factory=dict)
    arrival_by_hour: dict[int, int] = field(default_factory=dict)
    top_units: list[tuple[str, int]] = field(default_factory=list)
    ngap_mix: dict[str, int] = field(default_factory=dict)


@dataclass
class HospitalExternalSnapshot:
    """Hospital-wide views across all extracts."""

    demand_ranking: pd.DataFrame
    arrival_by_dow: pd.DataFrame
    arrival_by_hour: pd.DataFrame
    ngap_by_extract: pd.DataFrame
    top_units_global: pd.DataFrame
    overlap_pairs: pd.DataFrame
    n_patients_multi_specialty: int
    total_patients: int
    total_rows: int
    period_start: str | None
    period_end: str | None


def data_dir_available() -> bool:
    return DATA_DIR.is_dir() and any(DATA_DIR.glob("*.xlsx"))


@lru_cache(maxsize=1)
def load_all_extracts() -> pd.DataFrame:
    """Load every Excel extract into one annotated DataFrame."""
    if not DATA_DIR.is_dir():
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for path in sorted(DATA_DIR.glob("*.xlsx")):
        try:
            df = pd.read_excel(path)
        except Exception:
            continue
        if df.empty:
            continue
        df = df.copy()
        df["_file"] = path.name
        df["_extract"] = _extract_key_from_filename(path.name)
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    all_df = pd.concat(frames, ignore_index=True)
    if "DATE ENTREE SEJ" in all_df.columns:
        all_df["DATE ENTREE SEJ"] = pd.to_datetime(all_df["DATE ENTREE SEJ"], errors="coerce")
    if "HEURE ENTREE SEJ" in all_df.columns:
        all_df["HEURE ENTREE SEJ"] = pd.to_datetime(all_df["HEURE ENTREE SEJ"], errors="coerce")
    return all_df


def clear_extract_cache() -> None:
    load_all_extracts.cache_clear()


def _slice_for_specialty(all_df: pd.DataFrame, specialty: str) -> pd.DataFrame:
    files = SPECIALTY_EXTRACT_FILES.get(specialty, [])
    if not files or all_df.empty:
        return pd.DataFrame()
    return all_df[all_df["_file"].isin(files)].copy()


def _arrival_frames(df: pd.DataFrame) -> tuple[dict[str, int], dict[int, int]]:
    if df.empty or "DATE ENTREE SEJ" not in df.columns:
        return {}, {}
    dates = df["DATE ENTREE SEJ"].dropna()
    dow_en = dates.dt.day_name()
    dow = dow_en.map(_DOW_FR).value_counts()
    by_dow = {d: int(dow.get(d, 0)) for d in _DOW_ORDER}
    hours: dict[int, int] = {}
    if "HEURE ENTREE SEJ" in df.columns:
        h = df["HEURE ENTREE SEJ"].dropna().dt.hour
        hours = {int(k): int(v) for k, v in h.value_counts().sort_index().items()}
    return by_dow, hours


def compute_specialty_priors(specialty: str) -> SpecialtyPriors:
    """Derive wizard suggestions and chart series for one app specialty."""
    base = SpecialtyPriors(specialty=specialty)
    all_df = load_all_extracts()
    if all_df.empty:
        base.note = "Aucun fichier dans documents/data."
        return base

    files = SPECIALTY_EXTRACT_FILES.get(specialty, [])
    if not files:
        base.note = "Pas d'extract CHU pour cette spécialité — saisie manuelle."
        return base

    df = _slice_for_specialty(all_df, specialty)
    if df.empty:
        base.note = "Fichiers attendus introuvables ou vides."
        return base

    n_patients = int(df["NUM IPP PATIENT"].nunique())
    n_sejours = int(df["NUM SEJOUR"].nunique())
    vp = df.groupby("NUM IPP PATIENT")["NUM SEJOUR"].nunique()
    visits_per = float(vp.mean()) if len(vp) else 1.0
    pct_repeat = float((vp >= 2).mean() * 100) if len(vp) else 0.0

    dmin = df["DATE ENTREE SEJ"].min()
    dmax = df["DATE ENTREE SEJ"].max()
    period_start = str(pd.Timestamp(dmin).date()) if pd.notna(dmin) else None
    period_end = str(pd.Timestamp(dmax).date()) if pd.notna(dmax) else None

    ages = df["AGE PATIENT ANNEES ENT SEJ"].dropna()
    mean_age = float(ages.mean()) if len(ages) else 0.0
    median_age = float(ages.median()) if len(ages) else 0.0

    metabolic_patients = 0
    metabolic_pct = 0.0
    if specialty == "diabetologie" and "LIBELLE DIAG" in df.columns:
        mask = _metabolic_mask(df["LIBELLE DIAG"])
        metabolic_patients = int(df.loc[mask, "NUM IPP PATIENT"].nunique())
        metabolic_pct = float(metabolic_patients / max(n_patients, 1) * 100)

    # Cross-specialty: patients in this slice who also appear in another extract key
    extract_keys = set(df["_extract"].unique())
    my_patients = set(df["NUM IPP PATIENT"].unique())
    other = all_df[~all_df["_extract"].isin(extract_keys)]
    cross = int(other.loc[other["NUM IPP PATIENT"].isin(my_patients), "NUM IPP PATIENT"].nunique())

    by_dow, by_hour = _arrival_frames(df)
    top_units = list(
        df["LIBELLE UNITE MVT"].fillna("Non renseigné").astype(str).value_counts().head(6).items()
    )
    ngap = df["COTATION NGAP"].map(_norm_ngap).value_counts()
    ngap_mix = {str(k): int(v) for k, v in ngap.items()}

    # Defaults tuned to EXT reality + HDJ opportunity
    if specialty == "diabetologie":
        frag = 90.0
        eligible = min(55.0, max(35.0, metabolic_pct * 0.7 + pct_repeat * 0.5))
        acts = 5  # cas d'usage présentation (parcours multi-actes)
        note = (
            "Extracts endocrino/diabéto = surtout urgences EXT avec diagnostics métaboliques, "
            "pas un HDJ structuré. Volume et cohortes préremplis depuis le CHU."
        )
    else:
        frag = 85.0
        eligible = min(45.0, max(25.0, 20.0 + pct_repeat * 0.8))
        acts = 3
        note = (
            "Extracts consultations externes CHU. Activité HDJ quasi absente dans les fichiers — "
            "les suggestions servent de baseline de demande."
        )

    suggested_patients = max(50, min(3000, n_patients))

    return SpecialtyPriors(
        specialty=specialty,
        has_data=True,
        n_rows=len(df),
        n_patients=n_patients,
        n_sejours=n_sejours,
        period_start=period_start,
        period_end=period_end,
        mean_age=round(mean_age, 1),
        median_age=round(median_age, 1),
        visits_per_patient=round(visits_per, 2),
        pct_repeat=round(pct_repeat, 1),
        suggested_patients=suggested_patients,
        suggested_fragmentation_pct=round(frag, 0),
        suggested_hdj_eligible_pct=round(eligible, 0),
        suggested_avg_acts=acts,
        metabolic_patients=metabolic_patients,
        metabolic_pct=round(metabolic_pct, 1),
        cross_specialty_patients=cross,
        note=note,
        arrival_by_dow=by_dow,
        arrival_by_hour=by_hour,
        top_units=[(str(u), int(c)) for u, c in top_units],
        ngap_mix=ngap_mix,
    )


def compute_hospital_snapshot() -> HospitalExternalSnapshot | None:
    """Build hospital-wide ranking / arrival / NGAP / units / overlap tables."""
    all_df = load_all_extracts()
    if all_df.empty:
        return None

    # Demand ranking by extract (unique patients)
    demand_rows = []
    for key, label in EXTRACT_LABELS.items():
        sub = all_df[all_df["_extract"] == key]
        if sub.empty:
            continue
        demand_rows.append(
            {
                "extract": key,
                "label": label,
                "patients": int(sub["NUM IPP PATIENT"].nunique()),
                "sejours": int(sub["NUM SEJOUR"].nunique()),
                "rows": len(sub),
            }
        )
    demand = pd.DataFrame(demand_rows).sort_values("patients", ascending=False)

    # Global arrival (recent-ish: exclude empty dates)
    by_dow, by_hour = _arrival_frames(all_df)
    dow_df = pd.DataFrame(
        {"jour": list(by_dow.keys()), "passages": list(by_dow.values())}
    )
    hour_df = pd.DataFrame(
        {"heure": list(by_hour.keys()), "passages": list(by_hour.values())}
    ).sort_values("heure")

    # NGAP by extract
    tmp = all_df.copy()
    tmp["ngap"] = tmp["COTATION NGAP"].map(_norm_ngap)
    ngap_by = (
        tmp.groupby(["_extract", "ngap"])
        .size()
        .reset_index(name="count")
        .rename(columns={"_extract": "extract"})
    )
    ngap_by["label"] = ngap_by["extract"].map(EXTRACT_LABELS).fillna(ngap_by["extract"])

    # Top units global
    units = (
        all_df["LIBELLE UNITE MVT"]
        .fillna("Non renseigné")
        .astype(str)
        .value_counts()
        .head(12)
        .rename_axis("unite")
        .reset_index(name="passages")
    )

    # Overlap pairs
    pat_specs = all_df.groupby("NUM IPP PATIENT")["_extract"].apply(lambda s: frozenset(s))
    multi = pat_specs[pat_specs.map(len) > 1]
    from collections import Counter

    pairs: Counter[tuple[str, str]] = Counter()
    for specs in multi:
        ordered = sorted(specs)
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                pairs[(ordered[i], ordered[j])] += 1
    overlap_rows = [
        {
            "a": EXTRACT_LABELS.get(a, a),
            "b": EXTRACT_LABELS.get(b, b),
            "patients": n,
        }
        for (a, b), n in pairs.most_common(12)
    ]
    overlap = pd.DataFrame(overlap_rows)

    dmin = all_df["DATE ENTREE SEJ"].min()
    dmax = all_df["DATE ENTREE SEJ"].max()

    return HospitalExternalSnapshot(
        demand_ranking=demand,
        arrival_by_dow=dow_df,
        arrival_by_hour=hour_df,
        ngap_by_extract=ngap_by,
        top_units_global=units,
        overlap_pairs=overlap,
        n_patients_multi_specialty=int(len(multi)),
        total_patients=int(all_df["NUM IPP PATIENT"].nunique()),
        total_rows=len(all_df),
        period_start=str(pd.Timestamp(dmin).date()) if pd.notna(dmin) else None,
        period_end=str(pd.Timestamp(dmax).date()) if pd.notna(dmax) else None,
    )


def apply_priors_to_session(session_state: dict, specialty: str) -> SpecialtyPriors:
    """Write suggested wizard keys from CHU extracts (does not touch tariffs)."""
    priors = compute_specialty_priors(specialty)
    session_state["wiz_data_backed"] = bool(priors.has_data)
    session_state["wiz_data_note"] = priors.note
    if not priors.has_data:
        return priors

    session_state["wiz_patients"] = int(priors.suggested_patients)
    session_state["wiz_fragmentation_pct"] = float(priors.suggested_fragmentation_pct)
    session_state["wiz_hdj_eligible_pct"] = float(
        min(priors.suggested_hdj_eligible_pct, priors.suggested_fragmentation_pct)
    )
    session_state["wiz_avg_acts"] = int(priors.suggested_avg_acts)
    session_state["wiz_mean_age"] = float(priors.mean_age)
    session_state["wiz_visits_per_patient"] = float(priors.visits_per_patient)
    session_state["wiz_metabolic_pct"] = float(priors.metabolic_pct)
    session_state["wiz_cross_specialty"] = int(priors.cross_specialty_patients)
    session_state["wiz_period"] = f"{priors.period_start} → {priors.period_end}"
    return priors


def specialty_has_extract(specialty: str) -> bool:
    return bool(SPECIALTY_EXTRACT_FILES.get(specialty))
