"""
@module microchip.chip_families_basis

Rank-1 DEVICE FAMILIES as data (MICROCHIP_LADDER_PLAN §2c, ratified
2026-08-31): rank 1 of the design ladder is `device`, and FET is its
first FAMILY, not its definition. Peer families (capacitor,
memristor, photonic, MEMS, inductor, spintronic) enter at rank 1
under the same contract — characterized behavior, derive-or-cite,
refusals by name — and rungs 2+ mix families freely (a 1T1C DRAM
cell is FET + capacitor; an RRAM crossbar is memristors + FET
selectors + CMOS periphery).

SHELL DISCIPLINE: a non-FET family ships here as a SHELL — the
characterization CONTRACT it must satisfy is data (`contract_json`,
revisable), but NO device treeObject class is defined until that
family's own arc characterizes something real (the per-class
schema-freeze rule: defining fields before the physics basis exists
locks in the wrong schema). Every shell says exactly that, plus its
first composition target and plan pointer — refusal, never pretense.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - microchip.chip_api (GET /api/microchip/families[/{name}])
  - microchip.families_selftest
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class DeviceFamilyDefinition(treeObject):
    """One rank-1 device family: its physics, its characterization
    contract (as revisable data), which Polari classes hold LIVE
    artifacts (empty for shells), and what it composes into."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        physics: str = '',
        # 'live' (device rows + characterization basis exist) or
        # 'shell' (contract defined, no classes yet — by rule).
        status: str = 'shell',
        # JSON list of {module, class} rows that ARE this family's
        # artifacts ([] for shells).
        artifact_classes_json: str = '[]',
        # JSON list of {quantity, unit, why} a characterized device
        # of this family must provide — the contract AS DATA.
        contract_json: str = '[]',
        # JSON list of example mixed-family compositions at rung 2+.
        composes_json: str = '[]',
        first_target: str = '',
        plan_pointer: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.physics = physics
        self.status = status
        self.artifact_classes_json = artifact_classes_json
        self.contract_json = contract_json
        self.composes_json = composes_json
        self.first_target = first_target
        self.plan_pointer = plan_pointer
        self.notes = notes


_SHELL_NOTE = ('SHELL: contract defined as data; NO device class '
               'until this family\'s own arc characterizes something '
               'real (per-class schema-freeze rule) — refusal, never '
               'pretense')

