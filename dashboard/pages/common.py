"""Petits utilitaires communs aux pages."""
from __future__ import annotations

import pandas as pd

from dashboard import format as fmt
from dashboard.state import resolved


def period_badge(filters: dict | None, patients: int | None = None) -> str:
    f = resolved(filters)
    start, end = (pd.Timestamp(f[k]).strftime("%d/%m/%Y") for k in ("start", "end"))
    text = f"{start} → {end}"
    return f"{text} · {fmt.integer(patients)} patients" if patients is not None else text
