"""
@module electrodevice.custom.cst_verdict

cst-1 (PROTOTYPING_VIEWS_PLAN.md §2, §8): WHAT SPICE SAYS IN EACH STATE, judged against the cited limits, and the rows the page and the ladder read.

  limits(tables)                    the per-pin and group limits from the ElectricalCharacteristic / PinGroupBudget rows (board.custom.electrical_atmega328p:
                                    I_PIN abs-max 40 mA, recommended 20 mA; VCC/GND abs-max 200 mA) — never a number typed here
  judge(state, run, cat, lim)       {verdict ok|warn|refuse|undetermined|not-simulated, currents {probe: mA}, findings [...]}: a pin past abs-max REFUSES, past
                                    recommended WARNS; the ground return past the VCC/GND budget refuses; a floating input (no driver, pull or closed switch on
                                    its net) warns — structural, true with or without an engine
  document(config, tables, spice)   the whole picture: catalogue, states, transitions, per-state verdicts (both pull-up ends when `spice`), rows for the tables
  persist(manager, doc)             CircuitState / CircuitStateTransition rows + one CircuitRunResult `<config>:<state>:op` per simulated state
  rung7_findings(config, pin, …)    for board.custom.ladder._rung7: the stored .op currents of this config's states that name the pin, as electrical findings
  active_current_ma(config, …)      the Battery profile's active-current term: the ground return of the `led-on` state (mA), with its basis — or None
"""
import datetime
import json

from electrodevice.custom import cst_modes as M
from electrodevice.custom import cst_netlist as N

STATE_CLASS, TRANSITION_CLASS, RUN_CLASS = 'CircuitState', 'CircuitStateTransition', 'CircuitRunResult'
_CACHE = {}


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def limits(tables=None):
    """{'pin_abs_max_ma', 'pin_recommended_ma', 'supply_abs_max_ma', 'cite': {...}} read from the characteristic / budget rows (the seeds when no table)."""
    from board.custom import electrical_atmega328p as E
    chars = (tables or {}).get('ElectricalCharacteristic') or E.characteristics()
    buds = (tables or {}).get('PinGroupBudget') or E.budgets()

    def pick(rows, pred):
        r = next((x for x in rows if pred(x)), None)
        return r

    a = pick(chars, lambda x: x.get('parameter') == 'I_PIN' and x.get('limit_class') == 'abs-max')
    rec = pick(chars, lambda x: x.get('parameter') == 'I_PIN' and x.get('limit_class') == 'recommended' and x.get('max_value'))
    sup = pick(buds, lambda x: x.get('limit_class') == 'abs-max' and 'VCC' in (x.get('members_json') or ''))
    return {'pin_abs_max_ma': float(a['max_value']) if a else None, 'pin_recommended_ma': float(rec['max_value']) if rec else None,
            'supply_abs_max_ma': float(sup['limit_ma']) if sup else None,
            'cite': {'pin_abs_max': '%s (%s %s)' % (a['name'], a.get('datasheet', ''), a.get('page_table', '')) if a else 'no ElectricalCharacteristic I_PIN abs-max row',
                     'pin_recommended': '%s (%s %s)' % (rec['name'], rec.get('datasheet', ''), rec.get('page_table', '')) if rec else 'no recommended row',
                     'supply_abs_max': '%s (%s %s)' % (sup['name'], sup.get('datasheet', ''), sup.get('page_table', '')) if sup else 'no VCC/GND budget row'}}


def _ma(v):
    return round(abs(float(v)) * 1000.0, 4)


