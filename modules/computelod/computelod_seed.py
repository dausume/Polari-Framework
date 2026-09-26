"""
@module computelod.computelod_seed

THE ELEVEN RUNGS, THEIR KINDS, AND THE compute-lod TECH TREE (plan §F1, §B3). Seeds are upserted by name.
Rungs point at what OWNS them: the microchip ladder (design_level_ref) for devices/cells/blocks/subsystems,
pspp for fabrication, materials_science for materials. die/package are NOT rungs (they hang off
microarchitecture through the ladder). A KIND is a row; adding one is data.
"""
import json

from computelod.computelod_basis import ComputeLOD, ComputeKind, ComputeMapping, CharacterizationMapping, CompilerArtifact

TREE = 'compute-lod'


def _rung(rank, name, group, title, desc, design_level_ref='', owner='', classes=(), langs=(), tools=(), status='planned'):
    return {'name': name, 'rank': rank, 'group': group, 'title': title, 'description': desc,
            'design_level_ref': design_level_ref, 'owner_module': owner,
            'artifact_classes_json': json.dumps([{'module': m, 'class': c} for m, c in classes]),
            'languages_json': json.dumps(list(langs)), 'tools_json': json.dumps(list(tools)),
            'concept_node': 'lod-' + name, 'status': status, 'notes': ''}


SEED_COMPUTE_LODS = [
    _rung(1, 'c-source', 'software', 'C / Source', 'The baseline systems language: variables, pointers, memory, structs, bitwise ops, volatile, memory-mapped I/O, interrupts, concurrency, firmware, drivers. Firmware complexity (direct / FreeRTOS / Zephyr / Linux) is a KIND here.',
          langs=('C',), tools=('gcc', 'clang')),
    _rung(2, 'compiler', 'software', 'Compiler', 'Parsing, AST, IR, optimization, instruction selection, register allocation, linking, object formats, ABI, calling conventions. IR is a CompilerArtifact of one compiler, not a rung.',
          langs=('C', 'assembly'), tools=('gcc', 'llvm/clang', 'binutils', 'ELF')),
    _rung(3, 'isa', 'software', 'ISA / Machine Instructions', 'The software/hardware contract: encoding, registers, arithmetic, branches, load/store, privilege, traps, interrupts, atomics, vector/tensor extensions. RISC-V first: RV32I, RV32IM, RV64I, RV64GC.',
          langs=('RISC-V assembly',), tools=('riscv-gnu-toolchain', 'spike')),
    _rung(4, 'microarchitecture', 'architecture', 'Microarchitecture', 'PC, decoder, register file, ALU, load/store, branch, pipeline, caches, MMU, memory controller, vector unit, tensor accelerator, NoC. = the microchip ladder\'s SUBSYSTEM rung by reference; die and package hang off it there.',
          design_level_ref='subsystem', owner='microchip', classes=(('microchip', 'MicrochipDesignNode'),), tools=('PicoRV32', 'Ibex', 'VexRiscv', 'CVA6', 'Rocket', 'BOOM')),
    _rung(5, 'rtl', 'architecture', 'RTL', 'Combinational + sequential logic, registers, clocks, reset, FSMs, pipelines, buses, modules, testbenches. Verilog-2001 generated RTL, SystemVerilog testbenches (D6); Chisel/Amaranth/SpinalHDL generate Verilog.',
          owner='hwfpga', classes=(('hwfpga', 'RegisterMapDefinition'),), langs=('Verilog', 'SystemVerilog'), tools=('Verilator', 'Icarus Verilog', 'Yosys', 'nextpnr', 'Renode'), status='partial'),
    _rung(6, 'logic-netlist', 'digital', 'Logic / Netlist', 'Boolean algebra, gates, muxes, decoders, adders, multipliers, flip-flops, clocking, netlists. = the ladder\'s FUNCTIONAL-BLOCK rung by reference.',
          design_level_ref='functional-block', owner='microchip', classes=(('cntfet', 'FunctionalBlock'),), tools=('Yosys', 'ABC')),
    _rung(7, 'standard-cells', 'digital', 'Standard Cells', 'INV BUF NAND NOR XOR MUX DFF latch, then adders and memory cells; timing, slew, fanout, capacitance, power, area; Liberty/LEF. = the ladder\'s STANDARD-CELL rung; 25 cells proven at switch level in cntfet/sifet.',
          design_level_ref='standard-cell', owner='microchip', classes=(('cntfet', 'CNTCellDefinition'), ('cntfet', 'CellCharacterizationRun')), tools=('OpenSTA', 'Liberty', 'LEF', 'SKY130 libraries'), status='partial'),
    _rung(8, 'devices', 'digital', 'Transistors / Devices', 'MOSFET (planar, FinFET/GAA later), CNFET: gate/source/drain/channel, Vth, IV, capacitance, subthreshold slope, leakage, variability. = the ladder\'s DEVICE rung; VS-CNFET + Si device models, SPICE, Verilog-A/OSDI.',
          design_level_ref='device', owner='microchip', classes=(('cntfet', 'AlignedCNTFETDevice'), ('sifet', 'SiliconMOSFET'), ('electrodevice', 'ElectronicDeviceDefinition')), tools=('ngspice', 'OpenVAF/OSDI', 'Verilog-A'), status='live'),
    _rung(9, 'layout', 'physical', 'Layout', 'Placement, routing, layers, vias, design rules, parasitics, clock trees, power distribution, DRC, LVS. netlist → placement → routing → physical layout.',
          tools=('OpenROAD', 'OpenLane', 'Magic', 'KLayout')),
    _rung(10, 'fabrication', 'physical', 'Fabrication Process', 'An ORDERED process, not a node number: substrate prep, oxidation/deposition, lithography, etch, doping, implantation, anneal, dielectric, metallization, planarization, packaging. = PSPP: materials → processing → structure → properties → performance.',
          owner='pspp', classes=(('pspp', 'ProcessingStage'), ('pspp', 'MaterialProcessDefinition'), ('sifet', 'SiliconProcessNode')), tools=('SKY130 / open PDK',), status='partial'),
    _rung(11, 'materials', 'physical', 'Materials', 'Si, SiO2, high-k dielectrics, Cu, Al, resists, dopants, CNTs, substrates, packaging — the existing multi-scale materials model (five resolutions) and PSPP states; never a second materials database.',
          owner='materials_science', classes=(('materials_science', 'MaterialsScienceMaterial'), ('pspp', 'MaterialState')), status='live'),
]

