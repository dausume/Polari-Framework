"""
@module hwnocode.custom.schematic_solve

cb-3 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §5): THE SCHEMATIC SOLVER over a board HardwareSolution. It runs what is already built
and proven, in order, and keeps every answer as rows:
  1. the board's electrical rules on the solution's circuit and firmware binding (board.custom.electrical_check (a)-(e) + electrical_hw
     (f)-(j): the same call `pol board circuit-check` makes)
  2. the components cut from that circuit (hwnocode.custom.schematic_derive)
  3. the four conditioning rules per component, and the electrical findings sorted onto the component they are about
     (hwnocode.custom.schematic_rules) -> each component solved or blocked, with its SchematicComponentCheck rows
  4. one HardwareFeature per component, every column from the HAL variables, the catom assertions and the twin kinds
     (hwnocode.custom.feature_derive), bound to the HardwareSolution, its real device and its simulator pair
Nothing is typed: change a circuit row, a pin net, a knob or a claim and the solve changes with it.

The solve takes seconds (the binding's pin claims are derived from the firmware's graph), so it is not run on every boot: the result is
RECORDED in custom/solved/<hardware-solution>.json with one sha256 over every input it read, and the seed reads the record. The selftest
and `pol hwnocode features <solution>` solve again and compare: a different inputs sha = the record is STALE (re-record with --write).

  targets()                                  -> the HardwareSolutions there are to solve: [{hardware_solution, variant, board, circuit}]
  solve(variant, board, circuit, hardware_solution='', tables=None)  -> {class: [rows]} + 'inputs_sha256', 'solver'
  solve_solution(name)                       -> solve() of one HardwareSolution, by name
  record(name) / load(name) / seed_rows()    -> write / read the record; every record's rows by class
  compare(name)                              -> (fresh, recorded, same: bool, why)

`python3 -m hwnocode.custom.schematic_solve <hardware-solution> [--write]` | `--circuit C --board B --variant V` (`pol hwnocode features`);
`<hardware-solution> --kicad [--out DIR]`: the whole solution as ONE KiCad sheet (hwnocode.custom.schematic_kicad), checked and drawn by the pcb
engine, KiCad's own netlist compared with the rows.
"""
import hashlib
import json
import os
import sys

from board.custom import electrical_check as EC
from hwnocode.custom import feature_derive as FD
from hwnocode.custom import schematic_derive as SD
from hwnocode.custom import schematic_rules as SR

SOLVER = 'hwnocode schematic solver v1 (cb-3): board electrical rules (a)-(j) + the pull, series, guard and filter rules'
CLASSES = ('SchematicComponent', 'SchematicComponentPort', 'SchematicComponentPart', 'SchematicComponentCheck', 'HardwareFeature')
RECORD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solved')


def _ref(refs_json, prefix):
    try:
        refs = json.loads(refs_json or '[]')
    except (TypeError, ValueError):
        refs = []
    return next((r.split(':', 1)[1] for r in refs if r.startswith(prefix + ':')), '')


def targets():
    from board.custom import board_object as BO
    from board.custom import hwsys_system as HS
    return [{'hardware_solution': s['name'], 'variant': s.get('solution', ''), 'board': _ref(s.get('boards_json'), 'BoardDefinition'),
             'circuit': _ref(s.get('circuits_json'), 'CircuitDefinition')} for s in HS.rows(BO.seed_tables())]


def soc_of(variant, board):
    from cmod.custom import catom_variables as CV
    vs = CV.variables(variant)
    if vs and vs[0].get('soc'):
        return vs[0]['soc']
    from board.custom import twin_kinds as TK
    k = next((k for k in TK.KINDS if k['board'] == board), None)
    return k['mcu'] if k else ''


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _inputs(circuit, board, variant, tables, claims, knobs):
    from cmod.custom import catom_assertions as CA
    from cmod.custom import catom_variables as CV
    circ, nets, comps, pin_nets = EC.circuit_rows(tables, circuit)
    return {'circuit': [circ, nets, comps, pin_nets], 'board': board, 'claims': sorted(claims, key=lambda c: c.get('name', '')), 'knobs': knobs,
            'variables': [(v['name'], v.get('bench_value'), v.get('board_value'), v.get('status')) for v in CV.variables(variant)],
            'bindings': CA.struct_pin_bindings(variant), 'solver': SOLVER}


