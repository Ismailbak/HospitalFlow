"""Étape 2 — Parcours : où les parcours se fragmentent-ils ?"""
from __future__ import annotations

import pandas as pd
from dash import Input, Output, html

from dashboard import figures, insights
from dashboard import format as fmt
from dashboard.components import (
    big_number, card, export_button, graph, step_hero, step_nav, table, takeaways,
)
from dashboard.state import dataset, resolved
from dashboard.theme import service_color
from hdj.analytics import activity_summary, conversion_potential, top_patterns
from hdj.data import service_transitions, visit_gaps

INDEX = 1


def _chip(service: str) -> html.Span:
    return html.Span(service, className="chip", style={"--chip": service_color(service)})


def episode_visual(days: list[tuple[int, list[str]]], window: int, kicker: str, caption: str,
                   hdj_caption: str) -> html.Div:
    """Venues étalées dans la fenêtre (gauche) → les mêmes consultations en une journée HDJ (droite).

    `days` : [(jour relatif, [services vus ce jour-là])].
    """
    stack = max(len(s) for _, s in days)
    services = [s for _, day_services in days for s in day_services]
    return html.Div(className="episode-demo", children=[
        html.Div(className="demo-side", children=[
            html.Div(kicker, className="demo-kicker"),
            html.Div(className="timeline", style={"height": f"{52 + 26 * stack}px"}, children=[
                html.Div(className="window-band"),
                *[
                    html.Div(className="visit", style={"left": f"{4 + 88 * d / window}%"}, children=[
                        html.Div([_chip(s) for s in day_services], className="visit-chips"),
                        html.Span(className="visit-dot"),
                        html.Span(f"J+{d}", className="visit-day"),
                    ])
                    for d, day_services in days
                ],
            ]),
            html.P(caption, className="demo-caption"),
        ]),
        html.Div("→", className="demo-arrow"),
        html.Div(className="demo-side demo-hdj", children=[
            html.Div("Avec un hôpital de jour", className="demo-kicker"),
            html.Div(className="hdj-day", children=[
                html.Div("1 journée", className="hdj-day-title"),
                html.Div([_chip(s) for s in services], className="hdj-day-chips"),
            ]),
            html.P(hdj_caption, className="demo-caption"),
        ]),
    ])


def episode_example(window: int, min_visits: int) -> html.Div:
    """Schéma : trois venues dans la fenêtre → une seule journée HDJ."""
    days = [(0, ["Infectiologie"]), (round(window * 0.4), ["Dermatologie"]), (round(window * 0.85), ["Infectiologie"])]
    return episode_visual(
        days, window, f"Aujourd'hui · fenêtre de {window} jours",
        f"3 venues séparées pour un même patient. Avec {min_visits} venues ou plus dans la fenêtre, "
        "l'ensemble forme un épisode regroupable.",
        "Les mêmes consultations, coordonnées le même jour : une seule venue, un bilan complet.",
    )


def _episode_days(visits: pd.DataFrame, episode) -> list[tuple[int, list[str]]]:
    v = visits[(visits["patient_id"] == episode.patient_id)
               & visits["date"].between(episode.start, episode.end)].sort_values(["date", "sejour_id"])
    grouped = v.groupby("date")["service"].apply(lambda s: list(dict.fromkeys(s)))
    return [((date - episode.start).days, services) for date, services in grouped.items()]


def real_cases(visits: pd.DataFrame, episodes: pd.DataFrame, window: int) -> list:
    """Épisodes réels lisibles : plusieurs services, venues pas trop serrées sur la frise.

    Triés du plus parlant (plus de venues, plus de services) au moins parlant ; au plus 40.
    """
    e = episodes[episodes["eligible"]]
    multi = e[e["n_services"] >= 2]
    e = (multi if len(multi) else e).sort_values(["n_days", "n_services", "start"],
                                                 ascending=[False, False, True]).head(400)
    readable, fallback = [], []
    for ep in e.itertuples():
        days = _episode_days(visits, ep)
        offsets = [d for d, _ in days]
        spaced = all(b - a >= window * 0.12 for a, b in zip(offsets, offsets[1:]))
        (readable if spaced else fallback).append((ep, days))
        if len(readable) >= 40:
            break
    return readable or fallback[:40]


