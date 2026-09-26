"""
Selftest for computelod (tt-0). Run from polari-framework/:
  PYTHONPATH=.:modules python3 modules/computelod/computelod_selftest.py
Fake manager; exercises: the five classes, the ELEVEN rungs and their owners (microchip by design_level_ref,
pspp, materials_science), die/package NOT rungs, kinds never rungs, the compute-lod tech tree (learning order ≠
implementation order), a downward walk and an upward characterization with its two statuses, the manifest.
"""
import json
import os
import sys
import types

from computelod.computelod_basis import COMPUTELOD_CLASSES, ComputeLOD, ComputeKind, ComputeMapping, CharacterizationMapping, CompilerArtifact
from computelod.computelod_seed import (COMPUTELOD_SEED_PAIRS, SEED_COMPUTE_LODS, SEED_COMPUTE_KINDS, SEED_COMPUTE_TECH_NODES,
                                        SEED_COMPUTE_TECH_TREES, SEED_COMPUTE_TECH_SEGMENTS, TREE)
from computelod.custom.computelod_walk import ladder, walk

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    tables = {c.__name__: {} for c in COMPUTELOD_CLASSES}; tables['TechNode'] = {}
    mgr = types.SimpleNamespace(objectTables=tables, db=None)
    for cls, rows in (('ComputeLOD', SEED_COMPUTE_LODS), ('ComputeKind', SEED_COMPUTE_KINDS), ('TechNode', SEED_COMPUTE_TECH_NODES)):
        for r in rows:
            row = types.SimpleNamespace(**r); tables[cls][id(row)] = row
    return mgr


def _add(mgr, cls, **kw):
    row = types.SimpleNamespace(**kw); mgr.objectTables[cls][id(row)] = row; return row


check('the module registers exactly FIVE row classes', len(COMPUTELOD_CLASSES) == 5, [c.__name__ for c in COMPUTELOD_CLASSES])
check('every class is one file under objects/computelod/', all(c.__module__ == 'computelod.objects.computelod.%s' % c.__name__ for c in COMPUTELOD_CLASSES))

# ---- the ladder (plan §F1)
names = [r['name'] for r in sorted(SEED_COMPUTE_LODS, key=lambda r: r['rank'])]
check('ELEVEN rungs, in order, C to materials', names == ['c-source', 'compiler', 'isa', 'microarchitecture', 'rtl', 'logic-netlist', 'standard-cells', 'devices', 'layout', 'fabrication', 'materials'], names)
check('ranks are 1..11 with no gap', sorted(r['rank'] for r in SEED_COMPUTE_LODS) == list(range(1, 12)))
check('the four groups: software / architecture / digital / physical', [r['group'] for r in sorted(SEED_COMPUTE_LODS, key=lambda r: r['rank'])] == ['software'] * 3 + ['architecture'] * 2 + ['digital'] * 3 + ['physical'] * 3)
check('die and package are NOT rungs — they hang off microarchitecture through the microchip ladder', 'die' not in names and 'package' not in names)
by = {r['name']: r for r in SEED_COMPUTE_LODS}
check('the four hardware rungs REFERENCE the ratified microchip ladder (design_level_ref), never a second ladder',
      by['devices']['design_level_ref'] == 'device' and by['standard-cells']['design_level_ref'] == 'standard-cell'
      and by['logic-netlist']['design_level_ref'] == 'functional-block' and by['microarchitecture']['design_level_ref'] == 'subsystem'
      and all(by[n]['design_level_ref'] == '' for n in ('c-source', 'compiler', 'isa', 'rtl', 'layout', 'fabrication', 'materials')))
check('fabrication is PSPP\'s and materials is the materials model\'s — no new materials database',
      by['fabrication']['owner_module'] == 'pspp' and by['materials']['owner_module'] == 'materials_science'
      and any(c['class'] == 'ProcessingStage' for c in json.loads(by['fabrication']['artifact_classes_json'])))
check('RTL is owned by hwfpga (generated Verilog-2001, SV testbenches — D6)', by['rtl']['owner_module'] == 'hwfpga' and json.loads(by['rtl']['languages_json']) == ['Verilog', 'SystemVerilog'])
check('every rung names its concept node in the compute-lod tree', all(r['concept_node'] == 'lod-' + r['name'] for r in SEED_COMPUTE_LODS))

# ---- kinds (plan §F1): a specialization within a rung, never a rung
check('70 kinds seeded as ROWS, each naming its rung', len(SEED_COMPUTE_KINDS) == 70 and all(k['rung'] in by for k in SEED_COMPUTE_KINDS))
check('tensor-array is a MICROARCHITECTURE kind, not "level 4.5"', any(k['rung'] == 'microarchitecture' and k['name'].endswith('/tensor-array') for k in SEED_COMPUTE_KINDS) and 'tensor-array' not in names)
check('  …and it maps onto the microchip ladder\'s npu-tensor-array subsystem kind', next(k for k in SEED_COMPUTE_KINDS if k['name'] == 'microarchitecture/tensor-array')['design_kind_ref'] == 'npu-tensor-array')
check('firmware complexity (direct / freertos / zephyr / linux) is a KIND on the C rung, not a rung', {k['name'] for k in SEED_COMPUTE_KINDS if k['rung'] == 'c-source'} == {'c-source/direct-firmware', 'c-source/freertos', 'c-source/zephyr', 'c-source/linux-kernel'})
m = _mgr()
lad = ladder(m)
check('GET /api/computelod renders the ladder with each rung\'s kinds', len(lad) == 11 and 'tensor-array' in lad[3]['kinds'] and lad[3]['name'] == 'microarchitecture')

# ---- the learning layer = the tech tree (plan §B3): learning order ≠ implementation order
check('one TechNode per rung in the compute-lod tree, with a cross_ref to the ComputeLOD row', len(SEED_COMPUTE_TECH_NODES) == 11 and all(n['tree_name'] == TREE for n in SEED_COMPUTE_TECH_NODES)
      and all(json.loads(n['cross_refs_json'])[0]['class'] == 'ComputeLOD' for n in SEED_COMPUTE_TECH_NODES))
deps = {n['name']: json.loads(n['depends_on_json']) for n in SEED_COMPUTE_TECH_NODES}
check('learning order ≠ implementation order: the ISA concept recommends logic first, though logic is five rungs BELOW isa', 'lod-logic-netlist' in deps['lod-isa'])
check('  …and devices recommend materials, which is the BOTTOM rung', deps['lod-devices'] == ['lod-materials'])
check('tools are tech-tree segment assignments of kind real (not columns on the rung)', all(s['segment_kind'] == 'real' for s in SEED_COMPUTE_TECH_SEGMENTS) and len(SEED_COMPUTE_TECH_SEGMENTS) == sum(len(json.loads(r['tools_json'])) for r in SEED_COMPUTE_LODS))
check('the tree is seeded inactive and not the baseline (it is a learning map, not the electronics tree)', SEED_COMPUTE_TECH_TREES[0]['is_active'] is False and SEED_COMPUTE_TECH_TREES[0]['is_baseline'] is False)
check('the tree rows ride in the seed pairs only when techtree is present (guarded), and the ladder seeds regardless',
      [p[0] for p in COMPUTELOD_SEED_PAIRS][:5] == ['ComputeLOD', 'ComputeKind', 'ComputeMapping', 'CharacterizationMapping', 'CompilerArtifact'])

# ---- walking: down through ComputeMappings, up through CharacterizationMappings (plan §F2, §F5)
_add(m, 'ComputeMapping', name='c-add→isa', kind='one-to-one', source_rung='c-source', source_ref='c = a + b', target_rung='isa', target_ref='add x5,x6,x7', mapping_status='implemented', evidence_level='simulated', evidence_ref='gcc-12 -O0', loss_note='')
_add(m, 'ComputeMapping', name='isa→uarch', kind='one-to-many', source_rung='isa', source_ref='add x5,x6,x7', target_rung='microarchitecture', target_ref='picorv32/alu', mapping_status='proposed', evidence_level='none', evidence_ref='', loss_note='')
w = walk(m, 'c-source', 'c = a + b', 'down')
check('walk down from a C statement reaches the ISA instruction, with the edge\'s two statuses', w['edges'][0]['to_ref'] == 'add x5,x6,x7' and w['edges'][0]['evidence_level'] == 'simulated' and w['edges'][0]['mapping_status'] == 'implemented')
w2 = walk(m, 'microarchitecture', 'picorv32/alu', 'down')
check('an absent edge is an HONEST gap, never invented', w2['unresolved'] and w2['edges'] == [] and 'gap' in w2['note'])
_add(m, 'CharacterizationMapping', name='fa→adder-delay', source_rung='standard-cells', source_ref='FA', target_rung='logic-netlist', target_ref='adder32', characteristic='propagation_delay',
     method='OpenSTA', conditions_json=json.dumps({'voltage': 1.8, 'temperature': 25, 'load': '4 FO4', 'corner': 'tt'}), result=0.42, units='ns', mapping_status='implemented', evidence_level='simulated', evidence_ref='sta-run-3')
u = walk(m, 'standard-cells', 'FA', 'up')
check('walk up from a cell reaches the block\'s characteristic with method, result, units and conditions', u['edges'][0]['characteristic'] == 'propagation_delay' and u['edges'][0]['method'] == 'OpenSTA' and u['edges'][0]['units'] == 'ns')
check('an OpenSTA characterization is `simulated`, never `measured` (plan §F2)', u['edges'][0]['evidence_level'] == 'simulated')
cm = CharacterizationMapping(name='x', conditions_json='{}')
check('CharacterizationMapping has conditions_json (voltage/temperature/load/corner) — the load-bearing column', 'conditions_json' in vars(cm) and 'load-bearing' in open('modules/computelod/objects/computelod/CharacterizationMapping.py').read())
ca = CompilerArtifact(name='ir-1', kind='IR', compiler='clang')
check('CompilerArtifact holds IR/AST/assembly/object of ONE compiler — LLVM IR is not a rung (plan §F5)', ca.kind == 'IR' and 'llvm-ir' not in names and 'ir' not in names)

