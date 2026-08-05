"""
@cross-cutting
@module casting.pour_loading
@tags @xc:bindings

cast-2c (Dustin 2026-08-05): simulate PUTTING THE GEOPOLYMER IN —
the static structural gate that the mold survives being filled.
Four loadings, each computed and each gated:

  1. HYDROSTATIC wall pressure — fresh slurry is a liquid: peak
     P = ρ·g·h_cavity at the cavity floor, plus any applied
     injection pressure on top of it.
  2. WALL BENDING — the thinnest mold wall (the stock margin) as a
     uniformly-loaded simply-supported square plate:
     σ_max ≈ 0.287·P·(span/t)²  (ν=0.3 plate factor, peak pressure
     applied uniformly = conservative). Compared against the mold
     feedstock's strength floor × a NAMED flexural knockdown.
  3. MASS — slurry mass, total weight, base bearing stress on the
     footprint (the "effects of mass" ask).
  4. UPLIFT — injected molds push UP on the top face (classic
     foundry cope lift): required clamping force is computed, not
     assumed.

Plus the check no pressure model catches: geopolymer CURES
EXOTHERMICALLY INSIDE the mold. The measured pspp dataset
(k-pss-exotherm-vs-cure-temperature: cure 40→peak 70°C, 60→100,
85→115) is checked against the mold feedstock's softening point —
curing geopolymer in a wax mold heats the wax from the inside, and
a PLA mold (Tg 60) is ALREADY below the lowest measured peak.

Named unmodelled v1: pour-stream impact, sloshing, thermal
expansion mismatch, creep over the cure's hours at temperature
(wax creeps — named loudly), non-square wall panels, wall openings.

Duck-typed manager, stdlib. @see /WAX_MOLD_NESTING_PLAN.md (cast-5's
structural slice, pulled forward)
"""

import json

from casting.mold_geometry import _mold_named
from casting.wax_feasibility import _row_named, _rows
from mathshapes.shape_analysis import _named, _shape_bounds

_G = 9.80665

#: Fresh-mix densities for loading, CONSERVATIVE-HIGH (a heavier
#: slurry presses harder — the safe direction for this check).
#: Claim status travels; a measured mix density replaces the prior.
POUR_MATERIAL_PRIORS = {
    'geopolymer-slurry': {
        'density_kg_m3': 2200.0,
        'claim': 'literature-approximate CONSERVATIVE-HIGH fresh '
                 'geopolymer paste density — measure the real mix',
        'exothermic_cure': True},
    'water-test': {
        'density_kg_m3': 1000.0,
        'claim': 'exact — bench-test a mold with water before '
                 'risking a real mix',
        'exothermic_cure': False},
}
#: Flexural strength ≈ this fraction of the compressive floor for
#: brittle-ish waxes/polymers — a NAMED knockdown, not physics.
FLEXURAL_KNOCKDOWN = 0.5
#: Simply-supported square plate, uniform load, ν = 0.3.
PLATE_FACTOR = 0.287
#: The pspp measured exotherm points (cure °C → peak °C), from
#: dataset k-pss-exotherm-vs-cure-temperature (Perera & Trautman
#: lineage). Validity domain 40–85°C cure — outside it we refuse to
#: extrapolate rather than invent a curve.
EXOTHERM_MEASURED = ((40.0, 70.0), (60.0, 100.0), (85.0, 115.0))
EXOTHERM_SOURCE = ('pspp dataset k-pss-exotherm-vs-cure-temperature '
                   '(measured; validity 40-85°C cure)')


