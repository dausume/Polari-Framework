"""Selftest for computers (cmp-c: taxonomy + assembly gates +
use-case profile fits).
Run from polari-framework/:
  PYTHONPATH=.:modules python3 -m computers.computers_selftest
Exercises the taxonomy's coverage of PART_KINDS, the DFA-style
gate engine (answers, refusals, honest unverified), the
composition view's derived level, and the ai-6-shaped profile fit
ladder — all against the seed dicts (dict-or-object tolerant pure
functions, no server boot).
"""

import json
import sys

from computerparts.parts_basis import PART_KINDS
from computerparts.parts_seed import (
    SEED_COMPUTER_BUILDS, SEED_COMPUTER_PARTS,
)

from computers.custom.computers_fit import fit_matrix, fit_profile
from computers.custom.computers_gates import (
    assembly_gate_report, composition_view,
)
from computers.computers_page import (
    SEED_COMPUTERS_PAGE_DISPLAYS,
)
from computers.computers_ports_basis import (
    SEED_INTERCONNECTS, SEED_PORT_EXAMPLE_PARTS,
    SEED_PORT_PART_CLASSES, interconnect_matrix,
    port_budget_gates, viable_links,
)
from computers.computers_seed import (
    SEED_COMPUTER_ASSEMBLIES, SEED_COMPUTER_PART_CLASSES,
    SEED_COMPUTER_PROFILES,
)

_results = []

#: Gates the engine can currently answer or honestly refuse.
KNOWN_GATES = {'socket', 'ram-type', 'psu-wattage',
               'gpu-clearance', 'ram-slots', 'slot-budget',
               'cooler-capacity', 'm2-or-bay-budget',
               # cmp-c-6: the generalized provided-vs-required
               # per-token gate family.
               'port-budget'}


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _parts_by_name():
    return {p['name']: p for p in SEED_COMPUTER_PARTS}


def _build(name):
    return next(b for b in SEED_COMPUTER_BUILDS
                if b['name'] == name)


def _profile(name):
    return next(p for p in SEED_COMPUTER_PROFILES
                if p['name'] == name)


def _assembly(name):
    return next(a for a in SEED_COMPUTER_ASSEMBLIES
                if a['name'] == name)


def _gate(report, name):
    return next(g for g in report['gates'] if g['check'] == name)