_KINDS = {
    'c-source': ['direct-firmware', 'freertos', 'zephyr', 'linux-kernel'],
    'compiler': ['frontend', 'optimizer', 'backend', 'assembler', 'linker'],
    'isa': ['base-isa', 'extension', 'privilege', 'vector', 'matrix-tensor', 'custom'],
    'microarchitecture': ['single-cycle', 'multicycle', 'in-order', 'pipelined', 'superscalar', 'out-of-order', 'vector', 'tensor-array', 'gpu-like', 'memory-controller'],
    'rtl': ['datapath', 'control', 'register-map', 'bus-interface', 'accelerator', 'core'],
    'logic-netlist': ['combinational', 'sequential', 'arithmetic', 'memory', 'control', 'interconnect'],
    'standard-cells': ['inverter', 'buffer', 'logic-gate', 'mux', 'sequential', 'arithmetic', 'clock', 'bitcell'],
    'devices': ['mosfet', 'cnfet', 'diode', 'capacitor', 'resistor', 'interconnect-device'],
    'layout': ['cell-layout', 'block-layout', 'macro-layout', 'die-layout'],
    'fabrication': ['lithography', 'deposition', 'etch', 'doping', 'anneal', 'planarization', 'metallization', 'packaging-process'],
    'materials': ['semiconductor', 'conductor', 'dielectric', 'resist', 'dopant', 'substrate', 'packaging'],
}
# the microchip ladder's subsystem kinds this rung's kinds map onto (lad: cpu-core / gpu-compute-unit / npu-tensor-array / sim-engine / memory-controller)
_DESIGN_KIND = {'tensor-array': 'npu-tensor-array', 'gpu-like': 'gpu-compute-unit', 'memory-controller': 'memory-controller',
                'in-order': 'cpu-core', 'pipelined': 'cpu-core', 'superscalar': 'cpu-core', 'out-of-order': 'cpu-core'}
SEED_COMPUTE_KINDS = [
    {'name': '%s/%s' % (rung, k), 'rung': rung, 'title': k.replace('-', ' '), 'description': '',
     'design_kind_ref': _DESIGN_KIND.get(k, '') if rung == 'microarchitecture' else '', 'notes': ''}
    for rung, ks in _KINDS.items() for k in ks]

