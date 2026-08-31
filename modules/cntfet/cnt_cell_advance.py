"""
@module cntfet.cnt_cell_advance

The cells-advance SERVICE (Dustin 2026-08-31: "a service that goes
through and takes all of the cells to the first step instead of them
starting as blank screens").

FIRST STEP = a real characterization every cell page can show:
  - combinational library at a COARSE corner grid (2 slews × 2 loads
    spanning the default grid's corners — ~4× cheaper than the full
    3×3; the grid is recorded on the run row, so a coarse first-step
    run is distinguishable from a full one) at the device's OWN Vdd;
  - the sequential DFF + latch (cnt_sequential — silicon works since
    the fg-4 standin-cap fix).

NEVER degrades: a device that already has ANY library run is SKIPPED
(the service fills blanks; deeper runs stay whatever they are), and
sequential steps run only where missing.

Surface:
  GET  /api/fet/cells/advance            the ladder report (dry run)
  POST /api/fet/cells/advance {"device"} advance ONE device (long —
       the engines worker does the SPICE for CNT devices); the sweep
       loop lives in polari-cli/shells/advance-cell-first-steps.sh.

@consumers
  - cnt_api (routes above)
  - polari-cli/shells/advance-cell-first-steps.sh (the sweep)
  - cntfet.selftest_cell_advance
"""

from cntfet.cnt_cells import PARASITIC_STANDIN_F
from cntfet.cnt_derive import get_row


def _devices(manager):
    tables = getattr(manager, 'objectTables', None) or {}
    return sorted(
        (getattr(r, 'name', ''), cls)
        for cls in ('AlignedCNTFETDevice', 'SiliconMOSFET')
        for r in (tables.get(cls) or {}).values())


def _coverage(manager, device_name):
    from cntfet.cnt_cell_coverage import device_cell_coverage
    cov = device_cell_coverage(manager, device_name)
    seq = {c['cell']: c.get('covered')
           for c in cov.get('cells', [])
           if c.get('cell') in ('cdff', 'clatch')}
    return cov.get('latestLibraryRun'), seq


def device_plan(manager, device_name):
    """The steps this device still needs to reach the first step."""
    device = (get_row(manager, 'AlignedCNTFETDevice', device_name)
              or get_row(manager, 'SiliconMOSFET', device_name))
    if device is None:
        return {'device': device_name, 'error': 'no such device'}
    steps = []
    if not getattr(device, 'derived_at', ''):
        steps.append('derive')
    run, seq = _coverage(manager, device_name)
    if not run:
        steps.append('characterize-library-coarse')
    if not seq.get('cdff'):
        steps.append('characterize-sequential')
    if not seq.get('clatch'):
        steps.append('characterize-latch')
    return {'device': device_name,
            'derived': bool(getattr(device, 'derived_at', '')),
            'libraryRun': run or '',
            'sequential': seq,
            'steps': steps,
            'done': not steps}


def advance_report(manager):
    """The whole grid's ladder position — what the sweep would do."""
    plans = [device_plan(manager, n) for n, _c in _devices(manager)]
    return {
        'ok': True, 'schema': 'cells-advance/1',
        'devices': plans,
        'blankDevices': [p['device'] for p in plans
                         if 'characterize-library-coarse'
                         in p.get('steps', [])],
        'done': all(p.get('done') for p in plans),
        'firstStep': ('coarse corner-grid library (2 slews × 2 '
                      'loads, recorded on the run row) + sequential '
                      'DFF/latch — a device with ANY library run is '
                      'never re-characterized by this service'),
    }


def _coarse_grid(manager, device, vdd):
    """The 2×2 corner grid of the default 3×3 (slews 2τ/32τ, loads
    Cin/4Cin) — same helpers characterize_cells uses."""
    from cntfet.cnt_cell_library import _pair_params, _tau_estimate
    p_n, _p_p, err = _pair_params(manager, device)
    if err:
        return None, None, err
    tau = _tau_estimate(p_n, vdd)
    cin = 2.0 * p_n['cinv_f_per_m'] * p_n['lg_m'] + PARASITIC_STANDIN_F
    return [2.0 * tau, 32.0 * tau], [cin, 4.0 * cin], None


def advance_device(manager, device_name, include_sequential=True,
                   cells=None, result_factory=None):
    """Take ONE device to the first step. Skips whatever already
    exists; every sub-report is returned verbatim (refusals
    included — nothing is retried into silence)."""
    device = (get_row(manager, 'AlignedCNTFETDevice', device_name)
              or get_row(manager, 'SiliconMOSFET', device_name))
    if device is None:
        return {'ok': False, 'error': f'no device "{device_name}"'}
    plan = device_plan(manager, device_name)
    out = {'ok': True, 'device': device_name, 'planned': plan['steps'],
           'library': None, 'sequential': None, 'latch': None}
    if 'derive' in plan['steps']:
        return {'ok': False, 'device': device_name,
                'error': 'device never derived — POST '
                         '{"action": "derive"} first (the sweep '
                         'script does)'}
    vdd = float(getattr(device, 'vdd_v', None) or 0.6)
    if 'characterize-library-coarse' in plan['steps']:
        from cntfet.cnt_cell_library import characterize_cells
        slews, loads, err = _coarse_grid(manager, device, vdd)
        if err:
            return {**err, 'device': device_name}
        rep = characterize_cells(
            manager, device, cells=cells, vdd=vdd,
            slews_s=slews, loads_f=loads,
            result_factory=result_factory)
        out['library'] = {k: rep.get(k) for k in
                         ('ok', 'error', 'refusal', 'failures')}
        out['library']['grid'] = '2×2 coarse corners (first step)'
        if not rep.get('ok'):
            out['ok'] = False
            return out
    else:
        out['library'] = {'skipped': True,
                          'why': f"library run exists "
                                 f"({plan['libraryRun']}) — the "
                                 'first-step service never '
                                 're-characterizes'}
    if include_sequential:
        from cntfet.cnt_sequential import (
            characterize_latch, characterize_sequential,
        )
        if 'characterize-sequential' in plan['steps']:
            rep = characterize_sequential(manager, device, vdd=vdd,
                                          result_factory=result_factory)
            out['sequential'] = {k: rep.get(k) for k in
                                 ('ok', 'error', 'refusal',
                                  'numericalAid')}
        else:
            out['sequential'] = {'skipped': True}
        if 'characterize-latch' in plan['steps']:
            rep = characterize_latch(manager, device, vdd=vdd,
                                     result_factory=result_factory)
            out['latch'] = {k: rep.get(k) for k in
                            ('ok', 'error', 'refusal',
                             'numericalAid')}
        else:
            out['latch'] = {'skipped': True}
    after = device_plan(manager, device_name)
    out['after'] = after
    out['ok'] = out['ok'] and not any(
        isinstance(v, dict) and v.get('ok') is False
        for v in (out['library'], out['sequential'], out['latch']))
    return out
