"""
@module motors.contact_wear

mag-18: the three analyses the mag-17 roles NAMED as not-built —
CONTACT stress, WEAR, and EDDY DRAG at a stated buffer. Each role
pointed at one of these and said "not built"; this builds them, so
the roles stop being promises.

CONTACT (the `colliding` role). A gear tooth does not fail by
bending — the load lives in a contact patch microns across, and the
surface goes first. Hertz line contact between two cylinders whose
radii are the teeth's relative curvature at the pitch point
(r_pitch * sin(pressure_angle)):
    p_max = sqrt(F' E* / (pi R*))
and the number that matters for a BRITTLE tooth is not p_max — it
is the SURFACE TENSILE stress at the trailing edge of the contact,
because compression does not crack a ceramic but tension does. Both
are reported and the brittle verdict uses the tensile one.

WEAR (the `sliding` role). Archard: V = k F s / H. The wear
coefficient k spans SIX orders of magnitude across material pairs
and lubrication states, so a single k is not a prediction — this
reports a RANGE and says which end of it a dry cast-on-cast pair
sits at.

EDDY DRAG (the `field-buffered` role). A conductive part in a
changing field dissipates. For a part of thickness t at frequency f
in field B, the classical plate loss density is
    P/V = (pi t f B)^2 * sigma / 6
and the buffer enters through B: the stray field falls steeply with
distance from the gap, so a part 2.6 mm away sees far less than one
in it. The distance-decay used here is a stated 1/r^3 dipole
approximation and is labelled as such — it is the weakest link in
this module and the honest fix is the mag-fv field solve.

@consumers motors.motor_api, motors.selftest_motors
"""

import math

from magnetics.magnet_analysis import _named, _rows
from motors.motor_stress import _prop, failure_criterion

#: Archard wear coefficients (dimensionless) by pair character.
#: SIX orders of magnitude — which is why a single value would be
#: a lie and this module reports a band.
WEAR_K_BANDS = {
    'dry-brittle-on-brittle': (1e-3, 1e-2,
                               'cast ceramic on cast ceramic, dry: '
                               'the worst practical case — abrasive '
                               'third-body debris from the parts '
                               'themselves'),
    'dry-metal-on-metal': (1e-4, 1e-3, 'unlubricated steel/brass'),
    'lubricated-metal': (1e-7, 1e-6,
                         'oiled clock pivots — four orders better '
                         'than dry, and the reason clocks are oiled'),
    'self-lubricating': (1e-6, 1e-5, 'PTFE/graphite pair'),
}

VALIDITY = (
    'Analytic contact/wear/eddy estimates, not FEM: Hertz assumes '
    'smooth elastic non-conforming bodies (real cast teeth are '
    'ROUGH, and roughness raises local pressure far above these '
    'numbers), Archard assumes steady sliding with a constant wear '
    'coefficient, and the eddy estimate uses a classical thin-plate '
    'formula with a 1/r^3 dipole decay for the buffer. None is '
    'measured on our parts.')


def _elastic(manager, material):
    E, _ = _prop(manager, material, 'youngs_modulus_mpa')
    nu, _ = _prop(manager, material, 'poisson_ratio')
    if not E or nu is None:
        return None, None
    return float(E) * 1e6, float(nu)


