"""
@module materialsScience.crystal_analysis

Backend half of ssp-3: delegate symmetry detection and powder-XRD
simulation for a CrystalStructureDefinition to the msci-engines worker
(pymatgen), through the same engines/remote ladder every heavy engine
uses — honest refusal with the compose knob when no worker answers.

The knobs-and-suggestions closing move lives here: when the DETECTED
space group disagrees with the row's declared space_group, the report
carries an evidence-bearing suggestion (detected symbol/number +
tolerance) — never a silent rewrite of the row.

Successful analyses cache on the row's last_analysis_json (object
coherence: inspectable via CRUDE like any field).

@consumers
  - materialsScience.crystal_structure_api (/analyze, /xrd routes)
  - materialsScience.selftest_crystal_analysis
"""

import json
from datetime import datetime, timezone

from materialsScience import crystal_ops
from materialsScience.engines import remote


def structure_payload(row):
    """The built P1 cell as the worker wire format
    {'ok', 'payload': {cell, symbols, frac}} | refusal."""
    built = crystal_ops.build_atoms(row)
    if not built['ok']:
        return built
    atoms = built['atoms']
    scaled = atoms.get_scaled_positions(wrap=True)
    return {'ok': True, 'payload': {
        'cell': [[float(v) for v in vec] for vec in atoms.cell],
        'symbols': atoms.get_chemical_symbols(),
        'frac': [[round(float(v), 6) for v in pos]
                 for pos in scaled],
    }}


def _cache(row, manager, key, report):
    try:
        cache = json.loads(getattr(row, 'last_analysis_json', '{}')
                           or '{}')
    except Exception:
        cache = {}
    cache[key] = report
    cache['cachedAt'] = datetime.now(timezone.utc).isoformat(
        timespec='seconds')
    try:
        row.last_analysis_json = json.dumps(cache)
    except (AttributeError, TypeError):
        return
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(row)
        except Exception:
            pass


def analyze(row, manager=None, symprec=0.01):
    """Symmetry analysis via the worker. Adds the space-group
    agreement verdict (+ suggestion on disagreement)."""
    built = structure_payload(row)
    if not built['ok']:
        return built
    report = remote.remote_post('/structure/analyze',
                                dict(built['payload'],
                                     symprec=symprec))
    if not report.get('ok'):
        return report
    declared = int(getattr(row, 'space_group', 0) or 0)
    detected = int(report.get('spaceGroupNumber', 0) or 0)
    report['declaredSpaceGroup'] = declared
    report['agreesWithDeclared'] = (declared == detected
                                    or declared == 0)
    if declared and declared != detected:
        report['suggestion'] = {
            'evidence': f'pymatgen detects space group '
                        f"{report.get('spaceGroupSymbol')} "
                        f'(#{detected}) at symprec {symprec}, but '
                        f'the row declares #{declared}',
            'knob': 'space_group',
            'action': 'review the Wyckoff coordinates/origin '
                      'setting, or update the row to the detected '
                      'group — never applied automatically',
        }
    _cache(row, manager, 'symmetry', report)
    return report


def xrd(row, manager=None, wavelength='CuKa', two_theta_max=90.0,
        top_n=30):
    """Simulated powder XRD pattern via the worker — the
    bench-comparable prediction for this lattice."""
    built = structure_payload(row)
    if not built['ok']:
        return built
    report = remote.remote_post('/structure/xrd',
                                dict(built['payload'],
                                     wavelength=wavelength,
                                     twoThetaMax=two_theta_max,
                                     topN=top_n))
    if report.get('ok'):
        _cache(row, manager, 'xrd', report)
    return report