# ---- the compute-lod tech tree: one concept node per rung, prerequisites = LEARNING order (≠ implementation order)
_PREREQ = {  # what you should know before this rung's concepts (plan §7: learning may run in any order; these are RECOMMENDED)
    'c-source': [], 'compiler': ['c-source', 'isa'], 'isa': ['c-source', 'logic-netlist'],
    'microarchitecture': ['isa', 'rtl'], 'rtl': ['logic-netlist'], 'logic-netlist': [],
    'standard-cells': ['logic-netlist', 'devices'], 'devices': ['materials'], 'layout': ['standard-cells'],
    'fabrication': ['materials'], 'materials': [],
}
SEED_COMPUTE_TECH_TREES = [{'name': TREE, 'title': 'Compute levels of detail — what to learn at each rung', 'owner': 'polari',
                            'description': 'One concept node per ComputeLOD rung; edges are RECOMMENDED prerequisites (learning order), '
                                           'deliberately different from the implementation order the ladder itself encodes.',
                            'is_active': False, 'is_baseline': False, 'notes': 'plan COMPUTE_LOD_TENSOR_PLAN.md §B3/§F1'}]
SEED_COMPUTE_TECH_NODES = [
    {'name': 'lod-' + r['name'], 'tree_name': TREE, 'title': r['title'], 'description': r['description'],
     'depends_on_json': json.dumps(['lod-' + p for p in _PREREQ[r['name']]]), 'layout_hints_json': json.dumps({'column': r['rank']}),
     'cross_refs_json': json.dumps([{'module': 'computelod', 'class': 'ComputeLOD', 'name': r['name'], 'relation': 'concepts-of'}]),
     'data_dependencies_json': '[]', 'notes': ''}
    for r in SEED_COMPUTE_LODS]
SEED_COMPUTE_TECH_SEGMENTS = [   # tools = 'real' segments; languages = 'theory' segments pointing at the owning module
    {'name': 'lod-%s:%s' % (r['name'], t), 'tech_node': 'lod-' + r['name'], 'tree_name': TREE, 'segment_kind': 'real', 'ref_name': t, 'notes': 'tool'}
    for r in SEED_COMPUTE_LODS for t in json.loads(r['tools_json'])]

# ---- lod-1: THE TEACHING PATH, from the committed report of a real run (custom/lod1_chain.py). The rows
# exist only because the tools ran: gcc's assembly and encoding, PicoRV32's cited lines, yosys' cell counts,
# iverilog's verdicts; and two rows are left UNRESOLVED on purpose (technology mapping, delay — lod-2).
from computelod.custom.lod1_chain import report as _lod1_report, rows as _lod1_rows
SEED_LOD1_ARTIFACTS, SEED_LOD1_MAPPINGS, SEED_LOD1_CHARACTERIZATIONS = _lod1_rows(_lod1_report())
# ---- lod-2: OPEN SILICON — the SKY130 mapping + OpenSTA timing REPLACE lod-1's two gaps by name (the unresolved
# netlist → standard cells mapping; the delay characterization with evidence none) and add the next partial
# step (cells → devices) and the area. Without a lod-2 report the gaps stay, honestly.
from computelod.custom.lod2_silicon import report as _lod2_report, rows as _lod2_rows
_l2m, _l2c = _lod2_rows(_lod2_report(), (_lod1_report() or {}).get('adder_synth', {}).get('cells', 0))
def _merge(base, over):
    names = {r['name'] for r in over}
    return [r for r in base if r['name'] not in names] + over
