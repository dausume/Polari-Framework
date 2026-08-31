"""
@module cntfet.cnt_cell_pages

Cell arc (Dustin 2026-08-31): "general cell detail pages AND another
object that is those cells with particular FET configurations… a
detail page that enables sensibly looking at the Cell in both the
general case and selecting one of the FET-specific cases — solved at
least for two samples of the proven open-source cases."

Three pieces, all fet-named (fet, not cntfet):

  CellFETConfiguration      the OBJECT: one row per cell × FET
                            (object-coherence — the cell-on-this-
                            device pairing is addressable whether or
                            not it is characterized; absence is data,
                            served with the fill affordance).
  GET /api/fet/cell/{cell}/summary          cell-summary/1 — the
                            GENERAL cell (identity from CELL_LIBRARY
                            + the CNTCellDefinition variants, proof,
                            and the configuration index across every
                            FET, proven-free + characterized ones
                            flagged as OPEN-SOURCE SAMPLES).
  GET /api/fet/cellcfg/{cell}/{device}/summary
                            cell-config-summary/1 — the SPECIFIC
                            case: numbers from that device's latest
                            library run (score vs the FET's intrinsic
                            limits, leakage per input state, dynamic
                            energy), the simulate/characterize acts,
                            and the proof ROLL-UP (worst of cell +
                            device, the cnt_blocks convention).
  GET /api/fet/cells        the generic cell catalogue.

The generic page seed `cell-detail` (open as
/display/cell-detail?object=<cell>) shows the general cell (logic
diagram, schematic, freedom proof — device-independent) with the
`cell-detail-panel` component providing the FET-configuration
selector.

@consumers
  - cnt_api (routes above)
  - polariServer (class + SEED_CELL_CONFIGS + SEED_CELL_PAGES)
  - polari-platform-angular cell-detail-panel
  - cntfet.selftest_cell_pages
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_cell_library import CELL_LIBRARY, fet_count
from cntfet.cnt_compare import _component_item
from cntfet.cnt_derive import get_row
from cntfet.cnt_pages_seed import _row, _sapi

CELL_SCHEMA = 'cell-summary/1'
CONFIG_SCHEMA = 'cell-config-summary/1'

#: every library cell key + the sequential DFF (cnt_cell_coverage's
#: entry list) — the general pages and the config grid share it.
CELL_KEYS = tuple(sorted(CELL_LIBRARY)) + ('cdff',)


class CellFETConfiguration(treeObject):
    """One cell × FET pairing as a ROW — the addressable identity of
    'this cell built from this device'. The numbers are DERIVED live
    from the device's latest characterization run (never stamped
    here); an uncharacterized pairing is still a row, served with
    the fill affordance."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',        # 'cellcfg-{cell}-{device}'
        cell: str = '',
        device: str = '',
        drive_strength: int = 1,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.cell = cell
        self.device = device
        self.drive_strength = drive_strength
        self.notes = notes


def config_name(cell, device):
    return f'cellcfg-{cell}-{device}'


def _device_names(manager):
    tables = getattr(manager, 'objectTables', None) or {}
    return sorted(
        (getattr(r, 'name', ''), cls)
        for cls, tech in (('AlignedCNTFETDevice', 'cnt'),
                          ('SiliconMOSFET', 'silicon'))
        for r in (tables.get(cls) or {}).values())


def seed_cell_configs(device_names):
    """The seed grid: every cell × every seeded device (drive x1)."""
    return [{'name': config_name(c, d), 'cell': c, 'device': d,
             'drive_strength': 1,
             'notes': 'the cell-on-this-FET pairing as an object; '
                      'numbers derive from the device\'s latest '
                      'characterization run'}
            for c in CELL_KEYS for d in device_names]


def _kind(cell):
    from cntfet.cnt_cell_coverage import _sequential_keys, _tristate_keys
    if cell in _sequential_keys() or cell == 'cdff':
        return 'sequential'
    if cell in _tristate_keys():
        return 'tri-state'
    return 'combinational'


def _proof_rollup(manager, cell, device):
    """Worst of the cell's and the device's freedom proofs (the
    cnt_blocks convention) — an open-source SAMPLE needs both
    proven-free."""
    from cntfet import cnt_evidence as ev
    parts, statuses = [], []
    for kind, name in (('cell', cell), ('device', device)):
        pr = ev.freedom_proof(manager, kind, name)
        statuses.append(pr.get('status', 'unknown'))
        parts.append({'kind': kind, 'subject': name,
                      'status': pr.get('status', 'unknown'),
                      'detailPath': pr.get('detailPath')})
    status = ev._combine(statuses)
    return {'status': status, 'parts': parts,
            'openSourceSample': status == 'proven-free',
            'rule': 'worst over the cell and the device — a free '
                    'circuit on an encumbered FET is not an open '
                    'sample (and vice versa)'}


