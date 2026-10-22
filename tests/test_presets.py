"""Chaque jeu de démonstration doit aboutir à l'organisation qu'il illustre (sur les données réelles)."""
import pytest

from dashboard.params import PRESETS, matching_preset, missing, preset_values
from dashboard.state import default_filters, simulate


@pytest.mark.parametrize("name", list(PRESETS))
def test_preset_leads_to_its_scenario(name):
    params = preset_values(name)
    assert missing(params) == []
    assert matching_preset(params) == name
    _, reco = simulate(default_filters(), params)
    assert reco["choice"] == name


def test_modified_preset_is_no_longer_flagged_as_demo():
    params = {**preset_values("optimize_existing"), "consult": 31}
    assert matching_preset(params) is None
