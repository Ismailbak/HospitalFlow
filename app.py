"""HDJ Agent MVP - Streamlit dashboard for scenario comparison."""

from __future__ import annotations

import base64
import math
import random
import time
from pathlib import Path

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import importlib

import src.data
import src.agents
import src.simulation
import src.metrics
import src.external_data

importlib.reload(src.data)
importlib.reload(src.agents)
importlib.reload(src.simulation)
importlib.reload(src.metrics)
importlib.reload(src.external_data)

from src.data import (
    SCENARIO_LABELS,
    SPECIALTIES,
    SimulationConfig,
    config_cache_key,
    load_hospital_data,
)
from src.external_data import (
    apply_priors_to_session,
    compute_hospital_snapshot,
    compute_specialty_priors,
    data_dir_available,
    specialty_has_extract,
)
from src.metrics import run_full_analysis
from src.user_prefs import (
    PREF_KEYS,
    apply_saved_inputs,
    clear_saved_inputs,
    save_inputs,
    sync_wiz_to_cfg,
)

ANALYSIS_CACHE_VERSION = 8

_ASSETS = Path(__file__).resolve().parent / "assets"
_LOGO_PATH = _ASSETS / "logo.png"
_THEME_CSS = (_ASSETS / "theme.css").read_text(encoding="utf-8")

SPECIALTY_META = {
    "oncologie": ("🎗️", "Chimiothérapie, suivi ambulatoire"),
    "cardiologie": ("❤️", "Insuffisance, cathétérisme"),
    "diabetologie": ("🩺", "Education thérapeutique, suivi"),
    "nephrologie": ("💧", "Dialyse, consultations spécialisées"),
    "douleur_chronique": ("💊", "Prise en charge pluridisciplinaire"),
}

C_PRIMARY = "#1976D2"
C_SECONDARY = "#ECEFF1"
C_ACCENT = "#26A69A"
C_BG = "#FAFAFA"
C_TEXT = "#212121"
C_PRIMARY_LIGHT = "#BBDEFB"
C_PRIMARY_MID = "#64B5F6"
C_TEXT_MUTED = "#616161"
CHART_SEQUENCE = [C_SECONDARY, C_PRIMARY_MID, C_PRIMARY]