SEED_DEVICE_FAMILIES = [
    {'name': 'fet', 'display_name': 'Field-effect transistor',
     'description': 'The proven family — voltage-controlled '
                    'switches; every rung 2+ artifact today is '
                    'built from these.',
     'physics': 'field-effect channel modulation',
     'status': 'live',
     'artifact_classes_json': json.dumps([
         {'module': 'cntfet', 'class': 'AlignedCNTFETDevice'},
         {'module': 'sifet', 'class': 'SiliconMOSFET'},
         {'module': 'electrodevice',
          'class': 'ElectronicDeviceDefinition'}]),
     'contract_json': json.dumps([
         {'quantity': 'Id(Vg,Vd)', 'unit': 'A',
          'why': 'the switching characteristic everything derives '
                 'from'},
         {'quantity': 'Ion/Ioff', 'unit': 'ratio',
          'why': 'usable-as-a-switch gate'},
         {'quantity': 'SS', 'unit': 'mV/dec', 'why': 'turn-off '
          'quality'},
         {'quantity': 'Cgg', 'unit': 'F', 'why': 'loads the '
          'driving stage — delay/energy'},
         {'quantity': 'vdd_v', 'unit': 'V', 'why': 'device-'
          'relative rule: everything at the device\'s OWN Vdd'}]),
     'composes_json': json.dumps([
         {'target': 'standard cells (INV..DFF)', 'with': ['fet']}]),
     'first_target': 'LIVE — cell library characterized',
     'plan_pointer': 'CNT_FET_SIMULATION_PLAN / '
                     'FET_GENERIC_PAGES_PLAN',
     'notes': 'the family the ladder was proven on'},
    {'name': 'capacitor', 'display_name': 'Capacitor (storage)',
     'description': 'Charge-storage element — the C in 1T1C DRAM; '
                    'also decoupling and MIM/MOM passives.',
     'physics': 'electrostatic charge storage',
     'status': 'shell',
     'artifact_classes_json': '[]',
     'contract_json': json.dumps([
         {'quantity': 'C(V)', 'unit': 'F', 'why': 'stored charge '
          'per cell state'},
         {'quantity': 'I_leak', 'unit': 'A', 'why': 'sets DRAM '
          'refresh time'},
         {'quantity': 'ESR', 'unit': 'ohm', 'why': 'read/write '
          'transient behavior'},
         {'quantity': 'V_breakdown', 'unit': 'V', 'why': 'rail '
          'compatibility with the FET family'}]),
     'composes_json': json.dumps([
         {'target': '1T1C DRAM bitcell (rank 2)',
          'with': ['fet', 'capacitor']},
         {'target': 'decoupling in any block', 'with': ['fet',
          'capacitor']}]),
     'first_target': '1T1C DRAM bitcell — the D6 default first '
                     'family (unlocks the DRAM memory kinds)',
     'plan_pointer': 'MICROCHIP_LADDER_PLAN §2b memory kinds, D4/D6',
     'notes': _SHELL_NOTE},
    {'name': 'memristor',
     'display_name': 'Memristive element (RRAM/PCM class)',
     'description': 'Resistance-state storage — filamentary RRAM, '
                    'phase-change; crossbar arrays with FET '
                    'selectors.',
     'physics': 'non-volatile resistance switching',
     'status': 'shell',
     'artifact_classes_json': '[]',
     'contract_json': json.dumps([
         {'quantity': 'R_on/R_off', 'unit': 'ohm',
          'why': 'state window'},
         {'quantity': 'V_set/V_reset', 'unit': 'V',
          'why': 'write compatibility with FET drivers'},
         {'quantity': 'retention', 'unit': 's',
          'why': 'non-volatility claim'},
         {'quantity': 'endurance', 'unit': 'cycles',
          'why': 'lifetime honesty'}]),
     'composes_json': json.dumps([
         {'target': 'RRAM crossbar block (rank 3)',
          'with': ['memristor', 'fet']}]),
     'first_target': 'RRAM crossbar block with FET selectors',
     'plan_pointer': 'MICROCHIP_LADDER_PLAN §2c',
     'notes': _SHELL_NOTE},
    {'name': 'photonic',
     'display_name': 'Photonic device (modulator/photodiode/'
                     'waveguide)',
     'description': 'On-die optical interconnect devices, CMOS-'
                    'driven.',
     'physics': 'electro-optic modulation / photodetection',
     'status': 'shell',
     'artifact_classes_json': '[]',
     'contract_json': json.dumps([
         {'quantity': 'insertion_loss', 'unit': 'dB',
          'why': 'link budget'},
         {'quantity': 'bandwidth', 'unit': 'GHz',
          'why': 'data-rate ceiling'},
         {'quantity': 'responsivity', 'unit': 'A/W',
          'why': 'receiver sensitivity'},
         {'quantity': 'wavelength', 'unit': 'nm',
          'why': 'channel plan'}]),
     'composes_json': json.dumps([
         {'target': 'optical transceiver block (rank 3)',
          'with': ['photonic', 'fet']}]),
     'first_target': 'die-to-die optical link block (pairs with '
                     'rank-6 chiplet assembly)',
     'plan_pointer': 'MICROCHIP_LADDER_PLAN §2c',
     'notes': _SHELL_NOTE},
    {'name': 'mems-resonator',
     'display_name': 'MEMS resonator',
     'description': 'Mechanical resonance on-die: clock references, '
                    'sensors — MEMS-on-CMOS.',
     'physics': 'electromechanical resonance',
     'status': 'shell',
     'artifact_classes_json': '[]',
     'contract_json': json.dumps([
         {'quantity': 'f0', 'unit': 'Hz', 'why': 'the reference '
          'itself'},
         {'quantity': 'Q', 'unit': 'ratio', 'why': 'phase noise / '
          'stability'},
         {'quantity': 'V_drive', 'unit': 'V', 'why': 'FET-rail '
          'compatibility'},
         {'quantity': 'temp_coeff', 'unit': 'ppm/K',
          'why': 'honest drift'}]),
     'composes_json': json.dumps([
         {'target': 'clock-reference block (rank 3)',
          'with': ['mems-resonator', 'fet']}]),
     'first_target': 'clock-reference block',
     'plan_pointer': 'MICROCHIP_LADDER_PLAN §2c',
     'notes': _SHELL_NOTE},
    {'name': 'inductor', 'display_name': 'On-die inductor',
     'description': 'Spiral/solenoid passives for PMIC and RF '
                    'blocks.',
     'physics': 'magnetic energy storage',
     'status': 'shell',
     'artifact_classes_json': '[]',
     'contract_json': json.dumps([
         {'quantity': 'L(f)', 'unit': 'H', 'why': 'the element '
          'value across frequency'},
         {'quantity': 'Q(f)', 'unit': 'ratio', 'why': 'loss '
          'honesty'},
         {'quantity': 'SRF', 'unit': 'Hz', 'why': 'usable band '
          'ceiling'}]),
     'composes_json': json.dumps([
         {'target': 'PMIC / RF front-end blocks (rank 3)',
          'with': ['inductor', 'capacitor', 'fet']}]),
     'first_target': 'on-die PMIC block',
     'plan_pointer': 'MICROCHIP_LADDER_PLAN §2c',
     'notes': _SHELL_NOTE},
    {'name': 'spintronic-mtj',
     'display_name': 'Magnetic tunnel junction (MRAM class)',
     'description': 'Spin-state storage; MRAM bitcells with FET '
                    'selectors.',
     'physics': 'tunnel magnetoresistance',
     'status': 'shell',
     'artifact_classes_json': '[]',
     'contract_json': json.dumps([
         {'quantity': 'TMR', 'unit': '%', 'why': 'read window'},
         {'quantity': 'Rp/Rap', 'unit': 'ohm', 'why': 'sense '
          'design'},
         {'quantity': 'I_switch', 'unit': 'A', 'why': 'FET '
          'selector sizing'},
         {'quantity': 'retention', 'unit': 's',
          'why': 'non-volatility claim'}]),
     'composes_json': json.dumps([
         {'target': 'MRAM bitcell (rank 2)',
          'with': ['spintronic-mtj', 'fet']}]),
     'first_target': 'MRAM bitcell',
     'plan_pointer': 'MICROCHIP_LADDER_PLAN §2c',
     'notes': _SHELL_NOTE},
]


