"""Persist last user simulation inputs locally between sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.data import SPECIALTIES

_PREFS_FILE = Path(__file__).resolve().parent.parent / "data" / "last_inputs.json"

WIZ_TO_CFG: tuple[tuple[str, str], ...] = (
    ("wiz_patients", "cfg_patients"),
    ("wiz_fragmentation_pct", "cfg_fragmentation_pct"),
    ("wiz_hdj_eligible_pct", "cfg_hdj_eligible_pct"),
    ("wiz_avg_wait", "cfg_avg_wait"),
    ("wiz_avg_acts", "cfg_avg_acts"),
    ("wiz_slot", "cfg_slot_duration"),
    ("wiz_frag", "cfg_frag_tariff"),
    ("wiz_hdj", "cfg_hdj_tariff"),
    ("wiz_days", "cfg_sim_days"),
    ("wiz_hdj_units", "cfg_hdj_units"),
    ("wiz_hdj_beds", "cfg_hdj_beds"),
    ("wiz_hdj_slots", "cfg_hdj_slots"),
    ("wiz_hdj_exams", "cfg_hdj_exams"),
    ("wiz_setup_cost", "cfg_setup_cost"),
)

PREF_KEYS = (
    "wiz_specialty",
    "wiz_patients",
    "wiz_fragmentation_pct",
    "wiz_hdj_eligible_pct",
    "wiz_avg_wait",
    "wiz_avg_acts",
    "wiz_slot",
    "wiz_days",
    "wiz_frag",
    "wiz_hdj",
    "wiz_setup_cost",
    "wiz_hdj_units",
    "wiz_hdj_beds",
    "wiz_hdj_slots",
    "wiz_hdj_exams",
    "cfg_patients",
    "cfg_fragmentation_pct",
    "cfg_hdj_eligible_pct",
    "cfg_avg_wait",
    "cfg_avg_acts",
    "cfg_slot_duration",
    "cfg_sim_days",
    "cfg_frag_tariff",
    "cfg_hdj_tariff",
    "cfg_setup_cost",
    "cfg_hdj_units",
    "cfg_hdj_beds",
    "cfg_hdj_slots",
    "cfg_hdj_exams",
    "cfg_grouping_rate",
)


def sync_wiz_to_cfg(session_state: dict[str, Any]) -> None:
    """Keep sidebar (cfg_*) aligned with wizard (wiz_*) inputs."""
    for src, dst in WIZ_TO_CFG:
        if src in session_state:
            session_state[dst] = session_state[src]


def _validate(data: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key in PREF_KEYS:
        if key not in data:
            continue
        value = data[key]
        if key == "wiz_specialty" and value not in SPECIALTIES:
            continue
        cleaned[key] = value
    return cleaned


def load_saved_inputs() -> dict[str, Any]:
    if not _PREFS_FILE.exists():
        return {}
    try:
        raw = json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return _validate(raw)


def save_inputs(session_state: dict[str, Any]) -> None:
    sync_wiz_to_cfg(session_state)
    payload = _validate({k: session_state[k] for k in PREF_KEYS if k in session_state})
    if not payload:
        return
    _PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PREFS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def apply_saved_inputs(session_state: dict[str, Any]) -> bool:
    """Pre-fill empty session keys from the last saved file."""
    if session_state.get("_prefs_restored"):
        return bool(session_state.get("_prefs_had_save"))
    saved = load_saved_inputs()
    for key, value in saved.items():
        session_state.setdefault(key, value)
    sync_wiz_to_cfg(session_state)
    session_state["_prefs_restored"] = True
    session_state["_prefs_had_save"] = bool(saved)
    return bool(saved)


def clear_saved_inputs() -> None:
    if _PREFS_FILE.exists():
        _PREFS_FILE.unlink()
