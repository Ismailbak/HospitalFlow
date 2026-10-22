"""Étape 5 — Décision : quelle organisation retenir, et pourquoi."""
from __future__ import annotations

from dash import Input, Output, dcc, html

from dashboard import figures, insights
from dashboard import format as fmt
from dashboard.components import (
    METHOD_PATH, card, demo_notice, graph, needs_parameters, stat, step_hero, step_nav, table, takeaways,
)
from dashboard.params import GROUPS, NEW_UNIT_COST, PRESETS, has_new_units, matching_preset, missing
from dashboard.state import simulate
from hdj.simulation import SCENARIO_DESCRIPTIONS, SCENARIO_LABELS, SCENARIOS, STATUS_QUO

INDEX = 4


def _reco_banner(reco: dict, runs: int) -> html.Div:
    return html.Div(className="reco span-12", children=[
        html.Div(className="reco-main", children=[
            html.Div("Organisation recommandée", className="reco-kicker"),
            html.Div(reco["label"], className="reco-title"),
            html.Div(className="reco-pills", children=[
                html.Span(f"Même choix dans {fmt.percent(reco['robustness'])} des {runs} simulations", className="pill"),
                html.Span(f"Seuil de saturation {fmt.percent(reco['max_occupancy'])}", className="pill"),
            ]),
        ]),
        html.Div(className="reco-why", children=[
            html.Div("Pourquoi", className="reco-kicker"),
            html.Ul([html.Li(r) for r in reco["reasons"]], className="reco-reasons"),
        ]),
    ])


def _node(state: str, title: str, detail: str) -> html.Div:
    """state : ok | ko | skip (non évalué car écarté plus tôt) | win | info."""
    icon = {"ok": "✓", "ko": "✕", "skip": "–", "win": "★", "info": "="}[state]
    return html.Div(className=f"path-node {state}", children=[
        html.Span(icon, className="path-icon"),
        html.Div([html.Div(title, className="path-title"), html.Div(detail, className="path-detail")]),
    ])


def _decision_path(results: dict, reco: dict) -> html.Div:
    """Les règles de recommend() dessinées : saturation → délai → rentabilité → meilleur gain."""
    s = results["scenarios"]
    threshold = reco["max_occupancy"]
    sq_delay = s[STATUS_QUO]["kpis"]["mean_delay"]["mean"]
    choice = reco["choice"]

    rows = [html.Div(className="path-row status_quo", children=[
        html.Div(SCENARIO_LABELS[STATUS_QUO], className="path-label"),
        _node("info", "Référence", "Toujours recevable, gain 0 €"),
        html.Div(className="path-spacer"), html.Div(className="path-spacer"),
        _node("win" if choice == STATUS_QUO else "skip",
              "Recommandé" if choice == STATUS_QUO else "Retenu à défaut",
              "Aucune alternative recevable et rentable" if choice == STATUS_QUO
              else "Seulement si rien d'autre ne passe"),
    ])]

    for key in (k for k in SCENARIOS if k != STATUS_QUO):
        c = reco["checks"][key]
        delay = s[key]["kpis"]["mean_delay"]["mean"]
        steps, alive = [], True

        steps.append(_node("ok" if c["occupancy_ok"] else "ko", "Sans saturation ?",
                           f"{fmt.percent(c['worst_occupancy'])} {'≤' if c['occupancy_ok'] else '>'} "
                           f"{fmt.percent(threshold)} · {c['worst_unit']}"))
        alive = c["occupancy_ok"]

        state = ("ok" if c["delay_ok"] else "ko") if alive else "skip"
        steps.append(_node(state, "Délai tenu ?",
                           f"{fmt.decimal(delay)} j vs {fmt.decimal(sq_delay)} j aujourd'hui"))
        alive = alive and c["delay_ok"]

        profitable = c["net_gain"] > 0
        state = ("ok" if profitable else "ko") if alive else "skip"
        steps.append(_node(state, "Rentable ?", f"{fmt.euros(c['net_gain'])} par an"))
        alive = alive and profitable

        if key == choice:
            final = _node("win", "Recommandé", "Meilleur gain parmi les organisations recevables")
        elif alive:
            final = _node("skip", "Moins favorable", f"Gain inférieur à « {reco['label']} »")
        else:
            final = _node("ko", "Écarté", "Ne passe pas tous les contrôles")
        rows.append(html.Div(className=f"path-row {key}", children=[
            html.Div(SCENARIO_LABELS[key], className="path-label"), *steps, final,
        ]))

    return html.Div(className="decision-path", children=[
        html.Div(className="path-row path-header", children=[
            html.Div(),
            *[html.Div(t, className="path-col") for t in
              ("1 · Saturation", "2 · Délais", "3 · Rentabilité", "Résultat")],
        ]),
        *rows,
    ])


