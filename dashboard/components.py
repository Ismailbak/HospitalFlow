"""Briques d'interface partagées : en-tête à étapes, introduction d'étape, « À retenir »,
cartes, tuiles, tableaux, navigation précédent / suivant."""
from __future__ import annotations

from dash import dcc, html

from dashboard.theme import GRAPH_CONFIG

# (chemin, libellé court) — l'ordre est celui du parcours de lecture
STEPS = [
    ("/", "Données"),
    ("/parcours", "Parcours"),
    ("/parametres", "Paramètres"),
    ("/simulation", "Simulation"),
    ("/decision", "Décision"),
]
METHOD_PATH = "/methode"


def topbar() -> html.Header:
    return html.Header(className="topbar", children=[
        html.A(href="/", className="brand", children=[
            html.Img(src="/assets/logo.png", alt="CHU de Guyane"),
            html.Div([
                html.Div("HDJ Agent", className="brand-title"),
                html.Div("Pilotage des parcours ambulatoires", className="brand-sub"),
            ]),
        ]),
        html.Nav(className="stepper", children=[
            dcc.Link(href=path, id=f"step-{i}", className="step-link", children=[
                html.Span(str(i + 1), className="step-dot"),
                html.Span(label, className="step-label"),
            ])
            for i, (path, label) in enumerate(STEPS)
        ]),
        html.Div(className="topbar-right", children=[
            dcc.Link("Méthode & données", href=METHOD_PATH, id="nav-method", className="toplink"),
            html.Span("Données anonymisées", className="pill pill-green"),
        ]),
    ])


def step_hero(index: int, question: str, lead: str, actions=None, scope: bool = False) -> html.Div:
    """`scope=True` : rappel en lecture seule du périmètre choisi aux étapes 1-2 (barre masquée ensuite)."""
    return html.Div(className="hero", children=[
        html.Div([
            html.Div(f"Étape {index + 1} sur {len(STEPS)} · {STEPS[index][1]}", className="hero-kicker"),
            html.H1(question),
            html.P(lead, className="hero-lead"),
            html.Div(id="scope-summary", className="scope") if scope else None,
        ]),
        html.Div(actions, className="hero-actions") if actions else None,
    ])


SCOPE_PATHS = {"/", "/parcours"}  # pages où la barre « Périmètre » est affichée


def page_hero(kicker: str, title: str, lead: str) -> html.Div:
    return html.Div(className="hero", children=[html.Div([
        html.Div(kicker, className="hero-kicker"), html.H1(title), html.P(lead, className="hero-lead"),
    ])])


def takeaways(items: list[tuple[str, str]], title: str = "À retenir") -> html.Div:
    if not items:
        return html.Div()
    return html.Div(className="takeaways", children=[
        html.Div(title, className="takeaways-title"),
        html.Div(className="takeaways-list", children=[
            html.Div(className="takeaway", children=[html.Strong(value), html.Span(" " + text)])
            for value, text in items
        ]),
    ])


def step_nav(index: int, next_label: str | None = None) -> html.Nav:
    prev = STEPS[index - 1] if index > 0 else None
    nxt = STEPS[index + 1] if index + 1 < len(STEPS) else None
    return html.Nav(className="step-nav", children=[
        dcc.Link(href=prev[0], className="btn btn-ghost", children=f"← Étape {index} · {prev[1]}") if prev else html.Span(),
        dcc.Link(href=nxt[0], className="btn btn-primary btn-lg",
                 children=next_label or f"Étape {index + 2} · {nxt[1]} →") if nxt else html.Span(),
    ])


def export_button() -> html.Button:
    return html.Button("Exporter les épisodes (CSV)", id="export-btn", className="btn btn-ghost")


def field(label: str, control, width: str | None = None, help_text: str | None = None) -> html.Div:
    return html.Div(className="field", style={"width": width} if width else None, children=[
        html.Label(label, className="field-label"), control,
        html.Div(help_text, className="field-help") if help_text else None,
    ])