SEED_LOD_MAPPINGS = _merge(SEED_LOD1_MAPPINGS, _l2m)
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD1_CHARACTERIZATIONS, _l2c)
# ---- lod-2b: the SECOND Liberty — our own CNT cell library (cntfet characterization, ngspice) — NEW rows beside
# the SKY130 ones (different names; nothing replaced): the same netlist onto derived cells, timed under the
# library's own point, and a cells → devices step that for this library is a real reference (the derived device).
from computelod.custom.lod2_cnt import report as _lod2cnt_report, rows as _lod2cnt_rows
_l2cm, _l2cc = _lod2cnt_rows(_lod2cnt_report(), (_lod1_report() or {}).get('adder_synth', {}).get('cells', 0))
SEED_LOD_MAPPINGS = _merge(SEED_LOD_MAPPINGS, _l2cm)
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD_CHARACTERIZATIONS, _l2cc)
# ---- lod-3: cells → transistors → layout, READ from the artefacts (PDK .spice/.lef at a pinned commit; the CNT
# cell library's device lists). Replaces lod-2's partial cells → devices BY NAME; adds devices → layout (LEF area
# cross-checked against the Liberty), layout → fabrication (partial), and the CNT layout as unresolved.
from computelod.custom.lod3_cells import report as _lod3_report, rows as _lod3_rows
_l3m, _l3c = _lod3_rows(_lod3_report(), _lod2_report(), _lod2cnt_report())
SEED_LOD_MAPPINGS = _merge(SEED_LOD_MAPPINGS, _l3m)
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD_CHARACTERIZATIONS, _l3c)
# ---- lod-4: fabrication → materials, by reference: a SiliconProcessNode `sky130` in sifet's ladder shape (seeded
# here, manufacturable = None until he rules — D-lod4-1) and sifet's eg-si grade via the Siemens route. Replaces
# lod-3's partial layout → fabrication BY NAME; the walk from C then spans all eleven rungs.
from computelod.custom.lod4_process import report as _lod4_report, rows as _lod4_rows, SKY130_NODE
_l4m, _l4c = _lod4_rows(_lod4_report(), _lod3_report())
SEED_LOD_MAPPINGS = _merge(SEED_LOD_MAPPINGS, _l4m)
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD_CHARACTERIZATIONS, _l4c)
# ---- lod-4c: the process node's own numbers RUN — Ion / Ioff / Vt / DIBL / SS per device flavour from DC sweeps on the PDK's
# BSIM4 models (simulated); upward characterizations fabrication → devices; the sky130 row's key_numbers_json gains them (lod4_process).
from computelod.custom.lod4_devices import report as _lod4c_report, rows as _lod4c_rows
_l4cm, _l4cc = _lod4c_rows(_lod4c_report())
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD_CHARACTERIZATIONS, _l4cc)
# ---- lod-2c: the two Liberties' twin cells at the SAME conditions (the CNT point; each library's own FO4) — 24 upward rows,
# every one simulated; the CNT side intrinsic-grade, the SKY130 side a schematic netlist; area refused for CNT (stated in the report).
from computelod.custom.lod2_compare import report as _lod2c_report, rows as _lod2c_rows
_l2cmp_m, _l2cmp_c = _lod2c_rows(_lod2c_report())
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD_CHARACTERIZATIONS, _l2cmp_c)
# ---- lod-3e: the WHOLE adder placed and routed (ORFS, pinned image) — adder cells → layout per variant (measured: the router's
# DRC count), routed delay with parasitics, the wire cost (one subtraction on one netlist), core area (a knob, said so), wirelength.
from computelod.custom.lod3_pnr import report as _lod3e_report, rows as _lod3e_rows
_l3em, _l3ec = _lod3e_rows(_lod3e_report(), _lod2_report())
SEED_LOD_MAPPINGS = _merge(SEED_LOD_MAPPINGS, _l3em)
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD_CHARACTERIZATIONS, _l3ec)
# ---- lod-4b: fabrication as ROWS — the SKY130 route as PSPP ProcessingStage / MaterialProcessDefinition rows (stages from the PDK's
# documented layer stack, unit processes per the textbook, the recipe named as absent) and the CNT route by reference to cntfet; replaces
# lod-4's fabrication → materials by name, adds the CNT branch's. The PSPP rows themselves are seeded below (guarded on pspp).
from computelod.custom.lod4_steps import report as _lod4b_report, rows as _lod4b_rows, stage_rows as _lod4b_stages, process_rows as _lod4b_processes
_l4bm, _l4bc = _lod4b_rows(_lod4b_report(), _lod4_report(), _lod3_report())
SEED_LOD_MAPPINGS = _merge(SEED_LOD_MAPPINGS, _l4bm)
# ---- lod-3b: devices → cells SIMULATED by us — ngspice on the PDK's own BSIM4 models, cross-checked against the
# Liberty at the same slew/load; the gap (schematic netlist vs extracted layout) is reported, not tuned.
from computelod.custom.lod3_devices import report as _lod3b_report, rows as _lod3b_rows
_l3bm, _l3bc = _lod3b_rows(_lod3b_report())
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD_CHARACTERIZATIONS, _l3bc)
# ---- lod-3c: the layout RUN — magic DRC (context rules classified) + parasitic extraction + netgen LVS on the PDK's
# own .mag via polari-eda-tools; devices → layout becomes measured; the extracted netlists re-timed (the parasitics
# hypothesis TESTED: half rejected, stated).
from computelod.custom.lod3_layout import report as _lod3c_report, rows as _lod3c_rows
_l3cm, _l3cc = _lod3c_rows(_lod3c_report())
SEED_LOD_MAPPINGS = _merge(SEED_LOD_MAPPINGS, _l3cm)
SEED_LOD_CHARACTERIZATIONS = _merge(SEED_LOD_CHARACTERIZATIONS, _l3cc)