st.set_page_config(
    page_title="HDJ Agent MVP",
    page_icon=str(_LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def _logo_b64() -> str:
    return base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")


def logo_img(*, css_class: str = "", alt: str = "CHU Guyane") -> str:
    cls = f' class="{css_class}"' if css_class else ""
    return f'<img src="data:image/png;base64,{_logo_b64()}" alt="{alt}"{cls}/>'


def render_html(html: str) -> None:
    """Render HTML without markdown sanitizer stripping tags (fixes stray </div>)."""
    st.html(html)

st.markdown(f"<style>{_THEME_CSS}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    /* Hide Streamlit chrome so it reads like a product UI */
    header[data-testid="stHeader"] { background: transparent; height: 0; }
    #MainMenu, footer { visibility: hidden; }
    div[data-testid="stToolbar"] { display: none; }
    div[data-testid="stDecoration"] { display: none; }

    html, body, .stApp {
        background: var(--color-bg, #FAFAFA) !important;
        color: var(--color-text, #212121) !important;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1320px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--color-white, #FFFFFF) !important;
        border-right: 1px solid var(--color-secondary, #ECEFF1);
    }
    section[data-testid="stSidebar"] * {
        color: var(--color-text, #212121) !important;
    }

    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label {
        color: var(--color-text, #212121);
    }

    .hero-card {
        background: var(--color-white, #FFFFFF);
        border: 1px solid var(--color-secondary, #ECEFF1);
        border-radius: 26px;
        padding: 24px 30px;
        box-shadow: var(--shadow-card, 0 12px 32px rgba(25, 118, 210, 0.08));
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .hero-eyebrow {
        color: var(--color-primary, #1976D2) !important;
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .10em;
        margin-bottom: 6px;
    }
    .hero-title {
        color: var(--color-text, #212121) !important;
        font-size: 1.9rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.15;
    }
    .hero-subtitle {
        color: var(--color-text-muted, #616161) !important;
        font-size: .98rem;
        margin-top: 8px;
        max-width: 720px;
    }
    .hero-badge {
        background: var(--color-primary, #1976D2);
        color: var(--color-white, #FFFFFF) !important;
        border-radius: 18px;
        padding: 16px 20px;
        text-align: center;
        min-width: 150px;
        box-shadow: 0 14px 30px rgba(25, 118, 210, 0.25);
    }
    .hero-badge .small { font-size: .72rem; opacity: .85; letter-spacing: .06em; }
    .hero-badge .big { font-size: 1.15rem; font-weight: 800; margin-top: 4px; }

    .rail-card {
        background: var(--color-white, #FFFFFF);
        border: 1px solid var(--color-secondary, #ECEFF1);
        border-radius: 26px;
        padding: 18px 10px;
        min-height: 640px;
        box-shadow: var(--shadow-card, 0 12px 32px rgba(25, 118, 210, 0.08));
        text-align: center;
    }
    .rail-logo {
        width: 44px; height: 44px; line-height: 44px;
        border-radius: 14px; margin: 0 auto 22px auto;
        background: var(--color-secondary, #ECEFF1);
        color: var(--color-primary, #1976D2) !important;
        font-weight: 900; font-size: 1.15rem;
    }
    .rail-item, .rail-item-active {
        width: 42px; height: 42px; line-height: 42px;
        border-radius: 14px; margin: 12px auto; font-weight: 800;
    }
    .rail-item {
        background: var(--color-bg, #FAFAFA);
        color: var(--color-primary, #1976D2) !important;
        border: 1px solid var(--color-secondary, #ECEFF1);
    }
    .rail-item-active {
        background: var(--color-primary, #1976D2);
        color: var(--color-white, #FFFFFF) !important;
        box-shadow: 0 12px 24px rgba(25, 118, 210, 0.22);
    }
    .rail-block { margin: 16px auto 8px auto; }
    .rail-label {
        font-size: .72rem; color: var(--color-text-muted, #616161) !important; font-weight: 700;
        margin-top: 4px; white-space: nowrap;
    }

    .dash-card, .insight-card {
        background: var(--color-white, #FFFFFF);
        border: 1px solid var(--color-secondary, #ECEFF1);
        border-radius: 22px;
        padding: 22px;
        box-shadow: var(--shadow-card, 0 12px 32px rgba(25, 118, 210, 0.08));
        margin-bottom: 18px;
    }
    .dash-card h3, .insight-card h3 {
        color: var(--color-text, #212121) !important;
        margin-top: 0; margin-bottom: 12px; font-size: 1.05rem; font-weight: 800;
    }
    .muted { color: var(--color-text-muted, #616161) !important; font-size: .9rem; }

    .decision-pill {
        display: inline-block; padding: 8px 14px; border-radius: 999px;
        background: var(--color-secondary, #ECEFF1);
        color: var(--color-primary, #1976D2) !important; font-weight: 800;
        font-size: .82rem; margin-bottom: 12px;
    }
    .metric-grid {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px; margin-top: 6px;
    }
    .metric-card {
        background: var(--color-bg, #FAFAFA);
        border: 1px solid var(--color-secondary, #ECEFF1);
        border-radius: 18px; padding: 16px;
    }
    .metric-label {
        color: var(--color-text-muted, #616161) !important; font-size: .72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: .04em;
    }
    .metric-value { color: var(--color-text, #212121) !important; font-size: 1.4rem; font-weight: 800; margin-top: 4px; }
    .metric-delta { color: var(--color-accent, #26A69A) !important; font-size: .82rem; font-weight: 700; margin-top: 4px; }

    .progress-track {
        height: 12px; background: var(--color-secondary, #ECEFF1); border-radius: 999px;
        overflow: hidden; margin: 10px 0 4px 0;
    }
    .progress-fill {
        height: 12px;
        background: linear-gradient(90deg, var(--color-primary, #1976D2), var(--color-accent, #26A69A));
        border-radius: 999px;
    }

    .check-row {
        border-radius: 14px; padding: 11px 14px; margin: 8px 0;
        background: var(--color-bg, #FAFAFA); border: 1px solid var(--color-secondary, #ECEFF1);
        color: var(--color-text, #212121) !important; font-weight: 600;
    }
    .check-ok { border-left: 5px solid var(--color-accent, #26A69A); }
    .check-warn { border-left: 5px solid var(--color-primary, #1976D2); }

    div[data-testid="stMetric"] {
        background: var(--color-white, #FFFFFF);
        border: 1px solid var(--color-secondary, #ECEFF1);
        border-radius: 18px; padding: 14px 16px;
        box-shadow: var(--shadow-card, 0 12px 32px rgba(25, 118, 210, 0.08));
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--color-white, #FFFFFF);
        border: 1px solid var(--color-secondary, #ECEFF1) !important;
        border-radius: 22px;
        padding: 8px 14px 6px 14px;
        box-shadow: var(--shadow-card, 0 12px 32px rgba(25, 118, 210, 0.08));
    }

    .greeting-title { color: var(--color-text, #212121) !important; font-size: 1.55rem; font-weight: 800; margin: 0; }
    .greeting-sub { color: var(--color-text-muted, #616161) !important; font-size: .92rem; margin-top: 2px; }
    .card-eyebrow {
        color: var(--color-text-muted, #616161) !important; font-size: .72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: .05em; margin-bottom: 6px;
    }

    .promo-card {
        background: linear-gradient(140deg, var(--color-primary, #1976D2) 0%, var(--color-primary-dark, #1565C0) 100%);
        border-radius: 22px; padding: 22px; color: var(--color-white, #FFFFFF) !important;
        box-shadow: var(--shadow-hero, 0 24px 56px rgba(25, 118, 210, 0.18)); margin-bottom: 18px;
        min-height: 150px;
    }
    .promo-card .small { font-size: .74rem; opacity: .9; letter-spacing: .05em; }
    .promo-card .big { font-size: 1.9rem; font-weight: 850; margin: 6px 0; }
    .promo-card .tag { font-size: .82rem; opacity: .95; }

    .pbar-row { margin: 14px 0; }
    .pbar-top { display: flex; justify-content: space-between; font-size: .82rem; color: var(--color-text-muted, #616161) !important; }
    .pbar-top b { color: var(--color-text, #212121) !important; }

    .list-row {
        display: flex; align-items: center; gap: 12px;
        padding: 10px 0; border-bottom: 1px solid var(--color-secondary, #ECEFF1);
    }
    .list-icon {
        width: 38px; height: 38px; border-radius: 12px; flex: none;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; color: var(--color-white, #FFFFFF) !important; font-size: .85rem;
    }
    .list-main { flex: 1; }
    .list-title { color: var(--color-text, #212121) !important; font-weight: 700; font-size: .9rem; }
    .list-sub { color: var(--color-text-muted, #616161) !important; font-size: .76rem; }
    .list-val { color: var(--color-primary, #1976D2) !important; font-weight: 800; font-size: .9rem; }

    .cta-card {
        background: var(--color-white, #FFFFFF);
        border: 1px solid var(--color-secondary, #ECEFF1);
        border-radius: 22px;
        padding: 22px; text-align: center;
        box-shadow: var(--shadow-card, 0 12px 32px rgba(25, 118, 210, 0.08));
    }
    .cta-card .crown { font-size: 1.8rem; }
    .cta-card .cta-title { color: var(--color-text, #212121) !important; font-weight: 800; margin: 8px 0 4px 0; }
    .cta-btn {
        display: inline-block; margin-top: 12px; padding: 11px 18px; border-radius: 14px;
        background: var(--color-primary, #1976D2);
        color: var(--color-white, #FFFFFF) !important; font-weight: 800; font-size: .86rem;
        box-shadow: 0 12px 24px rgba(25, 118, 210, 0.22);
    }

    /* Landing */
    .landing-hero {
        background: linear-gradient(140deg, var(--color-primary, #1976D2) 0%, var(--color-primary-dark, #1565C0) 100%);
        border-radius: 30px; padding: 54px 46px; color: var(--color-white, #FFFFFF) !important;
        box-shadow: var(--shadow-hero, 0 24px 56px rgba(25, 118, 210, 0.18));
        margin-bottom: 22px;
        position: relative; overflow: hidden;
    }
    .landing-hero:after {
        content: ""; position: absolute; right: -60px; top: -60px;
        width: 260px; height: 260px; border-radius: 50%;
        background: rgba(255,255,255,0.10);
    }
    .landing-eyebrow { font-size: .8rem; font-weight: 800; letter-spacing: .14em; opacity: .9; }
    .landing-title { font-size: 2.7rem; font-weight: 850; line-height: 1.08; margin: 10px 0 12px 0; color:#ffffff !important; }
    .landing-sub { font-size: 1.05rem; opacity: .95; max-width: 640px; color:#ffffff !important; }
    .landing-stats { display: flex; gap: 30px; margin-top: 26px; }
    .landing-stat .n { font-size: 1.8rem; font-weight: 850; color:#ffffff !important; }
    .landing-stat .l { font-size: .82rem; opacity: .9; }
    .landing-stats-pending .n { opacity: .45; }
    .landing-pending {
        margin-top: 18px; font-size: .92rem; opacity: .88; color: #ffffff !important;
        font-style: italic;
    }

    .narr-card {
        background: var(--color-white, #FFFFFF);
        border: 1px solid var(--color-secondary, #ECEFF1);
        border-radius: 24px;
        padding: 34px;
        box-shadow: var(--shadow-card, 0 12px 32px rgba(25, 118, 210, 0.08));
        min-height: 230px;
    }
    .narr-step { color: var(--color-primary, #1976D2) !important; font-weight: 800; letter-spacing: .08em; font-size: .8rem; }
    .narr-title { color: var(--color-text, #212121) !important; font-size: 1.7rem; font-weight: 850; margin: 8px 0 12px 0; }
    .narr-text { color: var(--color-text, #212121) !important; font-size: 1.08rem; line-height: 1.55; opacity: 0.85; }

    .lane-chip {
        display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px;
        border-radius: 999px; font-weight: 800; font-size: .85rem; margin: 4px 8px 4px 0;
        border: 1px solid var(--color-secondary, #ECEFF1);
        background: var(--color-white, #FFFFFF);
    }
    .lane-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
    .flow-count { color: var(--color-text, #212121) !important; font-size: 1.5rem; font-weight: 850; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Display helpers ---
def explain_scenario(scenario: str) -> str:
    explanations = {
        "status_quo": (
            "Situation actuelle simulée : les actes restent majoritairement séparés, "
            "avec peu de coordination entre consultations, examens et retours."
        ),
        "optimize_existing": (
            "Amélioration sans créer de nouvelle unité : les patients éligibles sont "
            "mieux regroupés dans les HDJ existants."
        ),
        "new_hdj": (
            "Scénario de transformation : un HDJ dédié est ajouté pour la spécialité "
            "où le volume convertible est le plus fort."
        ),
    }
    return explanations.get(scenario, "")


def format_eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", " ")


def format_specialty(specialty: str) -> str:
    return specialty.replace("_", " ").capitalize()


def fragmentation_decision_guidance(
    *,
    frag_pct: float,
    eligible_pct: float,
    frag_count: int,
    eligible_count: int,
    total: int,
    wait_days: int,
) -> str:
    """Plain-language next steps from the fragmentation formula result."""
    computed = frag_count / max(total, 1) * 100
    lines = [
        "**Que faire selon le résultat ?**",
        "",
        f"Calcul : `{frag_count} ÷ {total} × 100 = {computed:.0f} %` "
        f"(votre saisie : **{frag_pct:.0f} %**).",
        "",
    ]

    if frag_pct >= 60:
        lines += [
            f"- **Taux ≥ 60 %** ({computed:.0f} %) : fragmentation **élevée**. "
            "Les parcours sont trop dispersés — **priorisez le regroupement en HDJ** "
            "ou l'étude d'une **nouvelle unité** pour votre spécialité.",
        ]
    elif frag_pct >= 40:
        lines += [
            f"- **Taux entre 40 et 59 %** ({computed:.0f} %) : marge d'amélioration **significative**. "
            "Commencez par **optimiser les HDJ existants** (créneaux, coordination des actes), "
            "puis comparez avec un scénario de création si le gain reste insuffisant.",
        ]
    else:
        lines += [
            f"- **Taux < 40 %** ({computed:.0f} %) : parcours **déjà relativement coordonnés**. "
            "Un changement lourd (nouvel HDJ) est probablement **peu prioritaire** — "
            "validez d'abord le scénario **statu quo** et ciblez plutôt les délais ou la capacité.",
        ]

    if eligible_pct < frag_pct:
        gap = frag_pct - eligible_pct
        lines += [
            "",
            f"- **Convertibles HDJ ({eligible_pct:.0f} %) inférieurs aux fragmentés ({frag_pct:.0f} %)** : "
            f"seuls **{eligible_count}** patients sur **{frag_count}** fragmentés peuvent être regroupés "
            f"(écart de **{gap:.0f} points**). Affinez le ciblage clinique avant d'augmenter la capacité HDJ.",
        ]
    elif eligible_pct >= frag_pct and frag_pct >= 40:
        lines += [
            "",
            f"- **Convertibles HDJ ({eligible_pct:.0f} %) ≥ fragmentés ({frag_pct:.0f} %)** : "
            f"la majorité des **{frag_count}** parcours fragmentés peut être orientée vers un HDJ — "
            "le volume justifie de **tester les scénarios d'optimisation** à l'étape suivante.",
        ]

    if wait_days >= 45:
        lines += [
            "",
            f"- **Délai moyen ≥ 45 jours** ({wait_days} j) : l'attente est **critique** — "
            "même avec une fragmentation modérée, le **regroupement des actes** doit être examiné en priorité.",
        ]
    elif wait_days >= 30:
        lines += [
            "",
            f"- **Délai entre 30 et 44 jours** ({wait_days} j) : vigilance sur l'**expérience patient** ; "
            "croisez ce résultat avec la saturation des créneaux HDJ à l'étape capacité.",
        ]
    else:
        lines += [
            "",
            f"- **Délai < 30 jours** ({wait_days} j) : l'urgence patient est **modérée** ; "
            "arbitrez surtout sur la **fragmentation** et le **coût / gain** des scénarios simulés.",
        ]

    return "\n".join(lines)


def next_step_box(message: str) -> None:
    st.info(f"Prochaine étape : {message}")


def metric_card(label: str, value: str, delta: str = "") -> str:
    delta_html = f'<div class="metric-delta">{delta}</div>' if delta else ""
    return (
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f"{delta_html}</div>"
    )


def check_row(label: str, passed: bool) -> str:
    klass = "check-ok" if passed else "check-warn"
    status = "OK" if passed else "A vérifier"
    return f'<div class="check-row {klass}">{label}<br><span class="muted">{status}</span></div>'


def rail(page_name: str) -> str:
    items = [
        ("Flux des agents", "🔄", "Flux"),
        ("Décision guidée", "🎯", "Décision"),
        ("Comparer les scénarios", "📊", "Comparer"),
        ("Vérifier la capacité", "🏥", "Capacité"),
        ("Prioriser la spécialité", "⭐", "Spécialité"),
        ("Synthèse comité", "📋", "Synthèse"),
    ]
    rows = [logo_img(css_class="rail-logo-img")]
    for name, icon, label in items:
        klass = "rail-item-active" if name == page_name else "rail-item"
        rows.append(
            f'<div class="rail-block">'
            f'<div class="{klass}" title="{name}">{icon}</div>'
            f'<div class="rail-label">{label}</div>'
            f"</div>"
        )
    return f'<div class="rail-card">{"".join(rows)}</div>'


def style_chart(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=C_TEXT,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def gauge_chart(value_pct: float, title: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value_pct,
            number={"suffix": " %", "font": {"size": 30, "color": C_TEXT}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": C_TEXT_MUTED},
                "bar": {"color": C_PRIMARY},
                "bgcolor": C_SECONDARY,
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 60], "color": C_BG},
                    {"range": [60, 85], "color": C_PRIMARY_LIGHT},
                    {"range": [85, 100], "color": "#FFCDD2"},
                ],
                "threshold": {
                    "line": {"color": "#E53935", "width": 3},
                    "thickness": 0.8,
                    "value": 85,
                },
            },
        )
    )
    fig.update_layout(
        title={"text": title, "font": {"size": 15, "color": C_TEXT}},
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=C_TEXT,
        margin=dict(l=18, r=18, t=50, b=10),
        height=240,
    )
    return fig


def progress_bar(label: str, value_text: str, pct: float) -> str:
    pct = max(0, min(pct, 100))
    return (
        f'<div class="pbar-row">'
        f'<div class="pbar-top"><span>{label}</span><b>{value_text}</b></div>'
        f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.0f}%"></div></div>'
        f"</div>"
    )


def list_row(letter: str, color: str, title: str, sub: str, value: str) -> str:
    return (
        f'<div class="list-row">'
        f'<div class="list-icon" style="background:{color}">{letter}</div>'
        f'<div class="list-main">'
        f'<div class="list-title">{title}</div>'
        f'<div class="list-sub">{sub}</div>'
        f"</div>"
        f'<div class="list-val">{value}</div>'
        f"</div>"
    )


LANE_Y = {"frag": 3.0, "ex": 0.0, "new": -3.0}
LANE_COLOR = {"frag": C_TEXT_MUTED, "ex": C_PRIMARY, "new": C_ACCENT}
LANE_LABEL = {"frag": "Parcours fragmenté", "ex": "HDJ existant", "new": "Nouveau HDJ"}


def flow_counts(summary: dict) -> tuple[int, int, int]:
    return (
        int(summary.get("fragmented_pathways", 0)),
        int(summary.get("existing_hdj_pathways", 0)),
        int(summary.get("new_hdj_pathways", 0)),
    )


def build_flow_dots(counts: tuple[int, int, int], n: int = 44) -> list[dict]:
    frag, ex, new = counts
    total = max(frag + ex + new, 1)
    seq = (
        ["frag"] * round(n * frag / total)
        + ["ex"] * round(n * ex / total)
        + ["new"] * round(n * new / total)
    )
    if not seq:
        seq = ["ex"]
    rng = random.Random(7)
    dots = []
    for lane in seq:
        dots.append(
            {
                "lane": lane,
                "y0": rng.uniform(-0.6, 0.6),
                "y1": LANE_Y[lane] + rng.uniform(-0.5, 0.5),
                "delay": rng.uniform(0.0, 0.45),
                "color": LANE_COLOR[lane],
            }
        )
    return dots


def flow_figure(dots: list[dict], t: float) -> go.Figure:
    xs, ys, colors = [], [], []
    for d in dots:
        denom = max(1 - d["delay"], 1e-6)
        p = min(max((t - d["delay"]) / denom, 0.0), 1.0)
        x = p * 2.0
        if x <= 1.0:
            y = d["y0"]
        else:
            y = d["y0"] + (d["y1"] - d["y0"]) * (x - 1.0)
        xs.append(x)
        ys.append(y)
        colors.append(d["color"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(size=13, color=colors, line=dict(width=1, color="#ffffff")),
            hoverinfo="skip",
        )
    )
    nodes_x = [0, 1, 2, 2, 2]
    nodes_y = [0, 0, LANE_Y["frag"], LANE_Y["ex"], LANE_Y["new"]]
    nodes_txt = ["Patients", "Triage", "Fragmenté", "HDJ existant", "Nouveau HDJ"]
    fig.add_trace(
        go.Scatter(
            x=nodes_x, y=nodes_y, mode="markers+text",
            marker=dict(size=26, color=C_SECONDARY, line=dict(width=2, color=C_PRIMARY)),
            text=nodes_txt, textposition="bottom center",
            textfont=dict(color=C_TEXT, size=12), hoverinfo="skip",
        )
    )
    fig.update_layout(
        showlegend=False, height=430,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(range=[-0.3, 2.5], visible=False),
        yaxis=dict(range=[-5, 5], visible=False),
    )
    return fig


def sankey_chart(summary: dict) -> go.Figure:
    frag, ex, new = flow_counts(summary)
    total = frag + ex + new
    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=18, thickness=18,
                line=dict(color="#ffffff", width=1),
                label=["Patients", "Triage", "Fragmenté", "HDJ existant", "Nouveau HDJ"],
                color=[C_PRIMARY_MID, C_PRIMARY, C_TEXT_MUTED, C_PRIMARY, C_ACCENT],
            ),
            link=dict(
                source=[0, 1, 1, 1],
                target=[1, 2, 3, 4],
                value=[max(total, 1), max(frag, 0), max(ex, 0), max(new, 0)],
                color=["rgba(25,118,210,.25)", "rgba(97,97,97,.35)",
                       "rgba(25,118,210,.40)", "rgba(38,166,154,.40)"],
            ),
        )
    )
    fig.update_layout(
        height=300, paper_bgcolor="rgba(0,0,0,0)",
        font_color=C_TEXT, margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


# --- Splash & landing gates ---
st.session_state.setdefault("splash_done", False)
st.session_state.setdefault("entered", False)
_prefs_loaded = apply_saved_inputs(st.session_state)


def render_splash() -> None:
    def splash_html(exit: bool = False) -> str:
        exit_cls = " splash-exit" if exit else ""
        return f"""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main {{
    overflow: hidden !important;
    height: 100vh !important;
    max-height: 100dvh !important;
}}
</style>
<div class="splash-screen{exit_cls}">
  <div class="splash-inner">
    {logo_img(css_class="splash-logo")}
  </div>
  <div class="splash-footer">© 2026 CHU de Guyane. Tous droits réservés.</div>
</div>
"""

    slot = st.empty()
    slot.markdown(splash_html(), unsafe_allow_html=True)
    time.sleep(1.25)
    slot.markdown(splash_html(exit=True), unsafe_allow_html=True)
    time.sleep(0.48)
    slot.empty()
    st.markdown(
        """
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main {
    overflow: auto !important;
    height: auto !important;
    max-height: none !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_landing_page() -> None:
    st.markdown('<div class="landing-page-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    render_landing_hero()

    cta_left, cta_right = st.columns(2, gap="medium")
    has_analysis = st.session_state.get("last_analysis") is not None
    with cta_left:
        start = st.button("🚀 Commencer l'analyse", use_container_width=True, type="primary")
    with cta_right:
        narrate = st.button(
            "▶ Demarrer la narration (60s)",
            use_container_width=True,
            disabled=not has_analysis,
        )

    if has_analysis:
        st.caption("Astuce : la narration reprend les resultats de votre derniere analyse.")
    else:
        st.caption("Astuce : lancez d'abord l'analyse guidee — la narration utilisera vos resultats.")

    if start:
        st.session_state["entered"] = True
        st.rerun()
    if narrate and has_analysis:
        run_narration(st.session_state["last_analysis"])
        st.session_state["entered"] = True
        st.rerun()


def render_workspace_header() -> None:
    st.markdown(
        f"""
<div class="workspace-header">
  <div class="workspace-header-brand">
    {logo_img()}
    <div>
      <h1 class="workspace-header-title">Assistant HDJ</h1>
      <div class="workspace-header-sub">CHU de Guyane — simulation multi-agents</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_analysis(_config_key: tuple, _version: int = ANALYSIS_CACHE_VERSION):
    config = SimulationConfig(
        total_patients=_config_key[0],
        fragmentation_pct=_config_key[1],
        hdj_eligible_pct=_config_key[2],
        avg_wait_days=_config_key[3],
        avg_act_count=_config_key[4],
        slot_duration_minutes=_config_key[5],
        grouping_rate=_config_key[6],
        fragmented_tariff_eur=_config_key[7],
        hdj_tariff_eur=_config_key[8],
        simulation_days=_config_key[9],
        focus_specialty=_config_key[10],
        hdj_unit_count=_config_key[11],
        hdj_total_beds=_config_key[12],
        hdj_daily_slots=_config_key[13],
        hdj_exam_capacity_per_day=_config_key[14],
        hdj_setup_cost_per_slot=_config_key[15],
    )
    return run_full_analysis(load_hospital_data(config))


if st.session_state.get("_analysis_cache_v") != ANALYSIS_CACHE_VERSION:
    load_analysis.clear()
    st.session_state["_analysis_cache_v"] = ANALYSIS_CACHE_VERSION


def store_last_analysis(analysis: dict) -> None:
    """Keep the most recent real analysis in session memory."""
    st.session_state["last_analysis"] = analysis


def render_landing_hero() -> None:
    analysis = st.session_state.get("last_analysis")
    if analysis:
        rec = analysis["recommendation"]
        lbest = analysis["results"][rec["recommended_scenario"]].summary
        lbase = analysis["results"]["status_quo"].summary
        lwait = lbase["avg_wait_days"] - lbest["avg_wait_days"]
        stats_html = f"""
  <div class="landing-stats">
    <div class="landing-stat"><div class="n">{lwait:+.1f} j</div><div class="l">gain d'attente estime</div></div>
    <div class="landing-stat"><div class="n">{lbest['hdj_conversion_rate'] * 100:.0f} %</div><div class="l">conversion HDJ</div></div>
    <div class="landing-stat"><div class="n">{len(analysis['results'])}</div><div class="l">scenarios compares</div></div>
  </div>
  <div class="landing-pending">Derniers resultats de votre analyse ({rec['recommended_label']}).</div>"""
    else:
        stats_html = """
  <div class="landing-stats landing-stats-pending">
    <div class="landing-stat"><div class="n">—</div><div class="l">gain d'attente estime</div></div>
    <div class="landing-stat"><div class="n">—</div><div class="l">conversion HDJ</div></div>
    <div class="landing-stat"><div class="n">—</div><div class="l">scenarios compares</div></div>
  </div>
  <div class="landing-pending">Renseignez vos donnees et lancez l'analyse pour obtenir ces indicateurs.</div>"""

    st.markdown(
        f"""
<div class="landing-hero">
  <div class="landing-brand-row">
    {logo_img()}
    <div>
      <div class="landing-brand-name">CHU de Guyane</div>
      <div class="landing-eyebrow">HDJ Agent — Défi 5</div>
    </div>
  </div>
  <div class="landing-title">Optimisez les hopitaux de jour<br>avec une simulation multi-agents</div>
  <div class="landing-sub">
    En un clic, simulez les parcours ambulatoires, comparez les scenarios et obtenez
    une recommandation claire : optimiser l'existant ou creer un nouvel HDJ.
  </div>
  {stats_html}
</div>
""",
        unsafe_allow_html=True,
    )


def run_narration(analysis_data) -> None:
    rec = analysis_data["recommendation"]
    best_s = analysis_data["results"][rec["recommended_scenario"]].summary
    base_s = analysis_data["results"]["status_quo"].summary
    conv = analysis_data["conversion_opportunity"]
    top = conv.iloc[0]["specialty"] if len(conv) else "N/A"
    wait_gain = base_s["avg_wait_days"] - best_s["avg_wait_days"]

    cards = [
        ("Le probleme", "Les parcours ambulatoires sont fragmentes : consultations, examens et actes disperses, des delais d'attente longs et des capacites mal utilisees."),
        ("Les donnees", "Toutes les donnees viennent de vos saisies : file active, taux de fragmentation, capacite HDJ, tarifs et delais."),
        ("Les agents", "Des agents autonomes representent les patients, le triage organisationnel, l'ordonnanceur des capacites et l'evaluateur medico-economique."),
        ("La simulation", "Trois scenarios sont rejoues : statu quo, optimisation des HDJ existants, et creation d'un nouvel HDJ dedie."),
        ("La recommandation", f"Scenario conseille : {rec['recommended_label']}. Specialite prioritaire : {str(top).capitalize()}."),
        ("L'impact", f"Gain d'attente estime : {wait_gain:+.1f} jours. Conversion HDJ portee a {best_s['hdj_conversion_rate'] * 100:.0f} %."),
    ]

    placeholder = st.empty()
    progress = st.progress(0)
    for i, (step, text) in enumerate(cards, start=1):
        placeholder.markdown(
            f"""
<div class="narr-card">
  <div class="narr-step">ETAPE {i} / {len(cards)}</div>
  <div class="narr-title">{step}</div>
  <div class="narr-text">{text}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        progress.progress(int(i / len(cards) * 100))
        time.sleep(8 if i < len(cards) else 4)


WIZ_STEPS = [
    "Choix de la spécialité",
    "Vos données",
    "Cartographie des parcours",
    "Création des agents",
    "Triage organisationnel",
    "Ordonnancement & capacité",
    "Évaluation médico-économique",
    "Recommandation",
]

WIZ_STEP_INTRO = {
    2: "L'agent lit vos données (et les extracts CHU s'ils sont disponibles) : volumes, fragmentation, calendrier d'arrivée, unités et facturation.",
    3: "Le système instancie des agents autonomes qui représentent chaque acteur du parcours ambulatoire.",
    4: "L'agent de triage oriente chaque patient vers le mode de prise en charge le plus pertinent.",
    5: "L'ordonnanceur affecte les patients aux capacités et vérifie qu'aucune ressource n'est saturée.",
    6: "L'évaluateur compare les scénarios sur l'attente, la conversion et l'impact financier.",
    7: "Synthèse : voici la décision conseillée et sa justification.",
}


def build_simulation_config(use_cfg_prefix: bool = False) -> SimulationConfig:
    """Build SimulationConfig from wizard/sidebar session state (+ optional CHU priors)."""
    mean_age = st.session_state.get("wiz_mean_age")
    visits = st.session_state.get("wiz_visits_per_patient")
    metabolic = float(st.session_state.get("wiz_metabolic_pct") or 0.0)
    data_backed = bool(st.session_state.get("wiz_data_backed"))
    if use_cfg_prefix:
        return SimulationConfig(
            total_patients=int(st.session_state["cfg_patients"]),
            fragmentation_pct=float(st.session_state["cfg_fragmentation_pct"]),
            hdj_eligible_pct=float(st.session_state["cfg_hdj_eligible_pct"]),
            avg_wait_days=int(st.session_state["cfg_avg_wait"]),
            avg_act_count=int(st.session_state["cfg_avg_acts"]),
            slot_duration_minutes=int(st.session_state["cfg_slot_duration"]),
            grouping_rate=float(st.session_state.get("cfg_grouping_rate", 0.35)),
            fragmented_tariff_eur=float(st.session_state["cfg_frag_tariff"]),
            hdj_tariff_eur=float(st.session_state["cfg_hdj_tariff"]),
            simulation_days=int(st.session_state["cfg_sim_days"]),
            focus_specialty=st.session_state.get("wiz_specialty"),
            hdj_unit_count=int(st.session_state["cfg_hdj_units"]),
            hdj_total_beds=int(st.session_state["cfg_hdj_beds"]),
            hdj_daily_slots=int(st.session_state["cfg_hdj_slots"]),
            hdj_exam_capacity_per_day=int(st.session_state["cfg_hdj_exams"]),
            hdj_setup_cost_per_slot=float(st.session_state["cfg_setup_cost"]),
            mean_age=float(mean_age) if mean_age is not None else None,
            visits_per_patient=float(visits) if visits is not None else None,
            metabolic_cohort_pct=metabolic if data_backed else 0.0,
            data_backed=data_backed,
        )
    return SimulationConfig(
        total_patients=int(st.session_state["wiz_patients"]),
        fragmentation_pct=float(st.session_state["wiz_fragmentation_pct"]),
        hdj_eligible_pct=float(st.session_state["wiz_hdj_eligible_pct"]),
        avg_wait_days=int(st.session_state["wiz_avg_wait"]),
        avg_act_count=int(st.session_state["wiz_avg_acts"]),
        slot_duration_minutes=int(st.session_state["wiz_slot"]),
        grouping_rate=float(st.session_state.get("cfg_grouping_rate", 0.35)),
        fragmented_tariff_eur=float(st.session_state["wiz_frag"]),
        hdj_tariff_eur=float(st.session_state["wiz_hdj"]),
        simulation_days=int(st.session_state["wiz_days"]),
        focus_specialty=st.session_state["wiz_specialty"],
        hdj_unit_count=int(st.session_state["wiz_hdj_units"]),
        hdj_total_beds=int(st.session_state["wiz_hdj_beds"]),
        hdj_daily_slots=int(st.session_state["wiz_hdj_slots"]),
        hdj_exam_capacity_per_day=int(st.session_state["wiz_hdj_exams"]),
        hdj_setup_cost_per_slot=float(st.session_state["wiz_setup_cost"]),
        mean_age=float(mean_age) if mean_age is not None else None,
        visits_per_patient=float(visits) if visits is not None else None,
        metabolic_cohort_pct=metabolic if data_backed else 0.0,
        data_backed=data_backed,
    )


def _wiz_value(key: str, default: int, *, lo: int, hi: int) -> int:
    """Safe numeric default for form widgets (clamps stale session values)."""
    raw = st.session_state.get(key, default)
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = default
    return max(lo, min(hi, val))


def wizard_config() -> SimulationConfig:
    return build_simulation_config(use_cfg_prefix=False)


@st.cache_data(show_spinner="Chargement des extracts CHU…")
def cached_hospital_snapshot():
    return compute_hospital_snapshot()


@st.cache_data(show_spinner=False)
def cached_specialty_priors(specialty: str):
    return compute_specialty_priors(specialty)


def render_chu_data_panels(specialty: str | None) -> None:
    """Medium-value charts from documents/data extracts."""
    if not data_dir_available():
        st.info("Aucun fichier Excel trouvé dans `documents/data`.")
        return

    snap = cached_hospital_snapshot()
    if snap is None:
        st.warning("Impossible de lire les extracts CHU.")
        return

    st.markdown("### Données CHU (consultations externes)")
    st.caption(
        f"{snap.total_rows:,} lignes · {snap.total_patients:,} patients · "
        f"période {snap.period_start} → {snap.period_end} · "
        f"{snap.n_patients_multi_specialty} patients multi-spécialités. "
        "Ces extractions ne sont pas des séjours HDJ."
    )

    # Demand ranking
    st.markdown("#### Demande par spécialité (extracts)")
    fig_demand = px.bar(
        snap.demand_ranking,
        x="label",
        y="patients",
        text="patients",
        labels={"label": "", "patients": "Patients uniques"},
        color_discrete_sequence=[C_PRIMARY],
    )
    fig_demand.update_traces(textposition="outside")
    fig_demand.update_layout(height=280, showlegend=False)
    st.plotly_chart(style_chart(fig_demand), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Arrivées par jour")
        fig_dow = px.bar(
            snap.arrival_by_dow,
            x="jour",
            y="passages",
            labels={"jour": "", "passages": "Passages"},
            color_discrete_sequence=[C_ACCENT],
        )
        fig_dow.update_layout(height=260, showlegend=False)
        st.plotly_chart(style_chart(fig_dow), use_container_width=True)
    with c2:
        st.markdown("#### Arrivées par heure")
        fig_h = px.bar(
            snap.arrival_by_hour,
            x="heure",
            y="passages",
            labels={"heure": "Heure", "passages": "Passages"},
            color_discrete_sequence=[C_PRIMARY_MID],
        )
        fig_h.update_layout(height=260, showlegend=False)
        st.plotly_chart(style_chart(fig_h), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### Mix NGAP (facturation)")
        ngap = snap.ngap_by_extract.copy()
        ngap = ngap[ngap["ngap"] != "MISSING"]
        if len(ngap):
            fig_ngap = px.bar(
                ngap,
                x="label",
                y="count",
                color="ngap",
                labels={"label": "", "count": "Cotations", "ngap": "NGAP"},
                color_discrete_sequence=CHART_SEQUENCE + [C_ACCENT, C_PRIMARY_LIGHT],
            )
            fig_ngap.update_layout(height=300)
            st.plotly_chart(style_chart(fig_ngap), use_container_width=True)
        else:
            st.caption("Pas de cotations NGAP exploitables.")
    with c4:
        st.markdown("#### Unités les plus fréquentes")
        fig_u = px.bar(
            snap.top_units_global.sort_values("passages"),
            x="passages",
            y="unite",
            orientation="h",
            labels={"unite": "", "passages": "Passages"},
            color_discrete_sequence=[C_PRIMARY],
        )
        fig_u.update_layout(height=300, showlegend=False)
        st.plotly_chart(style_chart(fig_u), use_container_width=True)

    if len(snap.overlap_pairs):
        st.markdown("#### Chevauchements multi-spécialités")
        st.caption(
            "Patients présents dans au moins deux extracts — signal de parcours transverses."
        )
        ov = snap.overlap_pairs.head(8).copy()
        ov["paire"] = ov["a"] + " ↔ " + ov["b"]
        fig_o = px.bar(
            ov,
            x="patients",
            y="paire",
            orientation="h",
            labels={"paire": "", "patients": "Patients"},
            color_discrete_sequence=[C_ACCENT],
        )
        fig_o.update_layout(height=280, showlegend=False)
        st.plotly_chart(style_chart(fig_o), use_container_width=True)

    # Specialty-specific callouts
    if specialty and specialty_has_extract(specialty):
        priors = cached_specialty_priors(specialty)
        if priors.has_data:
            st.markdown(f"#### Focus — {format_specialty(specialty)}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Patients extract", f"{priors.n_patients}")
            m2.metric("Âge moyen", f"{priors.mean_age:.0f} ans")
            m3.metric("Visites / patient", f"{priors.visits_per_patient:.2f}")
            m4.metric("Multi-spécialité", f"{priors.cross_specialty_patients}")
            if specialty == "diabetologie" and priors.metabolic_patients:
                st.info(
                    f"**Cohorte métabolique urgences :** {priors.metabolic_patients} patients "
                    f"({priors.metabolic_pct:.0f} %) avec diagnostic diabète / hypoglycémie / "
                    f"hypokaliémie — base du cas d'usage HDJ diabétique complexe. "
                    f"Période {priors.period_start} → {priors.period_end}."
                )
            if priors.top_units:
                st.caption(
                    "Unités principales : "
                    + ", ".join(f"{u} ({c})" for u, c in priors.top_units[:4])
                )


def render_wizard_header(step: int, chip_html: str) -> None:
    chip_part = f" {chip_html}" if chip_html else ""
    render_html(
        f"""
<div class="assistant-shell">
  <div class="assistant-topbar">
    <div class="assistant-brand">
      {logo_img()}
      HDJ Agent
    </div>
    <div class="assistant-meta">Étape {step + 1} / {len(WIZ_STEPS)}{chip_part}</div>
  </div>
  <div class="assistant-step-title">{WIZ_STEPS[step]}</div>
</div>
"""
    )


def render_wizard() -> None:
    st.markdown(
        """
<style>
.block-container:has(.wizard-active) {
    max-width: 1040px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: min(6vh, 56px) !important;
    padding-bottom: min(6vh, 56px) !important;
}
.block-container:has(.wizard-active) [data-testid="stButton"] button {
    font-size: 0.95rem;
    min-height: 2.65rem;
}
</style>
<div class="wizard-active" aria-hidden="true"></div>
""",
        unsafe_allow_html=True,
    )

    step = st.session_state["wizard_step"]
    last = len(WIZ_STEPS) - 1
    specialty = st.session_state.get("wiz_specialty")
    chip_html = (
        f'<span class="specialty-chip">{format_specialty(specialty)}</span>'
        if specialty and step > 0
        else ""
    )

    render_wizard_header(step, chip_html)
    st.progress(step / last)

    # Step 0: specialty first
    if step == 0:
        chu_ok = data_dir_available()
        msg = (
            "Commencez par <strong>choisir la spécialité</strong> à analyser. "
            "Toute l'analyse (file active, parcours, capacité HDJ) portera sur ce périmètre."
        )
        if chu_ok:
            msg += (
                " Les spécialités liées aux extracts CHU préremplissent volumes et profils "
                "à l'étape suivante."
            )
        render_html(
            f'<div class="assistant-msg">{msg}</div>'
            '<div class="specialty-choose-heading">Choisir</div>'
            '<div class="specialty-picker" aria-hidden="true"></div>'
        )
        cols = st.columns(len(SPECIALTIES))
        for col, spec in zip(cols, SPECIALTIES):
            icon, blurb = SPECIALTY_META[spec]
            badge = ""
            if specialty_has_extract(spec) and chu_ok:
                pri = cached_specialty_priors(spec)
                if pri.has_data:
                    badge = f"\n📊 {pri.n_patients} patients CHU"
            with col:
                if st.button(
                    f"{icon}\n{format_specialty(spec)}\n{blurb}{badge}",
                    key=f"pick_{spec}",
                    use_container_width=True,
                    type="secondary",
                ):
                    st.session_state["wiz_specialty"] = spec
                    apply_priors_to_session(st.session_state, spec)
                    st.session_state["wizard_step"] = 1
                    save_inputs(st.session_state)
                    st.rerun()
        return

    # Step 1: remaining inputs (specialty already chosen)
    if step == 1:
        if not specialty:
            st.session_state["wizard_step"] = 0
            st.rerun()
        focus_label = format_specialty(specialty)
        data_backed = bool(st.session_state.get("wiz_data_backed"))
        if data_backed:
            period = st.session_state.get("wiz_period", "")
            note = st.session_state.get("wiz_data_note", "")
            render_html(
                f'<div class="assistant-msg">Spécialité : <strong>{focus_label}</strong> — '
                f"champs préremplis depuis les <strong>extracts CHU</strong>"
                f"{f' ({period})' if period else ''}. "
                "Ajustez si besoin ; les tarifs restent à votre charge.</div>"
            )
            if note:
                st.caption(note)
            if st.button("Recharger les suggestions CHU"):
                apply_priors_to_session(st.session_state, specialty)
                save_inputs(st.session_state)
                st.rerun()
        else:
            render_html(
                f'<div class="assistant-msg">Spécialité sélectionnée : <strong>{focus_label}</strong> — '
                "renseignez les données pour cette spécialité. "
                "Aucun extract CHU n'est lié à ce périmètre (saisie manuelle).</div>"
            )
        if st.button("← Changer de spécialité"):
            st.session_state["wizard_step"] = 0
            st.rerun()
        with st.form("wiz_form"):
            st.markdown("**File active & parcours**")
            c1, c2 = st.columns(2)
            with c1:
                patients = st.number_input(
                    "Nombre de patients (file active)", 50, 3000,
                    _wiz_value("wiz_patients", 100, lo=50, hi=3000), 10,
                    help="Patients ambulatoires sur la période analysée (prérempli si extract CHU).",
                )
                fragmentation_pct = st.number_input(
                    "Parcours fragmentés (%)", 1, 100,
                    _wiz_value("wiz_fragmentation_pct", 50, lo=1, hi=100), 1,
                    help="Part des patients avec actes dispersés (consultation, examen, soin séparés).",
                )
                avg_wait = st.number_input(
                    "Délai moyen d'attente actuel (jours)", 1, 120,
                    _wiz_value("wiz_avg_wait", 30, lo=1, hi=120), 1,
                )
                avg_acts = st.number_input(
                    "Nombre moyen d'actes par patient", 2, 10,
                    _wiz_value("wiz_avg_acts", 3, lo=2, hi=10), 1,
                )
            with c2:
                hdj_eligible_pct = st.number_input(
                    "Patients convertibles en HDJ (%)", 1, 100,
                    _wiz_value("wiz_hdj_eligible_pct", 30, lo=1, hi=100), 1,
                    help="Part de la file pouvant être regroupée en hospitalisation de jour.",
                )
                days = st.selectbox(
                    "Horizon d'analyse (jours)", [14, 30, 60],
                    index=[14, 30, 60].index(st.session_state.get("wiz_days", 30))
                    if st.session_state.get("wiz_days", 30) in (14, 30, 60)
                    else 1,
                )
                slot = st.selectbox(
                    "Durée moyenne d'un créneau (min)", [20, 30, 45, 60],
                    index=[20, 30, 45, 60].index(st.session_state.get("wiz_slot", 30))
                    if st.session_state.get("wiz_slot", 30) in (20, 30, 45, 60)
                    else 1,
                )
                if data_backed:
                    st.metric(
                        "Âge moyen (extract)",
                        f"{float(st.session_state.get('wiz_mean_age') or 0):.0f} ans",
                    )
                    st.metric(
                        "Visites / patient (extract)",
                        f"{float(st.session_state.get('wiz_visits_per_patient') or 0):.2f}",
                    )

            st.markdown("**Tarification**")
            t1, t2, t3 = st.columns(3)
            with t1:
                frag = st.number_input(
                    "Tarif — parcours fragmenté (€)",
                    min_value=0,
                    max_value=2000,
                    value=_wiz_value("wiz_frag", 0, lo=0, hi=2000),
                    step=10,
                    help="Obligatoire pour lancer l'analyse (> 0 €).",
                )
            with t2:
                hdj = st.number_input(
                    "Tarif — parcours HDJ (€)",
                    min_value=0,
                    max_value=2000,
                    value=_wiz_value("wiz_hdj", 0, lo=0, hi=2000),
                    step=10,
                    help="Obligatoire pour lancer l'analyse (> 0 €).",
                )
            with t3:
                setup_cost = st.number_input(
                    "Coût d'ouverture / créneau HDJ (€)",
                    min_value=0,
                    max_value=10000,
                    value=_wiz_value("wiz_setup_cost", 0, lo=0, hi=10000),
                    step=100,
                    help="Investissement structurel par créneau si vous créez un nouvel HDJ.",
                )

            st.markdown("**Capacité HDJ de l'établissement**")
            cap1, cap2 = st.columns(2)
            with cap1:
                hdj_units = st.number_input(
                    "Nombre d'unités HDJ", 1, 6,
                    _wiz_value("wiz_hdj_units", 1, lo=1, hi=6), 1,
                )
                hdj_beds = st.number_input(
                    "Places / lits HDJ (total)", 1, 100,
                    _wiz_value("wiz_hdj_beds", 1, lo=1, hi=100), 1,
                )
            with cap2:
                hdj_slots = st.number_input(
                    "Créneaux patients / jour (total)", 1, 200,
                    _wiz_value("wiz_hdj_slots", 1, lo=1, hi=200), 1,
                )
                hdj_exams = st.number_input(
                    "Examens techniques / jour", 1, 100,
                    _wiz_value("wiz_hdj_exams", 1, lo=1, hi=100), 1,
                )

            submitted = st.form_submit_button(
                "Lancer l'analyse étape par étape", type="primary", use_container_width=True
            )
        if submitted:
            if hdj_eligible_pct > fragmentation_pct:
                st.error(
                    "Les patients convertibles en HDJ ne peuvent pas dépasser "
                    "le taux de parcours fragmentés."
                )
                return
            if frag <= 0 or hdj <= 0:
                st.error("Veuillez renseigner les tarifs fragmenté et HDJ (supérieurs à 0 €).")
                return
            st.session_state["wiz_patients"] = int(patients)
            st.session_state["wiz_fragmentation_pct"] = float(fragmentation_pct)
            st.session_state["wiz_hdj_eligible_pct"] = float(hdj_eligible_pct)
            st.session_state["wiz_avg_wait"] = int(avg_wait)
            st.session_state["wiz_avg_acts"] = int(avg_acts)
            st.session_state["wiz_hdj_units"] = int(hdj_units)
            st.session_state["wiz_hdj_beds"] = int(hdj_beds)
            st.session_state["wiz_hdj_slots"] = int(hdj_slots)
            st.session_state["wiz_hdj_exams"] = int(hdj_exams)
            st.session_state["wiz_slot"] = int(slot)
            st.session_state["wiz_days"] = int(days)
            st.session_state["wiz_frag"] = int(frag)
            st.session_state["wiz_hdj"] = int(hdj)
            st.session_state["wiz_setup_cost"] = int(setup_cost)
            st.session_state["wizard_step"] = 2
            save_inputs(st.session_state)
            st.rerun()
        return

    # Steps 2+: run analysis and reveal one stage at a time
    cfg = wizard_config()
    with st.spinner("L'agent travaille…"):
        wa = load_analysis(config_cache_key(cfg))
    store_last_analysis(wa)
    wresults = wa["results"]
    wrec = wa["recommendation"]
    wbk = wrec["recommended_scenario"]
    wbest = wresults[wbk].summary
    wbase = wresults["status_quo"].summary
    wconv = wa["conversion_opportunity"]
    wcomp = wa["comparison"]

    intro = WIZ_STEP_INTRO.get(step, "")
    if intro:
        render_html(f'<div class="assistant-msg">{intro}</div>')

    if step == 2:
        source_patients = load_hospital_data(cfg).patients
        total = len(source_patients)
        global_frag_count = int(source_patients["is_fragmented"].sum())
        frag_rate = global_frag_count / max(total, 1) * 100
        focus = st.session_state.get("wiz_specialty", SPECIALTIES[0])
        spec_stats = (
            source_patients.groupby("specialty", as_index=False)
            .agg(
                total_patients=("patient_id", "count"),
                fragmented=("is_fragmented", "sum"),
            )
        )
        spec_stats["fragmentation_pct"] = (
            spec_stats["fragmented"] / spec_stats["total_patients"] * 100
        ).round(1)
        focus_row = spec_stats[spec_stats["specialty"] == focus]
        focus_count = int(focus_row.iloc[0]["total_patients"]) if len(focus_row) else 0
        focus_frag_n = int(focus_row.iloc[0]["fragmented"]) if len(focus_row) else 0
        focus_frag = float(focus_row.iloc[0]["fragmentation_pct"]) if len(focus_row) else 0.0

        m1, m2, m3 = st.columns(3)
        m1.metric("Patients analysés", f"{total}")
        m2.metric(
            "Parcours fragmentés (global)",
            f"{frag_rate:.0f} %",
            f"{global_frag_count} / {total} patients",
        )
        m3.metric(
            f"Votre spécialité — {format_specialty(focus)}",
            f"{focus_frag:.0f} % fragmentés",
            f"{focus_frag_n} / {focus_count} patients",
        )
        if cfg.data_backed:
            meta_n = (
                int(source_patients["metabolic_cohort"].sum())
                if "metabolic_cohort" in source_patients.columns
                else 0
            )
            src = st.session_state.get("wiz_period", "extracts CHU")
            st.success(
                f"Paramètres ancrés sur les extracts CHU ({src})"
                + (f" · cohorte métabolique simulée : {meta_n} patients" if meta_n else "")
            )
        fig = px.bar(
            spec_stats.sort_values("fragmentation_pct", ascending=False),
            x="specialty",
            y="fragmentation_pct",
            color="specialty",
            color_discrete_map={
                s: (C_PRIMARY if s == focus else C_PRIMARY_LIGHT) for s in SPECIALTIES
            },
            labels={"specialty": "", "fragmentation_pct": "Fragmentation (%)"},
        )
        fig.update_layout(showlegend=False, height=260)
        st.plotly_chart(style_chart(fig), use_container_width=True)
        st.caption(
            f"Volume total : {total} patients · "
            f"**{format_specialty(focus)}** : {focus_frag_n} parcours fragmentés "
            f"sur {focus_count} patients ({focus_frag:.0f} %)."
        )
        with st.expander("Comment ce taux est calculé ?", expanded=False):
            hdj_eligible_count = int(source_patients["hdj_eligible"].sum())
            guidance = fragmentation_decision_guidance(
                frag_pct=float(cfg.fragmentation_pct),
                eligible_pct=float(cfg.hdj_eligible_pct),
                frag_count=global_frag_count,
                eligible_count=hdj_eligible_count,
                total=total,
                wait_days=int(cfg.avg_wait_days),
            )
            st.markdown(
                f"""
Les chiffres affichés reprennent **vos saisies** (préremplies depuis le CHU si disponible) :

- **{int(cfg.fragmentation_pct)} %** de parcours fragmentés → {global_frag_count} patients sur {total}
- **{int(cfg.hdj_eligible_pct)} %** convertibles en HDJ → {hdj_eligible_count} patients
- **{cfg.avg_wait_days} jours** de délai moyen · **{cfg.avg_act_count} actes** en moyenne par patient
- Spécialité : **{format_specialty(focus)}**

**Formule :** `taux = patients fragmentés ÷ patients total × 100`

{guidance}
                """
            )

        render_chu_data_panels(focus)

    elif step == 3:
        agents = [
            ("Agents patients", "Chaque patient porte sa spécialité, sa complexité et son besoin de coordination."),
            ("Agents ressources / HDJ", "Les HDJ et salles portent leurs contraintes de capacité et de créneaux."),
            ("Agent de triage", "Oriente les parcours : fragmenté, HDJ existant ou nouvel HDJ."),
            ("Agent ordonnanceur", "Lisse les flux et affecte les capacités disponibles."),
            ("Agent évaluateur", "Estime l'impact médico-économique de chaque scénario."),
        ]
        for title, desc in agents:
            st.markdown(f"**{title}** — {desc}")

    elif step == 4:
        frag, ex, new = flow_counts(wbest)
        total = max(frag + ex + new, 1)
        m1, m2, m3 = st.columns(3)
        m1.metric("Parcours fragmentés", f"{frag}")
        m2.metric("HDJ existant", f"{ex}")
        m3.metric("Nouveau HDJ", f"{new}")
        st.caption(f"{(ex + new) / total * 100:.0f} % des patients sont orientés vers un parcours HDJ.")
        st.plotly_chart(sankey_chart(wbest), use_container_width=True)

    elif step == 5:
        m1, m2 = st.columns(2)
        m1.metric(
            "Attente moyenne", f"{wbest['avg_wait_days']:.1f} j",
            f"{wbest['avg_wait_days'] - wbase['avg_wait_days']:+.1f} j vs statu quo",
        )
        m2.metric("Saturation max", f"{wbest['max_resource_saturation'] * 100:.0f} %")
        st.plotly_chart(gauge_chart(wbest["max_resource_saturation"] * 100, "Saturation des ressources"), use_container_width=True)
        if wbest["max_resource_saturation"] >= 0.85:
            st.warning("Vigilance : une ressource dépasse 85 %. Prévoir capacité ou lissage.")
        else:
            st.success("Capacité soutenable : aucune ressource ne dépasse 85 %.")

    elif step == 6:
        rec_scenario = wrec["recommended_scenario"]
        rec_row = wcomp[wcomp["scenario"] == rec_scenario].iloc[0]
        sq_row = wcomp[wcomp["scenario"] == "status_quo"].iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Gain net recommandé", format_eur(rec_row["net_gain_eur"]), "vs statu quo")
        m2.metric("Investissement structurel", format_eur(rec_row["investment_eur"]))
        m3.metric("Conversion HDJ", f"{wbest['hdj_conversion_rate'] * 100:.0f} %")
        fig = px.bar(
            wcomp,
            x="scenario_label",
            y="net_gain_eur",
            color="scenario_label",
            color_discrete_sequence=CHART_SEQUENCE,
            labels={"scenario_label": "", "net_gain_eur": "Gain net vs statu quo (€)"},
        )
        fig.update_layout(showlegend=False, height=260)
        st.plotly_chart(style_chart(fig), use_container_width=True)
        st.caption(
            "Le gain net = revenus hospitaliers supplémentaires − coût d'ouverture d'un nouveau HDJ. "
            f"Le statu quo génère {format_eur(sq_row['total_revenue_eur'])} de revenus — "
            "c'est moins que les scénarios HDJ, mais sans réorganisation."
        )

    elif step == 7:
        focus = st.session_state.get("wiz_specialty", SPECIALTIES[0])
        st.success(f"Décision conseillée : **{wrec['recommended_label']}**")
        st.markdown(f"Spécialité étudiée : **{format_specialty(focus)}**.")
        for reason in wrec["reasons"]:
            st.markdown(f"- {reason}")
        if wrec["recommended_scenario"] == "new_hdj" and wrec["proposed_hdj_specialty"]:
            st.info(
                f"Création d'un HDJ dédié à **{format_specialty(wrec['proposed_hdj_specialty'])}** "
                f"({wrec.get('proposed_hdj_slots', 0)} créneaux/jour · "
                f"investissement estimé {format_eur(wrec['proposed_hdj_slots'] * cfg.hdj_setup_cost_per_slot)})."
            )
        elif wrec["recommended_scenario"] == "optimize_existing":
            st.info(
                "Pas de nouvelle unité : maximiser les HDJ déjà en place "
                f"pour **{format_specialty(focus)}**."
            )

    # Navigation
    prev_col, next_col = st.columns(2)
    with prev_col:
        if step > 2 and st.button("← Étape précédente", use_container_width=True):
            st.session_state["wizard_step"] = step - 1
            st.rerun()
        elif step == 2 and st.button("← Modifier mes données", use_container_width=True):
            st.session_state["wizard_step"] = 1
            st.rerun()
    with next_col:
        if step < last:
            if st.button("Étape suivante →", type="primary", use_container_width=True):
                st.session_state["wizard_step"] = step + 1
                st.rerun()
        else:
            if st.button("← Retour à l'accueil", type="primary", use_container_width=True):
                sync_wiz_to_cfg(st.session_state)
                save_inputs(st.session_state)
                st.session_state["entered"] = False
                st.session_state["wizard_step"] = 0
                st.rerun()

    if step >= 2 and st.button("Recommencer (changer spécialité ou données)"):
        st.session_state["wizard_step"] = 0
        st.rerun()


if not st.session_state["splash_done"]:
    render_splash()
    st.session_state["splash_done"] = True

if not st.session_state["entered"]:
    render_landing_page()
    st.stop()

# --- Guided wizard ---
st.session_state.setdefault("wizard_step", 0)
render_wizard()
