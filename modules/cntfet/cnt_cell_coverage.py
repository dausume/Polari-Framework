"""
@module cntfet.cnt_cell_coverage

Cells wrap-up (Dustin 2026-08-29): "make sure the FETs plug into the
cells properly to give data." The plug is a CHARACTERIZATION RUN: a
cell has numbers only through a FET row (delay / transition / energy
from ngspice over that device's card; leakage from that device's
Ioff; scores against that device's intrinsic τ). This module makes
the plug VISIBLE per device: which runs exist, which cells each run
covers, which are missing (combinational, sequential setup/hold,
tri-state), and what to POST to fill the gap — never an implied
"characterized".

@consumers cnt_api (GET /api/cntfet/cells/coverage,
  /api/cntfet/device/{name}/cell-coverage), cnt_links, pages
"""

from cntfet.cnt_cell_library import (
    CELL_LIBRARY, COMBINATIONAL, liberty_cell_name,
)

DISCLAIMER = ('coverage = which cell numbers on this node trace to a '
              'characterization run on THIS device; a cell without a '
              'run has no timing/energy numbers here (its circuit '
              'proof and provenance stand regardless)')


def _runs(manager, device_name):
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        'CellCharacterizationRun') or {}
    rows = [r for r in (table.values() if isinstance(table, dict)
                        else table)
            if getattr(r, 'device', '') == device_name]
    return sorted(rows, key=lambda r: getattr(r, 'ran_at', ''))


def _liberty_cells(text):
    import re
    return set(re.findall(r'\n  cell \((\w+)\) \{', text or ''))


def _sequential_keys():
    try:
        from cntfet.cnt_cell_library import SEQUENTIAL_CELLS
        return list(SEQUENTIAL_CELLS)
    except ImportError:
        return ['cdff']


def _tristate_keys():
    try:
        from cntfet.cnt_cell_library import TRISTATE
        return list(TRISTATE)
    except ImportError:
        return []


def device_cell_coverage(manager, device_name):
    """Per device: the latest library run + every sequential run, the
    cells each covers, the missing ones, and the affordance to fill
    each gap."""
    runs = _runs(manager, device_name)
    library = [r for r in runs
               if str(getattr(r, 'cell', '')).startswith('library:')
               and getattr(r, 'liberty_text', '')]
    latest = library[-1] if library else None
    covered_lib = _liberty_cells(getattr(latest, 'liberty_text', '')) \
        if latest else set()
    seq_runs = {}
    # sequential runs label their cell by LIBERTY name (DFFX1 /
    # DLATCHX1) — map back to the cell keys
    seq_alias = {'DFFX1': 'cdff', 'DLATCHX1': 'clatch',
                 'cdff': 'cdff', 'clatch': 'clatch'}
    for r in runs:
        cell = seq_alias.get(str(getattr(r, 'cell', '')))
        if cell:
            seq_runs[cell] = getattr(r, 'name', '')
    cells = []
    entries = list(CELL_LIBRARY.items()) + [('cdff', {'sequential': True})]
    for key, cell in entries:
        lib_name = liberty_cell_name(key, 1)
        kind = ('sequential' if key in _sequential_keys() or key == 'cdff'
                else 'tri-state' if key in _tristate_keys()
                else 'combinational')
        if kind == 'sequential':
            has = key in seq_runs
            how = ('{"action": "characterize-sequential"}'
                   if key == 'cdff' else '{"action": "characterize-latch"}')
        else:
            has = lib_name in covered_lib
            how = '{"action": "characterize-cells"}'
        cells.append({
            'cell': key, 'libertyName': lib_name, 'kind': kind,
            'covered': has,
            'run': (seq_runs.get(key) if kind == 'sequential'
                    else (getattr(latest, 'name', '') if has else '')),
            'fill': ('' if has else
                     f'POST {how} to /api/cntfet/devices/{device_name}'),
            'dataPaths': ({
                'scores': f'/api/cntfet/device/{device_name}/cell-scores',
                'power': f'/api/cntfet/device/{device_name}/cell-power',
                'logic': f'/api/cntfet/cell/{key}/logic',
                'proof': f'/api/cntfet/cell/{key}/proof'} if has else
                {'logic': f'/api/cntfet/cell/{key}/logic',
                 'proof': f'/api/cntfet/cell/{key}/proof'}),
        })
    covered = [c for c in cells if c['covered']]
    missing = [c for c in cells if not c['covered']]
    return {
        'ok': True, 'device': device_name,
        'latestLibraryRun': getattr(latest, 'name', '') if latest else '',
        'libraryRuns': [getattr(r, 'name', '') for r in library],
        'sequentialRuns': seq_runs,
        'cellsTotal': len(cells), 'covered': len(covered),
        'missing': len(missing),
        'coverageFraction': round(len(covered) / max(len(cells), 1), 3),
        'cells': cells,
        'missingByKind': {
            k: [c['cell'] for c in missing if c['kind'] == k]
            for k in ('combinational', 'sequential', 'tri-state')},
        'plug': ('cell numbers = ngspice over THIS device\'s VS card '
                 '(pair-aware p side), leakage from THIS device\'s Ioff, '
                 'scores vs THIS device\'s intrinsic τ — nothing is '
                 'inherited from another FET'),
        'disclaimer': DISCLAIMER,
    }


def cells_coverage(manager):
    """The cells × FETs matrix: every device (CNT + Si) with its
    coverage, sorted most-covered first."""
    tables = getattr(manager, 'objectTables', {}) or {}
    names = sorted(
        getattr(r, 'name', '')
        for cls in ('AlignedCNTFETDevice', 'SiliconMOSFET')
        for r in (tables.get(cls) or {}).values())
    per = [device_cell_coverage(manager, n) for n in names]
    per.sort(key=lambda d: (-d['coverageFraction'], d['device']))
    return {
        'ok': True,
        'devices': [{k: d[k] for k in (
            'device', 'latestLibraryRun', 'covered', 'missing',
            'cellsTotal', 'coverageFraction', 'missingByKind',
            'sequentialRuns')} for d in per],
        'cells': list(CELL_LIBRARY),
        'combinational': list(COMBINATIONAL),
        'sequential': _sequential_keys(), 'tristate': _tristate_keys(),
        'fullyCovered': [d['device'] for d in per if d['missing'] == 0],
        'uncharacterized': [d['device'] for d in per if d['covered'] == 0],
        'disclaimer': DISCLAIMER,
    }