def contact_stress(manager, design_name, part_name,
                   mating_material=None):
    """Hertz line contact at the gear mesh — and for a brittle
    tooth, the SURFACE TENSILE stress that actually cracks it."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition named '
                           f'"{part_name}"'}
    material = getattr(part, 'material_ref', '')
    E1, nu1 = _elastic(manager, material)
    if E1 is None:
        return {'ok': False,
                'refusal': f'"{material}" states no E/nu — contact '
                           f'pressure depends on stiffness, so this '
                           f'refuses rather than guessing'}
    mate = mating_material or material
    E2, nu2 = _elastic(manager, mate)
    if E2 is None:
        E2, nu2 = E1, nu1

    # The mesh this part drives: gear geometry + the load it carries.
    train = next((t for t in _rows(manager, 'GearTrainDefinition')
                  if getattr(t, 'motor_design_ref', '')
                  == design_name), None)
    if train is None:
        return {'ok': False,
                'refusal': 'no gear train references this design — '
                           'no mesh, so no contact'}
    tname = getattr(train, 'name', '')
    in_shaft = getattr(train, 'input_shaft', '')
    pinion = next((g for g in _rows(manager, 'GearDefinition')
                   if getattr(g, 'train_ref', '') == tname
                   and getattr(g, 'shaft_ref', '') == in_shaft),
                  None)
    if pinion is None:
        return {'ok': False, 'refusal': 'no input gear on the train'}
    mesh = next((m for m in _rows(manager, 'GearMeshDefinition')
                 if getattr(m, 'driving_gear_ref', '')
                 == getattr(pinion, 'name', '')), None)
    wheel = None
    if mesh is not None:
        wheel = next((g for g in _rows(manager, 'GearDefinition')
                      if getattr(g, 'name', '')
                      == getattr(mesh, 'driven_gear_ref', '')), None)

    mod = float(getattr(pinion, 'module_mm', 1.0)) / 1000.0
    n1 = float(getattr(pinion, 'teeth', 1))
    r1 = mod * n1 / 2.0
    alpha = math.radians(float(getattr(pinion, 'pressure_angle_deg',
                                       20.0)))
    face = float(getattr(pinion, 'face_width_mm', 1.0)) / 1000.0
    torque = float(getattr(train, 'input_torque_nm', 0.0) or 0.0)
    if r1 <= 0 or face <= 0 or torque <= 0:
        return {'ok': False,
                'refusal': 'pitch radius, face width or torque is '
                           'zero'}
    force = torque / r1

    # Relative curvature at the pitch point.
    rho1 = r1 * math.sin(alpha)
    if wheel is not None:
        r2 = (float(getattr(wheel, 'module_mm', 1.0)) / 1000.0
              * float(getattr(wheel, 'teeth', 1)) / 2.0)
        rho2 = r2 * math.sin(alpha)
        r_star = 1.0 / (1.0 / rho1 + 1.0 / rho2)
    else:
        r_star = rho1
    e_star = 1.0 / ((1 - nu1 ** 2) / E1 + (1 - nu2 ** 2) / E2)
    f_prime = force / face
    p_max = math.sqrt(f_prime * e_star / (math.pi * r_star))
    half_width = math.sqrt(4.0 * f_prime * r_star
                           / (math.pi * e_star))
    # Subsurface max shear ~0.30 p_max at ~0.78a depth (line
    # contact) — where a DUCTILE pair pits.
    tau_max = 0.30 * p_max
    # Surface tensile at the trailing edge of contact — where a
    # BRITTLE tooth cracks. Huber: ~ (1-2nu)/3 * p_max.
    sigma_t = max((1.0 - 2.0 * nu1) / 3.0, 0.0) * p_max

    crit = failure_criterion(manager, material)
    brittle = crit.get('failureClass') == 'brittle'
    if brittle:
        judged, against, why = (
            sigma_t, crit.get('tensileMpa'),
            'a brittle tooth cracks from the SURFACE TENSILE stress '
            'at the trailing edge of contact — the peak pressure is '
            'compressive and a ceramic is 10-20x stronger there, so '
            'judging by p_max would flatter it badly')
    else:
        judged, against, why = (
            tau_max, (crit.get('tensileMpa') or 0) * 0.5,
            'a ductile pair pits from SUBSURFACE SHEAR (~0.3 p_max '
            'at ~0.78a deep), judged against ~half the tensile '
            'yield')
    sf = ((against * 1e6) / judged) if (against and judged) else None

    return {
        'ok': True, 'design': design_name, 'part': part_name,
        'material': material, 'matingMaterial': mate,
        'toothForceN': force, 'faceWidthM': face,
        'relativeRadiusM': r_star, 'effectiveModulusPa': e_star,
        'contactHalfWidthM': half_width,
        'contactHalfWidthUm': round(half_width * 1e6, 3),
        'peakPressurePa': p_max,
        'peakPressureMpa': round(p_max / 1e6, 4),
        'subsurfaceShearMpa': round(tau_max / 1e6, 4),
        'surfaceTensileMpa': round(sigma_t / 1e6, 4),
        'judgedMpa': round(judged / 1e6, 4),
        'judgedAgainstMpa': against,
        'criterion': why,
        'safetyFactor': (round(sf, 2) if sf else None),
        'passes': bool(sf and sf >= 4.0),
        'note': f'the whole tooth load rides a contact patch '
                f'{round(half_width * 2e6, 2)} um wide — that '
                f'concentration is why hardness, not bulk strength, '
                f'is what the colliding role demands',
        'validity': VALIDITY,
    }


def wear_life(manager, part_name, sliding_distance_m,
              pair='dry-brittle-on-brittle', load_n=None,
              allowable_loss_mm=0.02):
    """Archard wear, as a BAND — because k spans six orders."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return {'ok': False, 'refusal': f'no part "{part_name}"'}
    material = getattr(part, 'material_ref', '')
    hv, prov = _prop(manager, material, 'hardness_hv')
    if not hv:
        return {'ok': False,
                'refusal': f'"{material}" states no hardness_hv — '
                           f'Archard divides by hardness, so there '
                           f'is no wear estimate without it'}
    band = WEAR_K_BANDS.get(pair)
    if band is None:
        return {'ok': False,
                'refusal': f'unknown pair "{pair}"',
                'suggestion': {'action': f'use one of '
                                         f'{sorted(WEAR_K_BANDS)}'}}
    k_lo, k_hi, band_note = band
    # HV -> Pa (1 HV ~ 9.807 MPa)
    h_pa = float(hv) * 9.807e6
    f = float(load_n if load_n is not None else 0.001)
    vols = [k * f * float(sliding_distance_m) / h_pa
            for k in (k_lo, k_hi)]
    return {
        'ok': True, 'part': part_name, 'material': material,
        'hardnessHv': hv, 'hardnessProvenance': prov,
        'pair': pair, 'kBand': [k_lo, k_hi], 'kNote': band_note,
        'loadN': f, 'slidingDistanceM': sliding_distance_m,
        'wornVolumeM3Band': vols,
        'wornVolumeMm3Band': [round(v * 1e9, 6) for v in vols],
        'allowableLossMm': allowable_loss_mm,
        'honesty': 'the wear coefficient spans SIX orders of '
                   'magnitude across pairs and lubrication states, '
                   'so this is a BAND and not a prediction. A '
                   'lubricated metal pair is ~1e-7 and a dry '
                   'cast-on-cast pair ~1e-2 — which is the whole '
                   'reason clock pivots are oiled.',
        'validity': VALIDITY,
    }


