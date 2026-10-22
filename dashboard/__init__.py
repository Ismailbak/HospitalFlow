"""Dashboard Dash de HDJ Agent : un parcours de lecture en cinq étapes."""
from __future__ import annotations

import pandas as pd
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from dashboard import theme  # noqa: F401 — enregistre le template Plotly « chu »
from dashboard.components import METHOD_PATH, SCOPE_PATHS, STEPS, filter_bar, topbar
from dashboard.pages import ROUTES
from dashboard.params import missing
from dashboard.state import cohort_options, dataset, date_bounds, default_filters, resolved
from hdj.config import AGE_MAX, AGE_MIN

FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"


def create_app() -> Dash:
    app = Dash(
        __name__,
        title="HDJ Agent · CHU de Guyane",
        suppress_callback_exceptions=True,
        external_stylesheets=[FONTS],
    )
    defaults = default_filters()
    app.layout = html.Div(className="shell", children=[
        dcc.Location(id="url"),
        dcc.Store(id="filters", data=defaults),
        dcc.Store(id="sim-params", storage_type="local", data={}),
        dcc.Download(id="download"),
        topbar(),
        filter_bar(cohort_options(), date_bounds(), defaults),
        html.Main(id="page", className="page"),
        html.Footer(className="footer", children=[
            "HDJ Agent — prototype d'aide à la décision pour la gouvernance médico-administrative. ",
            "Ne constitue pas un outil d'aide à la décision médicale.",
        ]),
    ])
    _register_shell_callbacks(app)
    for page in ROUTES.values():
        page.register(app)
    return app


def _register_shell_callbacks(app: Dash) -> None:
    @app.callback(Output("page", "children"), Input("url", "pathname"), State("sim-params", "data"))
    def route(pathname, params):
        page = ROUTES.get(pathname, ROUTES["/"])
        return page.layout(params or {})

    @app.callback(
        *[Output(f"step-{i}", "className") for i in range(len(STEPS))],
        Output("nav-method", "className"),
        Input("url", "pathname"), Input("sim-params", "data"),
    )
    def stepper(pathname, params):
        paths = [p for p, _ in STEPS]
        current = paths.index(pathname) if pathname in paths else (-1 if pathname == METHOD_PATH else 0)
        incomplete = bool(missing(params))
        classes = []
        for i in range(len(STEPS)):
            warn = paths[i] == "/parametres" and incomplete
            state = "current" if i == current else "done" if 0 <= i < current and not warn else ""
            classes.append(f"step-link {state}{' warn' if warn else ''}")
        return (*classes, "toplink active" if pathname == METHOD_PATH else "toplink")

    @app.callback(Output("filterbar", "style"), Input("url", "pathname"))
    def toggle_filterbar(pathname):
        return None if pathname in SCOPE_PATHS else {"display": "none"}

    @app.callback(Output("scope-summary", "children"), Input("filters", "data"))
    def scope_summary(filters):
        f = resolved(filters)
        _, episodes = dataset(filters)
        start, end = (pd.Timestamp(f[k]).strftime("%d/%m/%Y") for k in ("start", "end"))
        age = "tous âges" if list(f["age"]) == [AGE_MIN, AGE_MAX] else f"{f['age'][0]}–{f['age'][1]} ans"
        cohorts = ", ".join(f["cohorts"]) if f["cohorts"] else "toutes les cohortes"
        return [
            html.Span("Périmètre simulé", className="scope-label"),
            html.Span(f"{start} → {end} · {cohorts} · {age} · venues regroupées sur {f['window']} j "
                      f"à partir de {f['min_visits']} · {int(episodes['eligible'].sum()):,} épisodes regroupables"
                      .replace(",", " ")),
            dcc.Link("Modifier", href="/parcours", className="scope-link"),
        ]

    @app.callback(
        Output("filters", "data"),
        Output("f-dates", "start_date"), Output("f-dates", "end_date"), Output("f-cohorts", "value"),
        Output("f-age", "value"), Output("f-window", "value"), Output("f-min-visits", "value"),
        Input("f-apply", "n_clicks"), Input("f-reset", "n_clicks"),
        State("f-dates", "start_date"), State("f-dates", "end_date"), State("f-cohorts", "value"),
        State("f-age", "value"), State("f-window", "value"), State("f-min-visits", "value"),
        prevent_initial_call=True,
    )
    def apply_filters(_apply, _reset, start, end, cohorts, age, window, min_visits):
        if ctx.triggered_id == "f-reset":
            d = default_filters()
            return d, d["start"], d["end"], d["cohorts"], d["age"], d["window"], d["min_visits"]
        filters = {"start": start, "end": end, "cohorts": cohorts or [], "age": age,
                   "window": window, "min_visits": min_visits}
        return (filters, *([no_update] * 6))

    @app.callback(
        Output("download", "data"),
        Input("export-btn", "n_clicks"), State("filters", "data"),
        prevent_initial_call=True,
    )
    def export(n_clicks, filters):
        if not n_clicks:
            return no_update
        _, episodes = dataset(filters)
        out = episodes.assign(services=episodes["services"].map(" + ".join)).drop(columns="pattern")
        stamp = pd.Timestamp.now().strftime("%Y%m%d")
        return dcc.send_data_frame(out.to_csv, f"hdj_episodes_{stamp}.csv", index=False, sep=";")
