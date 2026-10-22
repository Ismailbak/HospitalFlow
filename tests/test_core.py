import pandas as pd

from hdj.analytics import recommend
from hdj.data import build_episodes
from hdj.simulation import HDJUnitSpec, SimulationParams, run_simulation


def _visits(rows):
    df = pd.DataFrame(rows, columns=["patient_id", "date", "service"])
    df["date"] = pd.to_datetime(df["date"])
    df["sejour_id"] = range(len(df))
    df["cohort"] = df["service"]
    df["age"] = 50
    return df


def test_episodes_window_is_anchored_on_first_visit():
    v = _visits([
        ("p1", "2024-01-01", "A"), ("p1", "2024-01-20", "B"), ("p1", "2024-02-05", "A"),  # 35 j après la 1re
        ("p2", "2024-01-01", "A"), ("p2", "2024-01-01", "B"),                             # même jour
    ])
    e = build_episodes(v, window_days=30, min_visits=2).sort_values(["patient_id", "start"])
    assert e["n_visits"].tolist() == [2, 1, 2]
    assert e["eligible"].tolist() == [True, False, False]  # p2 : 2 visites mais 1 seul jour de venue
    assert e.iloc[0]["services"] == ("A", "B")


def _params(**overrides):
    base = dict(existing=HDJUnitSpec("HDJ", places_per_day=2), consult_tariff=30, hdj_tariff=100,
                lead_days=1, max_wait_days=30, no_show_rate=0.0, arrival_jitter_days=0, runs=3)
    return SimulationParams(**{**base, **overrides})


def test_simulation_converts_and_respects_capacity():
    rows = [(f"p{i}", "2024-01-08", "A") for i in range(6)] + [(f"p{i}", "2024-01-15", "A") for i in range(6)]
    e = build_episodes(_visits(rows), 30, 2)
    params = _params()
    res = run_simulation(e, params, "2024-01-01", "2024-03-31")
    opt = res["scenarios"]["optimize_existing"]["kpis"]
    assert opt["converted"]["mean"] == 6
    assert opt["trips_avoided"]["mean"] == 6
    assert res["scenarios"]["status_quo"]["kpis"]["mean_delay"]["mean"] == 7
    # 2 places/jour pour 6 demandes le même jour : étalement sur 3 jours ouvrés
    assert max(res["scenarios"]["optimize_existing"]["delays"]) >= 3


def test_recommendation_falls_back_to_status_quo_when_unprofitable():
    rows = [("p1", "2024-01-08", "A"), ("p1", "2024-01-15", "A")]
    e = build_episodes(_visits(rows), 30, 2)
    params = _params(hdj_tariff=10, runs=2)
    rec = recommend(run_simulation(e, params, "2024-01-01", "2024-03-31"), max_occupancy=0.9)
    assert rec["choice"] == "status_quo"
