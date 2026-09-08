"""
@module cntfet.cnt_targets_basis

Dustin 2026-08-29: "These cells are not made to work with these kinds
of FETs … saying they are failing does not make sense unless they are
something we are actively trying to make the FET work for. We should
have a mapping between FETs and the cells they are meant to map to."

So: a BUDGET belongs to a DESIGN TARGET (what a thing is engineered
FOR — low-power logic, general logic, high-performance logic, analog
signal, research reference), and a FET (and every library / cell /
block built on it) is MAPPED to the targets it was engineered for.
A budget check is pass / fail ONLY against a mapped target; against
any other target it is INFORMATIONAL ("would meet / would not meet")
— never a red "fail" on a device that was never meant to meet it.

@consumers cnt_power.budget_report, cnt_api, polariServer (seeds),
  fet-overview (frontend)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class DesignTarget(treeObject):
    """What a device / library is engineered FOR, as a row: the
    PowerBudget rows (by name) and other criteria that apply."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # PowerBudget names this target enforces (by scope)
        budgets_json: str = '[]',
        # non-power criteria (informational for now, data for later)
        criteria_json: str = '[]',
        # 'switching' | 'signal' | 'any' — the optimization class it
        # belongs with
        optimization: str = 'switching',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.budgets_json = budgets_json
        self.criteria_json = criteria_json
        self.optimization = optimization
        self.notes = notes
        self.is_prior = is_prior


