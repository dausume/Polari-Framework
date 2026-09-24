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
check('the seed MERGES lod-2 over lod-1 by name: no unresolved netlist→cells row remains, one delay row, eight mappings + seven characterizations',
      not any(m_['kind'] == 'unresolved' for m_ in SEED_LOD_MAPPINGS) and len(SEED_LOD_MAPPINGS) == 8 and len(SEED_LOD_CHARACTERIZATIONS) == 7
      and sum(1 for c in SEED_LOD_CHARACTERIZATIONS if 'propagation delay' in c['name']) == 1)
m5 = _mgr()
for cls, rws in (('ComputeMapping', SEED_LOD_MAPPINGS), ('CharacterizationMapping', SEED_LOD_CHARACTERIZATIONS)):
    for r_ in rws:
        _add(m5, cls, **r_)
p5 = path(m5, 'c-source', 'lod1/add.c: c = a + b')
check('the walk from the C statement now reaches STANDARD CELLS and stops at DEVICES — one rung deeper than lod-1, and still honest about where it ends',
      p5['rungs'] == ['c-source', 'compiler', 'isa', 'microarchitecture', 'rtl', 'logic-netlist', 'standard-cells', 'devices'] and p5['unresolved_at'] == 'devices', p5['rungs'])
u5 = path(m5, 'standard-cells', next(m_ for m_ in maps2 if m_['name'] == 'lod1: netlist → standard cells')['target_ref'], 'up')
check('walking UP from the SKY130 cells reaches the RTL through the delay characterization', u5['rungs'][:2] == ['standard-cells', 'rtl'], u5['rungs'])

man = json.load(open('modules/computelod/polari-app.json'))
from moduleService.manifests import validate
check('the manifest is valid and declares the five classes + the API', validate(man) == [] and len([c for c in man['classes'] if c != 'ComputeLodAPI']) == 5)

n_ok = sum(1 for _, ok in _results if ok)
print(f'\n{n_ok}/{len(_results)} checks passed')
sys.exit(0 if n_ok == len(_results) else 1)