def main():
    parts = _parts_by_name()

    # ---- cmp-c-1: taxonomy coverage -------------------------------
    all_part_classes = (SEED_COMPUTER_PART_CLASSES
                        + SEED_PORT_PART_CLASSES)
    tax_kinds = {c['name'] for c in all_part_classes}
    check('taxonomy: EVERY computerparts PART_KIND has a class '
          'row (incl. the cmp-c-1 additions nic/fpga-accelerator '
          'and the cmp-c-6 comms/usb-expansion kinds)',
          tax_kinds == set(PART_KINDS),
          f'taxonomy {sorted(tax_kinds)} vs '
          f'kinds {sorted(PART_KINDS)}')
    gate_names = set()
    for c in all_part_classes:
        for iface in json.loads(c['interface_specs_json']):
            gate_names.add(iface['gate'])
    check('taxonomy: every declared interface spec names a KNOWN '
          'gate — the taxonomy cannot promise a check the engine '
          'never heard of',
          gate_names <= KNOWN_GATES,
          f'unknown gates: {gate_names - KNOWN_GATES}')
    check('taxonomy: honest gaps are STATED where seeds do not '
          'declare (gpu length, board pcie slots, cpu tdp)',
          all(c['gaps_note'] for c in SEED_COMPUTER_PART_CLASSES
              if c['name'] in ('gpu', 'motherboard', 'cpu')))
    seed_kinds = {p['kind'] for p in SEED_COMPUTER_PARTS}
    check('seeds: the new kinds ship example parts with DATED '
          'prices (nic + fpga-accelerator)',
          {'nic', 'fpga-accelerator'} <= seed_kinds
          and all(p['price_as_of'] and p['price_note']
                  for p in SEED_COMPUTER_PARTS
                  if p['kind'] in ('nic', 'fpga-accelerator')))

    # ---- cmp-c-2: assembly gates ----------------------------------
    xeon = assembly_gate_report(_assembly('assembly-xeon-6338n'),
                                _build('build-xeon-6338n'), parts)
    check('gates(xeon): socket + ram-type + ram-slots ANSWER ok '
          '(LGA4189 both sides; 8 physical RDIMMs vs the '
          'X12SPL-F\'s 8 slots)',
          _gate(xeon, 'socket')['verdict'] == 'ok'
          and _gate(xeon, 'ram-type')['verdict'] == 'ok'
          and _gate(xeon, 'ram-slots')['verdict'] == 'ok'
          and '8 physical module(s) vs 8 board slot(s)'
          in _gate(xeon, 'ram-slots')['detail'],
          f'gates={xeon["gates"]}')
    check('gates(xeon): no-GPU build leaves psu-wattage and '
          'slot-budget honestly UNVERIFIED with the affordance '
          'named — feasible True over answered gates only',
          _gate(xeon, 'psu-wattage')['verdict'] == 'unverified'
          and _gate(xeon, 'slot-budget')['verdict'] == 'unverified'
          and 'declare' in _gate(xeon, 'slot-budget')['detail']
          and xeon['feasible'] is True
          and not xeon['refusals'],
          f'gates={xeon["gates"]}')
    b3090 = assembly_gate_report(_assembly('assembly-used-3090'),
                                 _build('build-used-3090'), parts)
    check('gates(3090): psu-wattage answers ok (850 W vs 625 '
          'needed); ram-slots counts the KIT\'s declared physical '
          'modules (2x32 -> 2 of 4); slot-budget stays unverified '
          'because the seed board does not declare pcie_x16_slots '
          '(the taxonomy gaps_note, demonstrated)',
          _gate(b3090, 'psu-wattage')['verdict'] == 'ok'
          and _gate(b3090, 'ram-slots')['verdict'] == 'ok'
          and '2 physical module(s)'
          in _gate(b3090, 'ram-slots')['detail']
          and _gate(b3090, 'slot-budget')['verdict'] == 'unverified'
          and 'pcie_x16_slots not declared'
          in _gate(b3090, 'slot-budget')['detail'],
          f'gates={b3090["gates"]}')
    # A board that DECLARES slots starts answering — and refuses
    # when consumers exceed them.
    tight_parts = dict(parts)
    tight_parts['mb-tight'] = {
        'name': 'mb-tight', 'kind': 'motherboard',
        'specs_json': '{"socket": "AM5", "ram_type": "DDR5", '
                      '"ram_slots": 4, "pcie_x16_slots": 1}'}
    tight_build = {
        'name': 'build-tight', 'parts_json': json.dumps(
            ['gpu-rtx3090-used', 'nic-10gbe-dual', 'mb-tight']),
        'specs_json': '{}'}
    tight = assembly_gate_report({'name': 'assembly-tight'},
                                 tight_build, tight_parts)
    check('gates: slot-budget ANSWERS once a board declares '
          'pcie_x16_slots — and REFUSES with the consumers named '
          'when they exceed the budget (2 consumed vs 1)',
          _gate(tight, 'slot-budget')['verdict'] == 'mismatch'
          and 'gpu-rtx3090-used'
          in _gate(tight, 'slot-budget')['detail']
          and tight['feasible'] is False
          and tight['refusals'],
          f'gates={tight["gates"]}')
    # A kit that does not declare its module count cannot be
    # counted — unverified, never a guess.
    nokit_parts = dict(tight_parts)
    nokit_parts['ram-mystery-kit'] = {
        'name': 'ram-mystery-kit', 'kind': 'ram',
        'specs_json': '{"capacity_mb": 32768, '
                      '"ram_type": "DDR5"}'}
    nokit = assembly_gate_report(
        {'name': 'assembly-nokit'},
        {'name': 'build-nokit', 'parts_json': json.dumps(
            ['ram-mystery-kit', 'mb-tight']), 'specs_json': '{}'},
        nokit_parts)
    check('gates: a ram kit without a declared physical module '
          'count leaves ram-slots UNVERIFIED naming the kit — '
          'counting rows would lie about a 2x16',
          _gate(nokit, 'ram-slots')['verdict'] == 'unverified'
          and 'ram-mystery-kit'
          in _gate(nokit, 'ram-slots')['detail'],
          f'gates={nokit["gates"]}')

    # ---- cmp-c-2: composition view --------------------------------
    view = composition_view(_assembly('assembly-used-3090'),
                            _build('build-used-3090'), parts)
    check('composition view: every interface designed-separable '
          '-> derived level ASSEMBLY (composition\'s own rule), '
          'cpu<->board + ram<->board + gpu<->board among the '
          'interfaces, honestly labeled view-only',
          view['derived_level'] == 'assembly'
          and not view['materialized']
          and {('socket-latch'), ('dimm-slot'), ('pcie-slot')}
          <= {i['retention_scheme'] for i in view['interfaces']}
          and len(view['members']) == 8,
          f'view={view}')

    # ---- cmp-c-3: profile fits ------------------------------------
    fit_ai_3090 = fit_profile(_profile('profile-assistive-ai'),
                              _build('build-used-3090'), parts)
    check('fit: used-3090 build CLEARS the assistive-AI floors '
          '(cores/ram/disk/vram/gpu) — overall fit with every '
          'verdict evidence-bearing',
          fit_ai_3090['overall'] == 'fit'
          and all(v['verdict'] == 'yes'
                  for v in fit_ai_3090['verdicts'])
          and fit_ai_3090['planner_class'] == 'gpu',
          f'fit={fit_ai_3090}')
    fit_ai_xeon = fit_profile(_profile('profile-assistive-ai'),
                              _build('build-xeon-6338n'), parts)
    check('fit: the GPU-less xeon build MISSES assistive-AI on '
          'vram + gpu_required with the failing numbers quoted '
          '(0 < 16384) — no-fit, never rounded up',
          fit_ai_xeon['overall'] == 'no-fit'
          and any(v['requirement'] == 'vram_mb'
                  and v['verdict'] == 'no'
                  and '0 < 16384' in v['detail']
                  for v in fit_ai_xeon['verdicts'])
          and any(v['requirement'] == 'gpu_required'
                  and v['verdict'] == 'no'
                  for v in fit_ai_xeon['verdicts']),
          f'fit={fit_ai_xeon}')
    fit_db_xeon = fit_profile(_profile('profile-db-bound-storage'),
                              _build('build-xeon-6338n'), parts)
    check('fit: DB-bound profile vs xeon — the 2 TB seed SSD '
          'misses the 4 TB disk floor (honest gap in the OWNED '
          'build, numbers quoted) and the declare-only db_binding '
          'block rides the result (decision 3)',
          fit_db_xeon['overall'] == 'no-fit'
          and any(v['requirement'] == 'disk_mb'
                  and v['verdict'] == 'no'
                  for v in fit_db_xeon['verdicts'])
          and fit_db_xeon['db_binding']['mode'] == 'declare-only'
          and 'object-ownership'
          in fit_db_xeon['db_binding']['note'],
          f'fit={fit_db_xeon}')
    fpga_build = {
        'name': 'build-fpga-bench', 'parts_json': json.dumps(
            ['cpu-ryzen7-7700', 'mb-am5-b650', 'ram-ddr5-32gb',
             'fpga-arty-a7-100t']),
        'specs_json': '{"cores": 8, "ram_mb": 32768}'}
    fit_fpga = fit_profile(_profile('profile-fpga-lab'),
                           fpga_build, parts)
    check('fit: fpga_required is a PRESENCE check that says so — '
          'the Arty bench board satisfies the fpga-lab profile '
          'and the verdict detail states the presence-only limit',
          fit_fpga['overall'] == 'fit'
          and any(v['requirement'] == 'fpga_required'
                  and 'presence check only' in v['detail']
                  for v in fit_fpga['verdicts']),
          f'fit={fit_fpga}')
    fit_lp = fit_profile(_profile('profile-low-power-member'),
                         _build('build-used-3090'), parts)
    check('fit: floors are MINIMUMS — a big machine clears the '
          'low-power member floors (fit); smallness is the '
          'planner_class\'s job, not a ceiling here',
          fit_lp['overall'] == 'fit'
          and fit_lp['planner_class'] == 'small')
    unverified = fit_profile(
        {'name': 'profile-vram-only',
         'floors_json': '{"vram_mb": 8192}'},
        {'name': 'build-undeclared', 'parts_json': '[]',
         'specs_json': '{"cores": 4}'}, parts)
    check('fit: a floor the build never declares yields '
          'UNVERIFIED overall with the affordance named — not a '
          'yes, not a no',
          unverified['overall'] == 'unverified'
          and 'does not declare'
          in unverified['verdicts'][0]['detail'],
          f'fit={unverified}')
    matrix = fit_matrix(SEED_COMPUTER_PROFILES,
                        SEED_COMPUTER_BUILDS, parts)
    check('fit matrix: every published profile scored against '
          'every published build',
          len(matrix) == len(SEED_COMPUTER_PROFILES)
          and all(len(r['fits']) == len(SEED_COMPUTER_BUILDS)
                  for r in matrix))

    # ---- profiles are data ----------------------------------------
    check('profiles: the decision-2 v1 set ships (4 planned + '
          'low-power member), every floor carries its WHY, and '
          'exactly the DB profile declares db_binding',
          len(SEED_COMPUTER_PROFILES) == 5
          and all(p['rationale'] for p in SEED_COMPUTER_PROFILES)
          and [p['name'] for p in SEED_COMPUTER_PROFILES
               if p['db_binding'] == 'declare']
          == ['profile-db-bound-storage'])
    check('profiles: planner_class keys stay within the dl-6 '
          'vocabulary (the cmp-c-5 splice)',
          {p['planner_class'] for p in SEED_COMPUTER_PROFILES}
          <= {'normal', 'highmem', 'highcpu', 'gpu', 'small'})

    # ---- page seed -------------------------------------------------
    page = SEED_COMPUTERS_PAGE_DISPLAYS[0]
    comps = set()
    for row in json.loads(page['definition'])['rows']:
        for item in row['items']:
            comps.add(item['componentProps']['componentName'])
    check('page seed: /display/computers is a PAGE of the two '
          'generic components only — zero Angular work',
          page['isPage'] and page['pageRoute'] == 'computers'
          and comps <= {'class-rows-table', 'api-structured-panel'},
          f'components={comps}')

    # ---- seed hygiene ----------------------------------------------
    # ---- cmp-c-6: interconnects as data ---------------------------
    m2wifi = next(p for p in SEED_PORT_EXAMPLE_PARTS
                  if p['name'] == 'comms-m2e-wifi-bt-example')
    usbwifi = next(p for p in SEED_PORT_EXAMPLE_PARTS
                   if p['name'] == 'comms-usb-wifi-example')
    usbcard = next(p for p in SEED_PORT_EXAMPLE_PARTS
                   if p['name'] == 'usbexp-pcie-usbc-card-example')
    board = {'name': 'mb-ports', 'kind': 'motherboard',
             'title': 'board declaring ports',
             'specs_json': json.dumps({
                 'ports_provided': {'m2-key-e': 1, 'pcie-x4': 1,
                                    'usb-a': 2}})}
    check('ports: viable_links matches provider to requirer per '
          'token, both directions (board m2-key-e seat <- m2 '
          'wifi module)',
          viable_links(board, m2wifi) == [{
              'interconnect': 'm2-key-e', 'from': 'mb-ports',
              'to': 'comms-m2e-wifi-bt-example',
              'provided': 1, 'required': 1}])
    check('ports: an ENABLER chains — the pcie usb-c card '
          'requires a pcie-x4 seat from the board AND provides '
          'usb-c the board lacks',
          viable_links(board, usbcard) == [{
              'interconnect': 'pcie-x4', 'from': 'mb-ports',
              'to': 'usbexp-pcie-usbc-card-example',
              'provided': 1, 'required': 1}]
          and viable_links(usbcard, usbwifi) == [])
    ic_by_name = {r['name']: r for r in SEED_INTERCONNECTS}
    matrix = interconnect_matrix(
        [board, m2wifi, usbwifi, usbcard], ic_by_name)
    check('ports: interconnect_matrix yields typed edges + every '
          'used token in the seeded vocabulary; no part here is '
          'undeclared',
          len(matrix['nodes']) == 4
          and matrix['undeclared'] == []
          and matrix['vocabularyMissing'] == []
          and {(e['from'], e['to'], e['interconnect'])
               for e in matrix['edges']}
          == {('mb-ports', 'comms-m2e-wifi-bt-example',
               'm2-key-e'),
              ('mb-ports', 'comms-usb-wifi-example', 'usb-a'),
              ('mb-ports', 'usbexp-pcie-usbc-card-example',
               'pcie-x4')},
          f'matrix={matrix}')
    undeclared_matrix = interconnect_matrix(
        [parts['cpu-xeon-6338n-owned'], m2wifi], ic_by_name)
    check('ports: a part with NO port declarations is listed '
          'undeclared, never guessed into edges',
          'cpu-xeon-6338n-owned' in undeclared_matrix['undeclared']
          and undeclared_matrix['edges'] == [],
          f'matrix={undeclared_matrix}')
    port_parts = {p['name']: p for p in
                  (SEED_PORT_EXAMPLE_PARTS + [board])}
    port_build = {'name': 'build-ports', 'parts_json': json.dumps(
        ['mb-ports', 'comms-m2e-wifi-bt-example',
         'comms-usb-wifi-example',
         'usbexp-pcie-usbc-card-example']), 'specs_json': '{}'}
    budget = {g['check']: g for g in
              port_budget_gates(port_build, port_parts)}
    check('ports: port-budget answers per token — seats ok '
          '(m2-key-e, pcie-x4, usb-a within provision)',
          budget['port-budget:m2-key-e']['verdict'] == 'ok'
          and budget['port-budget:pcie-x4']['verdict'] == 'ok'
          and budget['port-budget:usb-a']['verdict'] == 'ok',
          f'budget={budget}')
    crowded = {'name': 'build-crowded', 'parts_json': json.dumps(
        ['mb-ports', 'comms-m2e-wifi-bt-example',
         'comms-usb-wifi-example', 'comms-usb-wifi-2']),
        'specs_json': '{}'}
    crowded_parts = dict(port_parts)
    crowded_parts['comms-usb-wifi-2'] = dict(
        usbwifi, name='comms-usb-wifi-2',
        specs_json=json.dumps({'ports_required': {'usb-a': 2}}))
    cbudget = {g['check']: g for g in
               port_budget_gates(crowded, crowded_parts)}
    check('ports: a DECLARED shortage refuses (3 usb-a required '
          'vs 2 provided -> mismatch), never silently fits',
          cbudget['port-budget:usb-a']['verdict'] == 'mismatch'
          and '3 required' in cbudget['port-budget:usb-a']['detail'],
          f'budget={cbudget}')
    nodecl_budget = port_budget_gates(
        _build('build-xeon-6338n'), parts)
    check('ports: a build declaring NO ports gets one honest '
          'unverified port-budget gate naming the affordance',
          len(nodecl_budget) == 1
          and nodecl_budget[0]['verdict'] == 'unverified'
          and 'declare' in nodecl_budget[0]['detail'])
    check('ports seeds: example parts are honestly UNPRICED '
          '(price 0 + the ai-8 note) and every interconnect row '
          'has kind/carries/attachment',
          all(p['price_amount'] == 0.0 and 'UNPRICED'
              in p['price_note']
              for p in SEED_PORT_EXAMPLE_PARTS)
          and all(r['kind'] and r['carries'] and r['attachment']
                  for r in SEED_INTERCONNECTS))

    all_seeds = (SEED_COMPUTER_PART_CLASSES
                 + SEED_PORT_PART_CLASSES
                 + SEED_INTERCONNECTS
                 + SEED_PORT_EXAMPLE_PARTS
                 + SEED_COMPUTER_PROFILES
                 + SEED_COMPUTER_ASSEMBLIES)
    check('seeds: every row carries is_prior=True (the upsert '
          'path\'s human-edit protection) and unique names',
          all(s.get('is_prior') is True for s in all_seeds)
          and len({s['name'] for s in all_seeds})
          == len(all_seeds))
    check('seeds: every assembly names an existing build',
          all(any(b['name'] == a['build_ref']
                  for b in SEED_COMPUTER_BUILDS)
              for a in SEED_COMPUTER_ASSEMBLIES))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