# ---- lod-1: THE TEACHING PATH from the committed report of a real run (custom/lod1_chain.py)
from computelod.custom.lod1_chain import report, rows as lod1_rows, decode_rtype, RTL
from computelod.custom.computelod_walk import path
rep = report()
check('lod-1: a committed report exists (the chain RAN: gcc → yosys → iverilog) — through the engines ladder: path | docker (local image) | remote (a worker)', rep is not None and rep.get('how') in ('path', 'docker', 'remote'), rep and rep.get('how'))
check('  …PicoRV32 is pinned (commit + ISC licence file present)', os.path.exists(os.path.join(RTL, 'picorv32.v')) and os.path.exists(os.path.join(RTL, 'LICENSE')) and len(rep['picorv32_pin'].get('commit', '')) == 40)
check('  …the compiler produced `add a0,a0,a1` for c = a + b at -O1 rv32i', rep['compile']['add_instruction'].replace(' ', '') == 'adda0,a0,a1', rep['compile'])
d = decode_rtype(int(rep['compile']['encoding'], 16))
check('  …and the encoding DECODES to R-type add rd=x10 rs1=x10 rs2=x11 (the ISA rung\'s own arithmetic, checked here — not copied)',
      d['is_add'] and d['rd'] == 10 and d['rs1'] == 10 and d['rs2'] == 11 and rep['compile']['encoding'] == '0x00b50533', d)
check('  …yosys counted the core and the adder (cells > 0), the adder far smaller than the core', rep['core_synth']['cells'] > rep['adder_synth']['cells'] > 0, (rep['core_synth']['cells'], rep['adder_synth']['cells']))
check('  …the adder\'s netlist is gates only (XOR/AND/OR/…), no flip-flops', all('DFF' not in k for k in rep['adder_synth']['by_type']))
check('  …iverilog: the RTL and its gate netlist PASS the same vectors', 'PASS' in rep['simulation']['rtl'] and 'PASS' in rep['simulation']['netlist'], rep['simulation'])
arts, maps, chars = lod1_rows(rep)
check('the rows: 3 artifacts (source, assembly, object), 7 mappings, 5 characterizations', (len(arts), len(maps), len(chars)) == (3, 7, 5))
check('every mapping carries BOTH statuses and an evidence_ref when it claims evidence', all(m_['mapping_status'] and m_['evidence_level'] and (m_['evidence_level'] == 'none' or m_['evidence_ref']) for m_ in maps))
check('a tool\'s own output is `measured`, a simulation is `simulated`, a cited line is `analytical` — never mixed',
      next(m_ for m_ in maps if m_['name'] == 'lod1: gcc → isa add')['evidence_level'] == 'measured'
      and next(c for c in chars if 'correctness (rtl)' in c['name'])['evidence_level'] == 'simulated'
      and next(m_ for m_ in maps if 'picorv32 decode' in m_['name'])['evidence_level'] == 'analytical')
check('the ISA → microarchitecture mapping is ONE-TO-MANY (fetch/decode/read/add/writeback) and says so', next(m_ for m_ in maps if 'picorv32 decode' in m_['name'])['kind'] == 'one-to-many')
check('the path stops HONESTLY: netlist → standard cells is an unresolved mapping, and delay is a characterization with evidence_level none (lod-2)',
      next(m_ for m_ in maps if 'standard cells' in m_['name'])['kind'] == 'unresolved' and next(c for c in chars if 'delay' in c['name'])['evidence_level'] == 'none')
check('every characterization with evidence carries its CONDITIONS (the load-bearing column)', all(json.loads(c['conditions_json']) for c in chars if c['evidence_level'] != 'none'))
m3 = _mgr()
for cls, rws in (('ComputeMapping', maps), ('CharacterizationMapping', chars)):
    for r in rws:
        _add(m3, cls, **r)
pth = path(m3, 'c-source', 'lod1/add.c: c = a + b')
check('walking DOWN from the C statement follows the chain c-source → compiler → isa → microarchitecture → rtl → logic-netlist → standard-cells and stops there, saying so',
      pth['rungs'] == ['c-source', 'compiler', 'isa', 'microarchitecture', 'rtl', 'logic-netlist', 'standard-cells'] and pth['unresolved_at'] == 'standard-cells', pth['rungs'])
up = path(m3, 'logic-netlist', 'yosys synth rv32_add', 'up')
check('walking UP from the adder netlist reaches the RTL through the gate-count characterization', up['rungs'][:2] == ['logic-netlist', 'rtl'], up['rungs'])

# ---- lod-2: OPEN SILICON — the SKY130 mapping and the OpenSTA delay close lod-1's two gaps, with conditions
from computelod.custom.lod2_silicon import report as lod2_report, rows as lod2_rows, LIB, CONDITIONS
from computelod.computelod_seed import SEED_LOD_MAPPINGS, SEED_LOD_CHARACTERIZATIONS
rep2 = lod2_report()
check('lod-2: a committed report exists (yosys abc -liberty → OpenSTA ran)', rep2 is not None and 'mapping' in rep2 and 'timing' in rep2)
check('  …the Liberty is CITED, not committed: repo + pinned commit + sha256 + licence + the corner in words', all(k in rep2['liberty'] for k in ('repo', 'commit', 'sha256', 'licence', 'corner')) and len(rep2['liberty']['commit']) == 40
      and not os.path.exists(os.path.join('modules/computelod/initialData/lod2', LIB['name'])))
check('  …the adder maps onto SKY130 cells (XNOR2 + MAJ3 — a ripple-carry adder as abc builds it) with an area', rep2['mapping']['cells'] > 0 and rep2['mapping']['area_um2'] > 0
      and any('xnor2' in k for k in rep2['mapping']['by_type']) and any('maj3' in k for k in rep2['mapping']['by_type']), rep2['mapping']['by_type'])
check('  …OpenSTA found the worst path (ripple: op bit 1 → alu_out[31]) and the fastest (bit 0 → alu_out[0]), max ≫ min', rep2['timing']['max_path_ns'] > 20 * rep2['timing']['min_path_ns'] > 0 and 'alu_out[31]' in rep2['timing']['max_path'], rep2['timing'])
check('  …the conditions are NAMED: process, temperature, voltage, load, input slew (a delay without them is misleading, §F2)', all(k in CONDITIONS for k in ('process', 'temperature_c', 'voltage_v', 'load_pf', 'input_slew_ns')))
maps2, chars2 = lod2_rows(rep2, rep['adder_synth']['cells'])
check('lod-2 rows: the netlist → standard cells mapping is now MANY-TO-ONE, validated, measured (the tool\'s output) — the lod-1 gap closed BY NAME',
      next(m_ for m_ in maps2 if m_['name'] == 'lod1: netlist → standard cells')['mapping_status'] == 'validated' and next(m_ for m_ in maps2 if m_['name'] == 'lod1: netlist → standard cells')['kind'] == 'many-to-one')
check('  …the delay characterization is now a NUMBER with conditions, evidence SIMULATED (a timing model, not a bench)',
      next(c for c in chars2 if c['name'] == 'lod1: rv32_add propagation delay')['result'] > 0 and next(c for c in chars2 if c['name'] == 'lod1: rv32_add propagation delay')['evidence_level'] == 'simulated'
      and json.loads(next(c for c in chars2 if c['name'] == 'lod1: rv32_add propagation delay')['conditions_json'])['voltage_v'] == 1.8)
check('  …and the NEXT gap is stated honestly: standard cells → devices is PARTIAL (the cells\' SPICE is not read here — lod-3)', next(m_ for m_ in maps2 if 'devices' in m_['name'])['kind'] == 'partial' and next(m_ for m_ in maps2 if 'devices' in m_['name'])['evidence_level'] == 'none')
check('the seed MERGES lod-2 over lod-1 by name: no unresolved netlist→cells row remains, ONE SKY130 delay row',
      not any(m_['kind'] == 'unresolved' and 'netlist' in m_['name'] for m_ in SEED_LOD_MAPPINGS) and sum(1 for c in SEED_LOD_CHARACTERIZATIONS if c['name'] == 'lod1: rv32_add propagation delay') == 1)
# ---- lod-2b: the SECOND Liberty — our own CNT library, characterized here (ngspice), mapped + timed the same way
from computelod.custom.lod2_cnt import report as lod2cnt_report, rows as lod2cnt_rows, LIB_NAME as CNT_LIB
rep2c = lod2cnt_report()
check('lod-2b: a committed CNT report exists with the Liberty beside it (ours: small, derived, committed WITH its provenance)',
      rep2c is not None and os.path.exists(os.path.join('modules/computelod/initialData/lod2/cnt', CNT_LIB)) and rep2c['characterization']['liberty_sha256'] and rep2c['characterization']['result_row'])
check('  …the library is over a DERIVED device: device name + derived_at + the CellCharacterizationRun row are the provenance; the p side is stated',
      rep2c['device'] and rep2c['derivation']['derived_at'] and rep2c['characterization']['p_side'], rep2c['derivation'] if rep2c else None)
check('  …what it does NOT carry is listed (no cell area → area_um2 is None, not 0)', rep2c['mapping']['area_um2'] is None and any('area' in x for x in rep2c['characterization']['not_carried']))
check('  …the adder maps onto the CNT cells and OpenSTA timed it under NAMED conditions inside the characterized grid (V, T, load fF, slew ps)',
      rep2c['mapping']['cells'] > 0 and rep2c['timing']['max_path_ps'] > rep2c['timing']['min_path_ps'] > 0 and all(k in rep2c['conditions'] for k in ('voltage_v', 'temperature_k', 'load_ff', 'input_slew_ps'))
      and abs(rep2c['conditions']['load_ff'] * 1e-15 - max(rep2c['characterization']['grid_loads_f'])) < 1e-19, (rep2c['mapping'], rep2c['timing'], rep2c['conditions']))
