"""HDJ Agent MVP - Streamlit dashboard for scenario comparison."""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.data import SCENARIO_LABELS, SimulationConfig, load_hospital_data
from src.metrics import run_full_analysis

st.set_page_config(
    page_title="HDJ Agent MVP",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Hide Streamlit chrome so it reads like a product UI */
    header[data-testid="stHeader"] { background: transparent; height: 0; }
    #MainMenu, footer { visibility: hidden; }
    div[data-testid="stToolbar"] { display: none; }
    div[data-testid="stDecoration"] { display: none; }

    html, body, .stApp {
        background: #eef0fb !important;
        color: #1f2033 !important;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1320px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e9e9f5;
    }
    section[data-testid="stSidebar"] * {
        color: #2c2e40 !important;
    }

    /* Force readable text everywhere (theme-proof) */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label {
        color: #1f2033;
    }

    .hero-card {
        background: #ffffff;
        border: 1px solid #ececf6;
        border-radius: 26px;
        padding: 24px 30px;
        box-shadow: 0 18px 44px rgba(81, 77, 135, 0.10);
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .hero-eyebrow {
        color: #6d62f5 !important;
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .10em;
        margin-bottom: 6px;
    }
    .hero-title {
        color: #14152a !important;
        font-size: 1.9rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.15;
    }
    .hero-subtitle {
        color: #6b6d80 !important;
        font-size: .98rem;
        margin-top: 8px;
        max-width: 720px;
    }
    .hero-badge {
        background: #5b50ea;
        color: #ffffff !important;
        border-radius: 18px;
        padding: 16px 20px;
        text-align: center;
        min-width: 150px;
        box-shadow: 0 14px 30px rgba(91, 80, 234, 0.30);
    }
    .hero-badge .small { font-size: .72rem; opacity: .85; letter-spacing: .06em; }
    .hero-badge .big { font-size: 1.15rem; font-weight: 800; margin-top: 4px; }

    .rail-card {
        background: #ffffff;
        border: 1px solid #ececf6;
        border-radius: 26px;
        padding: 18px 10px;
        min-height: 640px;
        box-shadow: 0 16px 40px rgba(81, 77, 135, 0.08);
        text-align: center;
    }
    .rail-logo {
        width: 44px; height: 44px; line-height: 44px;
        border-radius: 14px; margin: 0 auto 22px auto;
        background: #f1efff; color: #5b50ea !important;
        font-weight: 900; font-size: 1.15rem;
    }
    .rail-item, .rail-item-active {
        width: 42px; height: 42px; line-height: 42px;
        border-radius: 14px; margin: 12px auto; font-weight: 800;
    }
    .rail-item { background: #f7f7fd; color: #5b50ea !important; border: 1px solid #eeeef7; }
    .rail-item-active {
        background: #5b50ea; color: #ffffff !important;
        box-shadow: 0 12px 24px rgba(91, 80, 234, 0.28);
    }
    .rail-block { margin: 16px auto 8px auto; }
    .rail-label {
        font-size: .72rem; color: #8a8ca0 !important; font-weight: 700;
        margin-top: 4px; white-space: nowrap;
    }

    .dash-card, .insight-card {
        background: #ffffff;
        border: 1px solid #ececf6;
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 16px 40px rgba(81, 77, 135, 0.08);
        margin-bottom: 18px;
    }
    .dash-card h3, .insight-card h3 {
        color: #14152a !important;
        margin-top: 0; margin-bottom: 12px; font-size: 1.05rem; font-weight: 800;
    }
    .muted { color: #74768a !important; font-size: .9rem; }

    .decision-pill {
        display: inline-block; padding: 8px 14px; border-radius: 999px;
        background: #f0efff; color: #5b50ea !important; font-weight: 800;
        font-size: .82rem; margin-bottom: 12px;
    }
    .metric-grid {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px; margin-top: 6px;
    }
    .metric-card {
        background: #fafaff; border: 1px solid #efeff8;
        border-radius: 18px; padding: 16px;
    }
    .metric-label {
        color: #7b7d91 !important; font-size: .72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: .04em;
    }
    .metric-value { color: #14152a !important; font-size: 1.4rem; font-weight: 800; margin-top: 4px; }
    .metric-delta { color: #5b50ea !important; font-size: .82rem; font-weight: 700; margin-top: 4px; }

    .progress-track {
        height: 12px; background: #eef0fb; border-radius: 999px;
        overflow: hidden; margin: 10px 0 4px 0;
    }
    .progress-fill { height: 12px; background: linear-gradient(90deg, #5b50ea, #ffb72c); border-radius: 999px; }

    .check-row {
        border-radius: 14px; padding: 11px 14px; margin: 8px 0;
        background: #fafaff; border: 1px solid #efeff8;
        color: #3f4154 !important; font-weight: 600;
    }
    .check-ok { border-left: 5px solid #39b980; }
    .check-warn { border-left: 5px solid #ffb72c; }

    div[data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #ececf6;
        border-radius: 18px; padding: 14px 16px;
        box-shadow: 0 10px 30px rgba(81, 77, 135, 0.06);
    }

    /* Make bordered containers look like dashboard cards (wrap charts) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border: 1px solid #ececf6 !important;
        border-radius: 22px;
        padding: 8px 14px 6px 14px;
        box-shadow: 0 16px 40px rgba(81, 77, 135, 0.08);
    }

    .greeting-title { color: #14152a !important; font-size: 1.55rem; font-weight: 800; margin: 0; }
    .greeting-sub { color: #74768a !important; font-size: .92rem; margin-top: 2px; }
    .card-eyebrow { color: #7b7d91 !important; font-size: .72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: .05em; margin-bottom: 6px; }

    .promo-card {
        background: linear-gradient(140deg, #6b5bff 0%, #5b50ea 60%, #4a3fd1 100%);
        border-radius: 22px; padding: 22px; color: #ffffff !important;
        box-shadow: 0 18px 40px rgba(91, 80, 234, 0.30); margin-bottom: 18px;
        min-height: 150px;
    }
    .promo-card .small { font-size: .74rem; opacity: .9; letter-spacing: .05em; }
    .promo-card .big { font-size: 1.9rem; font-weight: 850; margin: 6px 0; }
    .promo-card .tag { font-size: .82rem; opacity: .95; }

    .pbar-row { margin: 14px 0; }
    .pbar-top { display: flex; justify-content: space-between; font-size: .82rem; color: #6b6d80 !important; }
    .pbar-top b { color: #14152a !important; }

    .list-row {
        display: flex; align-items: center; gap: 12px;
        padding: 10px 0; border-bottom: 1px solid #f1f1f9;
    }
    .list-icon {
        width: 38px; height: 38px; border-radius: 12px; flex: none;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; color: #ffffff !important; font-size: .85rem;
    }
    .list-main { flex: 1; }
    .list-title { color: #14152a !important; font-weight: 700; font-size: .9rem; }
    .list-sub { color: #9a9caf !important; font-size: .76rem; }
    .list-val { color: #5b50ea !important; font-weight: 800; font-size: .9rem; }

    .cta-card {
        background: #ffffff; border: 1px solid #ececf6; border-radius: 22px;
        padding: 22px; text-align: center; box-shadow: 0 16px 40px rgba(81, 77, 135, 0.08);
    }
    .cta-card .crown { font-size: 1.8rem; }
    .cta-card .cta-title { color: #14152a !important; font-weight: 800; margin: 8px 0 4px 0; }
    .cta-btn {
        display: inline-block; margin-top: 12px; padding: 11px 18px; border-radius: 14px;
        background: #5b50ea; color: #ffffff !important; font-weight: 800; font-size: .86rem;
        box-shadow: 0 12px 24px rgba(91, 80, 234, 0.28);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
      <div>
        <div class="hero-eyebrow">HDJ Agent MVP</div>
        <h1 class="hero-title">Assistant de décision pour les hôpitaux de jour</h1>
        <div class="hero-subtitle">
          Simulez les parcours ambulatoires, comparez les scénarios et obtenez une
          recommandation simple pour optimiser ou créer un HDJ.
        </div>
      </div>
      <div class="hero-badge">
        <div class="small">CHU GUYANE</div>
        <div class="big">Défi 5</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar: assumptions ---
st.sidebar.title("Assistant HDJ")
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
    st.caption("Pour une démo, laissez ces valeurs par défaut.")
    patient_volume = st.slider(
        "Volume patients",
        0.5,
        2.0,
        1.0,
        0.1,
        help="1.0 correspond au volume de démonstration.",
    )
    room_capacity = st.slider(
        "Capacité salles / créneaux",
        0.5,
        2.0,
        1.0,
        0.1,
        help="Réduit ou augmente la capacité disponible des HDJ existants.",
    )
    grouping_rate = st.slider(
        "Seuil de regroupement HDJ",
        0.1,
        0.9,
        0.35,
        0.05,
        help="Plus le seuil est bas, plus le système regroupe facilement les patients en HDJ.",
    )
    slot_duration = st.selectbox("Durée créneau (minutes)", [20, 30, 45, 60], index=1)
    fragmented_tariff = st.number_input("Tarif parcours fragmenté (€)", 50, 500, 180, 10)
    hdj_tariff = st.number_input("Tarif parcours HDJ (€)", 100, 800, 420, 10)
    sim_days = st.selectbox("Horizon simulation (jours)", [14, 30, 60], index=1)

config = SimulationConfig(
    patient_volume_multiplier=patient_volume,
    room_capacity_multiplier=room_capacity,
    grouping_rate=grouping_rate,
    slot_duration_minutes=slot_duration,
    fragmented_tariff_eur=float(fragmented_tariff),
    hdj_tariff_eur=float(hdj_tariff),
    simulation_days=sim_days,
)

@st.cache_data(show_spinner=False)
def load_analysis(_config: SimulationConfig):
    data = load_hospital_data("synthetic", _config)
    return run_full_analysis(data)

with st.spinner("Simulation en cours…"):
    analysis = load_analysis(config)

results = analysis["results"]
comparison = analysis["comparison"]
deltas = analysis["deltas"]
conversion = analysis["conversion_opportunity"]
recommendation = analysis["recommendation"]

best_key = recommendation["recommended_scenario"]
best = results[best_key].summary
baseline = results["status_quo"].summary


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
        ("Décision guidée", "🎯", "Décision"),
        ("Comparer les scénarios", "📊", "Comparer"),
        ("Vérifier la capacité", "🏥", "Capacité"),
        ("Prioriser la spécialité", "⭐", "Spécialité"),
        ("Synthèse comité", "📋", "Synthèse"),
    ]
    rows = ['<div class="rail-logo">HDJ</div>']
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
        font_color="#3f4154",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def gauge_chart(value_pct: float, title: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value_pct,
            number={"suffix": " %", "font": {"size": 30, "color": "#14152a"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#9a9caf"},
                "bar": {"color": "#5b50ea"},
                "bgcolor": "#eef0fb",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 60], "color": "#e7e9fb"},
                    {"range": [60, 85], "color": "#fff0d6"},
                    {"range": [85, 100], "color": "#ffd9d9"},
                ],
                "threshold": {
                    "line": {"color": "#ff6b6b", "width": 3},
                    "thickness": 0.8,
                    "value": 85,
                },
            },
        )
    )
    fig.update_layout(
        title={"text": title, "font": {"size": 15, "color": "#14152a"}},
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#3f4154",
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
    "Décision guidée",
    "Comparer les scénarios",
    "Vérifier la capacité",
    "Prioriser la spécialité",
    "Synthèse comité",
]
default_index = steps.index(default_step(use_case))
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

rail_col, main_col, right_col = st.columns([0.12, 0.56, 0.32], gap="large")

with rail_col:
    st.markdown(rail(page), unsafe_allow_html=True)

if page == "Décision guidée":
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
                    color_discrete_sequence=["#c9c4ff", "#8b80f5", "#5b50ea"],
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
                    color_discrete_sequence=["#c9c4ff", "#8b80f5", "#5b50ea"],
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

        colors = ["#5b50ea", "#ff9f43", "#39b980", "#eb5286", "#3aa0ff"]
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
              <p class="muted">Cette conclusion reste à valider avec les données anonymisées réelles.</p>
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
              <h3>Hypothèses de démo</h3>
              <p class="muted">Cas d'usage : {use_case}</p>
              <p class="muted">Problème : {main_issue}</p>
              <p class="muted">Ambition : {decision_style}</p>
              <p class="muted">Spécialité : {focus_specialty}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if capacity_ok:
            st.success("La simulation soutient la recommandation.")
        else:
            st.warning("La capacité est le point de vigilance avant passage à l'échelle.")
