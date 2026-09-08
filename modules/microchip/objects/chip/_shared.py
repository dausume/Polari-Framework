"""@module microchip.objects.chip._shared — what the chip row classes share (constants, seeds, helpers); split from chip_basis.py (sap-2c)."""
import json

SEED_DESIGN_LEVELS = [
    {'name': 'device', 'rank': 1,
     'description': 'A singular FET — owned by the foundational '
                    'device modules, each with its own scale '
                    'axes; this ladder only references it.',
     'artifact_classes_json': json.dumps([
         {'module': 'cntfet', 'class': 'AlignedCNTFETDevice'},
         {'module': 'electrodevice',
          'class': 'ElectronicDeviceDefinition'}]),
     'scale_axes_json': json.dumps([
         {'axis': 'manufacturing_regime', 'values':
          ['percolation_film', 'coarse_alignment',
           'fine_alignment', 'aggressively_scaled', 'target_7nm'],
          'source': 'CNT_FET_SIMULATION_PLAN.md D6'},
         {'axis': 'physics_fidelity',
          'values': ['F0', 'F1-VS', 'F2-ToB', 'F3-NEGF',
                     'F4-atomistic'],
          'source': 'plan D12 (orthogonal to regime)'}]),
     'status': 'live',
     'plan_pointer': 'CNT_FET_SIMULATION_PLAN.md S1 (BUILT)',
     'notes': ''},
    {'name': 'standard-cell', 'rank': 2,
     'description': 'Logic cells characterized for synthesis; '
                    'minimal set INV NAND2 BUF DFF (plan D10), '
                    'Liberty via our CellCharacterizationRun '
                    'schema (D11/D16).',
     'artifact_classes_json': '[]',
     'scale_axes_json': json.dumps([
         {'axis': 'characterization-grid',
          'values': ['sparse (slew x load)', 'dense'],
          'source': 'plan D11'}]),
     'status': 'unbuilt',
     'plan_pointer': 'plan S4 (circuits) + S5 (characterization)',
     'notes': 'refuses until S4 — no fake cells'},
    {'name': 'functional-block', 'rank': 3,
     'description': 'Synthesized/composed blocks: pipeline '
                    'stages, register file, ALU, counters.',
     'artifact_classes_json': '[]',
     'scale_axes_json': '[]',
     'status': 'unbuilt',
     'plan_pointer': 'plan S6 (counter -> ALU -> FSM)',
     'notes': ''},
    {'name': 'core', 'rank': 4,
     'description': 'A processor core (RV32E first; DFF-array '
                    'memory, SRAM excluded until S8).',
     'artifact_classes_json': '[]',
     'scale_axes_json': '[]',
     'status': 'unbuilt',
     'plan_pointer': 'plan S6 (synthesis -> RV32E)',
     'notes': ''},
    {'name': 'chip', 'rank': 5,
     'description': 'Full chip: physical design, wire RC, metal '
                    'stack, IO.',
     'artifact_classes_json': '[]',
     'scale_axes_json': '[]',
     'status': 'unbuilt',
     'plan_pointer': 'plan S7 (physical-design abstraction, '
                     'OpenROAD-era)',
     'notes': ''},
]
_HIL = '[HIL19] Hills et al., Nature 572:595-602 (2019), DOI ' \
       '10.1038/s41586-019-1493-8 (reference-only; Springer ' \
       'exclusive licence)'
