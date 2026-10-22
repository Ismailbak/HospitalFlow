"""Méthode & données : comment le système raisonne, sur quoi, et avec quelles limites."""
from __future__ import annotations

from dash import dcc, html

from dashboard import format as fmt
from dashboard.components import card, page_hero, table
from hdj.analytics import data_quality
from hdj.data import load_visits

STEPS = [
    ("1", "Données", "8 extractions de consultations externes (IPP hachés). Une visite = un séjour externe."),
    ("2", "Épisodes", "Les visites d'un patient sont regroupées par fenêtre glissante ancrée sur la première venue."),
    ("3", "Triage", "L'agent de triage oriente chaque épisode : parcours fragmenté, HDJ existant ou HDJ dédié."),
    ("4", "Ordonnancement", "Le coordinateur cherche la première journée libre, gère saturation, absences et replanification."),
    ("5", "Évaluation", "L'évaluateur agrège venues, délais, occupation et recettes, sur N tirages Monte Carlo."),
    ("6", "Recommandation", "Scénario recevable (occupation, délai) au gain net annuel le plus élevé, avec sa robustesse."),
]

AGENTS = [
    ("PatientAgent", "Un épisode réel : services, jours de venue, étalement.", "Porte son mode, sa journée HDJ, son attente."),
    ("HDJUnitAgent", "Une unité HDJ : places/jour, jours d'ouverture, activité de fond.", "Expose ses places libres jour par jour."),
    ("TriageAgent", "Orientation de parcours (pas de diagnostic).", "HDJ dédié si une spécialité couverte, sinon existant s'il l'accepte."),
    ("CoordinatorAgent", "Ordonnanceur.", "Première date libre ≥ demande + délai d'organisation ; renvoi en fragmenté au-delà de l'attente max."),
    ("EvaluatorAgent", "Évaluation médico-économique.", "Venues, délai du bilan, occupation, recettes, coûts."),
]

ASSUMPTIONS = """
- **Épisode convertible** : au moins *n* jours de venue distincts dans la fenêtre (paramètres de la barre de filtres).
  C'est une approximation de l'éligibilité HDJ, à confronter aux critères de gradation des prises en charge ambulatoires.
- **Recettes** : consultation et journée HDJ valorisées par des tarifs **forfaitaires indicatifs** saisis par l'utilisateur,
  pas par les GHS réels.
- **Activité de fond** de l'HDJ existant : tirée chaque jour selon le taux d'occupation actuel saisi.
- **Aléa** : date de demande (± j), activité de fond, absences. Les 3 scénarios d'un tirage partagent la même graine.
- **Coût** : seules les places créées ont un coût (coût annuel par place × années de la période).
"""

LIMITS = """
- Les extractions ne contiennent que des **consultations externes** : les actes de ville, les autres établissements
  et l'hospitalisation ne sont pas visibles, la fragmentation réelle est donc **sous-estimée**.
- Diagnostics renseignés uniquement pour la cohorte endocrinologie ; actes CCAM quasi absents :
  le regroupement se fait sur les **venues**, pas sur le contenu médical des actes.
- La cohorte endocrinologie-diabétologie (2024-2026) est vue **majoritairement aux urgences** : son potentiel HDJ
  ne peut pas être estimé de façon fiable avec ces données.
- Les fichiers 2020-2023 ne couvrent que 2 cohortes : la période par défaut commence au 01/01/2024.
- Moins de 5 venues en « HDJ CONSULTATION » dans tout le corpus : l'activité HDJ existante est un **paramètre**, pas une mesure.
"""


def layout(params=None) -> html.Div:
    quality = data_quality(load_visits())
    rows = [{
        "file": r.source_file.replace("_A.xlsx", "").replace("Données_Externes_", ""),
        "cohort": r.cohort, "period": f"{r.start:%m/%Y} → {r.end:%m/%Y}",
        "visits": fmt.integer(r.visits), "patients": fmt.integer(r.patients),
        "diag": fmt.percent(r.with_diagnosis), "ccam": fmt.percent(r.with_ccam), "hdj": fmt.integer(r.hdj_visits),
    } for r in quality.itertuples()]

    return html.Div([
        page_hero("Référence", "Méthode & données",
                  "Comment HDJ Agent raisonne, à partir de quoi, et ce qu'il ne peut pas dire."),
        html.Div(className="grid", children=[
            card("Chaîne de traitement", html.Ol(className="steps", children=[
                html.Li(className="step", children=[
                    html.Span(n, className="step-num"), html.Div([html.Strong(t), html.P(d)]),
                ]) for n, t, d in STEPS
            ]), span=12),
            card("Agents", table(
                [("agent", "Agent"), ("role", "Rôle"), ("rule", "Règle de décision")],
                [{"agent": html.Code(a), "role": r, "rule": d} for a, r, d in AGENTS],
            ), span=12),
            card("Hypothèses", dcc.Markdown(ASSUMPTIONS, className="prose"), span=6),
            card("Limites connues", dcc.Markdown(LIMITS, className="prose"), span=6),
            card("Qualité des données par fichier source", table(
                [("file", "Fichier"), ("cohort", "Cohorte"), ("period", "Période"), ("visits", "Visites"),
                 ("patients", "Patients"), ("diag", "Avec diagnostic"), ("ccam", "Avec acte CCAM"),
                 ("hdj", "Venues HDJ")],
                rows, numeric={"visits", "patients", "diag", "ccam", "hdj"},
            ), span=12),
        ]),
    ])


def register(app) -> None:
    """Page statique : pas de callback."""
