# HDJ Agent — CHU de Guyane

Tableau de bord d'aide à la décision pour la gouvernance médico-administrative : reconstruction des
parcours ambulatoires à partir des consultations externes, simulation multi-agents de trois
organisations (statu quo, optimisation de l'HDJ existant, création de HDJ) et recommandation chiffrée.

> Outil de gestion, **pas** d'aide à la décision médicale. Défi 5 — sujet porté par A. EL-BAHRI et C. CARTIER.

## Lancer

```bash
pip install -r requirements.txt
python app.py            # http://127.0.0.1:8050
python -m pytest tests   # tests du moteur
```

**Aucune valeur métier n'est fournie par défaut.** Tarifs, capacité et occupation de l'HDJ existant,
coût des places créées et paramètres d'organisation (délais, absences) se saisissent sur la page
*Scénarios* ; la simulation ne se lance qu'une fois ces champs complets. Ils doivent provenir de
l'établissement (DIM, contrôle de gestion, encadrement de l'HDJ) et sont mémorisés dans le navigateur.
Seuls la fenêtre de regroupement (30 j), le minimum de venues (2) et le nombre de tirages (30)
sont pré-remplis.

Les extractions Excel vont dans `data/raw/` (non versionné). Au premier lancement elles sont converties
en `data/cache/visits_*.parquet` (cache invalidé automatiquement si un fichier change).

## Organisation

```
CHU-Guyanne/
├── app.py                    # point d'entrée (expose aussi `server` pour un déploiement WSGI)
├── hdj/                      # domaine métier — aucune dépendance à l'interface
│   ├── config.py             # chemins, référentiel cohortes / unités → services, valeurs par défaut
│   ├── data/
│   │   ├── loader.py         # Excel → une ligne par visite (séjour externe), cache parquet, filtres
│   │   └── pathways.py       # épisodes de soins, délais entre venues, enchaînements de services
│   ├── simulation/
│   │   ├── scenarios.py      # SimulationParams, HDJUnitSpec, les 3 scénarios
│   │   ├── agents.py         # Patient, HDJUnit, Triage, Coordinator, Evaluator
│   │   └── engine.py         # rejeu Monte Carlo des épisodes réels dans chaque scénario
│   └── analytics/
│       ├── kpis.py           # indicateurs d'activité, potentiel de conversion, qualité des données
│       └── recommend.py      # règle de recommandation + robustesse
├── dashboard/                # interface Dash
│   ├── __init__.py           # create_app() : coque, routage, filtres globaux, export CSV
│   ├── components.py         # en-tête, barre de filtres, cartes, tuiles, tableaux
│   ├── figures.py            # graphiques Plotly
│   ├── theme.py              # palette du logo CHU + template Plotly
│   ├── state.py              # données filtrées en cache
│   ├── params.py             # paramètres saisis : définitions, validation, conversion
│   ├── insights.py           # phrases « À retenir » calculées sur les données
│   ├── pages/                # activity · pathways · parameters · simulation · decision · method
│   └── assets/               # style.css, logo.png
├── tests/
├── data/raw/                 # extractions (ignorées par git)
└── docs/                     # sujet du défi, présentation, ancien README (mediflow)
```

## Navigation

Un parcours de lecture en cinq étapes (barre de progression dans l'en-tête, boutons précédent / suivant).
Chaque étape s'ouvre sur une question, un paragraphe d'explication et un bandeau « À retenir » calculé
sur les données ; chaque graphique indique comment le lire. La barre « Périmètre » (période, cohortes,
âge, fenêtre de regroupement, venues minimales) s'applique à toutes les étapes.

| Étape | Question |
|---|---|
| **1 · Données** | Que contiennent les extractions : combien de patients, quels services, quand ? |
| **2 · Parcours** | Qu'est-ce qu'un épisode, où les parcours se fragmentent-ils, combien de venues sont regroupables ? |
| **3 · Paramètres** | Quels sont les moyens de l'établissement ? (saisie obligatoire, mémorisée dans le navigateur) |
| **4 · Simulation** | Que fait chaque agent avec ces moyens : orientation, planification, occupation, délais ? |
| **5 · Décision** | Quelle organisation retenir, pourquoi, et sur quelles valeurs repose ce choix ? |

*Méthode & données* (lien en haut à droite) détaille la chaîne de traitement, les agents, les
hypothèses, les limites et la qualité de chaque fichier.

## Modèle

1. **Visites** : une ligne par séjour externe. Le *service* est l'unité de consultation réelle ;
   les unités génériques (« MEDECINE CONSULTATIONS EXTERNES ») prennent le nom de la cohorte.
2. **Épisodes** : visites d'un patient (toutes cohortes) dans une fenêtre de *N* jours ancrée sur la
   première venue. **Convertible** s'il compte au moins *k* jours de venue distincts.
3. **Simulation** — chaque épisode réel devient un `PatientAgent` :
   - `TriageAgent` : non convertible ou statu quo → fragmenté ; sinon HDJ dédié couvrant l'une de ses
     spécialités, à défaut HDJ existant s'il l'accepte ;
   - `CoordinatorAgent` : première journée ouverte et non pleine entre *demande + délai d'organisation*
     et *demande + attente max.* ; absence → place perdue et replanification ; aucune date → renvoi en fragmenté ;
   - `HDJUnitAgent` : places/jour, jours d'ouverture, activité de fond tirée selon l'occupation actuelle ;
   - `EvaluatorAgent` : venues, délai de réalisation du bilan, occupation, recettes, coûts.
4. **Monte Carlo** : *R* tirages (date de demande ± j, activité de fond, absences) ; les trois scénarios
   d'un tirage partagent la même graine. Résultats en moyenne et 10e–90e centiles.
5. **Recommandation** : scénario recevable (aucune unité au-dessus du seuil d'occupation, délai non
   dégradé) au gain net annuel moyen le plus élevé ; robustesse = part des tirages où il reste premier.

## Limites

Voir la page *Méthode & données*. En résumé : consultations externes uniquement (fragmentation
sous-estimée), diagnostics et actes CCAM quasi absents hors endocrinologie, tarifs indicatifs saisis
par l'utilisateur, activité HDJ existante paramétrée faute de données.

## Références

- Santibáñez P. et al. (2009). *Reducing patient wait times and improving resource utilization at an ambulatory care unit through simulation.*
- Li J. et al. (2024). *Agent Hospital: A Simulacrum of Hospital with Evolvable Medical Agents.*
- Creps J. & Lotfi V. (2017). *A dynamic approach for outpatients scheduling.*