class FETTargetMapping(treeObject):
    """Which targets a FET is engineered for, and WHY — the mapping
    Dustin asked for. Libraries / cells / blocks built on the FET
    inherit it."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        targets_json: str = '[]',
        engineered_for: str = '',
        source: str = '',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.device = device
        self.targets_json = targets_json
        self.engineered_for = engineered_for
        self.source = source
        self.notes = notes
        self.is_prior = is_prior


SEED_DESIGN_TARGETS = [
    {'name': 'low-power-logic', 'display_name': 'Low-power logic',
     'description': 'Sub-0.6 V switching where leakage dominates the '
                    'budget: ≤ 1 nW static per FET and per cell, '
                    '≤ 1 µW dynamic per cell. The [FC10] / [VS1] '
                    'aligned-CNT target.',
     'budgets_json': json.dumps(['fet-leakage-1nw', 'cell-leakage-1nw']),
     'criteria_json': json.dumps([{'metric': 'fet-on-off-decades',
                                   'min': 4, 'why': 'yield criterion'}]),
     'optimization': 'switching',
     'notes': 'PRIOR budgets — knobs on the PowerBudget rows.'},
    {'name': 'general-logic', 'display_name': 'General-purpose logic',
     'description': '0.8–1.0 V CMOS logic (90 nm-class planar / early '
                    'FinFET): ≤ 100 nW static per FET and per cell, '
                    '≤ 10 µW dynamic per cell.',
     'budgets_json': json.dumps(['fet-leakage-100nw',
                                 'cell-leakage-100nw']),
     'criteria_json': '[]', 'optimization': 'switching',
     'notes': 'PRIOR budgets for a 90 nm-class node at 1 V.'},
    {'name': 'high-performance-logic',
     'display_name': 'High-performance logic',
     'description': 'Speed first: leakage tolerated up to 1 µW per '
                    'FET / cell, dynamic ≤ 100 µW per cell; the '
                    'density ceiling is the binding limit.',
     'budgets_json': json.dumps(['fet-leakage-1uw', 'cell-leakage-1uw',
                                 'block-density-100w-cm2']),
     'criteria_json': '[]', 'optimization': 'switching',
     'notes': 'PRIOR budgets.'},
    {'name': 'analog-signal', 'display_name': 'Analog / signal',
     'description': 'Amplification and signal conditioning: gm/Id, '
                    'intrinsic gain and headroom matter; static power '
                    'is a bias current, not leakage — no leakage '
                    'budget applies.',
     'budgets_json': '[]',
     'criteria_json': json.dumps([{'metric': 'fet-intrinsic-gain',
                                   'min': 10, 'why': 'usable gain'}]),
     'optimization': 'signal',
     'notes': 'No power budgets by design; scored by '
              'fet-signal-quality.'},
    {'name': 'research-reference', 'display_name': 'Research reference',
     'description': 'A device kept to validate models and processes '
                    '(comparators, reference twins). No budget is '
                    'enforced; every check is informational.',
     'budgets_json': '[]', 'criteria_json': '[]', 'optimization': 'any',
     'notes': ''},
]

#: Extra PowerBudget rows the general / high-performance targets cite
#: (cnt_power's seeds carry the 1 nW priors + the density ceiling).
SEED_TARGET_POWER_BUDGETS = [
    {'name': 'fet-leakage-100nw', 'scope': 'fet',
     'max_static_w': 1e-7, 'max_dynamic_w': None,
     'max_density_w_per_cm2': None, 'max_temperature_k': None,
     'notes': 'PRIOR: general-logic FET leakage ≤ 100 nW at Vdd.',
     'is_prior': True},
    {'name': 'cell-leakage-100nw', 'scope': 'cell',
     'max_static_w': 1e-7, 'max_dynamic_w': 1e-5,
     'max_density_w_per_cm2': None, 'max_temperature_k': None,
     'notes': 'PRIOR: general-logic cell leakage ≤ 100 nW, dynamic '
              '≤ 10 µW (α 0.1, 1 GHz).',
     'is_prior': True},
    {'name': 'fet-leakage-1uw', 'scope': 'fet',
     'max_static_w': 1e-6, 'max_dynamic_w': None,
     'max_density_w_per_cm2': None, 'max_temperature_k': None,
     'notes': 'PRIOR: high-performance FET leakage ≤ 1 µW.',
     'is_prior': True},
    {'name': 'cell-leakage-1uw', 'scope': 'cell',
     'max_static_w': 1e-6, 'max_dynamic_w': 1e-4,
     'max_density_w_per_cm2': None, 'max_temperature_k': None,
     'notes': 'PRIOR: high-performance cell leakage ≤ 1 µW, dynamic '
              '≤ 100 µW.',
     'is_prior': True},
]


def _map(device, targets, why, source):
    return {'name': f'targets@{device}', 'device': device,
            'targets_json': json.dumps(list(targets)),
            'engineered_for': why, 'source': source}


SEED_FET_TARGET_MAPPINGS = [
    _map('cnt-aligned-s1', ('low-power-logic',),
         'the S1 aligned-CNT device is calibrated on the [FC10] / [VS1] '
         'sub-0.6 V low-leakage logic target', '[FC10] [VS1]'),
    _map('cnt-aligned-s1-tox2', ('low-power-logic',),
         'S1 with a thinner oxide — same low-power logic target, '
         'better gate control', 'comparator of S1'),
    _map('cnt-aligned-s1-lg10', ('low-power-logic', 'research-reference'),
         'S1 at Lg 10 nm: probes short-channel loss on the same target; '
         'also a reference for the DIBL story', 'comparator of S1'),
    _map('cnt-aligned-s1-lg30', ('research-reference',),
         'S1 at Lg 30 nm exists to show the trade-off, not as a '
         'product target', 'comparator of S1'),
    _map('cnt-aligned-s1-p', ('low-power-logic',),
         'the p-twin of S1 — the complementary half of the same '
         'low-power CMOS target', 'pair of S1'),
    _map('si-nmos-planar-90', ('general-logic',),
         '90 nm-class planar NMOS at 1.0 V — general-purpose CMOS '
         'logic, the open-library reference process', 'sifet seed'),
    _map('si-pmos-planar-90', ('general-logic',),
         'the planar PMOS of the same pair', 'sifet seed'),
    _map('si-nmos-planar-solgel-sio2', ('general-logic',
                                        'research-reference'),
         'planar NMOS on a sol-gel SiO2 dielectric: same logic target, '
         'kept to compare the sol-gel oxide against thermal oxide',
         'sifet seed'),
    _map('si-nmos-planar-solgel-hfo2', ('general-logic',),
         'planar NMOS on sol-gel HfO2 (high-k) — general logic with a '
         'thinner EOT', 'sifet seed'),
    _map('si-pmos-planar-solgel-hfo2', ('general-logic',),
         'the PMOS of the sol-gel HfO2 planar pair', 'sifet seed'),
    _map('si-nmos-finfet-solgel-hfo2', ('high-performance-logic',
                                        'general-logic'),
         'FinFET-class NMOS at 0.8 V on sol-gel HfO2 — the '
         'performance-leaning silicon option', 'sifet seed'),
    _map('si-pmos-finfet-solgel-hfo2', ('high-performance-logic',
                                        'general-logic'),
         'the PMOS of the FinFET pair', 'sifet seed'),
]

DEFAULT_TARGET = 'research-reference'


def _rows(manager, cls):
    table = (getattr(manager, 'objectTables', {}) or {}).get(cls) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def targets_index(manager):
    """{name: target dict} — manager rows win over seeds."""
    out = {t['name']: dict(t) for t in SEED_DESIGN_TARGETS}
    for r in _rows(manager, 'DesignTarget'):
        out[getattr(r, 'name', '')] = {
            k: getattr(r, k, '') for k in (
                'name', 'display_name', 'description', 'budgets_json',
                'criteria_json', 'optimization', 'notes')}
    return out


def mapping_for(manager, device_name):
    """The FETTargetMapping for a device (manager row wins over the
    seed); an unmapped device is a research reference, stated."""
    seed = next((m for m in SEED_FET_TARGET_MAPPINGS
                 if m['device'] == device_name), None)
    row = next((r for r in _rows(manager, 'FETTargetMapping')
                if getattr(r, 'device', '') == device_name), None)
    if row is not None:
        return {'device': device_name,
                'targets': json.loads(getattr(row, 'targets_json', '[]')),
                'engineered_for': getattr(row, 'engineered_for', ''),
                'source': getattr(row, 'source', ''), 'mapped': True}
    if seed is not None:
        return {'device': device_name,
                'targets': json.loads(seed['targets_json']),
                'engineered_for': seed['engineered_for'],
                'source': seed['source'], 'mapped': True}
    return {'device': device_name, 'targets': [DEFAULT_TARGET],
            'engineered_for': 'no FETTargetMapping row — treated as a '
                              'research reference (every budget is '
                              'informational). Map it: POST a '
                              'FETTargetMapping row.',
            'source': '', 'mapped': False}


def targets_for_device(manager, device_name):
    """Ordered list of target dicts the device is engineered for +
    the mapping itself."""
    idx = targets_index(manager)
    m = mapping_for(manager, device_name)
    return ([idx[t] for t in m['targets'] if t in idx], m, idx)
