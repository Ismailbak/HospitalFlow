"""Identité visuelle — palette issue du logo CHU de Guyane, template Plotly partagé.

Les couleurs sont dupliquées dans assets/style.css (variables --chu-*) : garder les deux en phase.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

BLUE = "#1E9BD7"      # « CHU »
NAVY = "#2B3990"      # « GUYANE »
GREEN = "#2E9B4A"     # contour de la Guyane
RED = "#E2231A"       # ibis rouge — réservé aux alertes
INK = "#1B2537"
MUTED = "#6B7487"
GRID = "#EDF0F5"
BORDER = "#E3E7EE"

SCENARIO_COLORS = {
    "status_quo": "#97A1B3",
    "optimize_existing": BLUE,
    "new_hdj": GREEN,
}

# Couleurs fixes par service : un service garde sa couleur sur tous les graphiques.
SERVICE_COLORS = {
    "Infectiologie": BLUE,
    "Dermatologie": "#F29A2E",
    "Gastro-entérologie": GREEN,
    "Chirurgie viscérale": "#14A3A3",
    "Hématologie-oncologie": NAVY,
    "Médecine interne": "#8E5CC9",
    "Neurologie": "#D9488F",
    "Urgences": RED,
    "Endocrinologie-diabétologie": "#C9A227",
    "Néphrologie": "#5B8DEF",
    "Gynéco-obstétrique": "#E57373",
    "Cardiologie": "#A1887F",
    "Imagerie": "#78909C",
    "HDJ": "#26A69A",
    "Autres": "#B0B8C4",
}
FALLBACK_COLORS = ["#5B8DEF", "#C9A227", "#A1887F", "#78909C", "#26A69A"]


def service_color(service: str) -> str:
    return SERVICE_COLORS.get(service, FALLBACK_COLORS[sum(map(ord, service)) % len(FALLBACK_COLORS)])


FONT = "Inter, 'Segoe UI', system-ui, -apple-system, sans-serif"

pio.templates["chu"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family=FONT, size=12, color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[BLUE, NAVY, GREEN, "#F29A2E", "#14A3A3", "#8E5CC9", "#D9488F", RED],
        margin=dict(l=8, r=8, t=8, b=8),
        xaxis=dict(gridcolor=GRID, linecolor=BORDER, zeroline=False, ticks="", title_font_color=MUTED,
                   automargin=True),
        yaxis=dict(gridcolor=GRID, linecolor=BORDER, zeroline=False, ticks="", title_font_color=MUTED,
                   automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, font_size=11,
                    bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="white", bordercolor=BORDER, font=dict(family=FONT, color=INK, size=12)),
        separators=", ",
    )
)
pio.templates.default = "chu"

GRAPH_CONFIG = {"displaylogo": False, "responsive": True,
                "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"]}
