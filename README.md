# HDJ Agent MVP

Prototype Streamlit de simulation multi-agents pour l'optimisation des hôpitaux de jour (HDJ) — Défi 5 CHU de Guyane.

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

## Structure

```
mediflow/
├── app.py              # Dashboard Streamlit
├── requirements.txt
├── README.md
└── src/
    ├── data.py         # Données synthétiques + config
    ├── agents.py       # Agents patients, HDJ, ressources, triage, coordinateur
    ├── simulation.py   # Moteur de scénarios
    └── metrics.py      # KPIs et recommandation
```

## Indicateurs restitués

- Délai moyen simulé par scénario
- Taux de conversion en parcours HDJ
- Saturation des ressources (créneaux, salles, examens)
- Revenus estimatifs
- Potentiel de conversion par spécialité
- Recommandation automatique (statu quo / optimiser / créer HDJ)

## Données

Le MVP utilise des **données synthétiques** réalistes (5 spécialités, 500+ patients simulés). Le module `src/data.py` expose `load_hospital_data()` pour brancher ultérieurement des extracts PMSI / CCAM / consultations anonymisées.

## Hypothèses ajustables (sidebar)

- Volume patients
- Capacité salles / créneaux
- Seuil de regroupement HDJ
- Durée des créneaux
- Tarifs parcours fragmenté vs HDJ
- Horizon de simulation

## Références

- Santibañez et al. (2009) — Simulation ambulatoire
- Li et al. (2024) — Agent Hospital
- Sujet HDJ Agent — EL-BAHRI / CARTIER, CHU Guyane
