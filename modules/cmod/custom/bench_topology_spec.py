"""
@module cmod.custom.bench_topology_spec

bss-8 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 7): A TOPOLOGY SPEC IS DATA AT THE BENCH SYSTEM LEVEL (custom/topologies/<bench system>.json),
applied to every Bench Solution of that System. The spec names its edges by ROLE (press / command / reset / period), never by pin: applied to one Bench
Solution, each role resolves to the Hardware Event that Solution's own firmware offers (press -> press-PD2 on uno-light, press-PD4 on uno-light-pcint,
press-ADC0 on uno-light-analog), and each execution's isotope resolves from the variant's own route knobs (button_route int0 -> read-button:ext-interrupt).
The SAME states, every route; nothing drawn twice. The nodes go in through the same doors the canvas writes (bench_topology.define / connect).

    specs()                        the shipped specs: [{name, bench_system, title, nodes}]
    load(name)                     one spec, or a refusal in words
    routes_of(variant)             {job: 'job:route'} from the variant's knobs (derived; '' for a job the variant does not use)
    resolve(manager, bs)           {role: HardwareEvent name} for a Bench Solution (a role the firmware does not offer is absent, said in words)
    apply(manager, bs, spec='')    define every node and edge of the spec on the Bench Solution (idempotent) -> {spec, roles, routes, nodes, skipped, words}
"""
import json
import os

from cmod.custom import bench_events as E
from cmod.custom import bench_topology as T
from cmod.custom import catom_config as CF
from cmod.custom import config_rows as R

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'topologies')
#: the variants file's route knob words -> the IsotopeVariant route (board.custom.variants: button_route / led_route / sense_route; absent = the first)
BUTTON_ROUTES = {'int0': 'ext-interrupt', 'pcint': 'pin-change-interrupt', 'adc': 'analog-threshold'}
LED_ROUTES = {'gpio': 'gpio-out', 'pwm': 'pwm', 'transistor': 'transistor-switch'}
SENSE_ROUTES = {'int1': 'ext-interrupt', 'poll': 'gpio-poll', 'pcint': 'pin-change-interrupt'}
ROLE_PREFIX = {'press': 'press-', 'release': 'release-', 'command': 'command-', 'period': 'period-', 'level': 'level-', 'reset': 'reset'}


def specs():
    out = []
    for f in sorted(os.listdir(DIR)) if os.path.isdir(DIR) else []:
        if f.endswith('.json'):
            try:
                d = json.load(open(os.path.join(DIR, f), encoding='utf-8'))
            except ValueError:
                continue
            out.append({'name': f[:-5], 'bench_system': d.get('bench_system', ''), 'title': d.get('title', ''), 'nodes': len(d.get('nodes') or []),
                        'roles': sorted((d.get('roles') or {}).keys()), 'notes': d.get('notes', '')})
    return out


def load(name):
    path = os.path.join(DIR, '%s.json' % name)
    if not name or not os.path.exists(path):
        raise R.ConfigRefused('no topology spec %r (the shipped ones: %s)' % (name, ', '.join(s['name'] for s in specs()) or 'none'), status=404)
    d = json.load(open(path, encoding='utf-8'))
    if d.get('schema') != 'bench-topology-spec/1':
        raise R.ConfigRefused('topology spec %r: schema %r is not bench-topology-spec/1' % (name, d.get('schema')))
    return d


def routes_of(variant):
    try:
        from board.custom import variants as V
        r = V.resolve(V.find(variant))
    except Exception:  # noqa: BLE001 - board absent or an unknown variant
        return {}
    k, feat = r.get('knobs', {}), r.get('features', {})
    out = {'read-button': 'read-button:%s' % BUTTON_ROUTES.get(str(k.get('button_route') or 'int0'), 'ext-interrupt'),
           'drive-led': 'drive-led:%s' % LED_ROUTES.get(str(k.get('led_route') or 'gpio'), 'gpio-out'),
           'report-state': 'report-state:uart-tx', 'receive-command': 'receive-command:uart-rx-interrupt' if feat.get('commands', True) else ''}
    if feat.get('sense'):
        out['sense-led-line'] = 'sense-led-line:%s' % SENSE_ROUTES.get(str(k.get('sense_route') or 'int1'), 'ext-interrupt')
    if feat.get('adc') and str(k.get('button_route') or '') != 'adc':
        out['read-temperature'] = 'read-temperature:analog-sensor'
    return out


