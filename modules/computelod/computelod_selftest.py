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
check('lod-1: a committed report exists (the chain RAN: gcc → yosys → iverilog)', rep is not None and rep.get('how') in ('path', 'docker'), rep and rep.get('how'))
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
check('the seed holds BOTH libraries: two propagation-delay rows (SKY130 and CNT) that do not collide',
      sum(1 for c in SEED_LOD_CHARACTERIZATIONS if 'propagation delay' in c['name']) == 2)

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
_kn = json.loads(SKY130_NODE['key_numbers_json'])
check('  …its key numbers are the ones READ in lod-2/lod-3 (L = 0.15 µm, 1.8 V core) with their sources; the metal count is documentation and says so',
      _kn['l_min_um']['value'] == 0.15 and 'lod-3' in _kn['l_min_um']['source'] and _kn['vdd_core_v']['value'] == 1.8 and 'documentation' in _kn['metal_layers']['note'])
maps4, _ = lod4_rows(rep4, rep3)
check('lod-4 rows: layout → fabrication RESOLVED by name (one-to-one, analytical, the process row); fabrication → materials enters the rung onto eg-si via the Siemens route and NAMES what is not modelled',
      {m_['name'] for m_ in maps4} == {'lod3: layout → fabrication', 'lod4: fabrication → materials'} and all(m_['evidence_level'] == 'analytical' for m_ in maps4)
      and 'eg-si' in next(m_ for m_ in maps4 if 'materials' in m_['name'])['target_ref'] and 'not modelled' in next(m_ for m_ in maps4 if 'materials' in m_['name'])['notes'])
check('  …the CNT branch stays blocked at LAYOUT (not at process): its process rows are named so the gap is precise', rep4['cnt']['layout'] is None and 'CNTAlignmentProcess' in rep4['cnt']['process_rows_named'])
# ---- lod-3b: devices → cells simulated by us, cross-checked against the Liberty
from computelod.custom.lod3_devices import report as lod3b_report, rows as lod3b_rows, interp, CONDITIONS as DEV_COND
rep3b = lod3b_report()
check('lod-3b: a committed device-level report exists — ngspice on the pinned sky130_fd_pr tt models (six files cited by sha256, never committed), three arcs (inv_1 A; nand2_1 A, B)',
      rep3b is not None and len(rep3b['models']['files']) == 6 and rep3b['summary']['arcs'] == 3 and not any(fn.endswith('.pm3.spice') for fn in os.listdir('modules/computelod/initialData/lod3')))
check('  …every arc is compared to the Liberty at the SAME slew (20–80 %) and load; the mean gap is ≤ 15 % and the max ≤ 25 % — reported, not tuned',
      rep3b['summary']['mean_abs_delta_pct'] <= 15 and rep3b['summary']['max_abs_delta_pct'] <= 25 and all('liberty' in a['compare']['tphl_ps'] for a in rep3b['arcs']), rep3b['summary'])
check('  …the pattern is the stated cause: our falls are FASTER than the Liberty on every arc (no internal-node parasitics in a schematic netlist)',
      all(a['compare']['tphl_ps']['delta_pct'] < 0 for a in rep3b['arcs']), [a['compare']['tphl_ps']['delta_pct'] for a in rep3b['arcs']])
check('  …the conditions name corner, temperature, voltage, load, slew convention and the netlist kind', all(k in DEV_COND for k in ('corner', 'temperature_c', 'voltage_v', 'load_pf', 'input_slew_ns_20_80', 'netlist')))
check('interp: bilinear on a 2×2 table returns the corner values exactly and the centre as the mean', interp(([0, 1], [0, 1], [[1, 2], [3, 4]]), 0, 0) == 1 and interp(([0, 1], [0, 1], [[1, 2], [3, 4]]), 1, 1) == 4 and interp(([0, 1], [0, 1], [[1, 2], [3, 4]]), 0.5, 0.5) == 2.5)
_, chars3b = lod3b_rows(rep3b)
check('lod-3b rows: six UPWARD characterizations (tpHL/tpLH per arc), devices → standard-cells, evidence SIMULATED, the Liberty value and the delta in conditions, validated when within 25 %',
      len(chars3b) == 6 and all(c['source_rung'] == 'devices' and c['target_rung'] == 'standard-cells' and c['evidence_level'] == 'simulated' and 'liberty_ps' in json.loads(c['conditions_json']) for c in chars3b)
      and all(c['mapping_status'] == 'validated' for c in chars3b), [(c['name'], c['mapping_status']) for c in chars3b])
check('the seed carries the sky130 SiliconProcessNode beside the compute rows (a sifet class, skipped when sifet is absent)', any(n == 'SiliconProcessNode' and len(r) == 1 for n, _, r in COMPUTELOD_SEED_PAIRS))
u5 = path(m5, 'standard-cells', next(m_ for m_ in maps2 if m_['name'] == 'lod1: netlist → standard cells')['target_ref'], 'up')
check('walking UP from the SKY130 cells reaches the RTL through the delay characterization', u5['rungs'][:2] == ['standard-cells', 'rtl'], u5['rungs'])

man = json.load(open('modules/computelod/polari-app.json'))
from moduleService.manifests import validate
check('the manifest is valid and declares the five classes + the API', validate(man) == [] and len([c for c in man['classes'] if c != 'ComputeLodAPI']) == 5)

n_ok = sum(1 for _, ok in _results if ok)
print(f'\n{n_ok}/{len(_results)} checks passed')
sys.exit(0 if n_ok == len(_results) else 1)