def judge(state, run, cat, lim):
    """-> {'verdict', 'currents', 'findings', 'words'}. `run` = cst_netlist.run(...) or None (structural rules only)."""
    findings, currents = [], {}
    for fl in N.floating_nets(state, cat):
        if fl['inputs']:
            findings.append({'rule': 'floating-input', 'status': 'warn', 'subject': ', '.join(fl['inputs']),
                             'detail': 'net %s has no driver, pull-up or closed switch to a rail in state %s: the input pin(s) %s read a floating line'
                                       % (fl['net'], state['name'], ', '.join(fl['inputs'])), 'cite': 'structural (the netlist of this state)'})
    if run is None:
        return {'verdict': 'not-simulated', 'currents': {}, 'findings': findings,
                'words': 'not simulated (%s)' % ('every pin high-Z: nothing drives the circuit' if state['lifecycle'] == 'reset' else 'no run') + (' — %d structural finding(s)' % len(findings) if findings else '')}
    if not run.get('ok'):
        return {'verdict': 'undetermined', 'currents': {}, 'findings': findings, 'words': 'SPICE did not run: %s' % run.get('error', '')}
    rails = 0.0
    for k, v in run['measurements'].items():
        if k.startswith('i('):
            currents[k] = _ma(v)
            if not k.startswith('i(vam_'):
                rails += _ma(v)   # a rail source (V<pin> / Vpu_<pin>): what it delivers comes back through ground
        else:
            currents[k] = round(float(v), 4)
    currents['i(gnd-return)'] = round(rails, 4)
    status = 'ok'
    for pin, d in cat['pins'].items():
        key = 'i(%s)' % N._ref('Vam_', pin).lower()
        if key not in currents:
            continue
        ma = currents[key]
        if lim['pin_abs_max_ma'] is not None and ma > lim['pin_abs_max_ma']:
            findings.append({'rule': 'pin-current-abs-max', 'status': 'refuse', 'subject': pin, 'detail': '%s carries %.2f mA in state %s, past the absolute maximum %.1f mA' % (pin, ma, state['name'], lim['pin_abs_max_ma']), 'cite': lim['cite']['pin_abs_max']})
            status = 'refuse'
        elif lim['pin_recommended_ma'] is not None and ma > lim['pin_recommended_ma']:
            findings.append({'rule': 'pin-current-recommended', 'status': 'warn', 'subject': pin, 'detail': '%s carries %.2f mA in state %s, past the recommended %.1f mA (under the %.1f mA absolute maximum)' % (pin, ma, state['name'], lim['pin_recommended_ma'], lim['pin_abs_max_ma'] or 0), 'cite': lim['cite']['pin_recommended']})
            status = 'warn' if status == 'ok' else status
        else:
            findings.append({'rule': 'pin-current', 'status': 'ok', 'subject': pin, 'detail': '%s carries %.3f mA in state %s (limit %.1f mA recommended / %.1f mA absolute)' % (pin, ma, state['name'], lim['pin_recommended_ma'] or 0, lim['pin_abs_max_ma'] or 0), 'cite': lim['cite']['pin_recommended']})
    g = currents.get('i(gnd-return)')
    if g is not None and lim['supply_abs_max_ma'] is not None:
        if g > lim['supply_abs_max_ma']:
            findings.append({'rule': 'supply-current-abs-max', 'status': 'refuse', 'subject': 'GND', 'detail': 'the circuit returns %.2f mA to ground in state %s, past the VCC/GND absolute maximum %.0f mA' % (g, state['name'], lim['supply_abs_max_ma']), 'cite': lim['cite']['supply_abs_max']})
            status = 'refuse'
        else:
            findings.append({'rule': 'supply-current', 'status': 'ok', 'subject': 'GND', 'detail': 'the circuit returns %.3f mA to ground in state %s (budget %.0f mA)' % (g, state['name'], lim['supply_abs_max_ma']), 'cite': lim['cite']['supply_abs_max']})
    if status == 'ok' and any(f['status'] == 'warn' for f in findings):
        status = 'warn'
    words = '; '.join(f['detail'] for f in findings if f['status'] != 'ok') or '; '.join(f['detail'] for f in findings if f['rule'] in ('pin-current', 'supply-current'))[:300]
    return {'verdict': status, 'currents': currents, 'findings': findings, 'words': words}


