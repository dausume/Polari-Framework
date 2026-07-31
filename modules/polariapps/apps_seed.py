"""
@cross-cutting
@module polariapps.apps_seed

The first three Polari-Apps (tt-12, Dustin's examples verbatim):
a local wax 3D-printing company, a lean judicial app, and a DMV
policy-analysis build. Each is just a module configuration — the
capability comes from modules that already exist; the app names
the use-case and its front doors.

@consumers
  - polariServer seed loop (idempotent-by-name)
  - polariapps.selftest_apps
"""

import json as _json


def _app(name, title, use_case, description, modules, pages,
         nav=(), personas=(), discipline=''):
    return {'name': name, 'title': title, 'use_case': use_case,
            'description': description,
            'modules_json': _json.dumps(list(modules)),
            'pages_json': _json.dumps(list(pages)),
            'nav_json': _json.dumps(list(nav)),
            'personas_json': _json.dumps(list(personas)),
            'discipline': discipline, 'notes': ''}


def _grp(group, *items):
    return {'group': group, 'items': list(items)}


def _it(label, kind, route='', requires_module='', ref=''):
    item = {'label': label, 'kind': kind}
    if route:
        item['route'] = route
    if requires_module:
        item['requires_module'] = requires_module
    if ref:
        item['ref'] = ref
    return item


SEED_POLARI_APPS = [
    _app('wax-print-shop', 'Wax 3D Printing Company',
         'A local wax 3D-printing company trying different wax '
         'simulations and different auger shapes for the different '
         'models they can offer.',
         'Wax print simulation + recipe optimizer (waxprint), the '
         'materials basis for wax formulations (materialsScience), '
         'auger/part shape variants (mathshapes), simulation '
         'composition (simulations), and the wax sourcing + supply '
         'ledger (waxsupply, supplychain).',
         ('waxprint', 'materialsScience', 'mathshapes',
          'simulations', 'waxsupply', 'supplychain'),
         ('/wax-print-sim', '/display/wax-supply',
          '/display/supply-chain')),
    _app('judicial-lean', 'Lean Judicial App',
         'A lean judicial deployment: court cases as no-code rows, '
         'democratic proofs, term competition and credibility '
         'tracking — nothing else.',
         'The no-code engine with the judicial CourtCase compiler '
         '(polariNoCode) plus the scoring/epistemics stack '
         '(scoring).',
         ('polariNoCode', 'scoring'),
         ('/custom-no-code', '/scoring')),
    _app('dmv-policy-analysis', 'DMV Policy Analysis',
         'A DMV-area policy-analysis build: cost-of-living '
         'evidence, source trust, legislation tracking, and the '
         'accountability scorecards over them.',
         'DMV cost-of-living catalog + trust stack (dmvdata) and '
         'the scoring engine that reads it (scoring).',
         ('dmvdata', 'scoring'),
         ('/scoring/survival', '/scoring/accountability')),
]