maps2c, chars2c = lod2cnt_rows(rep2c, rep['adder_synth']['cells'])
check('lod-2b rows: NEW names beside SKY130 (nothing replaced); mapping evidence is SIMULATED (a model of a model), cells → devices is a real reference to the device row, delay in ns with the conditions',
      {m_['name'] for m_ in maps2c} == {'lod2-cnt: netlist → CNT standard cells', 'lod2-cnt: CNT standard cells → devices'} and all(m_['evidence_level'] == 'simulated' for m_ in maps2c)
      and 'AlignedCNTFETDevice' in next(m_ for m_ in maps2c if 'devices' in m_['name'])['target_ref'] and next(c for c in chars2c if 'propagation' in c['name'])['result'] == rep2c['timing']['max_path_ps'] / 1000.0)
check('the seed holds BOTH libraries: the adder\'s propagation-delay rows are the SKY130 netlist (lod-1/2), the CNT netlist (lod-2b) and the two routed SKY130 variants (lod-3e) — four, none colliding',
      sorted(c['name'] for c in SEED_LOD_CHARACTERIZATIONS if 'propagation delay' in c['name']) == ['lod1: rv32_add propagation delay', 'lod2-cnt: rv32_add propagation delay', 'lod3e: rv32_add propagation delay (routed, with parasitics) (as-flow)', 'lod3e: rv32_add propagation delay (routed, with parasitics) (cells-kept)'],
      sorted(c['name'] for c in SEED_LOD_CHARACTERIZATIONS if 'propagation delay' in c['name']))

# ---- lod-3: cells → transistors → layout, read from the artefacts on both libraries
from computelod.custom.lod3_cells import report as lod3_report, rows as lod3_rows, parse_spice, parse_lef_size, cnt_devices, CELLS_REPO
rep3 = lod3_report()
check('lod-3: a committed report exists; the SKY130 cells are cited per file (url + sha256 at a pinned commit), NOT committed',
      rep3 is not None and all('sha256' in f['spice'] and CELLS_REPO['commit'] in f['spice']['url'] for f in rep3['sky130']['files'].values())
      and not any(fn.endswith('.spice') for fn in os.listdir('modules/computelod/initialData/lod3')))
check('  …every mapped SKY130 cell was READ down to its transistors: xnor2_1 = 10 (5 pfet_hvt + 5 nfet), maj3_1 = 14, all at L = 0.15 µm (the netlists\' 1e-6 scale applied)',
      rep3['sky130']['cells']['sky130_fd_sc_hd__xnor2_1']['transistors'] == 10 and rep3['sky130']['cells']['sky130_fd_sc_hd__maj3_1']['transistors'] == 14
      and all(l == 0.15 for c in rep3['sky130']['cells'].values() for _, l in c['w_l_um']), {k: v['transistors'] for k, v in rep3['sky130']['cells'].items()})
check('  …the adder = 1050 SKY130 transistors, and the LEF footprints summed AGREE with lod-2\'s Liberty area (855.82 µm²) — two independent PDK sources',
      rep3['adder']['sky130']['transistors'] == 1050 and rep3['adder']['sky130']['area_agrees'] and rep3['adder']['sky130']['lef_area_um2'] == rep3['adder']['sky130']['liberty_area_um2'], rep3['adder']['sky130'])
check('  …the CNT adder = 1016 transistors (508 p + 508 n) from the cell library\'s own device lists, composites expanded; NO layout (None, stated)',
      rep3['adder']['cnt']['transistors'] == 1016 and rep3['adder']['cnt']['p'] == rep3['adder']['cnt']['n'] == 508 and rep3['adder']['cnt']['layout'] is None, rep3['adder']['cnt'])
check('  …what is NOT done is listed: DRC/LVS, transistor-level simulation, fabrication, CNT layout', len(rep3['not_done']) == 4 and any('DRC' in x for x in rep3['not_done']))
_dv, _pins = parse_spice(os.path.join(os.path.expanduser('~/.cache/polari-lod/sky130_cells'), 'sky130_fd_sc_hd__nand2_1.spice'))
check('parse_spice reads a cached PDK netlist: nand2_1 = 4 devices with W 0.65/1.0 µm, L 0.15 µm, pins A B VGND VNB VPB VPWR Y',
      len(_dv) == 4 and {d['w_um'] for d in _dv} == {0.65, 1.0} and {d['l_um'] for d in _dv} == {0.15} and _pins == ['A', 'B', 'VGND', 'VNB', 'VPB', 'VPWR', 'Y'], (_dv, _pins))
check('cnt_devices expands composites: cbuf = two cinv = 4 devices', len(cnt_devices('cbuf', __import__('cntfet.objects.cnt_cell_library._shared', fromlist=['x']).CELL_LIBRARY)) == 4)
maps3, chars3 = lod3_rows(rep3, rep2, rep2c)
check('lod-3 rows: cells → devices RESOLVED by name (one-to-many, analytical: cited netlists); devices → layout VALIDATED by the area cross-check; layout → fabrication PARTIAL; CNT layout UNRESOLVED',
      next(m_ for m_ in maps3 if m_['name'] == 'lod2: standard cells → devices')['kind'] == 'one-to-many' and next(m_ for m_ in maps3 if m_['name'] == 'lod2: standard cells → devices')['evidence_level'] == 'analytical'
      and next(m_ for m_ in maps3 if m_['name'] == 'lod3: devices → layout')['mapping_status'] == 'validated' and next(m_ for m_ in maps3 if m_['name'] == 'lod3: layout → fabrication')['kind'] == 'partial'
      and next(m_ for m_ in maps3 if m_['name'] == 'lod3-cnt: devices → layout')['kind'] == 'unresolved', [(m_['name'], m_['kind']) for m_ in maps3])
check('  …the transistor counts are characterizations with units (1050 SKY130 analytical; 1016 CNT simulated — the device is a model)',
      {(c['name'], c['result'], c['evidence_level']) for c in chars3 if 'transistor' in c['name']} == {('lod3: rv32_add transistor count', 1050.0, 'analytical'), ('lod3-cnt: rv32_add transistor count', 1016.0, 'simulated')})
check('the seed merges lod-3 by name: no partial cells → devices row remains for SKY130; the walk below proves the depth', not any(m_['name'] == 'lod2: standard cells → devices' and m_['kind'] == 'partial' for m_ in SEED_LOD_MAPPINGS))
m5 = _mgr()
for cls, rws in (('ComputeMapping', SEED_LOD_MAPPINGS), ('CharacterizationMapping', SEED_LOD_CHARACTERIZATIONS)):
    for r_ in rws:
        _add(m5, cls, **r_)
p5 = path(m5, 'c-source', 'lod1/add.c: c = a + b')
check('the walk from the C statement now spans ALL ELEVEN rungs — C → … → layout → fabrication → materials — and ends at the ladder\'s bottom (materials), which is the end, not a gap',
      p5['rungs'] == ['c-source', 'compiler', 'isa', 'microarchitecture', 'rtl', 'logic-netlist', 'standard-cells', 'devices', 'layout', 'fabrication', 'materials'] and p5['unresolved_at'] == 'materials', (p5['rungs'], p5.get('unresolved_at')))

# ---- lod-4: fabrication → materials by reference; the process-node row in sifet's shape, manufacturable left to him
from computelod.custom.lod4_process import report as lod4_report, rows as lod4_rows, SKY130_NODE
from sifet.objects.si_ladder._shared import FABRICATION_EVIDENCE, RIGHTS_CLASS
rep4 = lod4_report()
check('lod-4: a committed report exists; the sky130 process-node row uses sifet\'s OWN vocabularies (fabrication evidence, rights class) and leaves manufacturable = None with the evidence and D-lod4-1 named',
      rep4 is not None and SKY130_NODE['fabrication_evidence'] in FABRICATION_EVIDENCE and SKY130_NODE['rights_class'] in RIGHTS_CLASS and SKY130_NODE['manufacturable'] is None
      and 'D-lod4-1' in SKY130_NODE['manufacturable_reason'] and 'D-lod4-1' in rep4['decisions'], SKY130_NODE['manufacturable_reason'][:120])
check('D-lod4-1 RULED (his, 2026-09-26): sky130 is manufacturability = proven-on-request, the bool stays None, the reason says who and when',
      SKY130_NODE.get('manufacturability') == 'proven-on-request' and SKY130_NODE['manufacturable'] is None and 'RULED 2026-09-26' in SKY130_NODE['manufacturable_reason'], SKY130_NODE.get('manufacturability'))
_kn = json.loads(SKY130_NODE['key_numbers_json'])
check('  …its key numbers are the ones READ in lod-2/lod-3 (L = 0.15 µm, 1.8 V core) with their sources; the metal count is documentation and says so',
      _kn['l_min_um']['value'] == 0.15 and 'lod-3' in _kn['l_min_um']['source'] and _kn['vdd_core_v']['value'] == 1.8 and 'documentation' in _kn['metal_layers']['note'])
maps4, _ = lod4_rows(rep4, rep3)
check('lod-4 rows: layout → fabrication RESOLVED by name (one-to-one, analytical, the process row); fabrication → materials enters the rung onto eg-si via the Siemens route and NAMES what is not modelled',
      {m_['name'] for m_ in maps4} == {'lod3: layout → fabrication', 'lod4: fabrication → materials'} and all(m_['evidence_level'] == 'analytical' for m_ in maps4)
      and 'eg-si' in next(m_ for m_ in maps4 if 'materials' in m_['name'])['target_ref'] and 'not modelled' in next(m_ for m_ in maps4 if 'materials' in m_['name'])['notes'])