def document(config, tables, spice=True, manager=None, pullups=N.PULLUP_OHMS):
    """The whole picture for one config. `spice`: run the .op per running state at each pull-up end (the LED current does not depend on it; D2's does)."""
    cat = M.catalogue(config, tables, manager)
    cat['_components'] = [c for c in (tables.get('CircuitComponentDefinition') or []) if c.get('circuit_name') == cat['circuit']]
    sts = M.states(config, tables, cat, manager)
    trs = M.transitions(config, tables, cat, sts, manager)
    lim = limits(tables)
    runs = []
    for s in sts:
        if s['lifecycle'] == 'reset' or not spice:
            v = judge(s, None, cat, lim)
            s.update(spice_verdict=v['verdict'], spice_words=v['words'], currents=v['currents'], findings=v['findings'], run='')
            continue
        per = []
        for ohms in pullups:
            r = N.run(s, cat, ohms)
            v = judge(s, r, cat, lim)
            per.append({'pullup_ohms': ohms, 'ok': r.get('ok', False), 'verdict': v['verdict'], 'currents': v['currents'], 'findings': v['findings'], 'words': v['words'],
                        'netlist': r.get('netlist', ''), 'error': r.get('error', ''), 'probes': r.get('probes', [])})
        worst = max(per, key=lambda p: ('ok', 'warn', 'undetermined', 'refuse').index(p['verdict']) if p['verdict'] in ('ok', 'warn', 'undetermined', 'refuse') else 0)
        s.update(spice_verdict=worst['verdict'], spice_words=' | '.join('RPU %d: %s' % (p['pullup_ohms'], p['words']) for p in per), currents=worst['currents'],
                 findings=worst['findings'], run='%s:%s:op' % (config, s['name']))
        runs.append({'name': '%s:%s:op' % (config, s['name']), 'state': s['name'], 'config': config, 'circuit': cat['circuit'], 'runs': per})
    return {'ok': True, 'config': config, 'circuit': cat['circuit'], 'circuit_why': cat['why'], 'engine': N.capability(), 'limits': lim,
            'components': cat['components'], 'pins': cat['pins'], 'driver': cat['driver'], 'press': cat['press'],
            'states': sts, 'transitions': trs, 'runs': runs, 'derived_at': _now(),
            'counts': {'states': len(sts), 'transitions': len(trs), 'simulated': len(runs), 'findings': sum(len(s.get('findings') or []) for s in sts)},
            'derived_by': 'electrodevice.custom.cst_modes / cst_netlist / cst_verdict — from the circuit rows, the HAL init (source), the parsed atoms, the press record, the cited limits; never typed'}


# ------------------------------------------------------------------ rows
def state_rows(doc):
    return [{'name': '%s:%s' % (doc['config'], s['name']), 'config': doc['config'], 'circuit': doc['circuit'], 'state': s['name'], 'lifecycle': s['lifecycle'],
             'modes_json': json.dumps(s['modes'], sort_keys=True), 'modes': ', '.join('%s %s' % kv for kv in sorted(s['modes'].items())), 'led': s['led'], 'words': s['words'],
             'reachable_by': s['reachable_by'], 'evidence': s['evidence'], 'spice_verdict': s.get('spice_verdict', ''), 'spice_words': s.get('spice_words', ''),
             'currents_json': json.dumps(s.get('currents') or {}), 'currents': ', '.join('%s %s' % (k, v) for k, v in sorted((s.get('currents') or {}).items()) if k.startswith('i(')),
             'findings_json': json.dumps(s.get('findings') or []), 'run': s.get('run', '')} for s in doc['states']]


def transition_rows(doc):
    return [dict(t, timing_ms=t.get('timing_ms', -1.0)) for t in doc['transitions']]


def spice_rows(doc):
    out = []
    for r in doc['runs']:
        for p in r['runs']:
            out.append({'name': '%s@%d' % (r['name'], p['pullup_ohms']), 'state': r['state'], 'config': r['config'], 'pullup_ohms': p['pullup_ohms'], 'verdict': p['verdict'],
                        'ok': p['ok'], 'words': p['words'] or p['error'], **{k: v for k, v in p['currents'].items()}})
    return out


def finding_rows(doc):
    out = []
    for s in doc['states']:
        for f in s.get('findings') or []:
            out.append(dict(f, state=s['name'], config=doc['config']))
    return out


