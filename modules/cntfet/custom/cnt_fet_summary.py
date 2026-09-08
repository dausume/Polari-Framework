"""
@module cntfet.custom.cnt_fet_summary

fg-0 (FET_GENERIC_PAGES_PLAN; Dustin 2026-08-30: "it should just be
fet, not cntfet — we want to dig into cntfets but we are not only
doing cntfets"): ONE stable summary payload every FET row answers,
CNT or Si, served at GET /api/fet/device/{name}/summary (the
/api/cntfet path stays as an alias of the same handler until the
fet-module split, plan fg-5).

Every section carries the SAME report its per-section endpoint
serves — the frontend needs no second mapping — and a section that
cannot answer carries its refusal INLINE ({'ok': False, 'refusal':
…}): the summary itself never 500s and its key set NEVER changes.
Schema tag: 'fet-summary/1'.

@consumers
  - cntfet.cnt_api (GET /api/fet/device/{name}/summary + fet_alias)
  - polari-platform-angular fet-overview (one fetch instead of 11)
  - cntfet.summary_selftest
"""

from cntfet.custom.cnt_derive import get_row

SCHEMA = 'fet-summary/1'

#: The stable top-level key set (selftests + the frontend rely on it).
SUMMARY_KEYS = (
    'ok', 'schema', 'device', 'identity',
    'figures', 'validity', 'parts', 'taxonomy', 'power', 'speed',
    'proof', 'links', 'coverage', 'compare', 'transport', 'signal',
    'characterization', 'curves', 'note',
)

#: Only the DEVICE-SCOPED generic surfaces alias under /api/fet —
#: the CNT catalogue/acts stay cntfet and the silicon catalogue
#: stays sifet until the fet-module split (fg-5).
_GENERIC_PREFIX = '/api/cntfet/device/'
_FET_PREFIX = '/api/fet/device/'


def fet_alias(path):
    """The /api/fet route a cntfet route also answers at, or None
    for a route that is NOT part of the generic contract. Generic =
    the per-device surfaces AND the cell surfaces (cells are
    technology-agnostic — the cell arc pages ride /api/fet)."""
    for prefix in (_GENERIC_PREFIX, '/api/cntfet/cell/',
                   '/api/cntfet/cells/'):
        if path.startswith(prefix):
            return '/api/fet/' + path[len('/api/cntfet/'):]
    return None


def _section(build):
    """Run one section builder; any failure becomes an inline
    refusal — the summary never 500s and never drops a key."""
    try:
        rep = build()
    except Exception as exc:            # noqa: BLE001 — inline, stated
        return {'ok': False,
                'refusal': f'{type(exc).__name__}: {exc}'}
    if not isinstance(rep, dict):
        return {'ok': False, 'refusal': 'section produced no report'}
    if not rep.get('ok', True) and 'refusal' not in rep:
        return {**rep, 'refusal': rep.get('error', 'refused')}
    return rep