def _part_extents(manager, mold):
    """(lateral_span_cm, height_cm) of the CAVITY = the scaled part's
    AABB. Math-shape molds read the shape bounds; grid molds read the
    imported shape's stored bounds × the derivation scale."""
    scaled = getattr(mold, 'scaled_part_shape_name', '') or ''
    part_ref = scaled or getattr(mold, 'part_shape_ref', '')
    part = _named(manager, part_ref)
    s = 1.0
    if part is None or getattr(part, 'family', '') == 'imported-mesh':
        # grid path — bounds_json on the imported shape, scaled.
        if part is None:
            from casting.mold_geometry import _resolve_imported_shape
            part, _ = _resolve_imported_shape(
                manager, getattr(mold, 'part_shape_ref', ''))
        if part is None:
            return None
        try:
            deriv = json.loads(getattr(mold, 'derivation_json', '{}')
                               or '{}')
            s = float(deriv.get('scaleFactor', 1.0) or 1.0)
        except (TypeError, ValueError):
            s = 1.0
        try:
            b = json.loads(getattr(part, 'bounds_json', '') or 'null')
        except (TypeError, ValueError):
            b = None
        if not b:
            return None
        b = [[float(lo) * s, float(hi) * s] for lo, hi in b]
    else:
        b = _shape_bounds(manager, part)
        if b is None:
            return None
    span = max(b[0][1] - b[0][0], b[1][1] - b[1][0])
    height = b[2][1] - b[2][0]
    return {'spanCm': span, 'heightCm': height, 'bounds': b}


def _cavity_volume_cm3(manager, mold):
    try:
        deriv = json.loads(getattr(mold, 'derivation_json', '{}')
                           or '{}')
    except (TypeError, ValueError):
        deriv = {}
    v = deriv.get('partVolumeCm3')          # grid path
    if v:
        return float(v)
    vc = deriv.get('volumeCheck') or {}
    v = vc.get('cavityFormCm3')             # field path
    return float(v) if v else None


def exotherm_check(feed, cure_temp_c=None):
    """Cure exotherm peak vs the mold feedstock's softening point.
    With no cure temp given, the LOWEST measured peak (70°C at 40°C
    cure) is the most favorable case — if even that softens the
    mold, no measured cure schedule saves it."""
    soften = float(getattr(feed, 'soften_temp_c', 0.0) or 0.0)
    name = getattr(feed, 'name', '')
    if cure_temp_c is not None:
        lo, hi = EXOTHERM_MEASURED[0][0], EXOTHERM_MEASURED[-1][0]
        if not lo <= cure_temp_c <= hi:
            return {'ok': None,
                    'refusal': f'cure {cure_temp_c:.0f}°C is outside '
                               f'the measured {lo:.0f}–{hi:.0f}°C '
                               f'validity — refusing to extrapolate '
                               f'the exotherm',
                    'source': EXOTHERM_SOURCE}
        peak = None
        for (c0, p0), (c1, p1) in zip(EXOTHERM_MEASURED,
                                      EXOTHERM_MEASURED[1:]):
            if c0 <= cure_temp_c <= c1:
                f = (cure_temp_c - c0) / (c1 - c0)
                peak = p0 + f * (p1 - p0)
                break
        basis = f'interpolated at cure {cure_temp_c:.0f}°C'
    else:
        peak = EXOTHERM_MEASURED[0][1]
        basis = (f'LOWEST measured peak (cure '
                 f'{EXOTHERM_MEASURED[0][0]:.0f}°C) — the most '
                 f'favorable measured case')
    if soften <= 0.0:
        return {'ok': None, 'refusal': f"'{name}' declares no "
                                       f'soften_temp_c',
                'source': EXOTHERM_SOURCE}
    margin = soften - peak
    result = {'ok': margin > 0.0, 'peakC': round(peak, 1),
              'softenC': soften, 'marginC': round(margin, 1),
              'basis': basis, 'source': EXOTHERM_SOURCE}
    if margin <= 0.0:
        result['blocker'] = (
            f'geopolymer cure exotherm peaks at {peak:.0f}°C '
            f'({basis}) — at/above {name} softening {soften:.0f}°C: '
            f'the mold softens FROM THE INSIDE during cure')
    elif margin < 15.0:
        result['finding'] = (
            f'only {margin:.0f}°C between the cure exotherm peak '
            f'({peak:.0f}°C) and {name} softening ({soften:.0f}°C) — '
            f'thin; prefer a low-temperature cure and monitor')
    return result