def _coverage_entry(manager, device, cell):
    from cntfet.cnt_cell_coverage import device_cell_coverage
    cov = device_cell_coverage(manager, device)
    entry = next((c for c in cov.get('cells', [])
                  if c.get('cell') == cell), None)
    return entry, cov.get('latestLibraryRun')


def cell_summary(manager, cell):
    """cell-summary/1 — the GENERAL cell + the configuration index."""
    if cell not in CELL_KEYS:
        return {'ok': False, 'schema': CELL_SCHEMA,
                'error': f'no library cell "{cell}" '
                         f'({" | ".join(CELL_KEYS)})'}
    lib = CELL_LIBRARY.get(cell, {})
    tables = getattr(manager, 'objectTables', None) or {}
    variants = sorted(
        getattr(r, 'name', '')
        for r in (tables.get('CNTCellDefinition') or {}).values()
        if str(getattr(r, 'name', '')).startswith(f'{cell}-x'))
    from cntfet import cnt_evidence as ev
    proof = ev.freedom_proof(manager, 'cell', cell)
    configs = []
    for device, cls in _device_names(manager):
        entry, run = _coverage_entry(manager, device, cell)
        rollup = _proof_rollup(manager, cell, device)
        configs.append({
            'config': config_name(cell, device),
            'device': device,
            'technology': 'silicon' if cls == 'SiliconMOSFET'
            else 'cnt',
            'characterized': bool(entry and entry.get('covered')),
            'run': (entry or {}).get('run', ''),
            'fill': (entry or {}).get('fill', ''),
            'proofStatus': rollup['status'],
            'openSourceSample': (rollup['openSourceSample']
                                 and bool(entry
                                          and entry.get('covered'))),
            'summaryPath': f'/api/fet/cellcfg/{cell}/{device}/summary',
        })
    open_samples = [c for c in configs if c['openSourceSample']]
    return {
        'ok': True, 'schema': CELL_SCHEMA, 'cell': cell,
        'identity': {
            'cell': cell, 'kind': _kind(cell),
            'function': lib.get('function',
                                'DFF' if cell == 'cdff' else ''),
            'inputs': lib.get('inputs', ['D', 'CLK']
                              if cell == 'cdff' else []),
            'output': lib.get('output', 'Q' if cell == 'cdff'
                              else 'Y'),
            'unate': lib.get('unate', ''),
            'liberty_function': lib.get('liberty_function', ''),
            'fet_count_x1': (fet_count(cell, 1)
                             if cell in CELL_LIBRARY else 24),
            'variants': variants,
            'composed_of': [s for s, _i, _o in lib.get('compose', [])],
        },
        'proof': {'status': proof.get('status', 'unknown'),
                  'detailPath': proof.get('detailPath')},
        'configurations': configs,
        'openSourceSamples': open_samples,
        'openSourceNote': ('a configuration is an OPEN-SOURCE SAMPLE '
                           'when the cell AND the device are '
                           'proven-free AND the pairing is '
                           'characterized (real numbers, free to '
                           'use)'),
        'api': {'logic': f'/api/fet/cell/{cell}/logic',
                'proof': f'/api/fet/cell/{cell}/proof'},
        'page': f'/display/cell-detail?object={cell}',
        'note': ('the general cell — device-independent; pick a '
                 'configuration for the FET-specific numbers'),
    }


