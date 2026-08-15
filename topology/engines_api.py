"""
@module topology.engines_api

sep-4 (decision 9): the ENGINE DATA PAGES. Every compute engine gets
its own tile whose page answers three questions honestly:
  - placement — which instances the topology assigns its modules to
    (ModuleAssignment rows via resolve_provider, refusals included)
  - reachability — the *_remote ladder's halves, each stated: env
    knob set? binding row bound? topology resolved? live capability?
  - usage — EngineUsageWindow rows through THIS instance's seam, or
    'not tracked yet' (never an empty chart pretending to be zero)

Dual natures (decision 9): odoo/livekit/reticulum are engine+app —
their tiles open their OWN UI and this page rides as the secondary
view; msci/cad are engine-only and this page IS their page.

@consumers
  - polariServer (instantiated next to the other APIs)
  - polari-platform-angular /engines/:engine
  - topology.selftest_engines_api
"""

import os

from objectTreeDecorators import treeObject, treeObjectInit

from topology.engine_metering import binding_url, usage_report

#: The engine registry: knob + the module keys whose assignments
#: place it + how to probe capability (lazy import, may be absent).
#: `app` names the PolariAppDefinition wearing the tile (duals keep
#: their own UI; engine-only apps point at this page).
ENGINES = {
    'msci': {
        'title': 'Materials-science engines (DFT / FEM)',
        'knob': 'MSCI_ENGINES_URL',
        'modules': ['materialsScience.dft', 'materialsScience.fem'],
        'nature': 'engine-only',
        'app': 'engine-msci',
    },
    'cad': {
        'title': 'CAD engines (trimesh / FreeCAD)',
        'knob': 'CAD_ENGINES_URL',
        'modules': ['mathshapes.cad'],
        'nature': 'engine-only',
        'app': 'engine-cad',
    },
    'business-ops': {
        'title': 'Business ops (Odoo)',
        'knob': '',
        'modules': ['odooconnect'],
        'nature': 'engine+app',
        'app': 'app-business',
    },
    'livekit': {
        'title': 'Meetings (LiveKit)',
        'knob': 'LIVEKIT_URL',
        'modules': ['collab'],
        'nature': 'engine+app',
        'app': 'app-collaboration',
    },
    'reticulum': {
        'title': 'Reticulum transport (sidecar)',
        'knob': 'RETICULUM_SIDECAR_URL',
        'modules': ['reticulum'],
        'nature': 'engine+app',
        'app': '',
    },
}


def _capability_probe(engine):
    """The live /capability answer where a seam exposes one; None =
    no probe exists for this engine kind (stated, not guessed)."""
    try:
        if engine == 'msci':
            from materialsScience.engines.remote import (
                remote_capability)
            return remote_capability(timeout=4)
        if engine == 'cad':
            from mathshapes.cad_remote import remote_capability
            return remote_capability(timeout=4)
    except Exception:
        return None
    return None


def engine_report(manager, engine):
    """The one data-page payload for one engine."""
    spec = ENGINES.get(engine)
    if spec is None:
        return {'ok': False,
                'error': f'no engine kind {engine!r} '
                         f'(known: {sorted(ENGINES)})'}
    knob = spec['knob']
    knob_value = (os.environ.get(knob, '') or '').strip() \
        if knob else ''
    bound = binding_url(engine)

    placement = []
    for module in spec['modules']:
        try:
            from topology.provider_registry import resolve_provider
            resolved = resolve_provider(module)
        except Exception as e:
            resolved = {'ok': False, 'error': str(e)}
        placement.append({
            'module': module,
            'resolved': bool(resolved.get('ok')),
            'instance': resolved.get('instance', ''),
            'url': resolved.get('url', ''),
            'refusal': ('' if resolved.get('ok')
                        else resolved.get('error', '')),
        })

    capability = _capability_probe(engine)
    reachability = {
        'ladder': [
            {'rung': 'env knob', 'name': knob or '(none for this '
             'engine kind)', 'set': bool(knob_value),
             'value': knob_value},
            {'rung': 'binding row (EngineProviderBinding)',
             'bound': bool(bound), 'url': bound},
            {'rung': 'topology resolve',
             'resolved': any(p['resolved'] for p in placement)},
        ],
        'capability': capability,
        'capabilityNote': ('' if capability is not None else
                           'no live capability answer — worker '
                           'unreachable, unbound, or this engine '
                           'kind exposes no probe'),
    }

    return {
        'ok': True,
        'engine': engine,
        'title': spec['title'],
        'nature': spec['nature'],
        'app': spec['app'],
        'placement': placement,
        'reachability': reachability,
        'usage': usage_report(manager, engine),
    }


class EnginesAPI(treeObject):
    """GET /api/engines (the tile list) + /api/engines/{engine}."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/engines'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/engines', self, suffix='engines')
            add('/api/engines/{engine}', self, suffix='engine')

    def on_get_engines(self, request, response):
        rows = []
        for engine in sorted(ENGINES):
            report = engine_report(self.manager, engine)
            rows.append({
                'engine': engine,
                'title': report['title'],
                'nature': report['nature'],
                'app': report['app'],
                'reachable': any(p['resolved']
                                 for p in report['placement'])
                or bool(report['reachability']['ladder'][0]['set'])
                or bool(report['reachability']['ladder'][1]['bound']),
                'tracked': report['usage']['tracked'],
            })
        response.media = {'ok': True, 'engines': rows}

    def on_get_engine(self, request, response, engine):
        report = engine_report(self.manager, engine)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