def pour_loading_report(manager, mold_name, feedstock_name=None,
                        cast_material='geopolymer-slurry',
                        inject_pressure_kpa=0.0, cure_temp_c=None,
                        density_override_kg_m3=None):
    """Does the mold survive being FILLED? Hydrostatic + injection
    wall bending, slurry mass and base bearing, uplift/clamping for
    injected fills, and the cure-exotherm softening gate. Blockers
    decide; every number carries its model and claim."""
    mold = _mold_named(manager, mold_name)
    if mold is None:
        return {'ok': False,
                'error': f"no MoldDefinition named '{mold_name}'"}
    if (not getattr(mold, 'body_shape_name', '')
            and not getattr(mold, 'derivation_json', '')):
        return {'ok': False,
                'error': f"mold '{mold_name}' is underived — run "
                         f'derive_mold first'}
    prior = dict(POUR_MATERIAL_PRIORS.get(cast_material) or {})
    if not prior:
        return {'ok': False,
                'error': f"no pour prior for '{cast_material}' — "
                         f'absent data is absent',
                'knownMaterials': sorted(POUR_MATERIAL_PRIORS)}
    if feedstock_name:
        feed = _row_named(manager, 'MasterFeedstockDefinition',
                          feedstock_name)
    else:
        core = [f for f in _rows(manager, 'MasterFeedstockDefinition')
                if getattr(f, 'priority', '') == 'core']
        feed = core[0] if core else None
    if feed is None:
        return {'ok': False,
                'error': 'no mold feedstock resolvable — name one'}
    feed_name = getattr(feed, 'name', '')
    strength_mpa = float(getattr(feed, 'compressive_strength_mpa',
                                 0.0) or 0.0)
    if strength_mpa <= 0.0:
        return {'ok': False,
                'error': f"'{feed_name}' carries no strength floor — "
                         f'cannot gate wall bending'}

    ext = _part_extents(manager, mold)
    if ext is None:
        return {'ok': False,
                'error': 'cavity extents underivable (no part '
                         'bounds)'}
    try:
        wall_t_cm = float(getattr(mold, 'stock_margin_cm', 0.0)
                          or 0.0)
    except (TypeError, ValueError):
        wall_t_cm = 0.0
    if wall_t_cm <= 0.0:
        return {'ok': False,
                'error': 'stock_margin_cm not positive — no wall to '
                         'assess'}

    rho = float(density_override_kg_m3
                or prior['density_kg_m3'])
    blockers, gaps, findings = [], [], []

    # 1. peak pressure at the cavity floor
    h_m = ext['heightCm'] / 100.0
    p_hydro_kpa = rho * _G * h_m / 1000.0
    p_total_kpa = p_hydro_kpa + float(inject_pressure_kpa or 0.0)

    # 2. wall bending (plate model, peak pressure everywhere)
    ratio = ext['spanCm'] / wall_t_cm
    sigma_kpa = PLATE_FACTOR * p_total_kpa * ratio * ratio
    allow_kpa = strength_mpa * 1000.0 * FLEXURAL_KNOCKDOWN
    wall_util = sigma_kpa / allow_kpa if allow_kpa else 1.0
    if wall_util >= 1.0:
        blockers.append(
            f'wall bending {sigma_kpa:.0f} kPa exceeds the '
            f'{feed_name} flexural allowable {allow_kpa:.0f} kPa '
            f'(span {ext["spanCm"]:.1f}cm / t {wall_t_cm:.1f}cm) — '
            f'the mold collapses on filling; thicken '
            f'stock_margin_cm or lower injection pressure')
    elif wall_util > 0.5:
        findings.append(f'wall bending at {wall_util:.0%} of the '
                        f'allowable — thin margin for pour-stream '
                        f'impact (unmodelled)')

    # 3. mass + base bearing
    cavity_cm3 = _cavity_volume_cm3(manager, mold)
    mass_kg = (cavity_cm3 or 0.0) * rho / 1.0e6
    stock = _named(manager, getattr(mold, 'stock_shape_name', '')
                   or '')
    base_kpa = None
    try:
        size = json.loads(getattr(stock, 'parameters_json', '{}')
                          ).get('size') or []
        foot_m2 = (size[0] / 100.0) * (size[1] / 100.0)
        base_kpa = (mass_kg * _G / foot_m2) / 1000.0 if foot_m2 else None
    except (AttributeError, TypeError, ValueError, IndexError):
        gaps.append('stock footprint unreadable — base bearing '
                    'unassessed')
    if cavity_cm3 is None:
        gaps.append('cavity volume absent from derivation_json — '
                    'mass unassessed')

    # 4. uplift (injected fills push up on the top face)
    uplift = None
    if inject_pressure_kpa and ext['spanCm'] > 0:
        area_m2 = (ext['bounds'][0][1] - ext['bounds'][0][0]) / 100.0 \
            * (ext['bounds'][1][1] - ext['bounds'][1][0]) / 100.0
        force_n = float(inject_pressure_kpa) * 1000.0 * area_m2
        uplift = {'forceN': round(force_n, 1),
                  'note': 'required clamping ≥ this minus the top '
                          'half\'s own weight (foundry cope lift) — '
                          'an unclamped injected mold opens at the '
                          'parting line'}
        findings.append(f'injection needs ~{force_n:.0f} N clamping '
                        f'against uplift')

    # 5. the exotherm gate (the check pressure models miss)
    exo = None
    if prior.get('exothermic_cure'):
        exo = exotherm_check(feed, cure_temp_c=cure_temp_c)
        if exo.get('blocker'):
            blockers.append(exo['blocker'])
        if exo.get('finding'):
            findings.append(exo['finding'])
        if exo.get('refusal'):
            gaps.append(exo['refusal'])

    gaps.extend([
        'pour-stream impact + sloshing unmodelled (static loads '
        'only)',
        f'{feed_name} creep over the cure\'s hours at temperature '
        f'unmodelled — wax creeps; a long hot cure deserves a '
        f'measured test',
        'wall panels modelled as square simply-supported plates '
        f'(factor {PLATE_FACTOR}); real panels and openings differ'])

    verdict = 'blocked' if blockers else 'feasible'
    return {'ok': True, 'mold': mold_name, 'verdict': verdict,
            'moldFeedstock': feed_name, 'castMaterial': cast_material,
            'densityKgM3': rho, 'densityClaim': prior.get('claim'),
            'cavity': {'heightCm': round(ext['heightCm'], 2),
                       'lateralSpanCm': round(ext['spanCm'], 2),
                       'volumeCm3': cavity_cm3,
                       'massKg': round(mass_kg, 4)},
            'pressure': {'hydrostaticPeakKpa': round(p_hydro_kpa, 3),
                         'injectionKpa': float(inject_pressure_kpa
                                               or 0.0),
                         'totalKpa': round(p_total_kpa, 3)},
            'wallBending': {'spanOverThickness': round(ratio, 2),
                            'stressKpa': round(sigma_kpa, 2),
                            'allowableKpa': round(allow_kpa, 1),
                            'utilization': round(wall_util, 4),
                            'model': f'simply-supported square '
                                     f'plate, factor {PLATE_FACTOR}, '
                                     f'flexural = compressive × '
                                     f'{FLEXURAL_KNOCKDOWN} (named)'},
            'baseBearingKpa': (round(base_kpa, 3)
                               if base_kpa is not None else None),
            'uplift': uplift, 'exotherm': exo,
            'blockers': blockers, 'findings': findings, 'gaps': gaps,
            'note': 'static fill-survival gate: blockers decide. '
                    'Suggestion: bench-test with water-test first — '
                    'same loading shape at 45% of the pressure, '
                    'zero exotherm.'}