def solve(variant, board, circuit, hardware_solution='', tables=None):
    from cmod.custom import catom_variables as CV
    tables = tables if tables is not None else EC.tables_for(None)
    tables.setdefault('_resolved', {})
    soc = soc_of(variant, board)
    knobs = CV.variant_knobs(variant, soc)
    resolved_board, claims = EC._resolve(variant, tables)
    solution_checks = []
    binding = variant
    if resolved_board != board:
        solution_checks.append({'component': '', 'rule': 'binding', 'status': 'undetermined', 'subject': variant,
                                'detail': 'the firmware variant %s does not resolve to a firmware binding on %s (it resolves to %r): its pin claims '
                                          'are not read, so a pull the firmware sets is not seen by the pull rule' % (variant, board, resolved_board),
                                'part': '', 'cite': ''})
        binding, claims = board, []
    findings = EC.check(circuit, binding, tables)
    prefix = hardware_solution or '%s@%s' % (circuit, board)
    out = SD.components(circuit, board, soc, tables, claims, prefix)
    meta = out.pop('_port_meta')
    _circ, _nets, _comps, pin_nets = EC.circuit_rows(tables, circuit)
    label_of = {n['name']: n['net'] for n in _nets}
    view = {'pin_nets_by_label': {}}
    for pn in pin_nets:
        view['pin_nets_by_label'].setdefault(label_of.get(pn.get('circuit_net'), ''), []).append(pn)
    inputs_sha = _sha(_inputs(circuit, board, variant, tables, claims, knobs))
    checks = []
    for comp in out['SchematicComponent']:
        ports = [p for p in out['SchematicComponentPort'] if p['component'] == comp['name']]
        parts = [p for p in out['SchematicComponentPart'] if p['component'] == comp['name']]
        mine = SR.conditioning(comp, ports, parts, meta, view, knobs, variant) + SR.electrical(comp, ports, parts, meta, findings)
        state, words = SR.verdict(mine)
        comp.update(solve_state=state, solved_by=SOLVER, findings=words, hardware_solution=hardware_solution, inputs_sha256=inputs_sha)
        checks += mine
    taken = {(c['rule'], c['subject']) for c in checks}
    solution_checks += [{'component': '', 'rule': f['rule'], 'status': f['status'], 'subject': f.get('subject', ''), 'detail': f.get('detail', ''),
                         'part': '', 'cite': f.get('cite', '')} for f in findings if (f['rule'], f.get('subject', '')) not in taken]
    rows = []
    for i, c in enumerate(checks + solution_checks):
        rows.append(dict(c, name='%s/%02d-%s' % (c['component'] or '%s/(solution)' % prefix, i, c['rule']), hardware_solution=hardware_solution,
                         order=i))
    out['SchematicComponentCheck'] = rows
    solved = dict(out, _claims=claims, _port_meta=meta)
    out['HardwareFeature'] = FD.features(hardware_solution, variant, board, soc, solved)
    for f in out['HardwareFeature']:
        comp = next(c for c in out['SchematicComponent'] if c['name'] == f['schematic_component'])
        comp['protocol'] = f['protocol']
    out['inputs_sha256'] = inputs_sha
    out['solver'] = SOLVER
    out['target'] = {'hardware_solution': hardware_solution, 'variant': variant, 'board': board, 'circuit': circuit}
    return out


def solve_solution(name, tables=None):
    t = next((t for t in targets() if t['hardware_solution'] == name), None)
    if t is None:
        raise KeyError('no HardwareSolution %r (there are: %s)' % (name, ', '.join(x['hardware_solution'] for x in targets())))
    return solve(t['variant'], t['board'], t['circuit'], name, tables)


def _path(name):
    return os.path.join(RECORD_DIR, '%s.json' % name)


def record(name, tables=None):
    res = solve_solution(name, tables)
    os.makedirs(RECORD_DIR, exist_ok=True)
    with open(_path(name), 'w') as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write('\n')
    return res