def resolve(manager, bs):
    events = E.offered(manager, bs)
    out, words = {}, []
    for role, prefix in ROLE_PREFIX.items():
        hits = [e['name'] for e in events if (e['name'].split(':', 1)[1] == prefix if prefix == 'reset' else e['name'].split(':', 1)[1].startswith(prefix))]
        if len(hits) == 1:
            out[role] = hits[0]
        elif len(hits) > 1:
            words.append('%s: %d events offered (%s); the spec cannot choose - name the pin' % (role, len(hits), ', '.join(h.split(':', 1)[1] for h in hits)))
    return out, words


def _req(object_map, field, value):
    if isinstance(value, bool):
        return {'object_map': object_map, 'field': field, 'kind': 'exact', 'value': int(value)}
    if isinstance(value, (int, float)):
        return {'object_map': object_map, 'field': field, 'kind': 'exact', 'value': value}
    v = str(value)
    if v == 'written':
        return {'object_map': object_map, 'field': field, 'kind': 'written', 'value': ''}
    if '..' in v:
        return {'object_map': object_map, 'field': field, 'kind': 'range', 'value': v}
    if '|' in v:
        return {'object_map': object_map, 'field': field, 'kind': 'set', 'value': v.replace('|', ',')}
    return {'object_map': object_map, 'field': field, 'kind': 'exact', 'value': v}


def apply(manager, bs, spec=''):
    ctx = CF.context(manager, bs)
    row = R.get(manager, 'BenchSolution', bs)
    name = spec or row.get('system') or ''
    sp = load(name)
    chain = T.root_chain(manager, bs)
    roles, words = resolve(manager, bs)
    variant = E.variant_of(manager, ctx['firmware_solution'])
    routes = routes_of(variant)
    done, skipped = [], []
    for n in sp.get('nodes') or []:
        slug = n['slug']
        node = '%s:%s' % (bs, slug)
        via = n.get('via', '')
        ev = roles.get(via)
        if not ev:
            skipped.append({'node': slug, 'why': 'the role %r has no Hardware Event on %s (the firmware %s offers none)' % (via, bs, variant)})
            continue
        frm = chain['boot'] if n.get('from', 'boot') == 'boot' else '%s:%s' % (bs, n['from'])
        if R.get(manager, 'StructNode', frm) is None:
            skipped.append({'node': slug, 'why': 'its start node %r was not defined (skipped above?)' % n['from']})
            continue
        reqs = [_req(n.get('object_map') or sp.get('object_map', ''), f, v) for f, v in (n.get('requirements') or {}).items()]
        execs = []
        for x in n.get('executions') or []:
            x = {'atom': x} if isinstance(x, str) else x
            iso = routes.get(x.get('job', ''), '') if x.get('job') else x.get('isotope', '')
            execs.append({'atom': x['atom'], 'isotope': iso})
        view = T.define(manager, bs, slug, n.get('title', ''), frm, 'trigger', ev, requirements=reqs, executions=execs, collaterals=n.get('collaterals') or ())
        for x in view['executions']:
            if x['isotope']:
                R.upsert(manager, 'StructNodeExecution', x['name'], notes='isotope: from the route knobs of %s (bench_topology_spec.routes_of)' % variant)
        for frm2, via2 in n.get('also_from') or []:
            ev2 = roles.get(via2)
            start = chain['boot'] if frm2 == 'boot' else '%s:%s' % (bs, frm2)
            if not ev2 or R.get(manager, 'StructNode', start) is None:
                words.append('%s: the extra edge from %r via %r was not made (%s)' % (slug, frm2, via2, 'no such event' if not ev2 else 'no such node'))
                continue
            T.connect(manager, bs, start, node, 'trigger', ev2)
        done.append(node)
    T.all_paths(manager, bs)
    nodes = [T.node_view(manager, n) for n in done]
    paths = sum(len(v['paths']) for v in nodes)
    return {'ok': True, 'spec': name, 'bench_solution': bs, 'variant': variant, 'roles': roles, 'routes': routes, 'nodes': nodes, 'skipped': skipped,
            'words': '%s applied to %s (firmware %s): %d node%s, %d path%s from the root; roles %s%s%s'
                     % (name, bs, variant, len(done), '' if len(done) == 1 else 's', paths, '' if paths == 1 else 's',
                        ', '.join('%s = %s' % (k, v.split(':', 1)[1]) for k, v in sorted(roles.items())),
                        ('; skipped: ' + '; '.join('%s (%s)' % (s['node'], s['why']) for s in skipped)) if skipped else '',
                        ('; ' + '; '.join(words)) if words else '')}
