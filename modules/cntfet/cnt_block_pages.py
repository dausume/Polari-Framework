"""
@module cntfet.cnt_block_pages

The BLOCK level (Dustin 2026-08-31: "move up to the next level …
detail page and object structure for bringing things up from the FET
level to the cell level and the cell level to the next up") — the
microchip design ladder here is FET → CELL → **BLOCK** → core →
chip, and rank 3 already has real citizens (cnt_blocks: reg4 / ctr4 /
fsm-traffic / alu4, composed ONLY of library cells, proven
exhaustively).

Same shape as the cell arc, one level up:

  BlockFETConfiguration     the OBJECT: one row per block × FET. Its
                            summary's `composition` lists the
                            CellFETConfiguration rows it builds on —
                            the explicit level-up linkage (FET →
                            cellcfg → blockcfg), each entry with its
                            characterized state and page link.
  GET /api/fet/block/{key}/summary        block-summary/1 — the
                            GENERAL block: ports, cell composition,
                            transistor count, the device-independent
                            exhaustive proof, the configuration
                            index (a config is READY when every cell
                            beneath it is characterized — the
                            cells-advance sweep un-blanks blocks for
                            free).
  GET /api/fet/blockcfg/{key}/{device}/summary?timing=1
                            block-config-summary/1 — this block ON
                            this FET: OpenSTA timing over the
                            device's own Liberty, power roll-up,
                            provenance roll-up (worst of device +
                            every cell), and the composition table.
  GET /api/fet/blocks       the generic block catalogue.

Generic page seed `block-detail` (/display/block-detail?object=<key>)
with the `block-detail-panel` selector.

@consumers
  - cnt_api (routes above)
  - polariServer (class + SEED_BLOCK_CONFIGS + SEED_BLOCK_PAGES)
  - polari-platform-angular block-detail-panel
  - cntfet.selftest_block_pages
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_compare import _component_item
from cntfet.cnt_derive import get_row
from cntfet.cnt_pages_seed import _row, _sapi

BLOCK_SCHEMA = 'block-summary/1'
BLOCK_CONFIG_SCHEMA = 'block-config-summary/1'


class BlockFETConfiguration(treeObject):
    """One functional block × FET pairing as a ROW — 'this block
    built from this device's cells'. Numbers derive live (timing/
    power read the device's latest Liberty); readiness = every cell
    beneath it characterized."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',        # 'blockcfg-{block}-{device}'
        block: str = '',
        device: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.block = block
        self.device = device
        self.notes = notes


def block_config_name(block, device):
    return f'blockcfg-{block}-{device}'


def _device_names(manager):
    tables = getattr(manager, 'objectTables', None) or {}
    return sorted(
        (getattr(r, 'name', ''), cls)
        for cls in ('AlignedCNTFETDevice', 'SiliconMOSFET')
        for r in (tables.get(cls) or {}).values())


def seed_block_configs(device_names):
    from cntfet.cnt_blocks import BLOCK_LIBRARY
    return [{'name': block_config_name(b, d), 'block': b, 'device': d,
             'notes': 'the block-on-this-FET pairing as an object; '
                      'timing/power derive from the device\'s '
                      'latest Liberty'}
            for b in sorted(BLOCK_LIBRARY) for d in device_names]


def _composition(manager, block, device_name):
    """The level-up linkage: every cell this block is built from,
    with its CellFETConfiguration name, characterized state and
    page — FET → cellcfg → blockcfg, explicit."""
    from cntfet.cnt_blocks import block_cells
    from cntfet.cnt_cell_pages import config_name
    from cntfet.cnt_cell_coverage import device_cell_coverage
    cov = device_cell_coverage(manager, device_name)
    covered = {c['cell']: c.get('covered')
               for c in cov.get('cells', [])}
    rows = []
    for cell, count in block_cells(block).items():
        rows.append({
            'cell': cell, 'instances': count,
            'cellConfig': config_name(cell, device_name),
            'characterized': bool(covered.get(cell)),
            'page': f'/display/cell-detail?object={cell}'
                    f'&device={device_name}',
            'summaryPath': f'/api/fet/cellcfg/{cell}/{device_name}'
                           '/summary',
        })
    return rows


def block_summary(manager, block):
    """block-summary/1 — the GENERAL block + configuration index."""
    from cntfet.cnt_blocks import (
        BLOCK_LIBRARY, block_cells, block_fet_count, block_row,
        prove_block,
    )
    if block not in BLOCK_LIBRARY:
        return {'ok': False, 'schema': BLOCK_SCHEMA,
                'error': f'no functional block "{block}" '
                         f'({" | ".join(sorted(BLOCK_LIBRARY))})'}
    row = block_row(block)
    proof = prove_block(block)
    configs = []
    for device, cls in _device_names(manager):
        comp = _composition(manager, block, device)
        ready = all(c['characterized'] for c in comp)
        configs.append({
            'config': block_config_name(block, device),
            'device': device,
            'technology': 'silicon' if cls == 'SiliconMOSFET'
            else 'cnt',
            'cellsReady': ready,
            'missingCells': [c['cell'] for c in comp
                             if not c['characterized']],
            'summaryPath': f'/api/fet/blockcfg/{block}/{device}'
                           '/summary',
        })
    return {
        'ok': True, 'schema': BLOCK_SCHEMA, 'block': block,
        'identity': {
            'block': block,
            'display_name': row.get('display_name', block),
            'description': row.get('description', ''),
            'inputs': json.loads(row.get('inputs_json', '[]')),
            'outputs': json.loads(row.get('outputs_json', '[]')),
            'state_bits': row.get('state_bits', 0),
            'clock': row.get('clock', ''),
            'cells': block_cells(block),
            'cell_count': row.get('cell_count', 0),
            'fet_count': block_fet_count(block),
        },
        'proof': {'proven': bool(proof.get('proven',
                                           proof.get('ok'))),
                  'vectors': proof.get('vectors',
                                       proof.get('vectorCount')),
                  'note': 'exhaustive boolean/switch-level proof — '
                          'device-independent (the same netlist '
                          'every configuration characterizes)'},
        'configurations': configs,
        'ladder': ('FET → cell → BLOCK → core → chip; a '
                   'configuration is READY when every cell beneath '
                   'it is characterized (the cells-advance sweep '
                   'un-blanks blocks for free)'),
        'page': f'/display/block-detail?object={block}',
    }


def block_config_summary(manager, block, device_name,
                         with_timing=True):
    """block-config-summary/1 — this block ON this FET."""
    from cntfet.cnt_blocks import (
        BLOCK_LIBRARY, block_proof, block_report,
    )
    if block not in BLOCK_LIBRARY:
        return {'ok': False, 'schema': BLOCK_CONFIG_SCHEMA,
                'error': f'no functional block "{block}"'}
    device = (get_row(manager, 'AlignedCNTFETDevice', device_name)
              or get_row(manager, 'SiliconMOSFET', device_name))
    if device is None:
        return {'ok': False, 'schema': BLOCK_CONFIG_SCHEMA,
                'error': f'no device named "{device_name}"'}
    comp = _composition(manager, block, device_name)
    ready = all(c['characterized'] for c in comp)
    rep = block_report(manager, device_name, block,
                      with_timing=with_timing)
    proof = block_proof(manager, device_name, block)
    out = {
        'ok': True, 'schema': BLOCK_CONFIG_SCHEMA,
        'config': block_config_name(block, device_name),
        'block': block, 'device': device_name,
        'cellsReady': ready,
        'composition': comp,
        'timing': rep.get('timing'),
        'power': rep.get('power'),
        'proof': {'status': proof.get('status', 'unknown'),
                  'parts': proof.get('parts'),
                  'rule': 'worst over the device and every distinct '
                          'cell (cnt_blocks roll-up)'},
        'openSourceSample': (proof.get('status') == 'proven-free'
                             and ready),
        'verdict': rep.get('verdict', rep.get('row', {})
                           .get('verdict', '')),
        'acts': {
            'fillCells': ('POST {"device": "%s"} to '
                          '/api/fet/cells/advance — the first-step '
                          'service characterizes every missing cell'
                          % device_name) if not ready else '',
        },
        'note': ('timing/power read the device\'s latest Liberty; '
                 'refusals inside them are verbatim (e.g. '
                 'sequential timing refuses until the DFF row '
                 'exists)'),
    }
    return out


def blocks_catalogue(manager):
    from cntfet.cnt_blocks import (
        BLOCK_LIBRARY, block_cells, block_fet_count,
    )
    rows = []
    for b in sorted(BLOCK_LIBRARY):
        rows.append({
            'block': b,
            'cells': sum(block_cells(b).values()),
            'fets': block_fet_count(b),
            'detailPage': f'/display/block-detail?object={b}',
            'summary': f'/api/fet/block/{b}/summary',
        })
    return {'ok': True, 'blocks': rows,
            'note': ('the generic block catalogue — rank 3 of the '
                     'ladder (FET → cell → BLOCK → core → chip)')}


# ---- the generic block-detail page seed -----------------------------

def _generic_block_page():
    o = '{object}'
    return {
        'name': 'block-detail',
        'description': 'The generic BLOCK detail page — one '
                       'definition for every functional block (rank '
                       '3: FET → cell → BLOCK → core → chip). Open '
                       'as /display/block-detail?object=<key>: the '
                       'GENERAL block (ports, cell composition, '
                       'exhaustive proof) plus the FET-configuration '
                       'selector — OpenSTA timing over that '
                       'device\'s Liberty, power and provenance '
                       'roll-ups, and the composition table linking '
                       'DOWN to each CellFETConfiguration.',
        'source_class': '',
        'isPage': True,
        'pageRoute': 'block-detail',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [
            _row(0, [_component_item(
                f'block-{o}-panel', 0, 12,
                f'{o}: general block + FET configurations',
                'block-detail-panel', {'block': o})],
                min_height=560),
            _row(1, [_sapi(f'block-{o}-summary', 0, 12,
                           f'{o}: configurations (cells ready / '
                           'missing per FET)',
                           f'/api/fet/block/{o}/summary',
                           pick='configurations')],
                 min_height=320),
        ]}),
    }


SEED_BLOCK_PAGES = [_generic_block_page()]