def families_report(manager):
    """Every family with LIVE artifact counts on THIS instance —
    shells report their contract + first target + the honest shell
    note; nothing pretends."""
    tables = getattr(manager, 'objectTables', None) or {}
    out = []
    for row in sorted((tables.get('DeviceFamilyDefinition')
                       or {}).values(),
                      key=lambda r: (getattr(r, 'status', '')
                                     != 'live',
                                     getattr(r, 'name', ''))):
        classes = json.loads(
            getattr(row, 'artifact_classes_json', '[]') or '[]')
        counts = []
        for ref in classes:
            n = len(tables.get(ref.get('class', ''), {}) or {})
            counts.append({**ref, 'rows': n})
        out.append({
            'family': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'physics': getattr(row, 'physics', ''),
            'status': getattr(row, 'status', ''),
            'artifactClasses': counts,
            'liveRows': sum(c['rows'] for c in counts),
            'contract': json.loads(
                getattr(row, 'contract_json', '[]') or '[]'),
            'composes': json.loads(
                getattr(row, 'composes_json', '[]') or '[]'),
            'firstTarget': getattr(row, 'first_target', ''),
            'planPointer': getattr(row, 'plan_pointer', ''),
            'notes': getattr(row, 'notes', ''),
        })
    return {'ok': True, 'schema': 'device-families/1',
            'families': out,
            'principle': ('rank 1 = device; FET is a FAMILY, not '
                          'the definition — rungs 2+ mix families '
                          '(MICROCHIP_LADDER_PLAN §2c). Shells '
                          'carry their contract as data and refuse '
                          'until their own arc characterizes '
                          'something real.')}


def family_report(manager, name):
    rep = families_report(manager)
    for fam in rep['families']:
        if fam['family'] == name:
            return {'ok': True, 'schema': 'device-families/1',
                    **fam}
    known = [f['family'] for f in rep['families']]
    return {'ok': False,
            'error': f'no device family "{name}" — known: '
                     f'{", ".join(known)}'}
