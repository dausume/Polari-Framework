"""
@module board.custom.views.kicad

THE KICAD VIEW (brd-bo; D-pcb-1 "write directly"): a KiCad netlist stub — `(export (version "E") …)`, the s-expression KiCad 6+
writes (`kicad-cli sch export netlist --format kicadsexpr`) — from the rows:
  components  BoardHardware.components_json: the MCU (value, KiCad lib/part, footprint ref), the USB bridge, the connectors (J1–J5,
              their footprints), a button — refs are ours (said on the BoardHardware row)
  nets        one per BoardNet that something lands on: the MCU node (its PACKAGE pin number from the SocPin row, pinfunction = the
              SoC pin) for every BoardPin on that net, and a connector node (pin number in the connector's order, pinfunction = the
              printed label) for every ConnectorPin on it — the net names ARE the pins' nets (D6 → PWM_LED …)
Deterministic: no date, tstamps are uuid5(board/ref). Validated by board.custom.sexpr.check_netlist (no kicad-cli here — the pcb
worker is pcb-0's). Ingest reads nets back into (canonical, soc_pin, net, connector_pin).
"""
import json
import uuid

from board.custom import sexpr
from board.custom.sexpr import Q
from board.custom.views import ViewRefused, banner


def _tstamp(board, ref):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'polari:board/%s/%s' % (board, ref)))


def render(r, bsha):
    hw = r['hardware']
    if not hw:
        raise ViewRefused('%s has no BoardHardware row — no components to put in a netlist' % r['board'])
    comps = json.loads(hw['components_json'] or '[]')
    mcu = next((c for c in comps if c.get('role') == 'mcu'), None)
    if mcu is None:
        raise ViewRefused('%s: no mcu component on its BoardHardware row' % r['board'])
    pkg = {s['pin']: s['package_pin'] for s in r['soc_pins']}
    conn_ref = {c['connector']: c['ref'] for c in r['connectors']}
    by_net = {}
    for p in r['pins']:
        if p['soc_pin'] and p['net']:
            if p['soc_pin'] not in pkg:
                raise ViewRefused('pin %s: soc pin %s has no package pin number (SocPin row)' % (p['canonical'], p['soc_pin']))
            by_net.setdefault(p['net'], []).append((mcu['ref'], pkg[p['soc_pin']], p['soc_pin']))
        for c in comps:
            if c.get('role') in ('button', 'led') and c.get('pin') == p['canonical'] and p['net']:
                by_net.setdefault(p['net'], []).append((c['ref'], '1', p['canonical']))
    for cp in r['connector_pins']:
        if cp['net']:
            by_net.setdefault(cp['net'], []).append((conn_ref[cp['connector']], str(cp['number']), cp['label']))
    design = ['design', ['source', Q('polari:board/%s' % r['board'])], ['date', Q('')], ['tool', Q('Polari board object (board.custom.views.kicad)')],
              ['sheet', ['number', Q('1')], ['name', Q('/')], ['tstamps', Q('/')],
               ['title_block', ['title', Q(r['board'])], ['company', Q('')], ['rev', Q(r['identity'].get('revision', ''))], ['date', Q('')],
                ['source', Q('board sha %s' % bsha)], ['comment', ['number', Q('1')], ['value', Q(banner('kicad', r, bsha))]]]]]
    components = ['components']
    for c in sorted(comps, key=lambda c: c['ref']):
        comp = ['comp', ['ref', Q(c['ref'])], ['value', Q(c['value'])]]
        if c.get('footprint'):
            comp.append(['footprint', Q(c['footprint'])])
        comp.append(['libsource', ['lib', Q(c.get('lib', ''))], ['part', Q(c.get('part', ''))], ['description', Q(c.get('role', ''))]])
        comp.append(['property', ['name', Q('polari_role')], ['value', Q(c.get('role', ''))]])
        comp += [['sheetpath', ['names', Q('/')], ['tstamps', Q('/')]], ['tstamps', Q(_tstamp(r['board'], c['ref']))]]
        components.append(comp)
    nets = ['nets']
    for i, name in enumerate(sorted(by_net), 1):
        net = ['net', ['code', Q(str(i))], ['name', Q(name)]]
        for ref, pin, fn in sorted(set(by_net[name]), key=lambda x: (x[0], int(x[1]) if x[1].isdigit() else 0)):
            net.append(['node', ['ref', Q(ref)], ['pin', Q(pin)], ['pinfunction', Q(fn)]])
        nets.append(net)
    tree = ['export', ['version', Q('E')], design, components, nets]
    text = sexpr.write(tree) + '\n'
    why = sexpr.check_netlist(sexpr.parse(text))
    if why:
        raise ViewRefused('the rendered netlist fails its own check: %s' % '; '.join(why))
    return {'%s.net' % r['board']: text}


def ingest(files, r):
    """→ pins [{canonical, soc_pin, net, connector_pin}] from a KiCad netlist (ours or KiCad's)."""
    name = next((n for n in files if n.endswith('.net')), None) or next(iter(files))
    tree = sexpr.parse(files[name])
    why = sexpr.check_netlist(tree)
    if why:
        raise ViewRefused('not a KiCad netlist we can read: %s' % '; '.join(why))
    comps = {sexpr.value(c, 'ref'): c for c in sexpr.find(sexpr.find(tree, 'components')[0], 'comp')}
    hw = json.loads((r['hardware'] or {}).get('components_json') or '[]')
    mcu_ref = next((c['ref'] for c in hw if c.get('role') == 'mcu'), 'U1')
    by_pkg = {s['package_pin']: s['pin'] for s in r['soc_pins']}
    ref_conn = {c['ref']: c['connector'] for c in r['connectors']}
    label = {(c['connector'], int(c['number'])): c['label'] for c in r['connector_pins']}
    canon = {p['canonical'] for p in r['pins']}
    pins = {}
    for net in sexpr.find(sexpr.find(tree, 'nets')[0], 'net'):
        nname = sexpr.value(net, 'name')
        soc, conn = '', []
        for node in sexpr.find(net, 'node'):
            ref, pin = sexpr.value(node, 'ref'), sexpr.value(node, 'pin')
            if ref == mcu_ref:
                soc = sexpr.value(node, 'pinfunction') or by_pkg.get(pin, '')
            elif ref in ref_conn:
                conn.append((ref_conn[ref], int(pin)))
        if not soc:
            continue
        cand = sorted(c for c in conn if label.get(c) in canon)   # the connector pin printed with a board pin's name
        c = label[cand[0]] if cand else soc                        # else (no header label) the SoC pin IS the canonical name
        pins[c] = {'canonical': c, 'soc_pin': soc, 'net': nname, 'connector_pin': '%s:%d' % cand[0] if cand else ''}
    return {'pins': [pins[k] for k in sorted(pins)], 'profile': {}, 'notes': json.dumps({'components': sorted(comps)})}