def real_case(case, window: int) -> html.Div:
    ep, days = case
    low = int(ep.age // 10 * 10)
    n_services = len({s for _, ss in days for s in ss})
    return episode_visual(
        days, window,
        f"Patient de {low} à {low + 9} ans · {ep.start:%Y}",
        f"{ep.n_visits} consultations sur {len(days)} jours de venue, en {ep.span_days} jours, "
        f"dans {n_services} service{'s' if n_services > 1 else ''}.",
        f"Les mêmes consultations le même jour : {len(days) - 1} venue{'s' if len(days) > 2 else ''} "
        f"en moins pour ce patient.",
    )


def layout(params=None) -> html.Div:
    return html.Div([
        step_hero(INDEX, "Où les parcours se fragmentent-ils ?",
                  "Un même patient revient souvent plusieurs fois en quelques semaines, parfois dans plusieurs "
                  "services. Ces venues rapprochées forment un épisode : c'est ce qu'un hôpital de jour pourrait "
                  "réunir en une seule journée.",
                  actions=[export_button()]),
        html.Div(id="pw-takeaways"),
        html.Div(className="grid", children=[
            card("Ce qu'on appelle un épisode", html.Div(id="pw-example"), span=12,
                 subtitle="La fenêtre et le nombre de venues se règlent dans la barre « Périmètre »."),
            card("Un cas réel", html.Div(id="pw-case"), span=12, cls="case-card",
                 subtitle="Un patient de la période, anonymisé : âge par tranche de 10 ans, jours comptés "
                          "depuis la première venue.",
                 extra=[html.Span(id="pw-case-count", className="case-count"),
                        html.Button("Voir un autre patient ↻", id="pw-case-next", className="btn btn-ghost")]),
            card("Épisodes regroupables", html.Div(id="pw-k-episodes"), span=3, cls="kpi-card"),
            card("Patients concernés", html.Div(id="pw-k-patients"), span=3, cls="kpi-card"),
            card("Venues évitables", html.Div(id="pw-k-trips"), span=3, cls="kpi-card"),
            card("Étalement d'un épisode", html.Div(id="pw-k-span"), span=3, cls="kpi-card"),
            card("D'un service à l'autre", graph("pw-sankey", 420), span=7,
                 subtitle="Chaque flux relie le service d'une visite à celui de la visite suivante, "
                          "lorsqu'elle a lieu dans la fenêtre. Une boucle sur le même service = un retour."),
            card("Combien de temps entre deux venues", graph("pw-gaps", 420), span=5,
                 subtitle="En vert, les retours assez rapprochés pour être regroupés."),
            card("Services concernés", graph("pw-potential", 360), span=5,
                 subtitle="Épisodes regroupables impliquant chaque service."),
            card("Combinaisons les plus fréquentes", html.Div(id="pw-patterns"), span=7,
                 subtitle="Services réunis dans un même épisode regroupable."),
        ]),
        step_nav(INDEX),
    ])


def register(app) -> None:
    @app.callback(
        Output("pw-takeaways", "children"), Output("pw-example", "children"),
        Output("pw-k-episodes", "children"), Output("pw-k-patients", "children"),
        Output("pw-k-trips", "children"), Output("pw-k-span", "children"),
        Output("pw-sankey", "figure"), Output("pw-gaps", "figure"), Output("pw-potential", "figure"),
        Output("pw-patterns", "children"),
        Input("filters", "data"),
    )
    def update(filters):
        f = resolved(filters)
        visits, episodes = dataset(filters)
        s = activity_summary(visits, episodes, f["window"])
        eligible = episodes[episodes["eligible"]]
        span = f"{eligible['span_days'].median():.0f} j" if len(eligible) else "–"

        rows = [{
            "pattern": html.Div([_chip(x) for x in r.pattern.split(" + ")], className="chips"),
            "episodes": fmt.integer(r.episodes), "patients": fmt.integer(r.patients),
            "days": fmt.decimal(r.mean_days), "span": f"{r.median_span:.0f} j",
        } for r in top_patterns(episodes, limit=8).itertuples()]

        return (
            takeaways(insights.pathways(visits, episodes, f["window"], f["min_visits"])),
            episode_example(f["window"], f["min_visits"]),
            big_number(fmt.integer(s["eligible_episodes"]), "épisodes", f"sur {fmt.integer(len(episodes))} au total"),
            big_number(fmt.integer(s["eligible_patients"]), "patients", f"{fmt.percent(s['eligible_share'], 1)} des patients suivis"),
            big_number(fmt.integer(s["groupable_trips"]), "venues", "en moins si chaque épisode tient en un jour"),
            big_number(span, "en médiane", "entre la première et la dernière venue"),
            figures.transitions_sankey(service_transitions(visits, f["window"])),
            figures.gap_histogram(visit_gaps(visits), f["window"]),
            figures.conversion_potential_bar(conversion_potential(episodes)),
            table([("pattern", "Services"), ("episodes", "Épisodes"), ("patients", "Patients"),
                   ("days", "Venues / épisode"), ("span", "Étalement médian")],
                  rows, numeric={"episodes", "patients", "days", "span"}),
        )

    @app.callback(
        Output("pw-case", "children"), Output("pw-case-count", "children"),
        Input("filters", "data"), Input("pw-case-next", "n_clicks"),
    )
    def case(filters, clicks):
        f = resolved(filters)
        visits, episodes = dataset(filters)
        cases = real_cases(visits, episodes, f["window"])
        if not cases:
            return html.Div("Aucun épisode regroupable avec ce périmètre.", className="empty"), None
        i = (clicks or 0) % len(cases)
        return real_case(cases[i], f["window"]), f"Exemple {i + 1} sur {len(cases)}"