def eddy_drag(manager, part_name, b_gap_t, frequency_hz,
              thickness_m=None):
    """Eddy dissipation in a conductive part at its STATED buffer.

    This is what the field-buffered role promised: a conductive part
    is acceptable only where dB/dt is small, and 'small' has to be
    computed from the buffer the part row states."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return {'ok': False, 'refusal': f'no part "{part_name}"'}
    material = getattr(part, 'material_ref', '')
    sigma, prov = _prop(manager, material, 'sigma_s_m')
    if sigma is None:
        return {'ok': False,
                'refusal': f'"{material}" states no sigma_s_m — no '
                           f'conductivity, no eddy estimate'}
    buffer_mm = getattr(part, 'field_buffer_mm', None)
    if not buffer_mm:
        return {'ok': False,
                'refusal': f'"{part_name}" states no '
                           f'field_buffer_mm — the whole point of '
                           f'the field-buffered role is that the '
                           f'GEOMETRY must be stated; without it '
                           f'there is no buffer to evaluate',
                'suggestion': {
                    'knob': 'MotorPartDefinition.field_buffer_mm',
                    'action': 'state the distance from the working '
                              'gap'}}
    t = thickness_m or 1.0e-3
    # Stray field decay: dipole 1/r^3 from the gap, referenced to
    # 1 mm. A STATED approximation and the weak link here.
    r_mm = float(buffer_mm)
    decay = (1.0 / max(r_mm, 1.0)) ** 3
    b_local = float(b_gap_t) * decay
    p_per_v = ((math.pi * t * float(frequency_hz) * b_local) ** 2
               * float(sigma) / 6.0)
    return {
        'ok': True, 'part': part_name, 'material': material,
        'sigmaSm': sigma, 'sigmaProvenance': prov,
        'bufferMm': r_mm, 'bGapT': b_gap_t,
        'bLocalT': b_local, 'decayFactor': decay,
        'frequencyHz': frequency_hz, 'thicknessM': t,
        'lossDensityWPerM3': p_per_v,
        'lossDensityNote': 'classical thin-plate eddy loss '
                           'P/V = (pi t f B)^2 sigma / 6',
        'bufferHelps': (f'the {r_mm} mm buffer cuts the field to '
                        f'{decay:.4f}x of the gap value, and eddy '
                        f'loss goes as B SQUARED, so it cuts the '
                        f'loss to {decay ** 2:.2e}x — that '
                        f'square is why a buffer works at all'),
        'weakestLink': 'the 1/r^3 dipole decay is a STATED '
                       'approximation, not a field solve. The '
                       'honest upgrade is to read B at this point '
                       'from the mag-fv field views instead of '
                       'assuming a decay law.',
        'validity': VALIDITY,
    }
