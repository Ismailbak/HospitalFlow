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

import src.data
import src.agents
import src.simulation
import src.metrics

from src.data import (
    SCENARIO_LABELS,
    SPECIALTIES,
    SimulationConfig,
    load_hospital_data,
)
from src.metrics import run_full_analysis

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
def load_analysis(_config: SimulationConfig, _version: int = 5):
    return run_full_analysis(load_hospital_data(_config))


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
    2: "L'agent lit vos données et reconstruit les parcours réels : combien de patients, quelle fragmentation, quelle spécialité.",
    3: "Le système instancie des agents autonomes qui représentent chaque acteur du parcours ambulatoire.",
    4: "L'agent de triage oriente chaque patient vers le mode de prise en charge le plus pertinent.",
    5: "L'ordonnanceur affecte les patients aux capacités et vérifie qu'aucune ressource n'est saturée.",
    6: "L'évaluateur compare les scénarios sur l'attente, la conversion et l'impact financier.",
    7: "Synthèse : voici la décision conseillée et sa justification.",
}


def build_simulation_config(use_cfg_prefix: bool = False) -> SimulationConfig:
    """Build SimulationConfig entirely from wizard or sidebar session state."""
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
        render_html(
            '<div class="assistant-msg">Commencez par <strong>choisir la spécialité</strong> à analyser. '
            "Toute l'analyse (file active, parcours, capacité HDJ) portera sur ce périmètre.</div>"
            '<div class="specialty-choose-heading">Choisir</div>'
            '<div class="specialty-picker" aria-hidden="true"></div>'
        )
        cols = st.columns(len(SPECIALTIES))
        for col, spec in zip(cols, SPECIALTIES):
            icon, blurb = SPECIALTY_META[spec]
            with col:
                if st.button(
                    f"{icon}\n{format_specialty(spec)}\n{blurb}",
                    key=f"pick_{spec}",
                    use_container_width=True,
                    type="secondary",
                ):
                    st.session_state["wiz_specialty"] = spec
                    st.session_state["wizard_step"] = 1
                    st.rerun()
        return

    # Step 1: remaining inputs (specialty already chosen)
    if step == 1:
        if not specialty:
            st.session_state["wizard_step"] = 0
            st.rerun()
        focus_label = format_specialty(specialty)
        render_html(
            f'<div class="assistant-msg">Spécialité sélectionnée : <strong>{focus_label}</strong> — '
            "renseignez maintenant les données pour cette spécialité. "
            "Tous les champs concernent <strong>vos chiffres réels</strong> (aucune donnée fictive).</div>"
        )
        if st.button("← Changer de spécialité"):
            st.session_state["wizard_step"] = 0
            st.rerun()
        with st.form("wiz_form"):
            st.markdown("**File active & parcours**")
            c1, c2 = st.columns(2)
            with c1:
                patients = st.number_input(
                    "Nombre de patients (file active)", 50, 2000,
                    int(st.session_state.get("wiz_patients", 100)), 10,
                    help="Patients ambulatoires sur la période analysée.",
                )
                fragmentation_pct = st.number_input(
                    "Parcours fragmentés (%)", 1, 100,
                    int(st.session_state.get("wiz_fragmentation_pct", 50)), 1,
                    help="Part des patients avec actes dispersés (consultation, examen, soin séparés).",
                )
                avg_wait = st.number_input(
                    "Délai moyen d'attente actuel (jours)", 1, 120,
                    int(st.session_state.get("wiz_avg_wait", 30)), 1,
                )
                avg_acts = st.number_input(
                    "Nombre moyen d'actes par patient", 2, 10,
                    int(st.session_state.get("wiz_avg_acts", 3)), 1,
                )
            with c2:
                hdj_eligible_pct = st.number_input(
                    "Patients convertibles en HDJ (%)", 1, 100,
                    int(st.session_state.get("wiz_hdj_eligible_pct", 30)), 1,
                    help="Part de la file pouvant être regroupée en hospitalisation de jour.",
                )
                days = st.selectbox(
                    "Horizon d'analyse (jours)", [14, 30, 60],
                    index=[14, 30, 60].index(st.session_state.get("wiz_days", 30)),
                )
                slot = st.selectbox(
                    "Durée moyenne d'un créneau (min)", [20, 30, 45, 60],
                    index=[20, 30, 45, 60].index(st.session_state.get("wiz_slot", 30)),
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
                    int(st.session_state.get("wiz_hdj_units", 1)), 1,
                )
                hdj_beds = st.number_input(
                    "Places / lits HDJ (total)", 1, 100,
                    int(st.session_state.get("wiz_hdj_beds", 1)), 1,
                )
            with cap2:
                hdj_slots = st.number_input(
                    "Créneaux patients / jour (total)", 1, 200,
                    int(st.session_state.get("wiz_hdj_slots", 1)), 1,
                )
                hdj_exams = st.number_input(
                    "Examens techniques / jour", 1, 100,
                    int(st.session_state.get("wiz_hdj_exams", 1)), 1,
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
            st.rerun()
        return

    # Steps 2+: run analysis and reveal one stage at a time
    cfg = wizard_config()
    with st.spinner("L'agent travaille…"):
        wa = load_analysis(cfg)
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
        with st.expander("Comment ce taux est calculé ?", expanded=True):
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
Les chiffres affichés reprennent **exactement vos saisies** :

- **{int(cfg.fragmentation_pct)} %** de parcours fragmentés → {global_frag_count} patients sur {total}
- **{int(cfg.hdj_eligible_pct)} %** convertibles en HDJ → {hdj_eligible_count} patients
- **{cfg.avg_wait_days} jours** de délai moyen · **{cfg.avg_act_count} actes** en moyenne par patient
- Spécialité : **{format_specialty(focus)}**

**Formule :** `taux = patients fragmentés ÷ patients total × 100`

{guidance}

Aucune donnée aléatoire ni jeu de démonstration n'est injecté.
                """
            )

    elif step == 3:
        agents = [
            ("👤 Agents patients", "Chaque patient porte sa spécialité, sa complexité et son besoin de coordination."),
            ("🏥 Agents ressources / HDJ", "Les HDJ et salles portent leurs contraintes de capacité et de créneaux."),
            ("🔀 Agent de triage", "Oriente les parcours : fragmenté, HDJ existant ou nouvel HDJ."),
            ("📅 Agent ordonnanceur", "Lisse les flux et affecte les capacités disponibles."),
            ("💶 Agent évaluateur", "Estime l'impact médico-économique de chaque scénario."),
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
            if st.button("Voir le tableau de bord détaillé →", type="primary", use_container_width=True):
                for src, dst in [
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
                ]:
                    st.session_state[dst] = st.session_state[src]
                st.session_state["wizard_done"] = True
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

# --- Guided wizard gate ---
st.session_state.setdefault("wizard_done", False)
st.session_state.setdefault("wizard_step", 0)
if not st.session_state["wizard_done"]:
    render_wizard()
    st.stop()

# --- Sidebar config defaults (pre-filled by the wizard) ---
for _k, _v in {
    "cfg_grouping_rate": 0.35,
}.items():
    st.session_state.setdefault(_k, _v)

if st.session_state.get("wizard_done") and "cfg_patients" not in st.session_state:
    st.warning("Relancez l'analyse guidée pour charger vos données.")
    st.session_state["wizard_done"] = False
    st.rerun()

# --- Sidebar: assumptions ---
st.sidebar.image(str(_LOGO_PATH), width=72)
st.sidebar.title("Assistant HDJ")
if st.sidebar.button("← Retour à l'accueil", use_container_width=True):
    st.session_state["entered"] = False
    st.rerun()
if st.sidebar.button("↻ Relancer l'analyse guidée", use_container_width=True):
    st.session_state["wizard_done"] = False
    st.session_state["wizard_step"] = 0
    st.rerun()
use_case = st.sidebar.radio(
    "Choisissez votre cas d'usage",
    [
        "Arbitrer une création HDJ",
        "Réduire les délais",
        "Prioriser une spécialité",
        "Préparer une présentation",
    ],
    help="Le tableau de bord adapte le parcours recommandé selon votre objectif.",
)

st.sidebar.markdown("### Questions rapides")
main_issue = st.sidebar.selectbox(
    "Quel problème voulez-vous traiter en premier ?",
    [
        "Délais patients trop longs",
        "Saturation des ressources",
        "Parcours trop fragmentés",
        "Impact financier à démontrer",
    ],
)
decision_style = st.sidebar.radio(
    "Quel niveau d'ambition ?",
    ["Prudent", "Équilibré", "Ambitieux"],
    index=1,
    help="Prudent privilégie la capacité existante. Ambitieux favorise la transformation.",
)
focus_specialty = st.sidebar.selectbox(
    "Spécialité à regarder",
    ["Automatique", "oncologie", "cardiologie", "diabetologie", "nephrologie", "douleur_chronique"],
)

with st.sidebar.expander("Réglages avancés", expanded=False):
    st.caption("Issus de votre analyse guidée. Ajustez pour tester d'autres hypothèses.")
    st.markdown("**File active & parcours**")
    cfg_patients = st.number_input("Patients (file active)", 50, 2000, step=10, key="cfg_patients")
    cfg_fragmentation_pct = st.number_input("Parcours fragmentés (%)", 1, 100, step=1, key="cfg_fragmentation_pct")
    cfg_hdj_eligible_pct = st.number_input("Convertibles en HDJ (%)", 1, 100, step=1, key="cfg_hdj_eligible_pct")
    cfg_avg_wait = st.number_input("Délai moyen (jours)", 1, 120, step=1, key="cfg_avg_wait")
    cfg_avg_acts = st.number_input("Actes moyens / patient", 2, 10, step=1, key="cfg_avg_acts")
    st.markdown("**Capacité HDJ**")
    cfg_hdj_units = st.number_input("Unités HDJ", 1, 6, step=1, key="cfg_hdj_units")
    cfg_hdj_beds = st.number_input("Places / lits (total)", 1, 100, step=1, key="cfg_hdj_beds")
    cfg_hdj_slots = st.number_input("Créneaux / jour (total)", 1, 200, step=1, key="cfg_hdj_slots")
    cfg_hdj_exams = st.number_input("Examens / jour", 1, 100, step=1, key="cfg_hdj_exams")
    cfg_setup_cost = st.number_input("Coût ouverture / créneau (€)", 0, 10000, step=100, key="cfg_setup_cost")
    grouping_rate = st.slider(
        "Seuil de regroupement HDJ", 0.1, 0.9, step=0.05, key="cfg_grouping_rate",
        help="Plus le seuil est bas, plus le système regroupe facilement les patients en HDJ.",
    )
    slot_duration = st.selectbox("Durée créneau (minutes)", [20, 30, 45, 60], key="cfg_slot_duration")
    fragmented_tariff = st.number_input(
        "Tarif parcours fragmenté (€)", min_value=0, max_value=2000, step=10, key="cfg_frag_tariff",
    )
    hdj_tariff = st.number_input(
        "Tarif parcours HDJ (€)", min_value=0, max_value=2000, step=10, key="cfg_hdj_tariff",
    )
    sim_days = st.selectbox("Horizon simulation (jours)", [14, 30, 60], key="cfg_sim_days")

config = build_simulation_config(use_cfg_prefix=True)

with st.spinner("Simulation en cours…"):
    analysis = load_analysis(config)
store_last_analysis(analysis)

results = analysis["results"]
comparison = analysis["comparison"]
deltas = analysis["deltas"]
conversion = analysis["conversion_opportunity"]
recommendation = analysis["recommendation"]

best_key = recommendation["recommended_scenario"]
best = results[best_key].summary
baseline = results["status_quo"].summary


def default_step(case: str) -> str:
    if case == "Réduire les délais":
        return "Comparer les scénarios"
    if case == "Prioriser une spécialité":
        return "Prioriser la spécialité"
    if case == "Préparer une présentation":
        return "Synthèse comité"
    return "Décision guidée"


def flow_steps(case: str) -> list[str]:
    if case == "Réduire les délais":
        return [
            "1. Vérifier quel scénario réduit le plus l'attente.",
            "2. Contrôler que les ressources ne dépassent pas 85 % de saturation.",
            "3. Ajuster le volume ou la capacité si le scénario devient irréaliste.",
        ]
    if case == "Prioriser une spécialité":
        return [
            "1. Identifier la spécialité avec le plus de patients convertibles.",
            "2. Vérifier que ce volume justifie un HDJ dédié.",
            "3. Utiliser la comparaison pour défendre l'impact attendu.",
        ]
    if case == "Préparer une présentation":
        return [
            "1. Lire la décision proposée.",
            "2. Garder les 4 chiffres clés pour la slide de synthèse.",
            "3. Montrer les écarts vs statu quo et la spécialité prioritaire.",
        ]
    return [
        "1. Répondre aux questions dans la barre latérale.",
        "2. Lire la décision proposée ci-dessous.",
        "3. Vérifier capacité et spécialité avant de conclure.",
    ]


steps = [
    "Flux des agents",
    "Décision guidée",
    "Comparer les scénarios",
    "Vérifier la capacité",
    "Prioriser la spécialité",
    "Synthèse comité",
]
if st.session_state.get("seen_flux"):
    default_index = steps.index(default_step(use_case))
else:
    default_index = 0
    st.session_state["seen_flux"] = True
st.sidebar.markdown("### Parcours recommandé")
page = st.sidebar.radio("Étape à afficher", steps, index=default_index)

st.sidebar.markdown("### Ce que l'assistant va faire")
for step in flow_steps(use_case):
    st.sidebar.caption(step)

wait_improved = best["avg_wait_days"] < baseline["avg_wait_days"]
revenue_improved = best["total_revenue_eur"] > baseline["total_revenue_eur"]
capacity_ok = best["max_resource_saturation"] < 0.85
conversion_ok = best["hdj_conversion_rate"] > baseline["hdj_conversion_rate"]
top_spec = conversion.iloc[0]["specialty"] if len(conversion) else "N/A"
top_row = conversion.iloc[0] if len(conversion) else None

if focus_specialty != "Automatique":
    focused_conversion = conversion[conversion["specialty"] == focus_specialty]
else:
    focused_conversion = conversion.head(1)

render_workspace_header()

rail_col, main_col, right_col = st.columns([0.15, 0.60, 0.35], gap="large")

with rail_col:
    st.markdown(rail(page), unsafe_allow_html=True)

if page == "Flux des agents":
    summary = results[best_key].summary
    frag, ex, new = flow_counts(summary)
    total = max(frag + ex + new, 1)
    hdj_total = ex + new

    with main_col:
        st.markdown(
            f"""
            <div style="margin-bottom:12px;">
              <div class="greeting-title">Les agents en action</div>
              <div class="greeting-sub">Scénario : {SCENARIO_LABELS.get(best_key, best_key)} — chaque point est un patient orienté par l'agent de triage.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<span class="lane-chip"><span class="lane-dot" style="background:{LANE_COLOR["frag"]}"></span>Parcours fragmenté</span>'
            f'<span class="lane-chip"><span class="lane-dot" style="background:{LANE_COLOR["ex"]}"></span>HDJ existant</span>'
            f'<span class="lane-chip"><span class="lane-dot" style="background:{LANE_COLOR["new"]}"></span>Nouveau HDJ</span>',
            unsafe_allow_html=True,
        )

        anim = st.empty()
        dots = build_flow_dots((frag, ex, new))
        replay = st.button("🔄 Rejouer l'animation")
        frames = 30
        for f in range(frames + 1):
            anim.plotly_chart(flow_figure(dots, f / frames), use_container_width=True)
            time.sleep(0.045)
        _ = replay

        with st.container(border=True):
            st.markdown('<div class="card-eyebrow">Répartition finale des parcours</div>', unsafe_allow_html=True)
            st.plotly_chart(sankey_chart(summary), use_container_width=True)

    with right_col:
        st.markdown(
            f"""
            <div class="insight-card">
              <h3>Patients orientés</h3>
              <div class="flow-count" style="color:{LANE_COLOR['frag']} !important">{frag} <span class="muted">fragmentés</span></div>
              <div class="flow-count" style="color:{LANE_COLOR['ex']} !important">{ex} <span class="muted">HDJ existant</span></div>
              <div class="flow-count" style="color:{LANE_COLOR['new']} !important">{new} <span class="muted">nouveau HDJ</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="insight-card">
              <h3>Lecture</h3>
              <p class="muted"><b>{hdj_total / total * 100:.0f} %</b> des patients sont orientés vers un parcours HDJ
              dans le scénario recommandé, contre une prise en charge fragmentée au statu quo.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        next_step_box("ouvrez 'Décision guidée' pour la recommandation chiffrée.")

elif page == "Décision guidée":
    with main_col:
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
              <div>
                <div class="greeting-title">Bonjour, voici votre recommandation</div>
                <div class="greeting-sub">Cas d'usage : {use_case} — Problème : {main_issue}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        row1_left, row1_right = st.columns([0.62, 0.38], gap="medium")
        with row1_left:
            with st.container(border=True):
                st.markdown('<div class="card-eyebrow">Attente par scénario</div>', unsafe_allow_html=True)
                fig_wait = px.bar(
                    comparison,
                    x="scenario_label",
                    y="avg_wait_days",
                    color="scenario_label",
                    color_discrete_sequence=CHART_SEQUENCE,
                    labels={"scenario_label": "", "avg_wait_days": "Jours"},
                )
                fig_wait.update_layout(showlegend=False, height=260)
                st.plotly_chart(style_chart(fig_wait), use_container_width=True)
        with row1_right:
            impact = best["total_revenue_eur"] - baseline["total_revenue_eur"]
            st.markdown(
                f"""
                <div class="promo-card">
                  <div class="small">DÉCISION RECOMMANDÉE</div>
                  <div class="big">{recommendation['recommended_label']}</div>
                  <div class="tag">Impact estimé : {format_eur(impact)}</div>
                  <div class="tag">Attente : {best['avg_wait_days'] - baseline['avg_wait_days']:+.1f} j vs statu quo</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        row2_left, row2_right = st.columns(2, gap="medium")
        with row2_left:
            st.markdown(
                f"""
                <div class="dash-card">
                  <h3>Indicateurs clés</h3>
                  <div class="metric-grid">
                    {metric_card("Attente", f"{best['avg_wait_days']:.1f} j", f"{best['avg_wait_days'] - baseline['avg_wait_days']:+.1f} j")}
                    {metric_card("Conversion HDJ", f"{best['hdj_conversion_rate'] * 100:.1f} %", f"{(best['hdj_conversion_rate'] - baseline['hdj_conversion_rate']) * 100:+.1f} pts")}
                    {metric_card("Impact", format_eur(best["total_revenue_eur"] - baseline["total_revenue_eur"]), "vs statu quo")}
                    {metric_card("Saturation", f"{best['max_resource_saturation'] * 100:.1f} %", "seuil 85 %")}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with row2_right:
            st.markdown(
                f"""
                <div class="dash-card">
                  <h3>Checklist de décision</h3>
                  {check_row("Les délais baissent", wait_improved)}
                  {check_row("La valorisation augmente", revenue_improved)}
                  {check_row("La capacité reste sous 85 %", capacity_ok)}
                  {check_row("La fragmentation diminue", conversion_ok)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        row3_left, row3_right = st.columns([0.62, 0.38], gap="medium")
        with row3_left:
            with st.container(border=True):
                st.markdown('<div class="card-eyebrow">Conversion HDJ par scénario</div>', unsafe_allow_html=True)
                fig_conv = px.bar(
                    comparison,
                    x="scenario_label",
                    y="hdj_conversion_rate",
                    color="scenario_label",
                    color_discrete_sequence=CHART_SEQUENCE,
                    labels={"scenario_label": "", "hdj_conversion_rate": "%"},
                )
                fig_conv.update_layout(showlegend=False, height=240)
                st.plotly_chart(style_chart(fig_conv), use_container_width=True)
        with row3_right:
            with st.container(border=True):
                st.markdown('<div class="card-eyebrow">Saturation ressources</div>', unsafe_allow_html=True)
                st.plotly_chart(
                    gauge_chart(best["max_resource_saturation"] * 100, ""),
                    use_container_width=True,
                )

    with right_col:
        wait_pct = max(0, min((1 - best["avg_wait_days"] / max(baseline["avg_wait_days"], 1)) * 100, 100))
        conv_pct = best["hdj_conversion_rate"] * 100
        sat_pct = best["max_resource_saturation"] * 100
        st.markdown(
            f"""
            <div class="insight-card">
              <h3>Performance du scénario</h3>
              {progress_bar("Réduction d'attente", f"{wait_pct:.0f} %", wait_pct)}
              {progress_bar("Conversion HDJ", f"{conv_pct:.0f} %", conv_pct)}
              {progress_bar("Saturation ressources", f"{sat_pct:.0f} %", sat_pct)}
            </div>
            """,
            unsafe_allow_html=True,
        )

        colors = [C_PRIMARY, C_ACCENT, C_PRIMARY_MID, C_TEXT_MUTED, C_PRIMARY_LIGHT]
        rows_html = ""
        for i, (_, r) in enumerate(conversion.head(4).iterrows()):
            rows_html += list_row(
                str(r["specialty"])[:2].upper(),
                colors[i % len(colors)],
                str(r["specialty"]).capitalize(),
                f"{int(r['eligible_patients'])} patients éligibles",
                f"{r['conversion_share_pct']:.0f} %",
            )
        st.markdown(
            f"""
            <div class="insight-card">
              <h3>Spécialités prioritaires</h3>
              {rows_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        proposed = recommendation["proposed_hdj_specialty"] or top_spec
        st.markdown(
            f"""
            <div class="cta-card">
              <div class="crown">🏥</div>
              <div class="cta-title">Passer aux données réelles</div>
              <div class="muted">Priorité : {str(proposed).capitalize()}. Branchez les extracts PMSI / CCAM pour fiabiliser la décision.</div>
              <div class="cta-btn">Connecter les données</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif page == "Comparer les scénarios":
    with main_col:
        st.markdown(
            """
            <div class="dash-card">
              <h3>Comparaison des scénarios</h3>
              <p class="muted">Objectif : voir quel scénario réduit l'attente et améliore la conversion HDJ.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_wait = px.bar(
            comparison,
            x="scenario_label",
            y="avg_wait_days",
            color="scenario_label",
            title="Attente moyenne par scénario",
            labels={"scenario_label": "Scénario", "avg_wait_days": "Jours"},
        )
        fig_wait.update_layout(showlegend=False)
        st.plotly_chart(style_chart(fig_wait), use_container_width=True)

        fig_conv = px.bar(
            comparison,
            x="scenario_label",
            y="hdj_conversion_rate",
            color="scenario_label",
            title="Conversion HDJ par scénario",
            labels={"scenario_label": "Scénario", "hdj_conversion_rate": "%"},
        )
        fig_conv.update_layout(showlegend=False)
        st.plotly_chart(style_chart(fig_conv), use_container_width=True)

    with right_col:
        st.markdown(
            f"""
            <div class="insight-card">
              <h3>Lecture rapide</h3>
              {check_row("Le scénario recommandé baisse les délais", wait_improved)}
              {check_row("Le scénario recommandé augmente la conversion HDJ", conversion_ok)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        simple_table = comparison[
            ["scenario_label", "avg_wait_days", "hdj_conversion_rate", "max_saturation"]
        ].rename(
            columns={
                "scenario_label": "Scénario",
                "avg_wait_days": "Attente (j)",
                "hdj_conversion_rate": "Conversion (%)",
                "max_saturation": "Saturation (%)",
            }
        )
        st.dataframe(simple_table, use_container_width=True, hide_index=True)
        next_step_box("vérifiez maintenant la capacité pour confirmer la faisabilité.")

elif page == "Vérifier la capacité":
    scenario_cap = st.selectbox(
        "Scénario à contrôler",
        options=list(results.keys()),
        index=list(results.keys()).index(best_key),
        format_func=lambda x: SCENARIO_LABELS.get(x, x),
    )
    res_df = results[scenario_cap].resources
    hdj_df = results[scenario_cap].hdj_units
    max_sat = float(res_df["saturation"].max()) if len(res_df) else 0.0

    with main_col:
        st.markdown(
            f"""
            <div class="dash-card">
              <h3>Capacité et saturation</h3>
              <p class="muted">Scénario contrôlé : {SCENARIO_LABELS.get(scenario_cap, scenario_cap)}.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_sat = px.bar(
            res_df,
            x="label",
            y="saturation",
            color="label",
            title="Saturation des ressources",
            labels={"label": "Ressource", "saturation": "Saturation"},
        )
        fig_sat.add_hline(y=0.85, line_dash="dash", annotation_text="Seuil 85 %")
        fig_sat.update_layout(showlegend=False)
        st.plotly_chart(style_chart(fig_sat), use_container_width=True)
        st.dataframe(hdj_df, use_container_width=True, hide_index=True)

    with right_col:
        status = "Capacité acceptable" if max_sat < 0.85 else "Risque capacitaire"
        width = min(max_sat * 100, 100)
        st.markdown(
            f"""
            <div class="insight-card">
              <h3>{status}</h3>
              <div class="metric-value">{max_sat * 100:.1f} %</div>
              <div class="progress-track"><div class="progress-fill" style="width:{width:.0f}%"></div></div>
              <p class="muted">Seuil de vigilance : 85 %. Si le seuil est dépassé, prévoir plus de capacité ou lisser les flux.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        next_step_box("si la capacité est acceptable, priorisez maintenant la spécialité.")

elif page == "Prioriser la spécialité":
    chosen = focused_conversion.iloc[0] if len(focused_conversion) else None
    with main_col:
        st.markdown(
            """
            <div class="dash-card">
              <h3>Priorisation clinique</h3>
              <p class="muted">Objectif : identifier la spécialité avec le plus fort potentiel de regroupement en HDJ.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_opp = px.bar(
            conversion,
            x="specialty",
            y="conversion_share_pct",
            color="avg_wait",
            color_continuous_scale="Purples",
            title="Potentiel de conversion HDJ par spécialité",
            labels={
                "specialty": "Spécialité",
                "conversion_share_pct": "Patients éligibles (%)",
                "avg_wait": "Attente moyenne (j)",
            },
        )
        st.plotly_chart(style_chart(fig_opp), use_container_width=True)
        st.dataframe(conversion, use_container_width=True, hide_index=True)

    with right_col:
        if chosen is not None:
            st.markdown(
                f"""
                <div class="insight-card">
                  <h3>Priorité proposée</h3>
                  <div class="metric-value">{chosen['specialty']}</div>
                  <p class="muted">{int(chosen['eligible_patients'])} patients éligibles, soit {chosen['conversion_share_pct']:.1f} % de la file.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("Aucune donnée disponible pour la spécialité sélectionnée.")
        next_step_box("ouvrez la synthèse comité pour obtenir le message de restitution.")

elif page == "Synthèse comité":
    with main_col:
        st.markdown(
            f"""
            <div class="dash-card">
              <div class="decision-pill">Synthèse prête à présenter</div>
              <h3>Conclusion</h3>
              <div class="metric-value">{recommendation['recommended_label']}</div>
              <p class="muted">Basée sur les données que vous avez saisies dans l'analyse guidée.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="dash-card">
              <h3>Message à porter</h3>
              <div class="check-row check-ok">Gain d'attente estimé : {best['avg_wait_days'] - baseline['avg_wait_days']:+.1f} jours vs statu quo</div>
              <div class="check-row check-ok">Impact estimé : {format_eur(best['total_revenue_eur'] - baseline['total_revenue_eur'])}</div>
              <div class="check-row {'check-ok' if capacity_ok else 'check-warn'}">Saturation maximale : {best['max_resource_saturation'] * 100:.1f} %</div>
              <div class="check-row check-ok">Périmètre prioritaire : {recommendation['proposed_hdj_specialty'] or top_spec}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(
            f"""
            <div class="insight-card">
              <h3>Vos hypothèses</h3>
              <p class="muted">Patients : {config.total_patients}</p>
              <p class="muted">Fragmentation : {config.fragmentation_pct:.0f} %</p>
              <p class="muted">Convertibles HDJ : {config.hdj_eligible_pct:.0f} %</p>
              <p class="muted">Capacité : {config.hdj_daily_slots} créneaux/j · {config.hdj_total_beds} lits</p>
              <p class="muted">Spécialité : {format_specialty(config.focus_specialty or '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if capacity_ok:
            st.success("La simulation soutient la recommandation.")
        else:
            st.warning("La capacité est le point de vigilance avant passage à l'échelle.")
