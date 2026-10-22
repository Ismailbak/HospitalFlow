from dashboard.components import METHOD_PATH, STEPS

from . import activity, decision, method, parameters, pathways, simulation

_STEP_PAGES = [activity, pathways, parameters, simulation, decision]

ROUTES = {path: page for (path, _), page in zip(STEPS, _STEP_PAGES)}
ROUTES[METHOD_PATH] = method