def persist(manager, doc):
    from electrodevice.circuit_basis import CircuitState, CircuitStateTransition
    from board.custom.installer import upsert
    for r in state_rows(doc):
        upsert(manager, CircuitState, r)
    for t in transition_rows(doc):
        upsert(manager, CircuitStateTransition, dict(t))
    try:
        from electrodevice.device_basis import CircuitRunResult
    except Exception:   # noqa: BLE001
        CircuitRunResult = None
    if CircuitRunResult is not None:
        for r in doc['runs']:
            best = r['runs'][0] if r['runs'] else {}
            upsert(manager, CircuitRunResult, {'name': r['name'], 'device_name': doc['config'], 'circuit': r['circuit'],
                                               'inputs_json': json.dumps({'state': r['state'], 'pullups': [p['pullup_ohms'] for p in r['runs']], 'netlist': best.get('netlist', '')}),
                                               'outputs_json': json.dumps({'per_pullup': [{'pullup_ohms': p['pullup_ohms'], 'currents': p['currents'], 'verdict': p['verdict']} for p in r['runs']]}),
                                               'verdict': max((p['verdict'] for p in r['runs']), key=lambda v: ('ok', 'warn', 'undetermined', 'refuse').index(v) if v in ('ok', 'warn', 'undetermined', 'refuse') else 0) if r['runs'] else 'undetermined',
                                               'engine': 'ngspice', 'ran_at': doc['derived_at'], 'notes': 'cst-1: the .op of circuit state %s (cst_netlist deck; ideal pin sources = the worst-case bound)' % r['state']})


# ------------------------------------------------------------------ readers for the ladder and the scorer
def _runs_of(config, manager):
    tab = ((getattr(manager, 'objectTables', None) or {}).get(RUN_CLASS) or {}) if manager is not None else {}
    return [r for r in (tab.values() if isinstance(tab, dict) else tab) if getattr(r, 'name', '').startswith(config + ':') and getattr(r, 'name', '').endswith(':op')]


def rung7_findings(config, pin, manager=None, tables=None):
    """The stored .op currents of this config's states that name `pin`, as electrical findings (rule, status, subject, detail, cite) for the ladder's rung 7."""
    lim = limits(tables)
    key = 'i(%s)' % N._ref('Vam_', pin).lower()
    out = []
    for r in _runs_of(config, manager):
        try:
            per = json.loads(r.outputs_json or '{}').get('per_pullup') or []
        except ValueError:
            per = []
        for p in per:
            ma = (p.get('currents') or {}).get(key)
            if ma is None:
                continue
            state = r.name.split(':')[1]
            if lim['pin_abs_max_ma'] is not None and ma > lim['pin_abs_max_ma']:
                out.append({'rule': 'spice-pin-current', 'status': 'refuse', 'subject': pin, 'detail': 'SPICE: %s carries %.2f mA in circuit state %s (RPU %s), past the %.0f mA absolute maximum' % (pin, ma, state, p.get('pullup_ohms'), lim['pin_abs_max_ma']), 'cite': lim['cite']['pin_abs_max']})
            elif lim['pin_recommended_ma'] is not None and ma > lim['pin_recommended_ma']:
                out.append({'rule': 'spice-pin-current', 'status': 'warn', 'subject': pin, 'detail': 'SPICE: %s carries %.2f mA in circuit state %s (RPU %s), past the %.0f mA recommended' % (pin, ma, state, p.get('pullup_ohms'), lim['pin_recommended_ma']), 'cite': lim['cite']['pin_recommended']})
            else:
                out.append({'rule': 'spice-pin-current', 'status': 'ok', 'subject': pin, 'detail': 'SPICE: %s carries %.3f mA in circuit state %s (RPU %s), within the limits' % (pin, ma, state, p.get('pullup_ohms')), 'cite': lim['cite']['pin_recommended']})
    return out


def active_current_ma(config, manager=None):
    """(mA, basis) from the stored .op of the `led-on` state's ground return (the worst pull-up end), or (None, why)."""
    for r in _runs_of(config, manager):
        if r.name == '%s:led-on:op' % config:
            try:
                per = json.loads(r.outputs_json or '{}').get('per_pullup') or []
            except ValueError:
                per = []
            vals = [(p.get('currents') or {}).get('i(gnd-return)') for p in per]
            vals = [v for v in vals if v is not None]
            if vals:
                return max(vals), 'SPICE .op of circuit state led-on (%s): the ground return %.3f mA (the larger of the pull-up ends %s); the MCU core current is not in it' % (r.name, max(vals), ', '.join(str(p.get('pullup_ohms')) for p in per))
    return None, 'no stored .op run of the led-on state for %s (POST /api/circuit-states/%s/run, or pol circuit states %s --spice)' % (config, config, config)