def _scenario_card(key: str, results: dict, reco: dict, new_units: bool) -> html.Div:
    k = results["scenarios"][key]["kpis"]
    check = reco["checks"][key]
    is_choice = key == reco["choice"]
    badge = (html.Span("Recommandé", className="pill pill-blue") if is_choice
             else html.Span("Écarté", className="pill pill-red") if not check["admissible"] else None)
    gain = k["annual_net_gain"]
    if key == STATUS_QUO:
        caption = "situation de référence"
    elif fmt.euros(gain["p10"]) == fmt.euros(gain["p90"]):
        caption = "identique dans toutes les simulations"
    else:
        caption = f"entre {fmt.euros(gain['p10'])} et {fmt.euros(gain['p90'])}"
    description = SCENARIO_DESCRIPTIONS[key]
    if key == "new_hdj" and not new_units:
        description = "Aucun nouvel HDJ défini : identique à l'optimisation de l'existant."
    return html.Div(className=f"scenario-card {key} {'is-choice' if is_choice else ''}", children=[
        html.Div(className="scenario-head", children=[html.H3(SCENARIO_LABELS[key]), badge]),
        html.P(description, className="scenario-desc"),
        html.Div(className="scenario-hero", children=[
            html.Div("Gain net par an", className="stat-label"),
            html.Div(fmt.euros(gain["mean"]), className="scenario-gain"),
            html.Div(caption, className="stat-caption"),
        ]),
        html.Div(className="stat-grid", children=[
            stat("Venues évitées", fmt.integer(k["trips_avoided"]["mean"])),
            stat("Bilan réalisé en", f"{fmt.decimal(k['mean_delay']['mean'])} j"),
            stat("Unité la plus chargée", fmt.percent(check["worst_occupancy"]), check["worst_unit"],
                 tone="alert" if not check["occupancy_ok"] else ""),
            stat("Épisodes en HDJ", fmt.integer(k["converted"]["mean"]), fmt.percent(k["conversion_rate"]["mean"])),
        ]),
    ])


def _units_table(results: dict) -> html.Div:
    rows = []
    for key in SCENARIOS:
        for name, u in results["scenarios"][key]["units"].items():
            rows.append({
                "scenario": SCENARIO_LABELS[key], "unit": name + (" (nouveau)" if u["is_new"] else ""),
                "places": fmt.integer(u["places"]),
                "occupancy": f"{fmt.percent(u['occupancy']['mean'])}",
                "saturated": fmt.percent(u["saturated_share"]["mean"]),
            })
    return table([("scenario", "Scénario"), ("unit", "Unité"), ("places", "Places / jour"),
                  ("occupancy", "Occupation"), ("saturated", "Jours complets")],
                 rows, numeric={"places", "occupancy", "saturated"})


def _inputs_used(params: dict) -> html.Div:
    rows = []
    for _, _, fields in GROUPS:
        for f in fields:
            v = params[f.key]
            shown = fmt.integer(v) if float(v).is_integer() else fmt.decimal(v, 2)
            rows.append({"label": f.label, "value": f"{shown} {f.unit or ''}"})
    for n in ("a", "b"):
        if params.get(f"{n}_services") and params.get(f"{n}_places"):
            rows.append({"label": f"HDJ {n.upper()}",
                         "value": f"{params[f'{n}_places']} places · {', '.join(params[f'{n}_services'])}"})
    if has_new_units(params):
        rows.append({"label": NEW_UNIT_COST.label, "value": fmt.euros(params["place_cost"], compact_form=False)})
    return table([("label", "Paramètre"), ("value", "Valeur saisie")], rows, numeric={"value"})


def layout(params=None) -> html.Div:
    return html.Div([
        step_hero(INDEX, "Quelle organisation retenir ?",
                  "Les trois organisations sont comparées sur les mêmes épisodes. Une organisation est écartée si "
                  "elle sature une unité ou allonge les délais ; parmi les autres, la recommandation retient le gain "
                  "net annuel le plus élevé.", scope=True),
        dcc.Loading(type="dot", color="#1E9BD7", children=html.Div(id="dc-content")),
        step_nav(INDEX),
    ])


def register(app) -> None:
    @app.callback(Output("dc-content", "children"), Input("filters", "data"), Input("sim-params", "data"))
    def update(filters, params):
        todo = missing(params)
        if todo:
            return html.Div(needs_parameters(todo), className="grid")
        results, reco = simulate(filters, params)
        runs = results["meta"]["params"]["runs"]
        new_units = has_new_units(params)
        demo = matching_preset(params)
        return html.Div(className="grid", children=[
            html.Div(demo_notice(PRESETS[demo]["label"]), className="span-12") if demo else None,
            _reco_banner(reco, runs),
            card("Comment la décision a été prise", _decision_path(results, reco), span=12,
                 subtitle="Chaque organisation passe trois contrôles dans l'ordre ; une seule croix suffit à "
                          "l'écarter. Parmi celles qui passent tout, la plus rentable est recommandée."),
            html.Div(takeaways(insights.decision(results, reco), title="En chiffres"), className="span-12"),
            html.Div([_scenario_card(k, results, reco, new_units) for k in SCENARIOS], className="span-12 scenario-cards"),
            card("Gain net annuel", graph(height=300, figure=figures.net_gain_bars(results, reco["choice"])), span=6,
                 subtitle="Recettes en plus par rapport à aujourd'hui, moins le coût des places créées. "
                          "Les traits indiquent la fourchette des simulations."),
            card("Charge des unités", _units_table(results), span=6,
                 subtitle="Occupation moyenne et part des jours où l'unité est complète."),
            card("Sur quoi repose cette recommandation", _inputs_used(params), span=6,
                 subtitle="Valeurs saisies à l'étape 3. Une valeur différente peut changer le résultat."),
            card("Avant de décider", html.Div([
                dcc.Markdown(
                    "- Les données ne couvrent que les **consultations externes** : le potentiel réel est "
                    "probablement **plus élevé**.\n"
                    "- Un épisode regroupable est défini par des **venues rapprochées**, pas par le contenu médical "
                    "des actes : les critères d'éligibilité HDJ restent à vérifier avec les équipes.\n"
                    "- Les recettes reposent sur les **tarifs moyens saisis**, pas sur la valorisation réelle des séjours.",
                    className="prose"),
                dcc.Link("Méthode et limites détaillées →", href=METHOD_PATH, className="text-link"),
            ]), span=6),
        ])