def filter_bar(cohorts: list[str], bounds: tuple[str, str], defaults: dict) -> html.Div:
    return html.Div(id="filterbar", className="filterbar", children=[
        html.Span("Périmètre", className="filter-title"),
        field("Période", dcc.DatePickerRange(
            id="f-dates", min_date_allowed=bounds[0], max_date_allowed=bounds[1],
            start_date=defaults["start"], end_date=defaults["end"], display_format="DD/MM/YYYY",
            first_day_of_week=1, className="date-range",
        )),
        field("Cohortes", dcc.Dropdown(
            id="f-cohorts", options=cohorts, value=defaults["cohorts"], multi=True,
            placeholder="Toutes les cohortes", className="dd",
        ), width="280px"),
        field("Âge", dcc.RangeSlider(
            id="f-age", min=0, max=100, step=5, value=defaults["age"],
            marks={0: "0", 18: "18", 65: "65", 100: "100"}, tooltip={"placement": "bottom"},
            allowCross=False,
        ), width="190px"),
        field("Regrouper les venues sur", dcc.Dropdown(
            id="f-window", options=[{"label": f"{d} jours", "value": d} for d in (7, 14, 21, 30, 45, 60, 90)],
            value=defaults["window"], clearable=False, className="dd",
        ), width="160px"),
        field("À partir de", dcc.Dropdown(
            id="f-min-visits", options=[{"label": f"{n} venues", "value": n} for n in (2, 3, 4)],
            value=defaults["min_visits"], clearable=False, className="dd",
        ), width="130px"),
        html.Div(className="filter-actions", children=[
            html.Button("Appliquer", id="f-apply", className="btn btn-primary"),
            html.Button("Réinitialiser", id="f-reset", className="btn btn-link"),
        ]),
    ])


def card(title: str, body, span: int = 6, subtitle: str | None = None, cls: str = "", extra=None) -> html.Section:
    return html.Section(className=f"card span-{span} {cls}", children=[
        html.Header(className="card-head", children=[
            html.Div([html.H3(title), html.P(subtitle, className="card-sub") if subtitle else None]),
            html.Div(extra, className="card-tools") if extra is not None else None,
        ]),
        html.Div(body, className="card-body"),
    ])


def graph(graph_id: str | None = None, height: int = 300, figure=None) -> dcc.Graph:
    kwargs = {"id": graph_id} if graph_id else {}
    if figure is not None:
        kwargs["figure"] = figure
    return dcc.Graph(config=GRAPH_CONFIG, style={"height": f"{height}px"}, **kwargs)


def big_number(value: str, unit: str, caption: str | None = None) -> html.Div:
    return html.Div(className="big-number", children=[
        html.Div(value, className="big-value"),
        html.Div(unit, className="big-unit"),
        html.Div(caption, className="big-caption") if caption else None,
    ])


def stat(label: str, value: str, caption: str | None = None, tone: str = "") -> html.Div:
    return html.Div(className=f"stat {tone}", children=[
        html.Div(label, className="stat-label"),
        html.Div(value, className="stat-value"),
        html.Div(caption, className="stat-caption") if caption else None,
    ])


def table(columns: list[tuple[str, str]], rows: list[dict], numeric: set[str] = frozenset()) -> html.Div:
    """columns : [(clé, en-tête)] ; les clés de `numeric` sont alignées à droite."""
    return html.Div(className="table-wrap", children=html.Table(className="table", children=[
        html.Thead(html.Tr([html.Th(h, className="num" if k in numeric else None) for k, h in columns])),
        html.Tbody([
            html.Tr([html.Td(r[k], className="num" if k in numeric else None) for k, _ in columns])
            for r in rows
        ]),
    ]))


def demo_notice(label: str) -> html.Div:
    return html.Div(className="notice demo-notice", children=[
        html.Strong(f"Valeurs de démonstration « {label} »"),
        " — fictives, non issues de l'établissement. Elles illustrent l'outil ; remplacez-les à l'étape 3 "
        "avant toute utilisation.",
    ])


def needs_parameters(missing: list[str]) -> html.Div:
    return html.Div(className="callout card span-12", children=[
        html.Div("Il manque des paramètres de l'établissement", className="callout-title"),
        html.P("La simulation dépend directement de ces valeurs. Aucune n'est supposée par défaut : "
               "elles doivent provenir du DIM, du contrôle de gestion ou de l'encadrement de l'HDJ."),
        html.Ul([html.Li(m) for m in missing]),
        dcc.Link("Renseigner les paramètres →", href="/parametres", className="btn btn-primary"),
    ])