def fet_summary(manager, name):
    """The fet-summary/1 payload for one FET row (CNT or Si)."""
    device = (get_row(manager, 'AlignedCNTFETDevice', name)
              or get_row(manager, 'SiliconMOSFET', name))
    if device is None:
        return {'ok': False, 'schema': SCHEMA,
                'error': f'no device named "{name}"'}

    from cntfet.cnt_device_viz_seed import device_vdd
    vdd = device_vdd(device)

    def _figures():
        from cntfet.cnt_scoring_seed import score_device
        return score_device(manager, name)

    def _parts():
        from cntfet.custom.cnt_parts import device_parts
        return device_parts(manager, device)

    def _taxonomy():
        from cntfet.cnt_taxonomy_basis import device_taxonomy_report
        return device_taxonomy_report(manager, name)

    def _power():
        from cntfet.cnt_power_basis import budget_report
        return budget_report(manager, name)

    def _speed():
        from cntfet.custom.cnt_fo4 import fo4_report
        return fo4_report(manager, name)

    def _proof():
        from cntfet.cnt_evidence_basis import freedom_proof
        return freedom_proof(manager, 'device', name)

    def _links():
        from cntfet.custom.cnt_links import device_links
        return device_links(manager, device)

    def _coverage():
        from cntfet.custom.cnt_cell_coverage import device_cell_coverage
        return device_cell_coverage(manager, name)

    def _compare():
        from cntfet.custom.cnt_compare import compare_devices
        return compare_devices(manager, name)

    def _transport():
        from cntfet.cnt_device_viz_seed import device_model
        from cntfet.cnt_transport_basis import transport_report
        id_fn, p, dev, refusal = device_model(manager, name)
        if refusal is not None:
            return refusal
        # device-relative rule: Vg = Vd = the device's OWN Vdd
        return transport_report(manager, dev, p, vgs=vdd, vds=vdd)

    def _signal():
        from cntfet.cnt_taxonomy_basis import score_signal
        return score_signal(manager, name)

    def _characterization():
        from cntfet.cnt_device_viz_seed import device_characterization
        return device_characterization(manager, name)

    def _curves():
        from cntfet.cnt_device_viz_seed import CURVES, extra_curve_builders
        return {'ok': True,
                'names': list(CURVES) + sorted(extra_curve_builders()),
                'pointsPath': f'{_FET_PREFIX}{name}/points?curve='}

    sections = {
        'figures': _section(_figures),
        'parts': _section(_parts),
        'taxonomy': _section(_taxonomy),
        'power': _section(_power),
        'speed': _section(_speed),
        'proof': _section(_proof),
        'links': _section(_links),
        'coverage': _section(_coverage),
        'compare': _section(_compare),
        'transport': _section(_transport),
        'signal': _section(_signal),
        'characterization': _section(_characterization),
        'curves': _section(_curves),
    }

    # validity rides the score report; surfaced top-level so a page
    # never digs for the score-0 explanation.
    fig = sections['figures']
    validity = fig.get('validity')
    sections['validity'] = (
        validity if isinstance(validity, dict)
        else {'ok': False,
              'refusal': fig.get('refusal', 'score refused — no '
                                            'validity frame')})

    # identity: who this FET is — from its own row + the sections.
    def _mapping():
        from cntfet.cnt_targets_basis import mapping_for
        return mapping_for(manager, name)
    mapping = _section(_mapping)
    tax = sections['taxonomy']
    shape = ''
    if tax.get('ok', True):
        s = tax.get('shape') or {}
        shape = ((s.get('row') or {}).get('display_name')
                 or s.get('shape') or s.get('name') or '')
    cov = sections['coverage']
    run = cov.get('latestLibraryRun') if isinstance(cov, dict) else None
    identity = {
        'name': name,
        'technology': ('silicon'
                       if get_row(manager, 'SiliconMOSFET', name)
                       is not None else 'cnt'),
        'polarity': getattr(device, 'polarity', ''),
        'shape': shape,
        'vdd_v': vdd,
        'temperature_k': getattr(device, 'temperature_k', None),
        'derived': bool(getattr(device, 'derived_at', '')),
        'targets': mapping.get('targets', []),
        'engineered_for': mapping.get('engineered_for', ''),
        'mapped': bool(mapping.get('mapped')),
        # the microchip-ladder CELL rung as this device sees it
        'cellRung': ('characterized' if run else
                     'unbuilt — no cell-library run for this device '
                     'yet (POST {"action": "characterize-cells"})'),
        'libraryRun': run or '',
    }

    return {
        'ok': True, 'schema': SCHEMA, 'device': name,
        'identity': identity, **sections,
        'note': ('every section is the same report its own endpoint '
                 'serves; a section that cannot answer carries its '
                 'refusal inline — the key set never changes'),
    }


def fet_catalogue(manager):
    """fg-2: the GENERIC FET catalogue — every FET row, both
    technologies, each with its generic-page and summary paths.
    (The per-technology catalogues stay at /api/cntfet/devices and
    /api/sifet/devices until the fet-module split, fg-5.)"""
    from cntfet.cnt_device_viz_seed import device_vdd
    tables = getattr(manager, 'objectTables', None) or {}
    devices = []
    for cls, tech in (('AlignedCNTFETDevice', 'cnt'),
                      ('SiliconMOSFET', 'silicon')):
        for r in (tables.get(cls) or {}).values():
            n = getattr(r, 'name', '')
            devices.append({
                'device': n, 'technology': tech,
                'polarity': getattr(r, 'polarity', ''),
                'shape': getattr(r, 'shape', ''),
                'vdd_v': device_vdd(r),
                'derived': bool(getattr(r, 'derived_at', '')),
                'scorePage': f'/display/fet?object={n}',
                'detailPage': f'/display/fet-detail?object={n}',
                'summary': f'{_FET_PREFIX}{n}/summary',
            })
    devices.sort(key=lambda d: (d['technology'], d['device']))
    return {'ok': True, 'devices': devices,
            'note': ('the generic FET catalogue — open scorePage / '
                     'detailPage (?object= pages), or GET summary '
                     'for the whole FET in one payload')}
