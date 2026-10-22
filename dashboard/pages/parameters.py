"""Étape 3 — Paramètres : les moyens de l'établissement, saisis par l'utilisateur."""
from __future__ import annotations

from dash import ALL, Input, Output, State, ctx, dcc, html, no_update

from dashboard import format as fmt
from dashboard.components import card, demo_notice, step_hero, step_nav
from dashboard.params import (
    DEFAULT_RUNS, GROUPS, NEW_UNIT_COST, PRESETS, REQUIRED, RUN_OPTIONS, Field, matching_preset, missing,
    preset_values,
)
from dashboard.state import service_options, simulate
from hdj.simulation import SCENARIO_LABELS, SCENARIOS

INDEX = 2


def _pid(key: str) -> dict:
    return {"type": "param", "key": key}


def _number(f: Field, value) -> html.Div:
    control = dcc.Input(id=_pid(f.key), type="number", value=value, min=f.min, max=f.max, step=f.step,
                        placeholder="À saisir", className="input")
    return html.Div(className="input-unit", children=[control, html.Span(f.unit, className="unit")]) if f.unit else control


def _param_row(f: Field, value) -> html.Div:
    return html.Div(className="param-row", children=[
        html.Div(className="param-text", children=[
            html.Label(f.label, className="param-label"),
            html.Div(f.help, className="param-help"),
            html.Span(f"Source : {f.source}", className="param-source") if f.source else None,
        ]),
        html.Div(_number(f, value), className="param-input"),
    ])


def _services(key: str, value, placeholder: str) -> dcc.Dropdown:
    return dcc.Dropdown(id=_pid(key), options=service_options(), value=value or [], multi=True,
                        placeholder=placeholder, className="dd")


def _new_units_card(p: dict) -> html.Section:
    def unit_row(name: str) -> html.Div:
        places = Field(f"{name}_places", "Places", "", min=0)
        return html.Div(className="param-row", children=[
            html.Div(className="param-text", children=[
                html.Label(f"HDJ {name.upper()}", className="param-label"),
                _services(f"{name}_services", p.get(f"{name}_services"), "Spécialités accueillies"),
            ]),
            html.Div(className="param-input", children=[
                html.Label("Places / jour", className="param-mini"), _number(places, p.get(f"{name}_places")),
            ]),
        ])

    return card("Nouveaux HDJ", [unit_row("a"), unit_row("b"), _param_row(NEW_UNIT_COST, p.get("place_cost"))],
                span=6, subtitle="Facultatif. Laissez vide pour ne tester que l'HDJ existant.")


def layout(params=None) -> html.Div:
    p = params or {}
    group_cards = []
    for title, description, fields in GROUPS:
        rows = [_param_row(f, p.get(f.key)) for f in fields]
        if title == "HDJ existant":
            rows.append(html.Div(className="param-row", children=[
                html.Div(className="param-text", children=[
                    html.Label("Spécialités accueillies", className="param-label"),
                    html.Div("Laissez vide si l'HDJ est polyvalent.", className="param-help"),
                ]),
                html.Div(_services("ex_services", p.get("ex_services"), "Toutes"), className="param-input wide"),
            ]))
        if title == "Décision":
            rows.append(html.Div(className="param-row", children=[
                html.Div(className="param-text", children=[
                    html.Label("Nombre de simulations", className="param-label"),
                    html.Div("Réglage technique : plus il est élevé, plus les fourchettes sont stables.",
                             className="param-help"),
                ]),
                html.Div(dcc.Dropdown(id=_pid("runs"), options=RUN_OPTIONS, value=p.get("runs") or DEFAULT_RUNS,
                                      clearable=False, className="dd"), className="param-input"),
            ]))
        group_cards.append(card(title, rows, span=6, subtitle=description))
    group_cards.insert(1, _new_units_card(p))

    return html.Div([
        step_hero(INDEX, "Quels sont les moyens de l'établissement ?",
                  "La simulation rejoue les épisodes réels dans l'organisation que vous décrivez ici. Ces valeurs "
                  "ne figurent pas dans les extractions : elles viennent de l'établissement. Rien n'est supposé "
                  "par défaut, et vos saisies sont mémorisées dans ce navigateur.", scope=True),
        _demo_card(),
        html.Div(id="pm-progress"),
        dcc.Loading(type="dot", color="#1E9BD7", children=html.Div(id="pm-preview")),
        html.Div(className="grid", children=group_cards),
        step_nav(INDEX, next_label="Lancer la simulation →"),
    ])