SEED_DESIGN_NODES = [
    # ---- OUR ladder ------------------------------------------------
    {'name': 'polari-chip', 'design': 'polari-cnt-ladder',
     'level': 'chip', 'parent': '', 'title': 'Polari CNT chip',
     'artifact_refs_json': '[]', 'citation': '',
     'metrics_json': '{}', 'status': 'unbuilt',
     'notes': 'plan S7 — exists as a ladder position only'},
    {'name': 'polari-rv32e-core', 'design': 'polari-cnt-ladder',
     'level': 'core', 'parent': 'polari-chip',
     'title': 'RV32E core (planned)',
     'artifact_refs_json': '[]', 'citation': '',
     'metrics_json': '{}', 'status': 'unbuilt',
     'notes': 'plan S6'},
    {'name': 'polari-blocks', 'design': 'polari-cnt-ladder',
     'level': 'functional-block', 'parent': 'polari-rv32e-core',
     'title': 'Synthesized blocks (planned)',
     'artifact_refs_json': '[]', 'citation': '',
     'metrics_json': '{}', 'status': 'unbuilt',
     'notes': 'plan S6: counter -> ALU -> FSM first'},
    {'name': 'polari-cell-lib', 'design': 'polari-cnt-ladder',
     'level': 'standard-cell', 'parent': 'polari-blocks',
     'title': 'Minimal cell library (planned: INV NAND2 BUF DFF)',
     'artifact_refs_json': '[]', 'citation': '',
     'metrics_json': json.dumps({
         'planned_cells': ['INV', 'NAND2', 'BUF', 'DFF'],
         's4a_status': 'INV DC half DEMONSTRATED 2026-08-21 '
                       '(complementary OSDI pair in ngspice: VM '
                       'VDD/2, gain -19.7, swing 99.996% — '
                       'CNTFETSimResult kind inverter-vtc); '
                       'characterized CELLS (delay/energy/'
                       'Liberty) still need the charge model'}),
     'status': 'unbuilt',
     'notes': 'plan D10 + S4/S5 — stays unbuilt until cells are '
              'CHARACTERIZED, not just demonstrated'},
    {'name': 'polari-aligned-cnt-s1', 'design': 'polari-cnt-ladder',
     'level': 'device', 'parent': 'polari-cell-lib',
     'title': 'S1 aligned one-tube CNFET (LIVE)',
     'artifact_refs_json': json.dumps([
         {'module': 'cntfet', 'class': 'AlignedCNTFETDevice',
          'name': 'cnt-aligned-s1'}]),
     'citation': 'model: VS-CNFET-derived (see /api/cntfet/'
                 'citations for the full source map)',
     'metrics_json': '{}', 'status': 'live',
     'notes': 'scale axes live ON the device row '
              '(manufacturing_regime, physics_fidelity)'},
    {'name': 'polari-film-fet', 'design': 'polari-cnt-ladder',
     'level': 'device', 'parent': 'polari-cell-lib',
     'title': 'Percolation-film CNT FET (D5 sibling regression '
              'device)',
     'artifact_refs_json': json.dumps([
         {'module': 'electrodevice',
          'class': 'ElectronicDeviceDefinition',
          'name': 'cnt-nfet-led-switch'}]),
     'citation': '',
     'metrics_json': '{}', 'status': 'live',
     'notes': 'sibling-not-successor (plan D5): film results '
              'never scale to aligned devices'},
    # ---- the RV16X-NANO precedent ---------------------------------
    {'name': 'rv16x-chip', 'design': 'rv16x-nano-precedent',
     'level': 'chip', 'parent': '',
     'title': 'RV16X-NANO (fabricated CNFET microprocessor, '
              '2019)',
     'artifact_refs_json': json.dumps([
         {'anchor': 'hil19-cnfet-count'},
         {'anchor': 'hil19-vdd'},
         {'anchor': 'hil19-clock-measured'}]),
     'citation': _HIL,
     'metrics_json': json.dumps({
         'cnfets': 14702, 'cnts': '>10 million', 'vdd_v': 1.8,
         'clock_hz_measured': 10e3,
         'clock_note': 'test-setup-limited; EDA max 1.19 MHz',
         'physical': '3D: metal layers above AND below the '
                     'CNFET layer'}),
     'status': 'reference',
     'notes': 'scientific reference ONLY — no released design '
              'collateral (S0 gate)'},
    {'name': 'rv16x-core', 'design': 'rv16x-nano-precedent',
     'level': 'core', 'parent': 'rv16x-chip',
     'title': 'RV16X core (RV32E ISA on 16-bit data/addresses)',
     'artifact_refs_json': '[]', 'citation': _HIL,
     'metrics_json': json.dumps({
         'isa': 'RV32E (all 31 instructions tested)',
         'data_bits': 16, 'max_logic_depth_stages': 86}),
     'status': 'reference', 'notes': ''},
    {'name': 'rv16x-pipeline', 'design': 'rv16x-nano-precedent',
     'level': 'functional-block', 'parent': 'rv16x-core',
     'title': 'Pipeline organization (IF/ID/EX/MEM/WB)',
     'artifact_refs_json': '[]', 'citation': _HIL,
     'metrics_json': json.dumps({
         'stages': ['instruction-fetch', 'decode', 'execute',
                    'memory', 'write-back'],
         'memory': 'off-chip DRAM + on-chip register file'}),
     'status': 'reference', 'notes': ''},
    {'name': 'rv16x-cell-library', 'design': 'rv16x-nano-precedent',
     'level': 'standard-cell', 'parent': 'rv16x-pipeline',
     'title': '63-cell CNFET standard library',
     'artifact_refs_json': json.dumps([
         {'anchor': 'hil19-cell-library'},
         {'anchor': 'hil19-nor-yield'}]),
     'citation': _HIL,
     'metrics_json': json.dumps({
         'cells': 63,
         'full_adder': '18 p + 18 n CNFETs, gain 17, swing >99%',
         'nor_yield': '14400/14400 (57600 CNFETs, 150 mm wafer)'}),
     'status': 'reference', 'notes': ''},
    {'name': 'rv16x-cnfet', 'design': 'rv16x-nano-precedent',
     'level': 'device', 'parent': 'rv16x-cell-library',
     'title': 'RV16X CNFET (solution-processed CNT network '
              'channel)',
     'artifact_refs_json': json.dumps([
         {'anchor': 'hil19-cnts-per-cnfet'},
         {'anchor': 'hil19-dream-purity-relaxation'},
         {'anchor': 'hil19-rinse-particle-reduction'}]),
     'citation': _HIL,
     'metrics_json': json.dumps({
         'cnts_per_cnfet': '15-25', 'purity_pS': 0.9999,
         'mitigations': ['RINSE (>250x particle reduction)',
                         'MIXED (CMOS doping/contacts)',
                         'DREAM (10000x purity relaxation by '
                         'design)']}),
     'status': 'reference',
     'notes': 'S3 variability anchors ride the cntfet '
              'CNTCalibrationAnchor rows this node references'},
]
