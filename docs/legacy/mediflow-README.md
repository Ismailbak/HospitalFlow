# HDJ Agent MVP

Prototype Streamlit de simulation multi-agents pour l'optimisation des hôpitaux de jour (HDJ) — Défi 5 CHU de Guyane.

Ce document explique **ce que fait réellement le code**, formule par formule : comment une saisie utilisateur devient une cohorte de patients simulée, comment le triage et l'ordonnancement calculent attente et revenus, et comment la recommandation finale est choisie. Pour une visite guidée écran par écran (pitch, démo), voir `prezo.md` à la racine du dépôt.

## Sommaire

1. [Problématique](#problématique-adressée)
2. [Installation & lancement](#installation)
3. [Structure du code](#structure-du-code)
4. [Pipeline de bout en bout](#pipeline-de-bout-en-bout)
5. [La configuration (`SimulationConfig`)](#la-configuration-simulationconfig)
6. [Construction de la cohorte patients](#construction-de-la-cohorte-patients)
7. [Les agents](#les-agents-srcagentspy)
8. [Le triage](#le-triage-triageagent)
9. [L'ordonnancement (attente, revenus, saturation)](#lordonnancement-coordinatoragent)
10. [Dimensionnement d'un nouveau HDJ](#dimensionnement-dun-nouveau-hdj)
11. [L'évaluation et les KPI](#lévaluation-evaluatoragent)
12. [Comparaison des scénarios](#comparaison-des-scénarios-metricspy)
13. [L'algorithme de recommandation](#lalgorithme-de-recommandation-recommend_scenario)
14. [Données CHU réelles vs cohorte simulée](#données-chu-réelles-vs-cohorte-simulée)
15. [Persistance & cache](#persistance--cache)
16. [Limites connues du moteur actuel](#limites-connues-du-moteur-actuel)
17. [Références](#références)

## Problématique adressée

Le CHU doit réduire la fragmentation des parcours ambulatoires, mieux utiliser les capacités HDJ existantes, et identifier où créer de nouveaux HDJ. Ce MVP répond à ces questions via 3 scénarios comparés :

| Scénario | Description |
|----------|-------------|
| **Statu quo** | Parcours fragmentés, coordination limitée |
| **Optimisation HDJ existants** | Regroupement et ordonnancement améliorés |
| **Création nouveau HDJ** | HDJ dédié pour la spécialité à plus fort potentiel |

## Installation

```bash
cd mediflow
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

Ouvrir `http://localhost:8501` dans le navigateur.

## Structure du code

```
mediflow/
├── app.py                  # Point d'entrée : config page, CSS, splash, landing, wizard
├── .streamlit/config.toml  # Thème natif Streamlit (couleurs, police, radius — hors CSS)
├── requirements.txt
├── src/
│   ├── data.py              # SimulationConfig + construction déterministe de la cohorte
│   ├── agents.py            # Dataclasses agents + TriageAgent + CoordinatorAgent + EvaluatorAgent
│   ├── simulation.py        # run_scenario / run_all_scenarios (3 scénarios)
│   ├── metrics.py           # Tableaux de comparaison + recommend_scenario (la décision finale)
│   ├── external_data.py     # Lecture des extracts CHU → priors wizard + graphiques
│   └── user_prefs.py        # Persistance locale des saisies (data/last_inputs.json)
├── ui/
│   ├── wizard.py             # Orchestration des 8 étapes, cache de l'analyse
│   ├── wizard_steps.py       # Contenu de chaque étape (formulaire, graphiques, décision)
│   ├── landing.py            # Splash screen + page d'accueil + narration automatique
│   ├── charts.py             # Constructeurs de graphiques Plotly (Sankey, barres, etc.)
│   ├── theme.py              # Palette de couleurs Python (synchronisée avec les CSS)
│   ├── format.py             # Formatage texte pur (€, noms de spécialité, etc.)
│   ├── components.py         # Primitives HTML partagées (logo, panel_title…)
│   └── assets.py             # Chemins vers les fichiers statiques
└── assets/
    ├── theme.css             # Tokens de design (couleurs, radius, ombres) + composants custom
    └── layout.css            # Masquage du chrome Streamlit + composants landing
```

## Pipeline de bout en bout

```
Saisie utilisateur (étape 2, éventuellement préremplie par des priors CHU réels)
        ↓
SimulationConfig (src/data.py)
        ↓
build_hospital_data() → cohorte de patients construite déterministiquement
        ↓
Pour chacun des 3 scénarios (status_quo / optimize_existing / new_hdj) :
   TriageAgent      → affecte chaque patient à un mode de parcours
   CoordinatorAgent → calcule attente simulée, revenu, saturation des ressources
   EvaluatorAgent   → agrège les KPI du scénario
        ↓
metrics.build_comparison_table()      → tableau comparatif des 3 scénarios
metrics.recommend_scenario()          → choix du scénario + justification textuelle
        ↓
Affichage étape par étape (ui/wizard_steps.py)
```

Le moteur est **entièrement déterministe** : à paramètres égaux, le résultat est strictement identique à chaque exécution (pas de tirage aléatoire, pas de Monte Carlo). C'est volontaire — utile en démonstration, mais cela signifie aussi qu'il n'y a ni incertitude ni intervalle de confiance sur les résultats affichés.

## La configuration (`SimulationConfig`)

`src/data.py` — tous les champs qui pilotent la simulation. Chaque ligne précise d'où vient la valeur et si elle est réellement utilisée en aval.

| Champ | Origine | Utilisé pour |
|---|---|---|
| `total_patients` | saisie étape 2 (prérempli si extract CHU) | taille de la cohorte construite |
| `fragmentation_pct` | saisie étape 2 (prérempli, **calculé sur dates réelles** si extract) | `n_frag` |
| `hdj_eligible_pct` | saisie étape 2 (prérempli, **calculé sur dates réelles** si extract) | `n_eligible` |
| `avg_wait_days` | saisie étape 2 | `baseline_wait_days` |
| `avg_act_count` | saisie étape 2 (prérempli depuis `visits_per_patient` réel si extract) | `act_count`, formule de revenu |
| `slot_duration_minutes` | saisie étape 2 | **lu mais jamais utilisé dans aucun calcul** (voir [Limites](#limites-connues-du-moteur-actuel)) |
| `grouping_rate` | **fixé en dur à 0.35**, non exposé dans l'UI | seuil de décision du `TriageAgent` |
| `fragmented_tariff_eur` / `hdj_tariff_eur` | saisie étape 2 | formules de revenu |
| `simulation_days` | saisie étape 2 (14/30/60) | dénominateur des capacités (`capacity × days`) |
| `focus_specialty` | choix étape 1 | spécialité unique simulée ; aussi la spécialité candidate pour un nouveau HDJ |
| `hdj_unit_count` / `hdj_total_beds` / `hdj_daily_slots` / `hdj_exam_capacity_per_day` | saisie étape 2 | capacité des `HDJAgent` et des `ResourceAgent` |
| `hdj_setup_cost_per_slot` | saisie étape 2 | coût d'investissement si `new_hdj` |
| `mean_age`, `visits_per_patient`, `metabolic_cohort_pct`, `data_backed` | priors CHU (optionnels) | influencent la complexité des patients simulés |

## Construction de la cohorte patients

`src/data.py::build_patients()` — **aucune ligne n'est tirée au hasard ni rejouée depuis un vrai PMSI patient par patient.** La cohorte est construite déterministiquement à partir des pourcentages agrégés ci-dessus :

```python
n_frag     = round(n * fragmentation_pct / 100)              # plafonné à n
n_eligible = round(n * hdj_eligible_pct / 100)                # plafonné à n_frag
n_metabolic = round(n * metabolic_cohort_pct / 100)

# Pour chaque patient i (0 ≤ i < n), déterministe sur l'index :
is_fragmented = i < n_frag
hdj_eligible  = is_fragmented and i < n_eligible and act_count >= 2
is_metabolic  = i < n_metabolic

complexity = 4 if is_metabolic else (3 if is_fragmented else 2)
if mean_age >= 55 and is_fragmented:
    complexity = min(5, complexity + 1)

coordination_need = 0.85 if is_metabolic else (0.75 if hdj_eligible else 0.35)
act_count          = avg_act_count if is_fragmented else max(1, avg_act_count - 1)
baseline_wait_days = avg_wait_days + (10 if is_fragmented else 0)
```

Les N premiers patients de l'index sont « fragmentés », les N suivants « éligibles HDJ parmi les fragmentés », etc. — c'est une construction par **seuils sur l'index**, pas un échantillonnage. Mêmes entrées ⇒ cohorte strictement identique.

## Les agents (`src/agents.py`)

| Agent | Champs clés | Rôle |
|---|---|---|
| `PatientAgent` | `specialty`, `complexity`, `coordination_need`, `hdj_eligible`, `assigned_mode`, `simulated_wait_days`, `revenue_eur` | Porte l'état d'un patient à travers triage → ordonnancement → évaluation |
| `HDJAgent` | `daily_slots`, `rooms`, `exam_capacity_per_day`, `assigned_patients`, `utilization` | Une unité HDJ existante (répartie par `build_hdj_units()` à partir de la capacité totale saisie, divisée également entre `hdj_unit_count` unités) |
| `ResourceAgent` | `resource_id` (`SLOTS`/`ROOMS`/`EXAMS`), `capacity`, `demand`, `saturation` | Une ressource partagée, dont la saturation est recalculée à chaque scénario |

`build_agents(data)` instancie ces objets depuis les DataFrames de `HospitalData`. `PathwayMode` est l'enum à 3 valeurs (`FRAGMENTED`, `EXISTING_HDJ`, `NEW_HDJ`) que porte chaque patient une fois trié.

## Le triage (`TriageAgent`)

Logique exacte de `TriageAgent.triage()`, appliquée patient par patient :

```
si not hdj_eligible          → FRAGMENTED (quel que soit le scénario)
sinon selon le scénario :
  status_quo                 → FRAGMENTED (aucun regroupement)
  optimize_existing          → EXISTING_HDJ  si coordination_need ≥ grouping_rate (0.35)
                                FRAGMENTED    sinon
  new_hdj                    → NEW_HDJ       si patient.specialty == new_hdj_specialty
                                EXISTING_HDJ  sinon si coordination_need ≥ grouping_rate × 0.85
                                FRAGMENTED    sinon
```

Remarque : en scénario `new_hdj`, seule la spécialité ciblée part vers la nouvelle unité ; les patients des **autres** spécialités peuvent quand même basculer vers un HDJ existant si leur besoin de coordination est élevé — c'est voulu, un nouveau HDJ ne doit pas dégrader le reste.

## L'ordonnancement (`CoordinatorAgent`)

`CoordinatorAgent.assign()` calcule, pour chaque patient selon son `assigned_mode`, un délai simulé et un revenu :

| Mode | Délai simulé (jours) | Revenu (€) |
|---|---|---|
| `FRAGMENTED` | `baseline_wait + act_count×4 + (6 − complexity)` | `fragmented_tariff × act_count × 0.6` |
| `EXISTING_HDJ` | `max(3, baseline_wait × (1 − reduction) + unit_load × 8)` où `reduction = 0.45 + 0.15 × coordination_need`, `unit_load = min(demande_spécialité / (daily_slots × days), 1.5)` | `hdj_tariff × (1 + 0.1 × act_count)` |
| `NEW_HDJ` | `max(2, baseline_wait × (1 − reduction) + new_load × 5)` où `reduction = 0.55 + 0.2 × coordination_need`, `new_load = demande_new_hdj / (new_hdj_slots × days)` | `hdj_tariff × (1 + 0.15 × act_count)` |

Un HDJ réduit donc toujours l'attente de base (45–75 % selon le mode et la coordination du patient) mais y ajoute une pénalité de charge si l'unité est sollicitée — c'est ce qui permet à la saturation de **dégrader** le bénéfice attendu plutôt que de l'ignorer.

**Saturation des ressources**, recalculée après affectation de tous les patients :

```
SLOTS : demande = patients non-fragmentés          capacité = Σ(daily_slots) × days
ROOMS : demande = 0.35 × patients non-fragmentés    capacité = Σ(rooms) × days
EXAMS : demande = 0.50 × patients non-fragmentés    capacité = Σ(exam_capacity) × days
saturation = min(demande / capacité, 1.5)            # plafonnée à 150 %
```

## Dimensionnement d'un nouveau HDJ

`simulation.py::run_scenario()`, uniquement pour le scénario `new_hdj` :

- La spécialité ciblée est **toujours** `config.focus_specialty` dans le parcours actuel (un repli existe dans `_identify_new_hdj_candidate()` qui classerait les spécialités par potentiel de conversion, mais il n'est jamais atteint tant que l'étape 1 impose une spécialité).
- Le nombre de créneaux de la nouvelle unité : `new_hdj_slots = max(12, int(patients_éligibles_de_la_spécialité / simulation_days × 1.2))` — un minimum de 12 créneaux/jour, sinon 20 % de marge au-dessus du débit moyen requis.

## L'évaluation (`EvaluatorAgent`)

`EvaluatorAgent.summarize()` agrège, pour un scénario donné :

- `avg_wait_days` = moyenne de `simulated_wait_days` sur tous les patients
- `total_revenue_eur` = somme de `revenue_eur`
- `hdj_conversion_rate` = (patients en `EXISTING_HDJ` + `NEW_HDJ`) / total
- `max_resource_saturation` = max des 3 saturations (`SLOTS`/`ROOMS`/`EXAMS`)
- comptes bruts par mode (`fragmented_pathways`, `existing_hdj_pathways`, `new_hdj_pathways`)

## Comparaison des scénarios (`metrics.py`)

- `scenario_investment(result, config)` : 0 € sauf pour `new_hdj`, où c'est `new_hdj_slots × hdj_setup_cost_per_slot`.
- `build_comparison_table()` : pour chaque scénario, `revenue_delta = revenu − revenu(statu quo)` puis `net_gain = revenue_delta − investment`. C'est ce `net_gain` qui pilote la recommandation (section suivante), pas une colonne « score ».
- `specialty_conversion_opportunity()` : classe les spécialités par part de patients éligibles HDJ (utilisé pour identifier la spécialité à plus fort potentiel — affiché mais pas utilisé pour choisir la spécialité du nouveau HDJ, qui reste toujours `focus_specialty`).
- `compute_baseline_delta()` : écarts simples (attente, revenu, conversion, saturation) de chaque scénario par rapport au statu quo.

## L'algorithme de recommandation (`recommend_scenario`)

C'est le cœur décisionnel de l'application — vaut la peine d'être lu en détail, y compris une nuance d'implémentation non évidente.

**Étape 1 — un score composite est calculé pour les 3 scénarios** (affiché dans l'UI via `analysis['recommendation']['scores']`, à titre informatif) :

```
score = wait_gain × 2.0
      + net_revenue_gain / 5000
      + conversion_gain × 40
      − saturation_penalty      # max(0, saturation − 0.85) × 50
```

> ⚠️ **Ce score n'est pas ce qui choisit le scénario gagnant.** Il est calculé et retourné pour transparence, mais la décision réelle (étape 2 ci-dessous) utilise directement `net_gain` et les seuils de saturation, pas ce score composite. C'est une distinction à connaître avant de modifier l'un des deux sans l'autre.

**Étape 2 — la décision réelle**, par branchement explicite sur `net_gain` (gain net = revenu supplémentaire − investissement, vs statu quo) :

```
si net_gain(optimize) ≤ 0 et net_gain(new_hdj) ≤ 0 :
    → statu quo (rien n'est rentable)
sinon si net_gain(new_hdj) > net_gain(optimize) et net_gain(new_hdj) > 0 :
    → new_hdj
sinon si net_gain(optimize) > 0 :
    → optimize_existing
sinon si net_gain(new_hdj) > 0 :
    → new_hdj
sinon :
    → statu quo

# Garde-fou de saturation, appliqué en dernier et prioritaire :
si saturation(optimize_existing) ≥ 85 % et net_gain(new_hdj) > net_gain(optimize) :
    → new_hdj   (même si une autre branche avait déjà tranché)
```

**Étape 3** — une liste de justifications textuelles (`reasons`) est générée selon la branche empruntée, avec les montants exacts en euros, affichée telle quelle à l'étape 8 (« Recommandation »).

## Données CHU réelles vs cohorte simulée

`src/external_data.py` lit les extracts Excel (`documents/data`, consultations externes hashées) pour **2 des 5 spécialités** (`oncologie`, `diabetologie`). Ce qui est réellement calculé à partir des données, et non d'une valeur par défaut :

- **Fragmentation et éligibilité HDJ** (`_pathway_fragmentation()`) : pour chaque patient, on regarde l'écart en jours entre ses séjours successifs dans *ce* service. Fragmenté si un écart ≤ 30 jours existe ; éligible (sous-ensemble) si un écart ≤ 14 jours existe. **Ce sont des planchers, explicitement documentés comme tels dans le code** : l'extract ne voit que les retours dans un seul service, pas les actes réalisés ailleurs (ville, autres établissements) — la fragmentation réelle est très probablement plus élevée.
- **Âge moyen, visites/patient, effectif suggéré** : calculés directement sur l'extract.
- **Cohorte métabolique** (diabétologie uniquement) : patients dont `LIBELLE DIAG` contient diabète/hypoglycémie/hypokaliémie.
- **Patients multi-spécialités** : patients présents dans au moins deux extracts différents.

Ce que ces priors **ne font pas** : ils ne rejouent pas les patients un par un dans le moteur de simulation. Une fois appliqués (`apply_priors_to_session`), ils ne font que préremplir les champs du formulaire de l'étape 2 (`wiz_patients`, `wiz_fragmentation_pct`, etc.) — la cohorte simulée en aval reste une construction déterministe par seuils (section 6), pas un rejeu ligne à ligne du PMSI. Les tarifs et la capacité HDJ restent toujours à la charge de l'utilisateur, jamais préremplis depuis les extracts.

Caveat supplémentaire côté extracts (voir aussi `.cursor/rules/hdj-agent-data-inventory.mdc`) : ces 8 fichiers contiennent quasiment aucune activité HDJ réelle (≈4 lignes `HDJ CONSULTATION` au total) — c'est un corpus de consultations externes fragmentées, utile comme base de calage de la demande, insuffisant seul pour modéliser des parcours HDJ coordonnés.

## Persistance & cache

- `src/user_prefs.py` : les derniers paramètres saisis (`wiz_*`) sont sauvegardés dans `data/last_inputs.json` à la soumission du formulaire et au retour à l'accueil, puis rechargés au prochain lancement de l'app (`apply_saved_inputs`, appelé dans `app.py`).
- `ui/wizard.py::load_analysis()` : le résultat complet de `run_full_analysis()` est mis en cache Streamlit (`st.cache_data`) par empreinte de configuration (`config_cache_key`) — changer un seul paramètre invalide le cache et relance le calcul ; revenir à une config déjà vue le réutilise. `ANALYSIS_CACHE_VERSION` doit être incrémenté manuellement si la forme du résultat change, pour forcer l'invalidation de tous les caches existants.

## Limites connues du moteur actuel

- **Déterministe, pas stochastique** : aucun tirage aléatoire ni intervalle de confiance — un même jeu de paramètres produit toujours exactement le même résultat.
- **`slot_duration_minutes` est saisi mais n'intervient dans aucun calcul** de `CoordinatorAgent.assign()` à ce jour (ni `load_factor`, calculé localement dans la même fonction, qui n'est lui non plus jamais réutilisé). Le champ reste dans le formulaire sans effet sur la sortie.
- **`grouping_rate` (seuil de regroupement du triage) est fixé en dur à 0.35** dans `SimulationConfig`, non exposé dans l'interface.
- **Le `score` composite de `recommend_scenario` n'est pas le mécanisme de décision réel** — voir la section dédiée ci-dessus.
- **La cohorte simulée est une construction paramétrique**, pas un échantillon de vrais patients, même quand les pourcentages d'entrée proviennent d'un calcul réel sur les extracts CHU.
- **Les extracts CHU ne couvrent que 2 des 5 spécialités** de l'app, et ne contiennent presque aucune activité HDJ réelle.

## Références

- Santibañez et al. (2009) — Simulation ambulatoire
- Li et al. (2024) — Agent Hospital
- Sujet HDJ Agent — EL-BAHRI / CARTIER, CHU Guyane
