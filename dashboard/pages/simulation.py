"""Étape 4 — Simulation : ce que font les agents avec les moyens saisis."""
from __future__ import annotations

from dash import Input, Output, dcc, html

from dashboard import figures, insights
from dashboard import format as fmt
from dashboard.components import card, demo_notice, graph, needs_parameters, step_hero, step_nav, takeaways
from dashboard.params import PRESETS, has_new_units, matching_preset, missing
from dashboard.state import resolved, simulate
from hdj.simulation import NEW_HDJ, OPTIMIZE_EXISTING, SCENARIO_LABELS, STATUS_QUO

INDEX = 3


def _agent(num: int, name: str, role: str, value: str, text: str) -> html.Div:
    return html.Div(className="agent", children=[
        html.Div(className="agent-head", children=[html.Span(str(num), className="agent-num"),
                                                   html.Div([html.Div(name, className="agent-name"),
                                                             html.Div(role, className="agent-role")])]),
        html.Div(value, className="agent-value"),
        html.P(text, className="agent-text"),
    ])


def _split(parts: list[tuple[str, float, str]]) -> html.Div:
    total = sum(v for _, v, _ in parts) or 1
    shown = [(label, v, color) for label, v, color in parts if v > 0]
    return html.Div(className="split", children=[
        html.Div(className="split-bar", children=[
            html.Div(style={"width": f"{100 * v / total}%", "background": color}, title=f"{label} : {v:.0f}")
            for label, v, color in shown
        ]),
        html.Div(className="split-legend", children=[
            html.Span([html.I(style={"background": color}), f"{label} · {fmt.integer(v)}"]) for label, v, color in shown
        ]),
    ])


def _agents_panel(results: dict, scenario: str, window: int, min_visits: int, runs: int) -> html.Div:
    k = {key: v["mean"] for key, v in results["scenarios"][scenario]["kpis"].items()}
    units = results["scenarios"][scenario]["units"]
    existing = k["converted"] - k["converted_new"]
    not_routed = max(k["eligible"] - k["converted"] - k["fallbacks"], 0)
    worst = max(units.values(), key=lambda u: u["occupancy"]["mean"])
    worst_name = next(n for n, u in units.items() if u is worst)
    return html.Div(className="agents-panel", children=[
        html.Div(className="agents", children=[
            _agent(1, "Agents patients", "Un par épisode réel", fmt.integer(k["episodes"]),
                   f"épisodes rejoués, dont {fmt.integer(k['eligible'])} regroupables "
                   f"({min_visits} venues ou plus en {window} jours)."),
            _agent(2, "Agent de triage", "Oriente chaque épisode", fmt.integer(k["converted"] + k["fallbacks"]),
                   f"épisodes orientés vers un HDJ. {fmt.integer(not_routed)} restent en parcours classique : "
                   "aucun HDJ défini n'accueille leurs spécialités."),
            _agent(3, "Agent coordinateur", "Planifie les journées", fmt.integer(k["converted"]),
                   f"journées HDJ planifiées, après {fmt.integer(k['replans'])} replanifications (absences, "
                   f"unités pleines). {fmt.integer(k['fallbacks'])} épisodes sans place dans le délai."),
            _agent(4, "Agent évaluateur", "Mesure le résultat", fmt.integer(k["trips_avoided"]),
                   f"venues évitées. Délai moyen du bilan : {fmt.decimal(k['mean_delay'])} j. "
                   f"Unité la plus chargée : {worst_name} à {fmt.percent(worst['occupancy']['mean'])}."),
        ]),
        html.Div(className="split-title", children="Devenir des épisodes regroupables"),
        _split([
            ("HDJ existant", existing, "#1E9BD7"),
            ("Nouveaux HDJ", k["converted_new"], "#2E9B4A"),
            ("Sans place dans le délai", k["fallbacks"], "#F29A2E"),
            ("Spécialité non accueillie", not_routed, "#C9D2DF"),
        ]),
        html.P(f"Moyennes sur {runs} simulations aléatoires.", className="agents-note"),
    ])


def layout(params=None) -> html.Div:
    return html.Div([
        step_hero(INDEX, "Que se passerait-il avec ces moyens ?",
                  "Chaque épisode réel devient un agent patient. L'agent de triage décide s'il peut rejoindre un "
                  "HDJ, l'agent coordinateur lui cherche une journée libre, l'agent évaluateur mesure le résultat. "
                  "L'opération est répétée avec des aléas (absences, dates de demande) pour obtenir des fourchettes.",
                  actions=[dcc.RadioItems(
                      id="sim-scenario", value=OPTIMIZE_EXISTING, inline=True, className="segmented",
                      options=[{"label": SCENARIO_LABELS[s], "value": s} for s in (OPTIMIZE_EXISTING, NEW_HDJ)],
                  )], scope=True),
        dcc.Loading(type="dot", color="#1E9BD7", children=html.Div(id="sim-content")),
        step_nav(INDEX),
    ])


def register(app) -> None:
    @app.callback(
        Output("sim-content", "children"),
        Input("filters", "data"), Input("sim-params", "data"), Input("sim-scenario", "value"),
    )
    def update(filters, params, scenario):
        todo = missing(params)
        if todo:
            return html.Div(needs_parameters(todo), className="grid")
        f = resolved(filters)
        results, reco = simulate(filters, params)
        note = None
        if scenario == NEW_HDJ and not has_new_units(params):
            note = html.Div("Aucun nouvel HDJ n'est défini à l'étape 3 : ce scénario est identique à "
                            "l'optimisation de l'existant.", className="notice")
        runs = results["meta"]["params"]["runs"]
        pair = (STATUS_QUO, scenario)
        demo = matching_preset(params)
        return html.Div([
            demo_notice(PRESETS[demo]["label"]) if demo else None,
            note,
            takeaways(insights.simulation(results, scenario)),
            html.Div(className="grid", children=[
                card("Ce que chaque agent a fait", _agents_panel(results, scenario, f["window"], f["min_visits"], runs),
                     span=12, subtitle=f"Scénario : {SCENARIO_LABELS[scenario]}."),
                card("Occupation des HDJ semaine par semaine",
                     graph(height=330, figure=figures.weekly_occupancy(results, reco["max_occupancy"], pair)), span=7,
                     subtitle="Gris : situation actuelle. Couleur : avec le regroupement. "
                              "Pointillés : nouveaux HDJ. Ligne rouge : seuil de saturation."),
                card("Temps pour réaliser le bilan",
                     graph(height=330, figure=figures.delay_boxes(results, pair)), span=5,
                     subtitle="Épisodes regroupables. Aujourd'hui : temps entre la première et la dernière "
                              "venue. En HDJ : attente avant la journée."),
            ]),
        ])