def _flow_owned(rows):
    """The lod rows are FLOW OUTPUT, not hand-edited data: every field but the name is code-owned, so a row an instance already
    holds CONVERGES to the seed (the seeder's `_converge`). Found 2026-09-26 on the home swarm: `lod4: fabrication → materials`
    still read its lod-4 text after lod-4b replaced it by name — a replace-by-name only ever reached a fresh instance."""
    return [dict(r, _converge=[k for k in r if k != 'name']) for r in rows]


COMPUTELOD_SEED_PAIRS = [
    ('ComputeLOD', ComputeLOD, _flow_owned(SEED_COMPUTE_LODS)),
    ('ComputeKind', ComputeKind, SEED_COMPUTE_KINDS),
    ('ComputeMapping', ComputeMapping, _flow_owned(SEED_LOD_MAPPINGS)),
    ('CharacterizationMapping', CharacterizationMapping, _flow_owned(SEED_LOD_CHARACTERIZATIONS)),
    ('CompilerArtifact', CompilerArtifact, _flow_owned(SEED_LOD1_ARTIFACTS)),
]
try:   # the fabrication rung's row is a sifet class (skipped by the seed loop when sifet is not loaded)
    from sifet.objects.si_ladder.SiliconProcessNode import SiliconProcessNode
    # D-lod4-1 (ruled 2026-09-26): the ruling lives in code, so these two fields FOLLOW the seed on an instance that
    # already holds the row (the seeder's `_converge`); the rest of the row stays as the instance has it
    COMPUTELOD_SEED_PAIRS += [('SiliconProcessNode', SiliconProcessNode,
                               [dict(SKY130_NODE, _converge=['manufacturability', 'manufacturable_reason', 'key_numbers_json'])] if _lod4_report() else [])]
except Exception:   # pragma: no cover
    pass
try:
    from pspp.objects.material_states.ProcessingStage import ProcessingStage as _PS
    from pspp.objects.material_processes.MaterialProcessDefinition import MaterialProcessDefinition as _MPD
except ImportError:   # pspp absent: the route rows are not seeded (the lod-4b mapping still names them)
    _PS = _MPD = None
if _PS is not None and _lod4b_report():
    # lod-4b: the fabrication route in PSPP's own classes — merged into pspp's tables by name (prefixes sky130-/cnt- never collide with pspp's seeds);
    # description/notes are code-owned (the reading may sharpen), so they converge onto an instance that already holds the rows
    COMPUTELOD_SEED_PAIRS += [('ProcessingStage', _PS, [dict(r, _converge=['description', 'notes', 'provenance_id']) for r in _lod4b_stages()]),
                              ('MaterialProcessDefinition', _MPD, [dict(r, _converge=['description', 'notes', 'provenance_id', 'parameter_schema_json']) for r in _lod4b_processes()])]
try:   # the tree rows belong to the techtree module; seeded only when it is present
    from techtree.techtree_basis import TechTreeDefinition, TechNode, TechSegmentAssignment
    COMPUTELOD_SEED_PAIRS += [('TechTreeDefinition', TechTreeDefinition, SEED_COMPUTE_TECH_TREES),
                              ('TechNode', TechNode, SEED_COMPUTE_TECH_NODES),
                              ('TechSegmentAssignment', TechSegmentAssignment, SEED_COMPUTE_TECH_SEGMENTS)]
except Exception:   # pragma: no cover — techtree absent: the ladder still seeds, the concept tree waits
    pass