def cell_config_summary(manager, cell, device_name):
    """cell-config-summary/1 — this cell ON this FET."""
    if cell not in CELL_KEYS:
        return {'ok': False, 'schema': CONFIG_SCHEMA,
                'error': f'no library cell "{cell}"'}
    device = (get_row(manager, 'AlignedCNTFETDevice', device_name)
              or get_row(manager, 'SiliconMOSFET', device_name))
    if device is None:
        return {'ok': False, 'schema': CONFIG_SCHEMA,
                'error': f'no device named "{device_name}"'}
    entry, run = _coverage_entry(manager, device_name, cell)
    rollup = _proof_rollup(manager, cell, device_name)
    out = {
        'ok': True, 'schema': CONFIG_SCHEMA,
        'config': config_name(cell, device_name),
        'cell': cell, 'device': device_name,
        'characterized': bool(entry and entry.get('covered')),
        'run': (entry or {}).get('run', ''),
        'proof': rollup,
        'openSourceSample': (rollup['openSourceSample']
                             and bool(entry and entry.get('covered'))),
        'acts': {
            'characterize': (entry or {}).get(
                'fill', '{"action": "characterize-cells"}'),
            'actTarget': f'/api/cntfet/devices/{device_name}',
            'logicStep': f'/api/fet/cell/{cell}/logic — the switch-'
                         'level simulation (step every vector) uses '
                         'the same netlist this configuration is '
                         'characterized from',
        },
        'dataPaths': (entry or {}).get('cell') and {
            k: v for k, v in (entry or {}).items()
            if k not in ('cell', 'kind', 'covered', 'run', 'fill')
        } or {},
    }
    if not out['characterized']:
        out['refusal'] = (
            f'"{cell}" has no characterized numbers on '
            f'"{device_name}" yet — POST {out["acts"]["characterize"]}'
            f' to {out["acts"]["actTarget"]} (the numbers then read '
            'back from the run row; nothing is invented meanwhile)')
        out['score'] = out['power'] = None
        return out
    # numbers: score vs THIS FET's intrinsic limits + leakage states
    from cntfet.cnt_cell_scoring import score_cells
    from cntfet.cnt_power import cell_power
    sc = score_cells(manager, device_name)
    mine = None
    if sc.get('ok'):
        mine = next((c for c in sc['cells']
                     if c.get('ok')
                     and (c.get('frame') or {}).get('cell') == cell),
                    None)
    out['score'] = ({'score': mine['score'], 'terms': mine['terms'],
                     'libertyCell': mine['cell'],
                     'tau_int_ps': sc.get('tau_int_ps'),
                     'vdd_v': sc.get('vdd_v'), 'run': sc.get('run')}
                    if mine else
                    {'refusal': sc.get('error',
                                       f'no scored frame for "{cell}" '
                                       'in the latest run')})
    pw = cell_power(manager, device_name, cell)
    out['power'] = (pw if pw.get('ok')
                    else {'refusal': pw.get('error',
                                            pw.get('refusal',
                                                   'power refused'))})
    return out


def cells_catalogue(manager):
    """/api/fet/cells — every cell with its page + summary paths."""
    rows = []
    for c in CELL_KEYS:
        lib = CELL_LIBRARY.get(c, {})
        rows.append({
            'cell': c, 'kind': _kind(c),
            'function': lib.get('function',
                                'DFF' if c == 'cdff' else ''),
            'fets_x1': fet_count(c, 1) if c in CELL_LIBRARY else 24,
            'detailPage': f'/display/cell-detail?object={c}',
            'summary': f'/api/fet/cell/{c}/summary',
        })
    return {'ok': True, 'cells': rows,
            'note': ('the generic cell catalogue — open detailPage '
                     'for the general cell + its FET '
                     'configurations')}


# ---- the generic cell-detail page seed ------------------------------

def _generic_cell_page():
    o = '{object}'
    return {
        'name': 'cell-detail',
        'description': 'The generic CELL detail page — one definition '
                       'for every library cell. Open as /display/'
                       'cell-detail?object=<cell>: the GENERAL cell '
                       '(logic diagram with switch-level stepping, '
                       'transistor schematic, freedom proof — '
                       'device-independent) plus the FET-'
                       'CONFIGURATION selector (every FET it can be '
                       'built from; proven-free + characterized '
                       'pairings flagged as open-source samples).',
        'source_class': '',
        'isPage': True,
        'pageRoute': 'cell-detail',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [
            _row(0, [_component_item(
                f'cell-{o}-panel', 0, 12,
                f'{o}: general cell + FET configurations',
                'cell-detail-panel', {'cell': o})], min_height=560),
            _row(1, [
                _component_item(f'cell-{o}-logic', 0, 6,
                                f'{o}: boolean logic — click inputs / '
                                'step every vector (switch-level '
                                'simulation)', 'cell-logic-diagram',
                                {'cell': o, 'drive': 1}),
                _component_item(f'cell-{o}-schematic', 1, 6,
                                f'{o}: transistor schematic — '
                                'conducting path per vector',
                                'cell-schematic',
                                {'cell': o, 'drive': 1}),
            ], min_height=460),
            _row(2, [_component_item(
                f'cell-{o}-proof', 0, 12,
                f'{o}: is it free to use? — proof chain',
                'freedom-proof-panel',
                {'path': f'/api/fet/cell/{o}/proof'})],
                min_height=420),
            _row(3, [_sapi(f'cell-{o}-configs', 0, 12,
                           f'{o}: every FET configuration '
                           '(characterized / proof / open-source '
                           'sample)',
                           f'/api/fet/cell/{o}/summary',
                           pick='configurations')],
                 min_height=360),
        ]}),
    }


SEED_CELL_PAGES = [_generic_cell_page()]
