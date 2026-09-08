"""
Selftest for the islemesh module (mac-1).

Run from polari-framework/:
    python3 -m islemesh.islemesh_selftest        (container root)
    PYTHONPATH=modules python3 -m islemesh.islemesh_selftest (host)

Stdlib-only: parsers + mock payloads + vocabulary coherence — no
DB, no falcon, no treeObject machinery. Covers: registry parsing
(isle's registry.sample.json shape incl. modes drift + absent
fields), fragment parsing (https/mtls/redirect blocks, upstream
resolution, brace balance), the mock feed's flag discipline (every
payload declares mock_network — the thing real data never does),
and that the mock exercises the REAL parse pipeline.
"""

import json

from islemesh.custom.islemesh_constants import (
    AVAILABILITY_MODES, CONNECTIVITY_MODES, DOWN_TRIGGERS,
    INGEST_KINDS, MOCK_BANNER, PACKAGE_KINDS, PERMIT_PROTOCOLS,
    PLACEMENTS, REALIZATION_KINDS, UP_TRIGGERS, UPLINK_KINDS,
)
from islemesh.custom.islemesh_mock import mock_ingests, mock_realizations
from islemesh.custom.islemesh_parse import (
    parse_fragment, parse_fragments, parse_registry,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


# ---- fixtures (isle's own registry.sample.json shape) ---------------

SAMPLE_REGISTRY = {
    'domains': {'myapp.local': 'myapp'},
    'subdomains': {'api.myapp.local': 'myapp'},
    'apps': {
        'health': {'domain': 'health.local', 'services': [],
                   'modes': [], 'updated_at': ''},
        'myapp': {
            'domain': 'myapp.local',
            'services': [
                {'name': 'api', 'subdomain': 'api',
                 'container': 'myapp-api-1', 'port': 3000,
                 'protocol': 'http'},
                {'name': 'web', 'subdomain': 'web',
                 'container': 'myapp-web-1', 'port': 8080,
                 'protocol': 'http'},
            ],
            'modes': ['local'],
            'updated_at': '2025-12-19T10:30:45.123456',
        },
        'webapp': {
            'domain': 'webapp.local',
            'availability_mode': 'on-demand',
            'services': [
                {'name': 'frontend', 'subdomain': 'frontend',
                 'container': 'webapp-frontend-1', 'port': 3000,
                 'protocol': 'http'}],
            'modes': ['isle'],
            'updated_at': '2025-12-19T11:15:22.789012',
        },
    },
}

FRAGMENT = """
upstream myapp_backend {
    server backend:8443;
    server backend2:8443;
}
server {
    listen 80;
    server_name myapp.local api.myapp.local;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl http2;
    server_name myapp.local;
    ssl_certificate /etc/nginx/ssl/certs/myapp.local.crt;
    location / {
        proxy_pass https://myapp_backend;
    }
}
server {
    listen 443 ssl http2;
    server_name api.myapp.local;
    ssl_verify_client on;
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
"""


def main():
    # ---- registry parsing -------------------------------------------
    parsed = parse_registry(SAMPLE_REGISTRY, 'isle-core')
    apps = {a['name']: a for a in parsed['apps']}
    check('all apps parsed (incl. empty health)', len(apps) == 3)
    check('domain carried', apps['myapp']['domain'] == 'myapp.local')
    check('device attributed',
          apps['myapp']['device_name'] == 'isle-core')
    check('absent availability_mode defaults always-available',
          apps['myapp']['availability_mode'] == 'always-available')
    check('present availability_mode kept',
          apps['webapp']['availability_mode'] == 'on-demand')
    check('modes sorted list', apps['webapp']['modes'] == ['isle'])
    services = {s['name']: s for s in parsed['services']}
    check('services keyed app/service',
          'myapp/api' in services and 'myapp/web' in services)
    check('service fields carried',
          services['myapp/api']['container'] == 'myapp-api-1'
          and services['myapp/api']['port'] == 3000)
    check('services carry the device (replace semantics reach '
          'them)', all(s['device_name'] == 'isle-core'
                       for s in parsed['services']))
    check('real data is never mock',
          not apps['myapp']['is_mock']
          and not services['myapp/api']['is_mock'])
    # tolerance: modes as scalar, junk service entries
    drifted = parse_registry(
        {'apps': {'odd': {'modes': 'local',
                          'services': [None, 'junk']}}}, 'dev')
    check('schema drift tolerated (scalar modes, junk services)',
          drifted['apps'][0]['modes'] == ['local']
          and drifted['services'] == [])

    # ---- fragment parsing -------------------------------------------
    permits = parse_fragment(FRAGMENT, 'isle-core',
                             app_name='myapp',
                             fragment_ref='myapp.conf')
    by_key = {(p['server_name'], p['listen_port']): p
              for p in permits}
    check('four permits (2 names x port 80, 2 on 443)',
          len(permits) == 4, str(sorted(by_key)))
    check('redirect block is an http permit',
          by_key[('myapp.local', 80)]['protocol'] == 'http')
    check('ssl listen is https',
          by_key[('myapp.local', 443)]['protocol'] == 'https')
    check('ssl_verify_client makes https-mtls',
          by_key[('api.myapp.local', 443)]['protocol']
          == 'https-mtls')
    check('upstream resolved to members',
          by_key[('myapp.local', 443)]['upstream']
          == 'backend:8443,backend2:8443')
    check('direct proxy_pass kept verbatim',
          by_key[('api.myapp.local', 443)]['upstream']
          == 'http://127.0.0.1:3000')
    check('permit protocols all in vocabulary',
          all(p['protocol'] in PERMIT_PROTOCOLS for p in permits))
    check('fragment provenance carried',
          all(p['fragment_ref'] == 'myapp.conf' for p in permits))
    named = parse_fragments({'other.conf': FRAGMENT}, 'dev')
    check('filename stem attributes the app',
          named and all(p['app_name'] == 'other' for p in named))
    check('empty/garbage fragment yields no permits',
          parse_fragment('', 'dev') == []
          and parse_fragment('server { broken', 'dev') == [])

    # ---- the mock feed ----------------------------------------------
    ingests = mock_ingests()
    # 'engine' is an app-declared ingest (isle app deploy --engine),
    # not part of the device/registry/fragment mock feed; 'vpn' is
    # the vpn module's acceptor (its own mock = vpn_demo, vpn-1).
    check('mock covers every device-facing ingest kind',
          {kind for kind, _ in ingests}
          == set(INGEST_KINDS) - {'engine', 'vpn'})
    check('EVERY mock payload declares mock_network '
          '(the flag real data never carries)',
          all(payload.get('mock_network') is True
              for _, payload in ingests))
    check('mock payloads are json-serializable',
          bool(json.dumps([p for _, p in ingests])))
    for kind, payload in ingests:
        if kind == 'registry':
            rows = parse_registry(payload['registry'],
                                  payload['device'], is_mock=True)
            check('mock registry parses through the real parser',
                  len(rows['apps']) == 3
                  and all(a['is_mock'] for a in rows['apps']))
        if kind == 'fragments':
            rows = parse_fragments(payload['fragments'],
                                   payload['device'], is_mock=True)
            check('mock fragments (%s) parse through the real '
                  'parser' % payload['device'],
                  len(rows) >= 1
                  and all(p['is_mock'] for p in rows))
            if payload['device'] == 'isle-core':
                protos = {p['protocol'] for p in rows}
                check('mock matrix shows all three protocol '
                      'classes', protos == set(PERMIT_PROTOCOLS),
                      str(protos))
        if kind == 'device':
            uplinks = payload.get('uplinks') or []
            check('mock uplink kinds valid (%s)'
                  % payload['device'],
                  all(u['kind'] in UPLINK_KINDS for u in uplinks))
            mode = payload['facts'].get('connectivity_mode')
            check('mock connectivity mode valid (%s)'
                  % payload['device'], mode in CONNECTIVITY_MODES)
    realizations = mock_realizations()
    check('mock realizations all flagged + kinds valid',
          all(r['is_mock'] and r['kind'] in REALIZATION_KINDS
              for r in realizations))
    check('mock includes the kvm hardware-pin example',
          any(r['kind'] == 'kvm' and r['hardware_pin_device']
              for r in realizations))
    check('mock package kinds valid',
          all(r.get('package_kind', '') in PACKAGE_KINDS
              for r in realizations))

    # ---- basis coherence (stdlib AST — treeObjects can't be
    # constructed here, so check the class SOURCE: every __init__
    # param must be assigned to self, or the decorator silently
    # drops it — the device_name-on-IsleAppService bug, live-caught
    # 2026-08-07) --------------------------------------------------
    import ast
    import os
    basis_path = os.path.join(os.path.dirname(__file__),
                              'islemesh_basis.py')
    tree = ast.parse(open(basis_path).read())
    unassigned = []
    for cls in [n for n in ast.walk(tree)
                if isinstance(n, ast.ClassDef)]:
        for fn in [n for n in cls.body
                   if isinstance(n, ast.FunctionDef)
                   and n.name == '__init__']:
            params = ({a.arg for a in fn.args.args}
                      - {'self', 'manager'})
            assigned = {node.attr for node in ast.walk(fn)
                        if isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == 'self'}
            for missing in sorted(params - assigned):
                unassigned.append('%s.%s' % (cls.name, missing))
    check('every basis __init__ param is assigned to self '
          '(decorator drops the rest silently)',
          not unassigned, str(unassigned))

    # ---- engine binder (§20.4) --------------------------------------
    from islemesh.custom.islemesh_engines import bind_engine, _BINDERS
    saved = []
    # a manager complete enough to construct treeObjects
    fakemgr = type('M', (), {'objectTables': {}, 'idList': []})()
    # unknown kind: recorded, not bound, honest note
    bound, to, note = bind_engine(fakemgr, 'x', 'weather', 'u',
                                  saved.append)
    check('unknown engine kind records unbound + honest',
          not bound and 'no polari consumer' in note)
    # known kind: binds when odooconnect is importable (full tree),
    # else records available-but-unbound naming the consumer
    try:
        import odooconnect.odoo_basis  # noqa: F401
        odoo_here = True
    except ImportError:
        odoo_here = False
    bound, to, note = bind_engine(fakemgr, 'books', 'business-ops',
                                  'http://books.isle', saved.append)
    if odoo_here:
        cfg = next((r for r in fakemgr.objectTables.get(
            'OdooInstanceConfig', {}).values()
            if getattr(r, 'name', '') == 'books'), None)
        check('business-ops binds an OdooInstanceConfig at the url',
              bound and cfg is not None
              and getattr(cfg, 'base_url', '') == 'http://books.isle')
    else:
        check('business-ops unbound when odooconnect absent, '
              'names it', not bound and to == 'odooconnect')
    check('business-ops + odoo both map to the odoo binder',
          _BINDERS['business-ops'][0] == 'odooconnect'
          and _BINDERS['odoo'][0] == 'odooconnect')

    # ---- sep-4: ladder-engine binders (msci/cad) ---------------------
    # treeObjectInit does not insert into a FAKE manager's tables —
    # save() stands in for the real persistence, inserting into the
    # table so the second bind exercises the real dedup path.
    table = {}
    fakemgr.objectTables['EngineProviderBinding'] = table

    def save_binding(row):
        table[getattr(row, 'name', '')] = row

    bound, to, note = bind_engine(fakemgr, 'science-1', 'msci',
                                  'http://msci.isle:9500',
                                  save_binding)
    binding = table.get('msci')
    check('sep-4: msci binds an EngineProviderBinding row at the '
          'url (the row form of MSCI_ENGINES_URL)',
          bound and to == 'EngineProviderBinding:msci'
          and binding is not None
          and getattr(binding, 'url', '') == 'http://msci.isle:9500'
          and getattr(binding, 'bound_from', '') == 'science-1',
          note)
    # re-bind updates the SAME row, never a duplicate. (The table
    # may hold the row under an id key too — treeObjectInit
    # self-inserts on real-ish managers — so count by NAME.)
    bind_engine(fakemgr, 'science-2', 'msci',
                'http://msci2.isle:9500', save_binding)
    named = {id(r) for r in table.values()
             if getattr(r, 'name', '') == 'msci'}
    check('sep-4: re-binding msci updates the one row',
          len(named) == 1
          and getattr(table['msci'], 'url', '')
          == 'http://msci2.isle:9500'
          and getattr(table['msci'], 'bound_from', '')
          == 'science-2')
    # a manager without the topology tables refuses honestly
    bare = type('M', (), {'objectTables': {}, 'idList': []})()
    bound, to, note = bind_engine(bare, 'x', 'cad', 'http://c',
                                  save_binding)
    check('sep-4: cad binder refuses when topology tables absent, '
          'names the consumer',
          not bound and to == 'topology' and 'not present' in note,
          f'{bound} {to!r} {note!r}')

    # ---- ai-3: the reasoning binder ----------------------------------
    # NEVER exercise the real set_active here — in-container this
    # selftest runs on the LIVE instance and would flip its active
    # provider. A recorder stands in; restored in finally.
    check('ai-3: reasoning maps to the reasoning_config binder',
          _BINDERS['reasoning'][0] == 'reasoning_config')
    try:
        from polariApiServer import reasoning_config as _rc
    except ImportError:
        _rc = None
    if _rc is None:
        bound, to, note = bind_engine(fakemgr, 'localai',
                                      'reasoning', 'http://l',
                                      saved.append)
        check('ai-3: reasoning unbound when reasoning_config '
              'absent, names it',
              not bound and to == 'reasoning_config')
    else:
        recorded = []
        real_set_active = _rc.set_active
        _rc.set_active = lambda name, settings=None: recorded.append(
            (name, settings or {}))
        try:
            bound, to, note = bind_engine(
                fakemgr, 'localai', 'reasoning',
                'http://localai.isle:8080/', saved.append)
        finally:
            _rc.set_active = real_set_active
        check('ai-3: reasoning binds the managed config to '
              'openai_compatible at the /v1 base_url',
              bound and to == 'reasoning_config:openai_compatible'
              and recorded == [('openai_compatible',
                                {'base_url':
                                 'http://localai.isle:8080/v1'})],
              f'{bound} {to!r} {recorded!r}')

    # ---- ai-2: the derived AI store section --------------------------
    from islemesh.islemesh_catalog import (ai_tool_install_plan,
                                           ai_tool_options)
    try:
        from appstore.appstore_seed import SEED_AI_TOOLS
    except ImportError:
        SEED_AI_TOOLS = []
    if SEED_AI_TOOLS:
        ai_opts = ai_tool_options(SEED_AI_TOOLS, set())
        check('ai-2: all four seeded tools derive as category-ai '
              'entries with sovereignty stated',
              [o['name'] for o in ai_opts]
              == ['claude', 'localai', 'null', 'openai']
              and all(o['category'] == 'ai' and o['derived']
                      and 'internet_required' in o
                      and 'data_leaves_isle' in o
                      for o in ai_opts))
        plans = {o['name']: ai_tool_install_plan(o)
                 for o in ai_opts}
        check('ai-2: built-in installs as NOTHING (honesty)',
              plans['null']['ok'] and plans['null']['steps'] == [])
        check('ai-2: remote intermediaries install as the '
              '/ai/providers binding flow, credential human-only',
              all('select' in p['steps'][0]
                  and 'set_auth' in p['steps'][1]
                  and 'human' in p['steps'][1]
                  for p in (plans['claude'], plans['openai'])))
        check('ai-2: local-hosted installs as isle app deploy '
              '--engine reasoning (the ai-3 binder wires it)',
              'isle app deploy localai' in plans['localai']['steps'][0]
              and '--engine reasoning' in plans['localai']['steps'][0])
        check('ai-2: a taken name is skipped (persisted rows win)',
              len(ai_tool_options(SEED_AI_TOOLS, {'localai'})) == 3)
        check('ai-2: unknown hosting kind refuses honestly',
              not ai_tool_install_plan({'hosting': 'bogus'})['ok'])
    else:
        check('ai-2: appstore seeds unavailable in this context '
              '(stated, suite skipped)', True)

    # ---- catalog install plans (§20.1/§20.3) ------------------------
    from islemesh.islemesh_catalog import SEED_CATALOG, install_plan
    kinds = {e['kind'] for e in SEED_CATALOG}
    check('catalog seeds both proven variants',
          'mesh-app' in kinds and 'polari-app' in kinds)
    check('seed catalog is never mock',
          all(not e.get('is_mock') for e in SEED_CATALOG))
    by_name = {e['name']: e for e in SEED_CATALOG}
    mesh = install_plan(by_name['whoami'])
    check('mesh-app plan calls isle app deploy',
          mesh['ok'] and 'isle app deploy whoami' in mesh['steps'][0]
          and '--image traefik/whoami' in mesh['steps'][0])
    odoo = install_plan(by_name['odoo'])
    check('engine app plan: image ref + --engine business-ops',
          '--image odoo:16' in odoo['steps'][0]
          and '--engine business-ops' in odoo['steps'][0])
    papp = install_plan(by_name['polari'])
    check('polari-app plan is ONE shell-launcher step that installs',
          papp['ok'] and any('shell launcher' in s
                             for s in papp['steps'])
          and any('--install' in s for s in papp['steps']))
    check('unknown kind plan refuses honestly',
          not install_plan({'kind': 'bogus',
                            'name': 'x'})['ok'])

    # ---- sep-3: derived app options (§43 projection) -----------------
    from islemesh.islemesh_catalog import (
        option_install_plan, polari_app_options)

    class _Row:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    app_defs = [
        _Row(name='app-climate', title='Climate', use_case='co2',
             modules_json='["climate"]', is_prior=True),
        _Row(name='wax-print-shop', title='Wax Print Shop',
             use_case='', description='wax', modules_json='[]',
             is_prior=True),
        _Row(name='my-app', title='Mine', use_case='',
             modules_json='[]', is_prior=False),
        _Row(name='polari', title='shadowed', modules_json='[]'),
    ]
    shell_defs = [
        _Row(name='wax-print-shop-shell', scope='app',
             app_name='wax-print-shop'),
        _Row(name='polari-instance-shell', scope='instance',
             app_name=''),
    ]
    opts = polari_app_options(app_defs, shell_defs, {'polari'})
    by = {o['name']: o for o in opts}
    check('sep-3: every app projects as a derived OPTION; names '
          'taken by real catalog entries are skipped',
          set(by) == {'app-climate', 'wax-print-shop', 'my-app'})
    check('sep-3: converted marker rides the scope=app shell row '
          '(instance shells never convert an app)',
          by['wax-print-shop']['converted']
          and by['wax-print-shop']['shell'] == 'wax-print-shop-shell'
          and not by['app-climate']['converted'])
    check('sep-3: standard marker = seeded (is_prior)',
          by['app-climate']['standard']
          and not by['my-app']['standard'])
    check('sep-3: options are derived, never rows '
          '(kind/derived/defined_at)',
          all(o['derived'] and o['kind'] == 'polari-app-option'
              and o['defined_at'] == 'isle-core' for o in opts))
    unconverted = option_install_plan(by['app-climate'])
    converted = option_install_plan(by['wax-print-shop'])
    check('sep-3: ONE idempotent command either way '
          '(pol apps shell <name>)',
          unconverted['steps'] == ['pol apps shell app-climate']
          and converted['steps']
          == ['pol apps shell wax-print-shop']
          and 'launcher row exists' in converted['note']
          and 'AT INSTALL TIME' in unconverted['note'])

    # ---- instance tracking (chosen duplicates across devices) -------
    from islemesh.islemesh_catalog import instances_of
    app_rows = [
        {'name': 'whoami', 'device_name': 'isle-core',
         'domain': 'whoami.isle', 'is_mock': False},
        {'name': 'whoami-2', 'device_name': 'pol-core',
         'domain': 'whoami-2.isle', 'is_mock': False},
        {'name': 'whoami-extra', 'device_name': 'x', 'domain': '',
         'is_mock': False},
        {'name': 'whoami', 'device_name': 'mockdev', 'domain': '',
         'is_mock': True},
        {'name': 'odoo', 'device_name': 'isle-core',
         'domain': 'odoo.isle', 'is_mock': False},
    ]
    inst = instances_of(app_rows, 'whoami')
    check('instances: base + -N duplicates counted, per device',
          [i['app'] for i in inst] == ['whoami', 'whoami-2']
          and {i['device'] for i in inst}
          == {'isle-core', 'pol-core'})
    check('instances: mock rows + non-suffix names excluded',
          all(i['app'] != 'whoami-extra' for i in inst)
          and all(i['device'] != 'mockdev' for i in inst)
          and len(instances_of(app_rows, 'odoo')) == 1)

    # ---- topology coherence (joined isle x polari view) -------------
    from islemesh.custom.islemesh_coherence import assess_topology
    coh = assess_topology(
        devices=[
            {'name': 'isle-core', 'agent_present': True},
            {'name': 'pol-core', 'agent_present': True},
            {'name': 'econ-core', 'agent_present': False},
        ],
        apps=[
            {'name': 'polari', 'device_name': 'isle-core',
             'domain': 'polari.isle'},
            {'name': 'polari-2', 'device_name': 'pol-core',
             'domain': 'polari-2.isle'},
            {'name': 'ghost', 'device_name': 'econ-core',
             'domain': 'ghost.isle'},
        ],
        services=[
            {'app_name': 'polari', 'device_name': 'isle-core',
             'subdomain': 'api.polari.isle'},
        ])
    # sibling-app folding: polari-api (domain api.polari.isle) must
    # fold UNDER polari, not stand beside it
    coh2 = assess_topology(
        devices=[{'name': 'isle-core', 'agent_present': True}],
        apps=[
            {'name': 'polari', 'device_name': 'isle-core',
             'domain': 'polari.isle'},
            {'name': 'polari-api', 'device_name': 'isle-core',
             'domain': 'api.polari.isle'},
        ])
    core2 = coh2['polari']['core']
    check('coherence: sibling api-app folds under its parent',
          core2 is not None
          and core2['subdomains'] == ['api.polari.isle']
          and all(a['name'] != 'polari-api'
                  for a in coh2['devices'][0]['apps']))
    codes = {a['code'] for a in coh['assessments']}
    check('coherence: polari instances joined per device',
          sorted(coh['polari']['devices'])
          == ['isle-core', 'pol-core']
          and coh['polari']['candidates'] == [])
    check('coherence: apps without an agent flagged',
          'apps-without-agent' in codes)
    check('coherence: THE CORE polari = the polari.isle server, '
          'subdomains attached',
          coh['polari']['core']['device'] == 'isle-core'
          and coh['polari']['core']['subdomains']
          == ['api.polari.isle']
          and next(i for i in coh['polari']['instances']
                   if i['app'] == 'polari-2')['role']
          == 'additional')
    check('coherence: device apps carry their SUB-DOMAINS',
          next(a for a in coh['devices']
               if a['name'] == 'isle-core')['apps'][0]['subdomains']
          == ['api.polari.isle'])
    check('coherence: the component shape names backend as the '
          'replicable subsection',
          coh['polari']['components']['backend'] == 'replicable'
          and coh['polari']['components']['frontend']
          == 'singleton')
    empty = assess_topology(devices=[], apps=[])
    check('coherence: no polari anywhere is a WARN',
          any(a['code'] == 'no-polari'
              for a in empty['assessments']))

    # ---- app placement resolver (module-collection apps) ------------
    from islemesh.islemesh_catalog import resolve_app_placement
    insts = [
        {'name': 'polari', 'device': 'isle-core',
         'modules': ['islemesh', 'polariapps', 'scoring']},
        {'name': 'polari-2', 'device': 'isle-core',
         'modules': ['islemesh', 'gears']},
    ]
    rp = resolve_app_placement(
        'judicial-lean', ['polariNoCode', 'scoring'], insts)
    check('appplan: satisfied vs missing split',
          [s['module'] for s in rp['satisfied']] == ['scoring']
          and rp['missing'] == ['polariNoCode']
          and not rp['complete'])
    check('appplan: plan targets a real instance with a verb',
          len(rp['plan']) == 1
          and rp['plan'][0]['module'] == 'polariNoCode'
          and rp['plan'][0]['target'] in ('polari', 'polari-2')
          and 'isle polari module add' in rp['plan'][0]['cmd'])
    rp2 = resolve_app_placement('done', ['gears'], insts)
    check('appplan: complete when every module is placed',
          rp2['complete'] and not rp2['plan'])
    rp3 = resolve_app_placement('fresh', ['x'], [])
    check('appplan: no instances → deploy-instance plan',
          rp3['plan'][0]['action'] == 'deploy-instance')

    # ---- network resource ledger (scale-without-collision) ----------
    from islemesh.custom.islemesh_netledger import (
        cidrs_overlap, pool_conflicts, port_conflicts,
        free_subnet, free_port, assess_resources)
    check('netledger: overlap detection (the econ-core case)',
          cidrs_overlap('172.20.0.0/16', '172.20.0.0/24')
          and not cidrs_overlap('172.20.0.0/16', '172.21.0.0/16'))
    pc = pool_conflicts([
        {'name': 'isle-agent-net', 'cidr': '172.20.0.0/16'},
        {'name': 'polari-suite_polari-network',
         'cidr': '172.20.0.0/16'},
        {'name': 'bridge', 'cidr': '172.17.0.0/16'}])
    check('netledger: names the overlapping pools, ignores the rest',
          len(pc) == 1 and pc[0]['a'] == 'isle-agent-net')
    check('netledger: free_subnet skips taken pools',
          not cidrs_overlap(free_subnet([
              {'name': 'x', 'cidr': '172.22.0.0/24'}]),
              '172.22.0.0/24'))
    check('netledger: port conflict + free_port',
          port_conflicts([{'port': 80}, {'port': 80},
                          {'port': 81}]) == [80]
          and free_port([{'port': 18080}]) == 18081)
    ra = assess_resources([{'name': 'econ-core', 'pools': [
        {'name': 'a', 'cidr': '10.0.0.0/24'},
        {'name': 'b', 'cidr': '10.0.0.0/24'}], 'ports': []}])
    check('netledger: assess flags a pool overlap per host',
          any(a['code'] == 'pool-overlap' for a in ra))

    # ---- UDP port ranges (mtg-0: media servers own RANGES) ----------
    from islemesh.custom.islemesh_netledger import (
        udp_range_conflicts, free_udp_range)
    check('netledger: same port different proto is NOT a conflict',
          port_conflicts([{'port': 80},
                          {'port': 80, 'proto': 'udp'}]) == []
          and port_conflicts([{'port': 80, 'proto': 'udp'},
                              {'port': 80, 'proto': 'udp'}])
          == ['80/udp'])
    rc = udp_range_conflicts([
        {'name': 'livekit-media', 'lo': 50000, 'hi': 50099},
        {'name': 'other-webrtc', 'lo': 50050, 'hi': 50149},
        {'name': 'clear', 'lo': 51000, 'hi': 51099}])
    check('netledger: overlapping UDP ranges named, disjoint ignored',
          len(rc) == 1 and rc[0]['a'] == 'livekit-media'
          and rc[0]['b'] == 'other-webrtc')
    check('netledger: a single udp port inside a range collides',
          udp_range_conflicts(
              [{'name': 'livekit-media', 'lo': 50000, 'hi': 50099}],
              [{'port': 50007, 'proto': 'udp', 'container': 'wg'}])
          != [] and udp_range_conflicts(
              [{'name': 'livekit-media', 'lo': 50000, 'hi': 50099}],
              [{'port': 50007, 'container': 'tcp-thing'}]) == [])
    fr = free_udp_range([{'name': 'x', 'lo': 50000, 'hi': 50099}],
                        [{'port': 50100, 'proto': 'udp'}], width=100)
    check('netledger: free_udp_range skips ranges AND udp ports',
          fr == {'lo': 50101, 'hi': 50200})
    ra2 = assess_resources([{'name': 'pol-core', 'pools': [],
                             'ports': [],
                             'udp_ranges': [
                                 {'name': 'a', 'lo': 1, 'hi': 9},
                                 {'name': 'b', 'lo': 5, 'hi': 14}]}])
    check('netledger: assess flags a UDP range collision per host',
          any(a['code'] == 'udp-range-conflict' for a in ra2))

    # ---- synthetic-IP pools (ret-3: the mesh resolver's kind) --------
    from islemesh.custom.islemesh_netledger import (
        synthetic_pool_conflicts, free_synthetic_pool)
    sc = synthetic_pool_conflicts(
        [{'name': 'rns-isle', 'cidr': '10.77.0.0/24'},
         {'name': 'rns-arch', 'cidr': '10.77.0.128/25'}],
        [{'name': 'polari-link', 'cidr': '172.20.0.0/16'}])
    check('netledger: synthetic pools colliding with each other are '
          'named as such',
          len(sc) == 1 and sc[0]['kind'] == 'synthetic-vs-synthetic')
    sc = synthetic_pool_conflicts(
        [{'name': 'rns-isle', 'cidr': '172.20.5.0/24'}],
        [{'name': 'polari-link', 'cidr': '172.20.0.0/16'}])
    check('netledger: a synthetic pool inside a REAL docker pool is '
          'the dangerous case and is flagged',
          len(sc) == 1 and sc[0]['kind'] == 'synthetic-vs-real')
    check('netledger: disjoint synthetic + real pools are clean',
          synthetic_pool_conflicts(
              [{'name': 'rns-isle', 'cidr': '10.77.0.0/24'}],
              [{'name': 'polari-link', 'cidr': '172.20.0.0/16'}]) == [])
    fs = free_synthetic_pool(
        [{'name': 'weird', 'cidr': '10.77.0.0/24'}],
        [{'name': 'rns-other', 'cidr': '10.77.1.0/24'}])
    check('netledger: free_synthetic_pool skips real AND synthetic '
          'reservations', fs == '10.77.2.0/24')
    ra3 = assess_resources([{'name': 'pol-core', 'pools': [
        {'name': 'polari-link', 'cidr': '172.20.0.0/16'}],
        'ports': [], 'synthetic_pools': [
            {'name': 'rns-isle', 'cidr': '172.20.9.0/24'}]}])
    check('netledger: assess flags a synthetic pool the resolver and '
          'docker would both route',
          any(a['code'] == 'synthetic-pool-conflict'
              and 'docker also routes' in a['message'] for a in ra3))

    # ---- vocabulary coherence ---------------------------------------
    check('availability presets are named modes over the triple',
          AVAILABILITY_MODES == ('always-available', 'on-demand')
          and 'resource-permitting' in UP_TRIGGERS
          and 'resource-pressure' in DOWN_TRIGGERS
          and 'replicated' in PLACEMENTS)
    check('mock banner is loud and self-describing',
          'MOCK NETWORK' in MOCK_BANNER)

    failed = sum(1 for _, ok in _results if not ok)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