check('  …the CNT branch stays blocked at LAYOUT (not at process): its process rows are named so the gap is precise', rep4['cnt']['layout'] is None and 'CNTAlignmentProcess' in rep4['cnt']['process_rows_named'])
from computelod.custom.explain import CHARACTERISTIC_WORDS, FLOWS
# ---- lod-4c: the process node's OWN numbers RUN — Ion / Ioff / Vt / DIBL / SS from DC sweeps on the PDK's BSIM4 models
from computelod.custom.lod4_devices import report as lod4c_report, rows as lod4c_rows, key_numbers as lod4c_key_numbers, metrics as lod4c_metrics, CONDITIONS as L4C_COND, DEVICES as L4C_DEVICES
rep4c = lod4c_report()
check('lod-4c: a committed device report exists — the two flavours the cells use (nfet_01v8, pfet_01v8_hvt), six model files cited by sha256, definitions of every metric stated with the sifet conventions (constant-current Vt = 100 nA × W)',
      rep4c is not None and set(rep4c['devices']) == set(L4C_DEVICES) == {'nfet_01v8', 'pfet_01v8_hvt'} and len(rep4c['models']['files']) == 6 and set(rep4c['definitions']) == {'ion', 'ioff', 'vt', 'dibl', 'ss'}
      and '100 nA' in L4C_COND['vt_criterion'] and L4C_COND['w_um'] == 1.0 and L4C_COND['l_um'] == 0.15, rep4c and rep4c['summary'])
_n, _p = rep4c['devices']['nfet_01v8']['metrics'], rep4c['devices']['pfet_01v8_hvt']['metrics']
check('  …the numbers are physically coherent: nfet Ion 400–600 µA/µm at 1.8 V, Ioff in the pA/µm range (a low-leakage 130 nm process), Vt_sat ≈ the model card\'s vth0 (0.519 V) within 20 mV, Vt_lin > Vt_sat (DIBL positive, < 100 mV/V), SS 60–110 mV/dec; the hvt p device slower and higher-Vt than the n',
      400 <= _n['ion_ua_per_um'] <= 600 and 0 < _n['ioff_na_per_um'] < 0.1 and abs(_n['vt_sat_v'] - 0.519) < 0.02 and _n['vt_lin_v'] > _n['vt_sat_v'] and 0 < _n['dibl_mv_per_v'] < 100 and 60 <= _n['ss_mv_per_dec'] <= 110
      and _p['ion_ua_per_um'] < _n['ion_ua_per_um'] and _p['vt_sat_v'] > _n['vt_sat_v'] and 0 < _p['ioff_na_per_um'] < 0.1, (_n, _p))
check('  …the metric extraction is deterministic on a synthetic curve: Ion = the last sample, Ioff the first, Vt where Id crosses 100 nA × W, SS from the decade window',
      lod4c_metrics([(v / 100.0, 1e-12 * 10 ** (v / 10.0)) for v in range(0, 181)], [(v / 100.0, 1e-12 * 10 ** (v / 10.0) * 0.5) for v in range(0, 181)])['ss_mv_per_dec'] == 100.0
      and abs(lod4c_metrics([(v / 100.0, 1e-12 * 10 ** (v / 10.0)) for v in range(0, 181)], [(v / 100.0, 1e-12 * 10 ** (v / 10.0)) for v in range(0, 181)])['vt_sat_v'] - 0.5) < 0.01)
_kn4c = lod4c_key_numbers(rep4c)
check('  …the sky130 SiliconProcessNode row GAINS the numbers in sifet\'s key names and {value, unit, source, note} shape (ion_ua_per_um, ioff_na_per_um, vt_v, dibl_mv_per_v, ss_mv_per_dec + pmos_*), source naming the report; the seed converges key_numbers_json onto an existing row',
      {'ion_ua_per_um', 'ioff_na_per_um', 'vt_v', 'dibl_mv_per_v', 'ss_mv_per_dec', 'pmos_ion_ua_per_um', 'pmos_ioff_na_per_um', 'pmos_vt_v'} <= set(_kn4c) and all({'value', 'unit', 'source'} <= set(v) for v in _kn4c.values())
      and 'lod4/devices_report.json' in _kn4c['ion_ua_per_um']['source'] and json.loads(SKY130_NODE['key_numbers_json'])['ion_ua_per_um']['value'] == _n['ion_ua_per_um']
      and 'key_numbers_json' in next(r_[0].get('_converge', []) for n_, _, r_ in COMPUTELOD_SEED_PAIRS if n_ == 'SiliconProcessNode' and r_), sorted(_kn4c))
_, chars4c = lod4c_rows(rep4c)
check('lod-4c rows: ten UPWARD characterizations fabrication → devices (five per flavour: on_current, off_current, threshold_voltage, dibl, subthreshold_swing), evidence SIMULATED, status implemented (a model, not a die), the FreePDK45 documented value beside Ion/Ioff for the reading',
      len(chars4c) == 10 and all(c['source_rung'] == 'fabrication' and c['target_rung'] == 'devices' and c['evidence_level'] == 'simulated' and c['mapping_status'] == 'implemented' for c in chars4c)
      and {c['characteristic'] for c in chars4c} == {'on_current', 'off_current', 'threshold_voltage', 'dibl', 'subthreshold_swing'}
      and json.loads(next(c for c in chars4c if c['name'] == 'lod4c: nfet_01v8 on current')['conditions_json'])['freepdk45_documented'] == 975.5, [c['name'] for c in chars4c])
check('  …every new characteristic has plain words for the explainer', all(k in CHARACTERISTIC_WORDS for k in ('on_current', 'off_current', 'threshold_voltage', 'dibl', 'subthreshold_swing')) and 'lod4c' in FLOWS)
# ---- lod-2c: the two Liberties' twin cells at the SAME conditions (the CNT point; each library's own FO4); CNT area refused
from computelod.custom.lod2_compare import report as lod2c_report, rows as lod2c_rows, TWINS, CNT_POINT, read_point, units as lib_units, timing_groups, CNT_LIB
rep2cmp = lod2c_report()
check('lod-2c: a committed comparison report exists — six twin pairs (same Boolean function), both Liberties cited by sha256, three views (cnt-point, own-fo4, sky130-liberty-point), CNT area REFUSED with the reason',
      rep2cmp is not None and len(rep2cmp['twins']) == 6 and [tuple(t) for t in rep2cmp['twins']] == TWINS and set(rep2cmp['views']) == {'cnt-point', 'own-fo4', 'sky130-liberty-point'}
      and rep2cmp['area']['cnt_um2'] is None and 'refused' in rep2cmp['area']['cnt_refused'] and rep2cmp['area']['sky130_um2']['inv_1'] == 3.7536, rep2cmp and rep2cmp['summary'])
_v1, _v2 = rep2cmp['views']['cnt-point'], rep2cmp['views']['own-fo4']
check('  …view cnt-point: the CNT numbers are exact grid points of its Liberty (INVX1 worst 1.117 ps at 0.6 V / 41.65 aF / 1.02 ps), every SKY130 twin FINISHED inside the 801 ns window and is four to five orders slower (hvt p in subthreshold at 0.6 V — stated in the reading)',
      _v1['cells']['inv_1']['cnt']['worst_ps'] == 1.117 and all(_v1['cells'][s]['sky130']['refused'] == 0 and _v1['cells'][s]['sky130']['worst_ps'] > 1e4 for s, _ in TWINS)
      and 1e4 <= rep2cmp['summary']['cnt_point_ratio_sky_over_cnt']['min'] and rep2cmp['summary']['cnt_point_ratio_sky_over_cnt']['max'] < 1e5 and 'subthreshold' in rep2cmp['summary']['reading'], rep2cmp['summary'])
check('  …view own-fo4: FO4 loads are 4 × each library\'s own inverter input (SKY130 9.208 fF, CNT 41.65 aF), the input slew iterated twice from its start value and every iteration kept (SKY130 50 → 64.0 → 65.1 ps; CNT 1.02 → 1.21 → 1.25 ps)',
      _v2['conditions']['sky130']['load_ff'] == 9.208 and abs(_v2['conditions']['cnt']['load_ff'] - 0.041652) < 1e-6 and len(_v2['conditions']['sky130']['slew_iterations_ps']) == 3 and _v2['conditions']['sky130']['slew_iterations_ps'][0] == 50.0
      and 60 < _v2['conditions']['sky130']['input_slew_ps_20_80'] < 70 and 1.2 < _v2['conditions']['cnt']['input_slew_ps_20_80'] < 1.3, _v2['conditions'])
check('  …at own FO4 the SKY130 inverter is ~101 ps and the CNT one ~1.17 ps: ratios 58–135 across the six twins, ALL in the same direction — reported with the CNT side named intrinsic-grade (no layout, standin parasitics), never as a ranking',
      95 < _v2['cells']['inv_1']['sky130']['worst_ps'] < 110 and 1.1 < _v2['cells']['inv_1']['cnt']['worst_ps'] < 1.3 and 50 < rep2cmp['summary']['own_fo4_ratio_sky_over_cnt']['min'] and rep2cmp['summary']['own_fo4_ratio_sky_over_cnt']['max'] < 150
      and 'ranking' in rep2cmp['summary']['reading'], rep2cmp['summary']['own_fo4_ratio_sky_over_cnt'])
check('  …the SKY130 Liberty at its own point (read, not simulated) is kept beside for the reading: inv_1 worst = the lod-3b Liberty tpLH (117.9 ps)',
      abs(rep2cmp['views']['sky130-liberty-point']['cells']['inv_1']['worst_ps'] - 117.94) < 0.1, rep2cmp['views']['sky130-liberty-point']['cells']['inv_1'])
