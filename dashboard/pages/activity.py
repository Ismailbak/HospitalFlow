"""Étape 1 — Données : que contiennent les extractions ?"""
from __future__ import annotations

from dash import Input, Output, dcc, html

from dashboard import figures, insights
from dashboard import format as fmt
from dashboard.components import (
    big_number, card, export_button, graph, stat, step_hero, step_nav, takeaways,
)
from dashboard.pages.common import period_badge
from dashboard.state import dataset
from hdj.analytics import activity_summary

INDEX = 0

BLIND_SPOTS = """
- **Consultations externes uniquement** : la ville, les autres établissements et l'hospitalisation ne sont pas visibles.
- **Diagnostics** présents seulement pour la cohorte endocrinologie ; **actes techniques** quasi absents.
- La cohorte **endocrinologie-diabétologie** est vue surtout **aux urgences** : son potentiel reste incertain.
- Presque **aucune venue HDJ** dans les fichiers : l'activité HDJ actuelle se renseigne à l'étape 3.
"""


def layout(params=None) -> html.Div:
    return html.Div([
        step_hero(INDEX, "Que contiennent les données ?",
                  "Les extractions décrivent les consultations externes de six cohortes de patients, telles "
                  "qu'elles ont eu lieu. Cette étape donne les ordres de grandeur : combien de patients, "
                  "dans quels services, à quels moments.",
                  actions=[html.Span(id="ov-badge", className="pill"), export_button()]),
        html.Div(id="ov-takeaways"),
        html.Div(className="grid", children=[
            card("Patients suivis", html.Div(id="ov-patients"), span=3,
                 subtitle="Patients distincts sur la période choisie"),
            card("Repères", html.Div(id="ov-stats", className="stat-grid"), span=3),
            card("Activité mois par mois", graph("ov-monthly", 260), span=6,
                 subtitle="Nombre de consultations par mois, par service."),
            card("Où ont lieu les consultations", graph("ov-services", 340), span=6,
                 subtitle="Service = unité où la consultation a été réalisée."),
            card("Quand arrivent les patients", graph("ov-heatmap", 340), span=6,
                 subtitle="Plus la case est foncée, plus il y a d'arrivées ce jour-là à cette heure."),
            card("Âge des patients", graph("ov-age", 260), span=6,
                 subtitle="Âge à la première consultation de la période."),
            card("Ce que les données ne montrent pas", dcc.Markdown(BLIND_SPOTS, className="prose"), span=6,
                 subtitle="À garder en tête pour la suite."),
        ]),
        step_nav(INDEX),
    ])


def register(app) -> None:
    @app.callback(
        Output("ov-badge", "children"), Output("ov-takeaways", "children"),
        Output("ov-patients", "children"), Output("ov-stats", "children"),
        Output("ov-monthly", "figure"), Output("ov-services", "figure"),
        Output("ov-heatmap", "figure"), Output("ov-age", "figure"),
        Input("filters", "data"),
    )
    def update(filters):
        visits, episodes = dataset(filters)
        s = activity_summary(visits, episodes, 0)
        return (
            period_badge(filters),
            takeaways(insights.activity(visits, episodes)),
            big_number(fmt.integer(s["patients"]), "patients", f"{fmt.integer(s['visits'])} consultations"),
            [
                stat("Consultations par patient", fmt.decimal(s["visits_per_patient"])),
                stat("Âge moyen", f"{fmt.decimal(s['mean_age'], 0)} ans"),
                stat("Suivis par plusieurs services", fmt.integer(s["multi_service_patients"]),
                     fmt.percent(s["multi_service_share"])),
                stat("Cohortes", fmt.integer(visits["cohort"].nunique()), "fichiers sources"),
            ],
            figures.monthly_activity(visits), figures.services_bar(visits),
            figures.weekday_hour_heatmap(visits), figures.age_distribution(visits),
        )
