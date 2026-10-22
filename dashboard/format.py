"""Formatage des nombres à la française."""
from __future__ import annotations

NBSP = " "


def integer(x: float) -> str:
    return f"{x:,.0f}".replace(",", NBSP)


def compact(x: float) -> str:
    """3 029 → « 3,03 k » ; 12 345 → « 12,3 k » ; < 1 000 inchangé."""
    if abs(x) < 1000:
        return integer(x)
    value = x / 1000
    digits = 2 if abs(value) < 10 else 1 if abs(value) < 100 else 0
    return f"{value:.{digits}f}".replace(".", ",") + f"{NBSP}k"


def decimal(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def percent(x: float, digits: int = 0) -> str:
    return f"{x * 100:.{digits}f}".replace(".", ",") + f"{NBSP}%"


def euros(x: float, compact_form: bool = True) -> str:
    sign = "−" if x < 0 else ""
    x = abs(x)
    if compact_form and x >= 1000:
        return f"{sign}{decimal(x / 1000, 0 if x >= 100_000 else 1)}{NBSP}k€"
    return f"{sign}{integer(x)}{NBSP}€"