_cnt_txt = open(CNT_LIB, errors='replace').read(); _ct, _cc = lib_units(_cnt_txt)
check('lod-2c Liberty reading: units normalised (CNT ps/fF → 1, 1); XOR2X1 has four timing groups with `when` conditions; a point OUTSIDE the grid is REFUSED, not extrapolated',
      (_ct, _cc) == (1.0, 1.0) and len(timing_groups(_cnt_txt, 'cell (XOR2X1)')) == 4 and all(g['when'] for g in timing_groups(_cnt_txt, 'cell (XOR2X1)'))
      and all('refused' in v for v in read_point(_cnt_txt, 'cell (INVX1)', 50.0, 14.6, _ct, _cc).values()), [g['when'] for g in timing_groups(_cnt_txt, 'cell (XOR2X1)')])
_, chars2cmp = lod2c_rows(rep2cmp)
check('lod-2c rows: 24 upward characterizations (6 twins × 2 views × 2 libraries), devices → standard-cells, evidence SIMULATED, implemented, each naming its twin, the view and the worst/mean per arc in conditions; the CNT rows say intrinsic-grade, the 0.6 V SKY130 rows say subthreshold',
      len(chars2cmp) == 24 and all(c['source_rung'] == 'devices' and c['target_rung'] == 'standard-cells' and c['evidence_level'] == 'simulated' and c['mapping_status'] == 'implemented' and 'twin' in json.loads(c['conditions_json']) for c in chars2cmp)
      and all('intrinsic-grade' in c['notes'] for c in chars2cmp if c['name'].startswith('lod2c: cnt')) and all('subthreshold' in c['notes'] for c in chars2cmp if c['name'].startswith('lod2c: sky130') and '@cnt-point' in c['name'])
      and {'lod2c: sky130 inv_1 FO4', 'lod2c: cnt INVX1 FO4', 'lod2c: sky130 xor2_1 @cnt-point', 'lod2c: cnt OAI21X1 @cnt-point'} <= {c['name'] for c in chars2cmp}, [c['name'] for c in chars2cmp][:6])
check('  …lod2c has a flow for the explainer', 'lod2c' in FLOWS)
try:
    from mathproofs.mathproofs_seed import LOD2C_TWINS as _PF_TWINS
    check('lod-2c: mathproofs.LOD2C_TWINS == computelod\'s TWINS (the claims name the rows that exist)', _PF_TWINS == TWINS, (_PF_TWINS, TWINS))
except ImportError:
    check('lod-2c: mathproofs.LOD2C_TWINS cross-check — mathproofs absent here, stated', False)
# ---- lod-3e: the WHOLE adder placed and routed (ORFS in its pinned image through the engines ladder), timed with and without its wires
from computelod.custom.lod3_pnr import report as lod3e_report, rows as lod3e_rows, VARIANTS as PNR_VARIANTS, _census as pnr_census
from computelod.custom.eda_engines import ORFS_IMAGE, ORFS_ENGINES, ENGINES as EDA_ENGINES
rep3e = lod3e_report()
check('lod-3e: a committed place-and-route report exists — both variants (as-flow, cells-kept) reached the final stage; the input is lod-2\'s OWN mapped netlist (96 cells, 855.82 µm², sha256 cited); the Liberty handed to the flow is lod-2\'s (sha256 cited); the flow image is pinned by tag AND digest',
      rep3e is not None and set(rep3e['variants']) == set(PNR_VARIANTS) == {'as-flow', 'cells-kept'} and all(e['finished'] for e in rep3e['variants'].values()) and rep3e['input_netlist']['cells'] == 96 and rep3e['input_netlist']['area_um2'] == 855.82
      and len(rep3e['input_netlist']['sha256']) == 64 and len(rep3e['liberty']['sha256']) == 64 and 'sha256:' in rep3e['flow'] and ORFS_IMAGE in rep3e['flow'], rep3e and rep3e['summary'])
_af, _ck = rep3e['variants']['as-flow'], rep3e['variants']['cells-kept']
check('  …the router\'s own DRC count is 0 on both, flow errors 0, wirelength and vias recorded; the flow RESIZED the carry chain (maj3_1 → maj3_2, 29 cells) in BOTH variants — the census says so, mapping_unchanged is False, nothing is hidden',
      all(e['metrics']['route_drc_errors'] == 0 and e['metrics']['flow_errors'] == 0 and e['metrics']['wirelength_um'] > 0 and e['metrics']['vias'] > 0 for e in (_af, _ck))
      and all(e['census']['resized'].get('maj3_2') == 29 and e['census']['mapping_unchanged'] is False and e['census']['logic_cells'] == 96 for e in (_af, _ck)), (_af['census'], _ck['census']))
check('  …as-flow buffered every port and repaired hold (146 buffers/delay cells, 292 std cells, 50 taps, 332 fill); cells-kept, with every switchable repair off, kept 17 buffers — the floorplan-stage repair is not switchable, said so',
      _af['census']['buffers_and_delays'] == 146 and _af['metrics']['stdcell_count'] == 292 and _af['metrics']['tap_cells'] == 50 and _af['metrics']['fill_cells'] == 332 and _af['metrics']['timing_repair_buffers'] == 146
      and _ck['census']['buffers_and_delays'] == 17 and _ck['metrics']['stdcell_count'] == 163 and all(k in _ck['knobs'] for k in ('SKIP_CTS_REPAIR_TIMING', 'DONT_BUFFER_PORTS')), (_af['metrics'], _ck['metrics']))
check('  …TIMING under lod-2\'s exact conditions: with the extracted parasitics 9.8 ns (as-flow) / 10.06 ns (cells-kept); the WIRE COST — the same routed netlist with minus without its SPEF — is 0.22–0.24 ns, 2.3–2.4 %; the routed numbers beat lod-2\'s 11.94 ns netlist ONLY because the flow resized (the note says so — not the wire cost)',
      9.7 < _af['timing']['with_parasitics']['max_path_ns'] < 9.9 and 10.0 < _ck['timing']['with_parasitics']['max_path_ns'] < 10.2 and all(0.2 < e['timing']['wire_cost_ns'] < 0.3 and 2.0 <= e['timing']['wire_cost_pct'] <= 2.6 for e in (_af, _ck))
      and all(e['timing']['with_parasitics']['max_path_ns'] > e['timing']['without_parasitics']['max_path_ns'] for e in (_af, _ck)) and rep3e['conditions']['baseline_lod2_ns'] == 11.9394
      and all(e['timing']['vs_lod2_netlist_ns'] < 0 and 'resized' in e['timing']['vs_lod2_note'] for e in (_af, _ck)), {v: e['timing'] for v, e in rep3e['variants'].items()})
check('  …the flow\'s own setup check against the 10 ns virtual clock is stated per variant: as-flow met, cells-kept MISSED (10.06 > 10) — what the repairs would have fixed; the SPEF nets are counted; the GDS/ODB and the 680 kB routing image are NOT committed, the DEF/SPEF/netlist/reports/placement image are',
      'met' in _af['flow_setup_note'] and 'MISSED' in _ck['flow_setup_note'] and _af['spef']['nets'] > _ck['spef']['nets'] > 100 and all('6_final.gds' in e['not_committed'][0] for e in (_af, _ck))
      and all(set(e['artefacts']) >= {'6_final.def', '6_final.spef', '6_final.v', '6_report.json', '6_finish.rpt', '5_route_drc.rpt', 'final_placement.webp.png', 'sta_with_parasitics.log', 'config.mk', 'constraint.sdc'} and 'final_routing.webp.png' not in e['artefacts'] for e in (_af, _ck))
      and all(os.path.exists('modules/computelod/initialData/lod3/pnr/%s/%s' % (v, f)) for v in ('as-flow', 'cells-kept') for f in ('6_final.spef', '6_final.def')), (_af['flow_setup_note'], _ck['flow_setup_note']))
check('  …the ORFS engines resolve ONLY through the pinned image or a worker (never the host\'s make, never the eda-tools image\'s): `orfs` and `openroad` are in the engines table and in ORFS_ENGINES',
      set(ORFS_ENGINES) == {'orfs', 'openroad'} and EDA_ENGINES['orfs'] == 'make' and EDA_ENGINES['openroad'] == 'openroad' and rep3e['engines']['orfs']['how'] in ('local-image', 'remote') and rep3e['engines']['orfs']['where'] in (ORFS_IMAGE,) + tuple(x for x in [rep3e['engines']['orfs']['where']] if rep3e['engines']['orfs']['how'] == 'remote'))
check('  …census helper: counts sky130 cells in a netlist', pnr_census('X1 a b sky130_fd_sc_hd__inv_1 (); X2 sky130_fd_sc_hd__inv_1 ; X3 sky130_fd_sc_hd__nand2_1') == {'inv_1': 2, 'nand2_1': 1})
maps3e, chars3e = lod3e_rows(rep3e, rep2)
check('lod-3e rows: two ComputeMappings adder cells → placed-and-routed layout (one per variant; MEASURED — the router\'s DRC and the flow\'s metrics are tool output; validated: 0 DRC, 0 errors; loss_note counts the resizing/buffers); twelve upward characterizations (6 per variant: routed delay, wire cost, core area (a knob, said so), wirelength, DRC count, instance count)',
      len(maps3e) == 2 and all(m_['evidence_level'] == 'measured' and m_['mapping_status'] == 'validated' and m_['source_rung'] == 'standard-cells' and m_['target_rung'] == 'layout' and 'resized' in m_['loss_note'] for m_ in maps3e)
      and len(chars3e) == 12 and {c['characteristic'] for c in chars3e} == {'propagation_delay', 'wire_delay', 'area', 'wirelength', 'drc_violations', 'device_count'}
      and all(c['source_rung'] == 'layout' and c['target_rung'] == 'standard-cells' for c in chars3e) and next(c for c in chars3e if c['name'] == 'lod3e: rv32_add core area (as-flow)')['mapping_status'] == 'implemented'
      and next(c for c in chars3e if c['name'] == 'lod3e: rv32_add wire delay cost (cells-kept)')['evidence_level'] == 'simulated', [(m_['name'], m_['mapping_status']) for m_ in maps3e] + [c['name'] for c in chars3e])