def load(name):
    try:
        with open(_path(name)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def recorded():
    if not os.path.isdir(RECORD_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(RECORD_DIR) if f.endswith('.json'))


def seed_rows():
    out = {c: [] for c in CLASSES}
    for name in recorded():
        rec = load(name) or {}
        for c in CLASSES:
            out[c] += rec.get(c, [])
    return out


def compare(name, tables=None):
    fresh = solve_solution(name, tables)
    rec = load(name)
    if rec is None:
        return fresh, None, False, 'no record yet: custom/solved/%s.json (pol hwnocode features %s --write)' % (name, name)
    if rec.get('inputs_sha256') != fresh['inputs_sha256']:
        return fresh, rec, False, 'the record is STALE: an input changed since it was solved (pol hwnocode features %s --write)' % name
    same = all(rec.get(c) == fresh[c] for c in CLASSES)
    return fresh, rec, same, 'the record matches a fresh solve' if same else 'same inputs but different rows: the solver changed (re-record with --write)'


def _print(res):
    t = res['target']
    print('%s - %s on %s, circuit %s' % (t['hardware_solution'] or '(no HardwareSolution)', t['variant'], t['board'], t['circuit']))
    for c in res['SchematicComponent']:
        print('  [%s] %s (%s): %s' % (c['solve_state'].upper(), c['title'], c['name'], c['findings']))
        for k in [k for k in res['SchematicComponentCheck'] if k['component'] == c['name']]:
            print('      %-12s %-16s %-18s %s' % (k['status'], k['rule'], k['subject'][:18], k['detail'][:150]))
    sol = [k for k in res['SchematicComponentCheck'] if not k['component']]
    if sol:
        print('  about the whole solution:')
        for k in sol:
            print('      %-12s %-16s %-18s %s' % (k['status'], k['rule'], k['subject'][:18], k['detail'][:150]))
    from hwnocode.custom import feature_columns as FC
    for f in res['HardwareFeature']:
        st = FC.state(f, res['SchematicComponent'])
        print('  feature %s: %s' % (f['name'], st['words']))
        for col in st['columns']:
            print('      %-20s %-9s %s' % (col['label'], col['source'], col['value'][:140]))


def _kicad(name, out):
    from hwnocode.custom import schematic_kicad as K
    from pcb.custom.pcb_engines import EngineRefused
    rec = load(name)
    if rec is None:
        print('refused: no record for %r (pol hwnocode features %s --write first)' % (name, name))
        return 2
    try:
        r = K.render(rec)
    except (EngineRefused, K.DesignRefused) as e:
        print('refused: %s' % e)
        return 2
    if not out:
        from polariApiServer.module_home import module_home
        out = os.path.join(module_home('hwnocode', os.environ.get('POLARI_HWNOCODE_HOME')), name, 'schematic')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, r['name']), 'w') as fh:
        fh.write(r['kicad_sch'])
    if r['svg']:
        with open(os.path.join(out, r['name'].replace('.kicad_sch', '.svg')), 'w') as fh:
            fh.write(r['svg'])
    same, diff = r['parity']
    print('%s: one KiCad sheet from the solved components (sha256 %s)' % (name, r['sha256'][:16]))
    print('  written: %s (+ .svg)' % os.path.join(out, r['name']))
    print('  KiCad netlist vs the rows: %s' % ('the same nets' if same else 'DIFFERENT'))
    for x in diff:
        print('    %s' % x)
    print('  electrical-rule check: %d errors, %d warnings %s' % (r['erc']['errors'], r['erc']['warnings'], r['erc']['by_type']))
    for x in r['report'].get('inside_chip', []):
        print('  inside the chip (not a part on the sheet): %s' % x)
    return 0 if same else 1


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol hwnocode features')
    ap.add_argument('solution', nargs='?', default='')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--circuit', default='')
    ap.add_argument('--board', default='')
    ap.add_argument('--variant', default='')
    ap.add_argument('--kicad', action='store_true', help='also write the whole solution as one KiCad sheet, check it and draw it (pcb engine)')
    ap.add_argument('--out', default='')
    a = ap.parse_args(argv)
    if a.kicad:
        return _kicad(a.solution, a.out)
    if a.circuit:
        if not (a.board and a.variant):
            print('refused: --circuit needs --board and --variant')
            return 2
        _print(solve(a.variant, a.board, a.circuit))
        return 0
    if not a.solution:
        for t in targets():
            print('%s: %s on %s, circuit %s (record: %s)' % (t['hardware_solution'], t['variant'], t['board'], t['circuit'],
                                                             'yes' if load(t['hardware_solution']) else 'none'))
        return 0
    try:
        if a.write:
            res = record(a.solution)
            _print(res)
            print('recorded: custom/solved/%s.json (inputs sha256 %s)' % (a.solution, res['inputs_sha256'][:16]))
            return 0
        fresh, _rec, same, why = compare(a.solution)
    except KeyError as e:
        print('refused: %s' % e.args[0])
        return 2
    _print(fresh)
    print('record: %s' % why)
    return 0 if same else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