def _demo_card() -> html.Div:
    return html.Div(className="demo-card", children=[
        html.Div(className="demo-card-head", children=[
            html.Div([
                html.Div("Exemples de démonstration", className="demo-card-title"),
                html.P("Remplissent le formulaire avec des valeurs fictives qui aboutissent chacune à une "
                       "organisation différente. Pour présenter l'outil, pas pour décider.", className="card-sub"),
            ]),
            html.Button("Tout effacer", id={"type": "preset", "key": "clear"}, className="btn btn-link"),
        ]),
        html.Div(className="demo-buttons", children=[
            html.Button(id={"type": "preset", "key": name}, className=f"demo-button {name}", children=[
                html.Span(preset["label"], className="demo-button-title"),
                html.Span(preset["story"], className="demo-button-story"),
            ])
            for name, preset in PRESETS.items()
        ]),
    ])


def _preview(filters: dict, params: dict) -> html.Div:
    results, reco = simulate(filters, params)
    tiles = []
    for key in SCENARIOS:
        k = results["scenarios"][key]["kpis"]
        check = reco["checks"][key]
        is_choice = key == reco["choice"]
        tag = ("Recommandé", "pill-blue") if is_choice else ("Écarté", "pill-red") if not check["admissible"] else None
        tiles.append(html.Div(className=f"preview-tile {key} {'is-choice' if is_choice else ''}", children=[
            html.Div(className="preview-head", children=[
                html.Span(SCENARIO_LABELS[key], className="preview-name"),
                html.Span(tag[0], className=f"pill {tag[1]}") if tag else None,
            ]),
            html.Div(fmt.euros(k["annual_net_gain"]["mean"]), className="preview-gain"),
            html.Div(f"gain net / an · {fmt.integer(k['trips_avoided']['mean'])} venues évitées · "
                     f"bilan en {fmt.decimal(k['mean_delay']['mean'])} j", className="preview-detail"),
        ]))
    return html.Div(className="preview", children=[
        html.Div(className="preview-top", children=[
            html.Div([html.Div("Résultat avec ces valeurs", className="demo-card-title"),
                      html.P(f"Organisation recommandée : {reco['label']}.", className="card-sub")]),
            html.Div(className="preview-links", children=[
                dcc.Link("Voir la simulation", href="/simulation", className="btn btn-ghost"),
                dcc.Link("Voir la décision →", href="/decision", className="btn btn-primary"),
            ]),
        ]),
        html.Div(tiles, className="preview-tiles"),
    ])


def _progress(params: dict) -> html.Div:
    demo = matching_preset(params)
    return html.Div([demo_notice(PRESETS[demo]["label"]) if demo else None, _completion(params)])


def _completion(params: dict) -> html.Div:
    todo = missing(params)
    total = len(REQUIRED)
    done = total - sum(1 for f in REQUIRED if params.get(f.key) is None)
    complete = not todo
    return html.Div(className=f"progress-card {'is-complete' if complete else ''}", children=[
        html.Div(className="progress-head", children=[
            html.Strong("Paramètres complets : la simulation peut être lancée." if complete
                        else f"{done} sur {total} paramètres obligatoires renseignés"),
            html.Span(f"{round(100 * done / total)} %", className="progress-pct"),
        ]),
        html.Div(className="progress-bar", children=html.Div(style={"width": f"{100 * done / total}%"})),
        html.Div(className="progress-missing", children=[
            html.Span("Reste à renseigner : "), ", ".join(todo),
        ]) if todo else None,
    ])


def register(app) -> None:
    @app.callback(
        Output("sim-params", "data"), Output("pm-progress", "children"),
        Input({"type": "param", "key": ALL}, "value"),
        State({"type": "param", "key": ALL}, "id"),
        State("sim-params", "data"),
    )
    def save(values, ids, stored):
        """Enregistrement immédiat : ne doit jamais attendre la simulation."""
        params = {**(stored or {}), **{i["key"]: v for i, v in zip(ids, values)}}
        return params, _progress(params)

    @app.callback(Output("pm-preview", "children"), Input("sim-params", "data"), Input("filters", "data"))
    def preview(params, filters):
        return None if missing(params) else _preview(filters, params)

    @app.callback(
        Output({"type": "param", "key": ALL}, "value"),
        Input({"type": "preset", "key": ALL}, "n_clicks"),
        State({"type": "param", "key": ALL}, "id"),
        prevent_initial_call=True,
    )
    def fill(clicks, ids):
        if not ctx.triggered_id or not any(clicks):
            return [no_update] * len(ids)
        name = ctx.triggered_id["key"]
        values = preset_values(None if name == "clear" else name)
        return [values[i["key"]] for i in ids]