check('  …lod3e has a flow for the explainer and plain words for its characteristics', 'lod3e' in FLOWS and all(k in CHARACTERISTIC_WORDS for k in ('wire_delay', 'wirelength', 'drc_violations')))
# ---- lod-4b: fabrication as ROWS — the SKY130 route from the PDK's documented layers (+ textbook unit processes), the CNT route by reference
from computelod.custom.lod4_steps import report as lod4b_report, rows as lod4b_rows, stage_rows as lod4b_stages, process_rows as lod4b_processes, SKY130_STAGES, CNT_STAGES, NOT_HERE, TEXTBOOK, FAM_SKY, FAM_CNT
rep4b = lod4b_report()
check('lod-4b: a committed steps report exists — the PDK docs (layers, rules, README) cited with the read date and the README quoted; the textbook cited; what the PDK publishes vs what it does not (the recipe) stated',
      rep4b is not None and rep4b['read_on'] == '2026-09-26' and all(k in rep4b['sources'] for k in ('pdk_layers', 'pdk_rules_summary', 'pdk_readme', 'readme_quote', 'textbook')) and '5 levels of metal' in rep4b['sources']['readme_quote']
      and 'Plummer' in rep4b['sources']['textbook']['citation'] and 'proprietary' in rep4b['not_here'] and 'recipe' in rep4b['sky130']['what_is_not'], rep4b and rep4b['sources'])
_st, _pr = lod4b_stages(), lod4b_processes()
check('  …14 ProcessingStage rows (8 SKY130 wafer states in a chain from the eg-si wafer to the passivated die; 6 CNT stages in a chain), each with family, prior stage, provenance and a description naming the PDK layers / the cntfet row',
      len(_st) == 14 and [r['name'] for r in _st if r['material_family'] == FAM_SKY] == [s[0] for s in SKY130_STAGES] and all(_st[i]['typical_prior_stage'] == _st[i - 1]['name'] for i in range(1, 8))
      and [r['name'] for r in _st if r['material_family'] == FAM_CNT] == [s[0] for s in CNT_STAGES] and all(r['provenance_id'] and r['description'] for r in _st)
      and 'PDK layers' in _st[1]['description'] and '`nwell` = "N-well region"' in _st[1]['description'] and 'CNTPurificationProcess:s1-target-purification' in _st[8]['description'], [r['name'] for r in _st])
check('  …every SKY130 stage says the recipe is NOT here and cites the layers page; every documented layer of the stack appears on exactly one stage (26 layers: dnwell … nsm/pad)',
      all(NOT_HERE in r['notes'] and 'skywater-pdk.readthedocs.io' in r['notes'] for r in _st if r['material_family'] == FAM_SKY) and len(rep4b['sky130']['layers_covered']) == 26
      and sum(len(s[3]) for s in SKY130_STAGES) == 26, rep4b['sky130']['layers_covered'])
check('  …14 MaterialProcessDefinition rows, ALL declared TRANSFORMATIVE (PSPP invariant I2: declared, never inferred), the 8 SKY130 unit processes citing the textbook and saying the recipe is absent, the 6 CNT ones naming their cntfet parameter row',
      len(_pr) == 14 and all(r['execution_effect'] == 'TRANSFORMATIVE' and r['process_type'] and r['provenance_id'] for r in _pr)
      and all(TEXTBOOK['citation'] in r['notes'] and NOT_HERE in r['notes'] for r in _pr if r['material_family'] == FAM_SKY) and all('cntfet_row' in json.loads(r['parameter_schema_json']) for r in _pr if r['material_family'] == FAM_CNT)
      and {r['energy_deposition_model'] for r in _pr if r['energy_deposition_model']} <= {'conventional-heating', 'rf'}, [(r['name'], r['process_type']) for r in _pr])
check('  …every unit process a SKY130 stage names is a row; the names never collide with pspp\'s own seeds (prefixes sky130- / cnt-)',
      {p_ for s_ in SKY130_STAGES for p_ in s_[5]} <= {r['name'] for r in _pr} and all(r['name'].startswith(('sky130-', 'cnt-')) for r in _st + _pr))
check('  …the seed pairs carry the PSPP rows (guarded on pspp) with description/notes converging onto existing rows',
      any(n == 'ProcessingStage' and len(r) == 14 and 'description' in r[0]['_converge'] for n, _, r in COMPUTELOD_SEED_PAIRS) and any(n == 'MaterialProcessDefinition' and len(r) == 14 for n, _, r in COMPUTELOD_SEED_PAIRS))
maps4b, _ = lod4b_rows(rep4b, rep4, rep3)
check('lod-4b rows: `lod4: fabrication → materials` REPLACED by name — the route as rows, the stack\'s materials NAMED in the target, the recipe as the loss; `lod4b-cnt: fabrication → materials` ADDED, status proposed (no line has made these devices; the cntfet rows say TUNABLE)',
      [m_['name'] for m_ in maps4b] == ['lod4: fabrication → materials', 'lod4b-cnt: fabrication → materials'] and 'ProcessingStage rows' in maps4b[0]['notes'] and 'Si3N4' in maps4b[0]['target_ref'] and 'recipe' in maps4b[0]['loss_note']
      and maps4b[0]['evidence_level'] == 'analytical' and maps4b[1]['mapping_status'] == 'proposed' and 'LAYOUT' in maps4b[1]['notes'], [(m_['name'], m_['mapping_status']) for m_ in maps4b])
check('  …and in the merged seed the lod-4 row IS the lod-4b one (17 ComputeMappings now)', next(m_ for m_ in SEED_LOD_MAPPINGS if m_['name'] == 'lod4: fabrication → materials')['notes'].startswith('lod-4b') and sum(1 for m_ in SEED_LOD_MAPPINGS if m_['name'].startswith('lod4')) == 2
      and 'lod4b' in FLOWS and 'lod4b-cnt' in FLOWS)
from computelod.custom.explain import explain_characterization
# ---- his rule (2026-09-26): every committed result carries the INITIAL CONDITIONS and SEEDS that produced it
from computelod.custom.repro import check_all as repro_check, complete as repro_complete, REQUIRED as REPRO_KEYS, record as repro_record
_rc = repro_check()
check('reproducibility: EVERY committed flow report carries a complete `reproduction` block (inputs by sha256/url, tool versions + image ids, knobs, conditions, generated files, a seed posture, how to rerun)',
      _rc and all(v['ok'] for v in _rc.values()) and len(_rc) >= 12, {k: v for k, v in _rc.items() if not v['ok']})
_r3b = json.load(open('modules/computelod/initialData/lod3/devices_report.json'))['reproduction']
check('  …lod-3b/3d: the 21 decks the tool consumed are COMMITTED beside the report (initialData/lod3/decks/lod3b) and hashed; the model files and the Liberty are cited by sha256; ngspice\'s version line is recorded; the flow states it is deterministic and why',
      len(_r3b['generated_files']) == 21 and all(os.path.exists(os.path.join('modules', g['file'])) for g in _r3b['generated_files']) and any('nfet_01v8__tt.corner' in i.get('label', '') for i in _r3b['inputs'])
      and 'ngspice' in _r3b['tools'].get('ngspice', '').lower() and _r3b['seeds'].get('deterministic') is True and 'ngspice' in _r3b['seeds']['why'], (_r3b['tools'], len(_r3b['generated_files'])))
_r3e = json.load(open('modules/computelod/initialData/lod3/pnr/pnr_report.json'))['reproduction']
check('  …lod-3e: the flow\'s three SEED knobs are recorded explicitly as the defaults this run used (GPL_RANDOM_SEED, GRT_SEED, OR_SEED) — a seed is never implicit; the netlist and Liberty inputs are hashed; config.mk / SDC / DEF / SPEF hashed as generated files',
      all(k in _r3e['seeds'] for k in ('GPL_RANDOM_SEED', 'GRT_SEED', 'OR_SEED')) and len(_r3e['inputs']) == 2 and all(i['sha256'] for i in _r3e['inputs']) and any(g['file'].endswith('config.mk') for g in _r3e['generated_files']), _r3e['seeds'])
_r2c = json.load(open('modules/computelod/initialData/lod2/cnt/report.json'))['reproduction']
check('  …lod-2b (not re-run): the block says so (attached_after_the_fact names the run and the date), hashes the committed Liberty it wrote, and states the characterization had no Monte Carlo',
      _r2c.get('attached_after_the_fact') and any('polari_cnt_lib' in i.get('file', '') for i in _r2c['inputs']) and 'Monte Carlo' in _r2c['seeds']['why'], _r2c.get('attached_after_the_fact'))
check('  …the block shape is checked by one function: a block without seeds or with an unhashed input is INCOMPLETE',
      repro_complete({k: {} for k in REPRO_KEYS} | {'inputs': [], 'seeds': {'deterministic': True}})[0] and not repro_complete({k: {} for k in REPRO_KEYS} | {'inputs': [{'file': 'x'}], 'seeds': {'deterministic': True}})[0]
      and not repro_complete({k: {} for k in REPRO_KEYS} | {'inputs': [], 'seeds': {}})[0] and repro_record('x', seeds={'rng': 7})['seeds'] == {'rng': 7})
