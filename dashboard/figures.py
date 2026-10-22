"""Constructeurs de graphiques Plotly. Chaque fonction reçoit des données déjà filtrées."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.theme import BLUE, BORDER, GREEN, MUTED, NAVY, RED, SCENARIO_COLORS, service_color
from hdj.simulation import SCENARIO_LABELS, SCENARIOS

WEEKDAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def empty(message: str = "Aucune donnée pour ces filtres") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(color=MUTED, size=13), x=0.5, y=0.5,
                       xref="paper", yref="paper")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def _top_services(series: pd.Series, n: int = 7) -> pd.Series:
    top = series.value_counts().head(n).index
    return series.where(series.isin(top), "Autres")


# --- Étape 1 · Données ------------------------------------------------------------------

def monthly_activity(visits: pd.DataFrame) -> go.Figure:
    if visits.empty:
        return empty()
    v = visits.assign(month=visits["date"].dt.to_period("M").dt.to_timestamp(),
                      service=_top_services(visits["service"]))
    counts = v.groupby(["month", "service"]).size().unstack(fill_value=0)
    order = counts.sum().sort_values(ascending=False).index
    fig = go.Figure()
    for service in order:
        fig.add_bar(x=counts.index, y=counts[service], name=service, marker_color=service_color(service),
                    hovertemplate="%{x|%b %Y}<br>" + service + " : %{y}<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.18, legend=dict(y=1.02))
    fig.update_yaxes(title="Consultations")
    return fig




def age_distribution(visits: pd.DataFrame) -> go.Figure:
    if visits.empty:
        return empty()
    ages = visits.drop_duplicates("patient_id")["age"]
    fig = go.Figure(go.Histogram(x=ages, xbins=dict(start=0, end=100, size=5), marker_color=BLUE,
                                 marker_line=dict(color="white", width=1),
                                 hovertemplate="%{x} ans : %{y} patients<extra></extra>"))
    fig.update_layout(bargap=0.04)
    fig.update_xaxes(title="Âge à l'entrée (années)")
    fig.update_yaxes(title="Patients")
    return fig


def weekday_hour_heatmap(visits: pd.DataFrame) -> go.Figure:
    v = visits[visits["hour"].between(7, 18)]
    if v.empty:
        return empty()
    grid = v.groupby(["weekday", "hour"]).size().unstack(fill_value=0).reindex(index=range(7), columns=range(7, 19),
                                                                               fill_value=0)
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=[f"{h}h" for h in grid.columns], y=WEEKDAY_LABELS,
        colorscale=[[0, "#F3F8FC"], [0.5, "#7CC4EA"], [1, NAVY]], xgap=2, ygap=2,
        hovertemplate="%{y} %{x} : %{z} arrivées<extra></extra>", colorbar=dict(thickness=10, outlinewidth=0),
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False)
    return fig


def services_bar(visits: pd.DataFrame) -> go.Figure:
    if visits.empty:
        return empty()
    counts = visits["service"].value_counts().sort_values()
    fig = go.Figure(go.Bar(
        x=counts.values, y=counts.index, orientation="h",
        marker_color=[service_color(s) for s in counts.index],
        text=counts.values, textposition="outside", cliponaxis=False,
        hovertemplate="%{y} : %{x} consultations<extra></extra>",
    ))
    fig.update_xaxes(showgrid=False, visible=False)
    fig.update_yaxes(showgrid=False)
    return fig




# --- Étape 2 · Parcours -----------------------------------------------------------------

def transitions_sankey(transitions: pd.DataFrame, limit: int = 25) -> go.Figure:
    if transitions.empty:
        return empty("Aucun enchaînement de visites dans la fenêtre")
    t = transitions.head(limit)
    sources = list(dict.fromkeys(t["source"]))
    targets = list(dict.fromkeys(t["target"]))
    labels = sources + targets
    index_src = {s: i for i, s in enumerate(sources)}
    index_tgt = {s: len(sources) + i for i, s in enumerate(targets)}
    colors = [service_color(s) for s in labels]

    def rgba(hex_color: str, alpha: float) -> str:
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
        return f"rgba({r},{g},{b},{alpha})"

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=colors, pad=14, thickness=14, line=dict(width=0),
                  hovertemplate="%{label} : %{value} passages<extra></extra>"),
        link=dict(
            source=[index_src[s] for s in t["source"]],
            target=[index_tgt[s] for s in t["target"]],
            value=t["count"],
            color=[rgba(service_color(s), 0.28) for s in t["source"]],
            hovertemplate="%{source.label} → %{target.label} : %{value}<extra></extra>",
        ),
    ))
    fig.update_layout(margin=dict(l=8, r=8, t=24, b=8), font_size=11)
    fig.add_annotation(text="Visite", x=0, y=1.07, xref="paper", yref="paper", showarrow=False,
                       font=dict(color=MUTED, size=11), xanchor="left")
    fig.add_annotation(text="Visite suivante", x=1, y=1.07, xref="paper", yref="paper", showarrow=False,
                       font=dict(color=MUTED, size=11), xanchor="right")
    return fig


def gap_histogram(gaps: pd.Series, window: int) -> go.Figure:
    g = gaps[gaps <= 180]
    if g.empty:
        return empty("Aucun patient revenu sur la période")
    inside = g[g <= window]
    fig = go.Figure()
    fig.add_histogram(x=inside, xbins=dict(start=0, end=181, size=7), marker_color=GREEN, name=f"≤ {window} j",
                      hovertemplate="%{x} j : %{y}<extra></extra>")
    fig.add_histogram(x=g[g > window], xbins=dict(start=0, end=181, size=7), marker_color="#C9D2DF",
                      name=f"> {window} j", hovertemplate="%{x} j : %{y}<extra></extra>")
    fig.add_vline(x=window, line=dict(color=GREEN, dash="dot", width=1.5))
    fig.update_layout(barmode="overlay", bargap=0.06)
    fig.update_xaxes(title="Jours entre deux venues")
    fig.update_yaxes(title="Retours")
    return fig


def conversion_potential_bar(potential: pd.DataFrame) -> go.Figure:
    if potential.empty:
        return empty("Aucun épisode convertible")
    p = potential.sort_values("episodes")
    fig = go.Figure(go.Bar(
        x=p["episodes"], y=p["service"], orientation="h", marker_color=[service_color(s) for s in p["service"]],
        text=p["episodes"], textposition="outside", cliponaxis=False,
        customdata=p["trips_avoided"],
        hovertemplate="%{y}<br>%{x} épisodes convertibles<br>%{customdata} venues évitables<extra></extra>",
    ))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(showgrid=False)
    return fig






# --- Étapes 4-5 · Simulation et décision -------------------------------------------------

def net_gain_bars(results: dict, choice: str) -> go.Figure:
    s = results["scenarios"]
    means = [s[k]["kpis"]["annual_net_gain"]["mean"] for k in SCENARIOS]
    lo = [m - s[k]["kpis"]["annual_net_gain"]["p10"] for m, k in zip(means, SCENARIOS)]
    hi = [s[k]["kpis"]["annual_net_gain"]["p90"] - m for m, k in zip(means, SCENARIOS)]
    fig = go.Figure(go.Bar(
        x=[SCENARIO_LABELS[k] for k in SCENARIOS], y=means,
        marker=dict(color=[SCENARIO_COLORS[k] for k in SCENARIOS],
                    line=dict(color=[NAVY if k == choice else "rgba(0,0,0,0)" for k in SCENARIOS], width=2)),
        error_y=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color=MUTED, thickness=1.2, width=6),
        hovertemplate="%{x}<br>%{y:,.0f} € / an<extra></extra>",
    ))
    fig.add_hline(y=0, line=dict(color=BORDER, width=1))
    fig.update_yaxes(title="Gain net annuel (€)", tickformat=",.0f")
    fig.update_xaxes(showgrid=False)
    fig.update_layout(bargap=0.5)
    return fig


def delay_boxes(results: dict, scenarios=SCENARIOS) -> go.Figure:
    fig = go.Figure()
    for k in scenarios:
        delays = results["scenarios"][k]["delays"]
        if not delays:
            continue
        fig.add_box(y=delays, name=SCENARIO_LABELS[k], marker_color=SCENARIO_COLORS[k], boxmean=True,
                    line_width=1.5, marker_size=3, jitter=0.3, pointpos=0, boxpoints="outliers",
                    hovertemplate="%{y} j<extra></extra>")
    if not fig.data:
        return empty("Aucun épisode convertible")
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title="Jours pour réaliser le bilan")
    return fig


def weekly_occupancy(results: dict, max_occupancy: float, scenarios=SCENARIOS) -> go.Figure:
    fig = go.Figure()
    for k in scenarios:
        for name, unit in results["scenarios"][k]["units"].items():
            dash = "dot" if unit["is_new"] else "solid"
            fig.add_scatter(
                x=pd.to_datetime(unit["weekly"]["week"]), y=unit["weekly"]["occupancy"], mode="lines",
                name=f"{SCENARIO_LABELS[k]} · {name}", line=dict(color=SCENARIO_COLORS[k], width=1.8, dash=dash,
                                                                 shape="spline", smoothing=0.6),
                hovertemplate="Semaine du %{x|%d/%m/%Y}<br>%{y:.0%}<extra>" + name + "</extra>",
            )
    fig.add_hline(y=max_occupancy, line=dict(color=RED, dash="dash", width=1),
                  annotation_text=f"seuil {max_occupancy:.0%}", annotation_font_color=RED,
                  annotation_position="top left")
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05], title="Occupation hebdomadaire")
    fig.update_layout(legend=dict(y=1.04))
    return fig
