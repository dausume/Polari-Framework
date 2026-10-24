"""
@module electrodevice.custom.cst_cli

cst-0/1: `pol circuit states|transitions|findings|deck <config> [--spice] [--json] [--rpu N]` — the circuit states of a firmware config, offline (the seeds
+ the local ngspice when asked). Exit 3 = refused (no such config, no bench circuit covers its pins), 1 = a state past a limit, 0 otherwise.

    python3 -m electrodevice.custom.cst_cli states uno-light --spice
"""
import argparse
import json
import sys


def _tables():
    from board.custom import electrical_check as EC
    from board.custom import electrical_atmega328p as E
    t = EC.tables_for(None)
    t['ElectricalCharacteristic'] = E.characteristics()
    t['PinGroupBudget'] = E.budgets()
    return t


def main(argv=None):
    ap = argparse.ArgumentParser(prog='pol circuit')
    ap.add_argument('verb', choices=('states', 'transitions', 'findings', 'deck'))
    ap.add_argument('config')
    ap.add_argument('state', nargs='?', default='')
    ap.add_argument('--spice', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--rpu', type=int, default=20000)
    a = ap.parse_args(argv)
    from electrodevice.custom import cst_verdict as V, cst_netlist as N
    from electrodevice.custom.cst_sources import SourceRefused
    from board.custom.firmware_state import StateRefused
    try:
        doc = V.document(a.config, _tables(), spice=a.spice or a.verb == 'findings')
    except (SourceRefused, StateRefused) as e:
        print('[REFUSED] %s' % e)
        return 3
    if a.verb == 'deck':
        st = next((s for s in doc['states'] if s['name'] == a.state), None)
        if st is None:
            print('[REFUSED] no state %r of %s — one of %s' % (a.state, a.config, ', '.join(s['name'] for s in doc['states'])))
            return 3
        from electrodevice.custom import cst_modes as M
        cat = M.catalogue(a.config, _tables())
        cat['_components'] = [c for c in _tables()['CircuitComponentDefinition'] if c.get('circuit_name') == cat['circuit']]
        print(N.deck(st, cat, a.rpu)[0])
        return 0
    if a.json:
        print(json.dumps({'states': V.state_rows(doc), 'transitions': V.transition_rows(doc), 'spice': V.spice_rows(doc), 'findings': V.finding_rows(doc),
                          'counts': doc['counts'], 'engine': doc['engine'], 'limits': doc['limits']}, indent=1, default=str))
        return 0
    print('[ OK ] %s on circuit %s: %d states, %d transitions%s — %s' % (a.config, doc['circuit'], doc['counts']['states'], doc['counts']['transitions'],
                                                                        (', %d simulated' % doc['counts']['simulated']) if a.spice else '', doc['circuit_why']))
    worst = 0
    if a.verb == 'states':
        for s in doc['states']:
            print('  %-22s %-8s %s' % (s['name'], s['lifecycle'], ', '.join('%s %s' % kv for kv in sorted(s['modes'].items()))))
            print('  %22s reached by: %s' % ('', s['reachable_by'][:150]))
            if a.spice:
                cur = {k: v for k, v in (s.get('currents') or {}).items() if k.startswith('i(')}
                print('  %22s spice %-14s %s' % ('', s.get('spice_verdict', ''), ', '.join('%s %s mA' % kv for kv in sorted(cur.items())) or s.get('spice_words', '')[:120]))
                worst = max(worst, 1 if s.get('spice_verdict') == 'refuse' else 0)
    elif a.verb == 'transitions':
        for t in doc['transitions']:
            print('  %-22s -> %-22s %-9s %s' % (t['from_state'], t['to_state'], t['kind'], t['trigger'][:110]))
            print('  %58s %s' % ('', t['timing'][:120]))
    else:
        rows = V.finding_rows(doc)
        for f in rows:
            if f['status'] != 'ok':
                print('  [%s] %-22s %-24s %s' % (f['status'].upper()[:6], f['state'], f['rule'], f['detail'][:140]))
        if not any(f['status'] != 'ok' for f in rows):
            print('  no finding past ok')
        worst = 1 if any(f['status'] == 'refuse' for f in rows) else 0
    return worst


if __name__ == '__main__':
    sys.exit(main())