from computelod.custom.lod3_devices import report as _r3b_rep, rows as _r3b_rows
_ev = explain_characterization(types.SimpleNamespace(objectTables={}), types.SimpleNamespace(**next(c for c in _r3b_rows(_r3b_rep())[1] if c['name'] == 'lod3: inv_1 A→Y tpHL')))
check('  …the explainer\'s "how to reproduce" points a person at the reproduction block', any('reproduction' in step for step in _ev['how to reproduce']), _ev['how to reproduce'])
# ---- lod-3b: devices → cells simulated by us, cross-checked against the Liberty
from computelod.custom.lod3_devices import report as lod3b_report, rows as lod3b_rows, interp, CONDITIONS as DEV_COND, ARCS as DEV_ARCS, arcs_of, FIRST_CELLS, liberty_tables, subckt_ports
rep3b = lod3b_report()
check('lod-3b/3d: a committed device-level report exists — ngspice on the pinned sky130_fd_pr tt models (six files cited by sha256, never committed), 21 arcs over the EIGHT cells the adder uses (lod-3d added six cells to lod-3b\'s two)',
      rep3b is not None and len(rep3b['models']['files']) == 6 and rep3b['summary']['arcs'] == 21 and rep3b['summary']['cells'] == 8 and rep3b['summary']['first_cells'] == FIRST_CELLS == ['inv_1', 'nand2_1']
      and set(rep3b['summary']['lod3d_cells']) == {'nor2_1', 'xor2_1', 'xnor2_1', 'maj3_1', 'o21ai_0', 'lpflow_isobufsrc_1'} and not any(fn.endswith('.pm3.spice') for fn in os.listdir('modules/computelod/initialData/lod3')), rep3b and rep3b['summary'])
check('  …the arc table covers EVERY cell type of the mapped adder (lod-3 report.json by_type) and sums to 21: the non-unate inputs (xor2, xnor2) carry one arc per tie, each with its Liberty timing_sense',
      set(DEV_ARCS) == {k.replace('sky130_fd_sc_hd__', '') for k in rep3['sky130']['cells']} | {'inv_1'} and sum(len(arcs_of(c)) for c in DEV_ARCS) == 21
      and {a['label'] for a in arcs_of('xor2_1')} == {'A@B=0', 'A@B=1', 'B@A=0', 'B@A=1'} and arcs_of('xor2_1')[0]['sense'] == 'positive_unate' and arcs_of('xor2_1')[1]['sense'] == 'negative_unate'
      and all(a['sense'] == 'positive_unate' for a in arcs_of('maj3_1')) and arcs_of('lpflow_isobufsrc_1')[1] ['inverting'], sorted(DEV_ARCS))
check('  …every arc is compared to the Liberty at the SAME slew (20–80 %) and load; the mean gap over 21 arcs is ≤ 15 %; the max (39.8 %, maj3_1 C tpHL — the deepest internal nodes) is REPORTED, not tuned, and its rows are `implemented`, not validated',
      rep3b['summary']['mean_abs_delta_pct'] <= 15 and 35 <= rep3b['summary']['max_abs_delta_pct'] <= 45 and all('liberty' in a['compare']['tphl_ps'] for a in rep3b['arcs'])
      and max(rep3b['arcs'], key=lambda a: abs(a['compare']['tphl_ps']['delta_pct']))['cell'] == 'sky130_fd_sc_hd__maj3_1', rep3b['summary'])
check('  …the pattern is the stated cause on ALL 21 arcs: our falls are FASTER than the Liberty (no internal-node parasitics in a schematic netlist)',
      all(a['compare']['tphl_ps']['delta_pct'] < 0 for a in rep3b['arcs']) and rep3b['summary']['tphl_faster_than_liberty_arcs'] == 21, [a['compare']['tphl_ps']['delta_pct'] for a in rep3b['arcs']])
check('  …the conditions name corner, temperature, voltage, load, slew convention and the netlist kind; each arc records its ties, timing sense and the cell\'s Liberty function',
      all(k in DEV_COND for k in ('corner', 'temperature_c', 'voltage_v', 'load_pf', 'input_slew_ns_20_80', 'netlist')) and all(a['ties'] is not None and a['sense'] and a['function'] for a in rep3b['arcs'])
      and next(a for a in rep3b['arcs'] if a['label'] == 'A@B=1')['ties'] == {'B': 'VPWR'})
check('interp: bilinear on a 2×2 table returns the corner values exactly and the centre as the mean', interp(([0, 1], [0, 1], [[1, 2], [3, 4]]), 0, 0) == 1 and interp(([0, 1], [0, 1], [[1, 2], [3, 4]]), 1, 1) == 4 and interp(([0, 1], [0, 1], [[1, 2], [3, 4]]), 0.5, 0.5) == 2.5)
# lod-3d: the Liberty group is picked by (related_pin, timing_sense); a non-unate pin asked without a sense is REFUSED (never "the first block found"),
# and a deck's pins follow the netlist's own .subckt line by name — checked on the cached Liberty + cell netlists when this machine has them
try:
    from computelod.custom.lod2_silicon import fetch_liberty as _fl
    _lib = open(_fl()[0], errors='replace').read() if os.path.exists(_fl()[0]) else ''
except Exception:
    _lib = ''
if _lib:
    _pos = liberty_tables(_lib, 'xor2_1', 'A', 'positive_unate'); _neg = liberty_tables(_lib, 'xor2_1', 'A', 'negative_unate')
    try:
        liberty_tables(_lib, 'xor2_1', 'A'); _refused = False
    except KeyError:
        _refused = True
    check('lod-3d: xor2_1 A has TWO Liberty timing groups (positive/negative unate) with different tables; asking without a sense is refused; a unate pin (inv_1 A) still answers without one',
          _pos['cell_fall'] != _neg['cell_fall'] and _refused and liberty_tables(_lib, 'inv_1', 'A')['cell_fall'], (_refused,))
    _mag = os.path.join(os.path.dirname(__file__), 'initialData', 'lod3', 'sky130_fd_sc_hd__maj3_1.magic.log')
    check('  …the maj3_1 Liberty block is bigger than the fixed 60 kB slice lod-3b used to take — the whole cell block is read now', len(_lib[_lib.index('cell ("sky130_fd_sc_hd__maj3_1")'):]) > 0 and 'maj3_1' in open(_mag).read())
else:
    check('lod-3d: Liberty group selection by timing sense — the Liberty is not cached on this machine (fetch_liberty); the committed report carries the numbers', True)
_, chars3b = lod3b_rows(rep3b)
check('lod-3b/3d rows: 42 UPWARD characterizations (tpHL/tpLH per arc), devices → standard-cells, evidence SIMULATED, the Liberty value, the delta, the ties and the timing sense in conditions; validated within 25 %, `implemented` beyond (4 tpHL rows: the three maj3_1 arcs and xnor2_1 B→Y (A=1) at −27.9 %)',
      len(chars3b) == 42 and all(c['source_rung'] == 'devices' and c['target_rung'] == 'standard-cells' and c['evidence_level'] == 'simulated' and 'liberty_ps' in json.loads(c['conditions_json']) and 'timing_sense' in json.loads(c['conditions_json']) for c in chars3b)
      and sum(1 for c in chars3b if c['mapping_status'] == 'implemented') == 4 and all(c['mapping_status'] == 'validated' for c in chars3b if not (('maj3_1' in c['name'] or 'xnor2_1 B→Y (A=1)' in c['name']) and 'tpHL' in c['name'])),
      [(c['name'], c['mapping_status']) for c in chars3b if c['mapping_status'] != 'validated'])
check('  …the row names carry the tie between the arrow and the delay kind ("lod3: xor2_1 A→X (B=0) tpHL") so a `name~tpHL` quantifier still selects every fall row; the two lod-3b names are unchanged',
      {c['name'] for c in chars3b} >= {'lod3: inv_1 A→Y tpHL', 'lod3: nand2_1 B→Y tpLH', 'lod3: xor2_1 A→X (B=0) tpHL', 'lod3: lpflow_isobufsrc_1 SLEEP→X tpLH'} and sum(1 for c in chars3b if 'tpHL' in c['name']) == 21)
# ---- lod-3c: the layout RUN (magic DRC + PEX, netgen LVS) through polari-eda-tools; the parasitics hypothesis tested
from computelod.custom.lod3_layout import report as lod3c_report, rows as lod3c_rows
rep3c = lod3c_report()
check('lod-3c/3d: a committed layout report exists — PDK ciel version + tech sha256 cited; EIGHT cells (every cell of the adder); DRC ran, PEX ran, LVS ran on each; 21 arcs re-timed',
      rep3c is not None and rep3c['pdk']['ciel_version'] and rep3c['pdk']['tech_sha256'] and len(rep3c['cells']) == 8 and rep3c['summary']['arcs'] == 21 and all(c['drc']['ran'] and c['pex']['ran'] and c['lvs']['ran'] for c in rep3c['cells']))
check('  …DRC: on all eight cells every reported rule is a standalone-cell CONTEXT rule (nwell.4 / LU.2 / LU.3 — taps and wells come from the row), zero real rules; the counts (3–10) are NOT zero and are kept',
      rep3c['summary']['drc_clean_in_context'] and all(c['drc']['count'] > 0 and c['drc']['real_rules'] == [] and len(c['drc']['standalone_context_rules']) == 3 for c in rep3c['cells']), [(c['cell'], c['drc']['count'], c['drc']['rules']) for c in rep3c['cells']])
check('  …LVS: netgen says "Circuits match uniquely" for all eight cells — the PDK\'s layout IS its schematic', rep3c['summary']['lvs_match'] and all(c['lvs']['match'] for c in rep3c['cells']))
check('  …PEX: the extracted netlists carry parasitic capacitors growing with the cell (inv_1 14 … maj3_1 58) and junction areas the schematic netlist lacked; the device counts equal lod-3\'s per-cell transistor counts',
      {c['cell']: c['pex']['capacitors'] for c in rep3c['cells']}['sky130_fd_sc_hd__inv_1'] == 14 and {c['cell']: c['pex']['capacitors'] for c in rep3c['cells']}['sky130_fd_sc_hd__maj3_1'] == 58 and all(c['pex']['junction_areas'] for c in rep3c['cells'])
      and all(c['pex']['devices'] == rep3['sky130']['cells'][c['cell']]['transistors'] for c in rep3c['cells'] if c['cell'] in rep3['sky130']['cells']), [(c['cell'], c['pex']['capacitors'], c['pex']['devices']) for c in rep3c['cells']])
check('  …the parasitics hypothesis TESTED on 21 arcs and the two-cell reading CORRECTED: extraction brings tpHL closer to the Liberty on 21/21 arcs (ALL of the fall gap) but tpLH closer on only 11/21 (PART); the verdict is computed from those counts, rejects the sole-cause reading and names what remains (the vendor setup)',
      rep3c['summary']['closer_after_extraction'] == {'tphl': [21, 21], 'tplh': [11, 21]} and rep3c['summary']['tphl_mean_delta_pct']['extracted'] > rep3c['summary']['tphl_mean_delta_pct']['schematic']
      and 'ALL of the fall gap' in rep3c['summary']['verdict'] and 'PART of the rise gap' in rep3c['summary']['verdict'] and 'REJECTED' in rep3c['summary']['verdict'] and 'vendor' in rep3c['summary']['verdict'], rep3c['summary'])
check('  …and the extracted numbers are CLOSER overall: mean |gap| 15.0 % (schematic) → 8.9 % (extracted) over the 42 delay numbers',
      rep3c['summary']['delay_mean_abs_delta_pct_schematic'] == 15.0 and rep3c['summary']['delay_mean_abs_delta_pct_extracted'] < 10, (rep3c['summary']['delay_mean_abs_delta_pct_schematic'], rep3c['summary']['delay_mean_abs_delta_pct_extracted']))
maps3c, chars3c = lod3c_rows(rep3c)
check('lod-3c/3d rows: devices → layout becomes MEASURED (DRC + LVS are the tools\' verdicts) and stays validated over all eight cells; 42 extracted-netlist delay characterizations carry the schematic value, the ties and the timing sense beside them',
      maps3c[0]['name'] == 'lod3: devices → layout' and maps3c[0]['evidence_level'] == 'measured' and maps3c[0]['mapping_status'] == 'validated' and len(chars3c) == 42
      and all(c['source_rung'] == 'layout' and 'schematic_ps' in json.loads(c['conditions_json']) and 'timing_sense' in json.loads(c['conditions_json']) for c in chars3c) and 'maj3_1: DRC 10' in maps3c[0]['notes'], [(m_['name'], m_['evidence_level']) for m_ in maps3c])
check('  …the extracted rows within 25 % of the Liberty are validated: every one now (the worst, maj3_1 C tpHL, is at −23.3 %)', all(c['mapping_status'] == 'validated' for c in chars3c), [(c['name'], json.loads(c['conditions_json'])['delta_pct']) for c in chars3c if c['mapping_status'] != 'validated'])
# lod-3d: the mathproofs claims name the same 21 arcs as a LITERAL (mathproofs cannot import computelod) — asserted equal here so the two tables cannot drift
try:
    from mathproofs.mathproofs_seed import LOD3_ARCS as _PF_ARCS
    _ours = [(c_, '%s→%s%s' % (a['pin'], a['out'], a['cond'])) for c_ in DEV_ARCS for a in arcs_of(c_)]
    check('lod-3d: mathproofs.LOD3_ARCS == computelod\'s arc table (21 (cell, arc) pairs, same order) — the claims\' about_refs name every characterization row that exists',
          _ours == _PF_ARCS and {'CharacterizationMapping:' + c['name'] for c in chars3b} == {'CharacterizationMapping:lod3: %s %s %s' % (c_, a_, k) for c_, a_ in _PF_ARCS for k in ('tpHL', 'tpLH')}, (_ours[:3], _PF_ARCS[:3]))
except ImportError:
    check('lod-3d: mathproofs.LOD3_ARCS cross-check — mathproofs absent here, stated', False)
check('the seed carries the sky130 SiliconProcessNode beside the compute rows (a sifet class, skipped when sifet is absent)', any(n == 'SiliconProcessNode' and len(r) == 1 for n, _, r in COMPUTELOD_SEED_PAIRS))
check('the lod rows CONVERGE onto an instance that already holds them: every ComputeMapping / CharacterizationMapping / CompilerArtifact / ComputeLOD seed names all its fields but the name in `_converge` (flow output is code-owned; a replace-by-name must reach a live instance)',
      all(set(r['_converge']) == set(r) - {'name', '_converge'} for n_, _, rows_ in COMPUTELOD_SEED_PAIRS if n_ in ('ComputeMapping', 'CharacterizationMapping', 'CompilerArtifact', 'ComputeLOD') for r in rows_))
u5 = path(m5, 'standard-cells', next(m_ for m_ in maps2 if m_['name'] == 'lod1: netlist → standard cells')['target_ref'], 'up')
check('walking UP from the SKY130 cells reaches the RTL through the delay characterization', u5['rungs'][:2] == ['standard-cells', 'rtl'], u5['rungs'])

# ---- pf-1: the lod cross-checks are CLAIM ROWS (mathproofs), asserted here as claims — not ad-hoc arithmetic.
# computelod SOFT-depends on mathproofs at runtime (D-pf-4); the selftest states plainly when the module is absent.
try:
    from computelod.computelod_seed import SEED_LOD_CHARACTERIZATIONS
    from mathproofs.mathproofs_seed import SEED_MATH_CLAIMS
    from mathproofs.custom import checkers as _pf
    _pm = types.SimpleNamespace(objectTables={'CharacterizationMapping': {}, 'MathClaim': {}, 'ProofRun': {}}, db=None)
    for _row in SEED_LOD_CHARACTERIZATIONS:
        _add(_pm, 'CharacterizationMapping', **_row)
    _mk = lambda cls, **f: _add(_pm, cls.__name__, **f)
    _want = {'lod3-lef-area-equals-liberty-area': 'witnessed', 'lod3b-falls-faster-than-liberty': 'witnessed', 'lod3c-extraction-slows-every-arc': 'witnessed',
             'lod3c-extraction-narrows-every-fall-gap': 'witnessed', 'lod3c-extraction-widens-every-rise-gap': 'refuted', 'lod3c-extraction-widens-the-rise-gap-where-already-slow': 'witnessed'}
    _got = {}
    _claims = {}
    for _c in SEED_MATH_CLAIMS:
        if _c['name'] in _want:
            _claim = _add(_pm, 'MathClaim', **_c); _claims[_c['name']] = _claim
            _res = _pf.check(_pm, _claim, make=_mk, save=False)
            _got[_c['name']] = (_res['after'], _res['tier'], _res['detail'])
    check('pf-1 + lod-3d: the six lod cross-checks are MathClaim rows; five are WITNESSED on the seeded characterization rows (LEF == Liberty area; every tpHL faster than the Liberty; extraction slows every arc; narrows every fall gap; '
          'widens the rise gap WHERE the schematic was already slow) and the two-cell statement "widens EVERY rise gap" is REFUTED by lod-3d\'s arcs — kept as the refutation it is', {k: v[0] for k, v in _got.items()} == _want, _got)
    check('  …each is the numeric tier\'s verdict — evidence MEASURED on these rows, never called a proof; the area claim reads two rows that agree to 0.01 µm²',
          all(v[1] == 'numeric' for v in _got.values()) and _got['lod3-lef-area-equals-liberty-area'][2]['lhs'] == _got['lod3-lef-area-equals-liberty-area'][2]['rhs'] == 855.82, _got['lod3-lef-area-equals-liberty-area'])
    _fall = _got['lod3c-extraction-narrows-every-fall-gap'][2]; _rise = _got['lod3c-extraction-widens-the-rise-gap-where-already-slow'][2]
    check('  …the two halves of the verdict now range over 21 extracted arcs each (lod-3d)', _fall['rows'] == 21 and _rise['rows'] == 21, (_fall, _rise))
    _ce = json.loads(_claims['lod3c-extraction-widens-every-rise-gap'].counterexample_json or '{}')
    check('  …the refuted claim\'s counterexample is a REAL row: an extracted tpLH arc whose schematic netlist was already FASTER than the Liberty (schematic_delta_pct < 0) — the first such row, an xor2_1 arc',
          'xor2_1' in json.dumps(_ce) and 'row' in json.dumps(_ce).lower(), _ce)
    _bad = next(r_ for r_ in _pm.objectTables['CharacterizationMapping'].values() if r_.name == 'lod3: rv32_add layout area (LEF)')
    _bad.result = 900.0
    _cl = next(c_ for c_ in _pm.objectTables['MathClaim'].values() if c_.name == 'lod3-lef-area-equals-liberty-area')
    check('  …and the claim is STALE the moment the LEF row changes; re-checked, it is REFUTED with both numbers kept (the row it speaks of is never deleted)',
          _pf.stale(_pm, _cl) and _pf.check(_pm, _cl, make=_mk, save=False)['after'] == 'refuted' and json.loads(_cl.counterexample_json) == {'lhs': 900.0, 'rhs': 855.82})
except ImportError as _e:
    check('pf-1: the lod cross-checks as MathClaim rows — mathproofs is ABSENT here (%s): stated, not skipped silently' % _e, False)

man = json.load(open('modules/computelod/polari-app.json'))
from moduleService.manifests import validate
check('the manifest is valid and declares the five classes + the API', validate(man) == [] and len([c for c in man['classes'] if c != 'ComputeLodAPI']) == 5)

n_ok = sum(1 for _, ok in _results if ok)
print(f'\n{n_ok}/{len(_results)} checks passed')
sys.exit(0 if n_ok == len(_results) else 1)
