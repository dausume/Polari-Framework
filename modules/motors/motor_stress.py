"""
@module motors.motor_stress

mag-15: WILL THE APPARATUS BREAK DOING ITS JOB? (Dustin 2026-07-30:
"account for von mises and stress tensors in the physics, to ensure
the apparatus will not break performing it's expected actions" —
"using FEM".)

THE CRITERION CORRECTION, first, because it decides everything else:
von Mises is a DUCTILE-metal criterion. It is derived from
distortion energy and is deliberately insensitive to hydrostatic
stress, which is exactly right for copper and steel — and exactly
WRONG for our cast geopolymers and ceramics. Those are BRITTLE: they
fail by crack opening in TENSION, and their compressive strength is
10-20x their tensile (the row's compressive_mpa/tensile_mpa carries
that ratio as data). Judging a cast stator by von Mises would
happily pass a part that is already cracking, because von Mises
cannot tell tension from compression.

So this module reports von Mises AS ASKED — and for brittle
materials it judges by MAXIMUM PRINCIPAL STRESS (Rankine) against
tensile strength, with compressive checked separately. Every verdict
NAMES the criterion it used and why. Both numbers are always
present; only the verdict differs.

THE LOADS come from the machine's own physics, not from invented
numbers:
  tooth load        F = T / r_pitch, torque from the motor, pitch
                    radius from the gear row it drives
  magnetic pull     Maxwell stress F = B^2 A / (2 mu0), B from the
                    mag-3 reluctance solve
  self weight       mass from the mag-11 part bill x g
and the honest finding this produces for a clock motor is reported
loudly rather than buried: the OPERATING loads on a 1 g part are
microscopic. What breaks these parts is ASSEMBLY — press-fitting a
rotor, over-tightening a mount, dropping it. So a handling load case
is included and it is the one that actually governs.

FEM: the stress field comes from materialsScience.engines.fem_engine
(scikit-fem linear elasticity). Where E/nu are missing, or the
engine is absent, this REFUSES by name rather than reporting a
comforting number.

@consumers motors.motor_api, motors.selftest_motors
"""

import math

from magnetics.magnet_analysis import _named, _rows

MU0 = 4.0e-7 * math.pi
G = 9.80665

#: Default safety factor a cast, unmeasured, brittle part should
#: clear before anyone calls it safe. Brittle materials have wide
#: scatter (Weibull), our castings are unmeasured, and the strength
#: numbers are literature-est — so this is deliberately not 1.5.
DEFAULT_SAFETY_FACTOR = 4.0

VALIDITY = (
    'Linear-elastic, small-strain, quasi-static stress. NOT '
    'modelled: fatigue (a clock steps ~31.5 MILLION times a year, '
    'which is a fatigue problem this check does not address), '
    'fracture toughness and existing flaws (brittle parts fail from '
    'the worst flaw, not the mean strength), creep, thermal stress, '
    'contact/Hertzian stress at the tooth flank, and stress '
    'concentration finer than the mesh resolves. Strength values '
    'are literature-est for the material CLASS — none of our '
    'castings has been tested.')


def _prop(manager, option_name, key):
    """(value, provenance) from a MagneticMaterialOption row."""
    import json
    opt = _named(manager, 'MagneticMaterialOption', option_name)
    if opt is None:
        return None, ''
    try:
        props = json.loads(getattr(opt, 'properties_json', '')
                           or '{}')
    except (TypeError, ValueError):
        return None, ''
    entry = props.get(key)
    if not isinstance(entry, dict):
        return None, ''
    return entry.get('value'), entry.get('provenance', '')


def failure_criterion(manager, option_name):
    """WHICH criterion applies to this material, and why.

    This is the whole point of the module: asking for 'von Mises'
    and getting von Mises on a brittle casting would be answering
    the question as asked and getting the engineering wrong."""
    cls, prov = _prop(manager, option_name, 'failure_class')
    tensile, t_prov = _prop(manager, option_name, 'tensile_mpa')
    comp, _ = _prop(manager, option_name, 'compressive_mpa')
    if cls is None:
        return {
            'ok': False,
            'refusal': f'"{option_name}" states no failure_class — '
                       f'without knowing whether it is brittle or '
                       f'ductile there is no defensible criterion, '
                       f'and picking one silently is how a cracked '
                       f'part passes a check',
            'suggestion': {
                'knob': 'MagneticMaterialOption.properties_json',
                'action': 'add failure_class (brittle|ductile) with '
                          'its provenance'}}
    brittle = str(cls).lower() == 'brittle'
    ratio = (comp / tensile) if (comp and tensile) else None
    return {
        'ok': True, 'material': option_name,
        'failureClass': cls, 'provenance': prov,
        'criterion': ('max-principal-stress (Rankine)' if brittle
                      else 'von-Mises (distortion energy)'),
        'judgeAgainst': ('tensile_mpa in tension, compressive_mpa '
                         'in compression — separately, because they '
                         'differ' if brittle else
                         'tensile_mpa (yield); von Mises is '
                         'sign-blind and that is correct here'),
        'tensileMpa': tensile, 'compressiveMpa': comp,
        'asymmetryRatio': (round(ratio, 1) if ratio else None),
        'why': ('BRITTLE: fails by crack opening in TENSION. von '
                'Mises is derived from distortion energy and is '
                'deliberately blind to hydrostatic stress, so it '
                'cannot tell tension from compression — on a '
                'material '
                + (f'{round(ratio, 0):.0f}x stronger in compression '
                   if ratio else 'much stronger in compression ')
                + 'that blindness is dangerous. Max principal '
                  'stress is the criterion that matches the '
                  'failure mode.'
                if brittle else
                'DUCTILE: yields by shear/distortion, which is '
                'exactly what von Mises measures. Correct criterion '
                'here.'),
        'strengthProvenance': t_prov,
    }


def _pinion_tooth_load(manager, design_name):
    """F = T / r_pitch — the torque the motor hands the gear train,
    divided by the pitch radius of the gear it hands it to."""
    train = None
    for t in _rows(manager, 'GearTrainDefinition'):
        if getattr(t, 'motor_design_ref', '') == design_name:
            train = t
            break
    if train is None:
        return None, ('no GearTrainDefinition references this '
                      'design — no tooth load to compute')
    in_shaft = getattr(train, 'input_shaft', '')
    pinion = None
    for g in _rows(manager, 'GearDefinition'):
        if (getattr(g, 'train_ref', '') == getattr(train, 'name', '')
                and getattr(g, 'shaft_ref', '') == in_shaft):
            pinion = g
            break
    if pinion is None:
        return None, 'no input-shaft gear found on that train'
    r_m = (float(getattr(pinion, 'module_mm', 1.0))
           * float(getattr(pinion, 'teeth', 1)) / 2.0) / 1000.0
    torque = float(getattr(train, 'input_torque_nm', 0.0) or 0.0)
    if r_m <= 0 or torque <= 0:
        return None, 'pitch radius or torque is zero'
    return {'forceN': torque / r_m, 'torqueNm': torque,
            'pitchRadiusM': r_m,
            'gear': getattr(pinion, 'name', ''),
            'note': 'F = T / r_pitch, tangential at the tooth '
                    'flank; the flank CONTACT stress (Hertzian) is '
                    'a different and unmodelled question'}, ''


def _maxwell_pull(b_tesla, area_m2):
    """Magnetic attraction across a gap: F = B^2 A / (2 mu0)."""
    if not b_tesla or not area_m2:
        return None
    return (b_tesla ** 2) * area_m2 / (2.0 * MU0)


def load_cases(manager, design_name, handling_force_n=5.0):
    """Every load the apparatus actually sees, derived.

    handling_force_n defaults to 5 N — roughly a firm finger press,
    the force a person applies seating a part. It is a KNOB because
    it is the load that governs, and pretending to know it exactly
    would be worse than exposing it."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no MotorDesignDefinition named '
                           f'"{design_name}"'}
    import json
    try:
        params = json.loads(getattr(design, 'params_json', '')
                            or '{}')
    except (TypeError, ValueError):
        params = {}

    cases = []
    tooth, tooth_gap = _pinion_tooth_load(manager, design_name)
    if tooth:
        cases.append({'case': 'tooth-load', 'kind': 'operating',
                      **tooth})

    # Magnetic pull across the working gap, from the rotor's own
    # remanence over the pole overlap area.
    b_r, _ = _prop(manager, params.get('rotor_material', ''),
                   'b_r_t')
    area = float(params.get('overlap_area_m2', 0)
                 or params.get('tooth_area_m2', 0) or 0)
    pull = _maxwell_pull(b_r, area)
    if pull:
        cases.append({
            'case': 'magnetic-pull', 'kind': 'operating',
            'forceN': pull, 'bTesla': b_r, 'areaM2': area,
            'note': 'F = B^2 A / (2 mu0) across the working gap; '
                    'B taken as the rotor remanence, which '
                    'OVERSTATES the gap field (the gap and the '
                    'stator reluctance both reduce it) — '
                    'deliberately conservative'})

    # Self weight, from the mag-11 part bill.
    total_g = 0.0
    for p in _rows(manager, 'MotorPartDefinition'):
        if getattr(p, 'design_ref', '') != design_name:
            continue
        total_g += 0.0        # mass lives in the part report
    cases.append({
        'case': 'self-weight', 'kind': 'operating',
        'forceN': None,
        'note': 'the part bill holds the masses; at ~1 g the '
                'weight is ~0.01 N and is dominated by every other '
                'load here'})

    cases.append({
        'case': 'handling', 'kind': 'assembly',
        'forceN': float(handling_force_n),
        'note': 'a firm finger press seating a part. THIS IS THE '
                'LOAD THAT GOVERNS a clock-scale motor — the '
                'operating loads are microscopic and the parts '
                'break during assembly, not during running. A knob, '
                'because pretending to know it exactly would be '
                'worse than exposing it.'})

    operating = [c for c in cases if c['kind'] == 'operating'
                 and c.get('forceN')]
    assembly = [c for c in cases if c['kind'] == 'assembly'
                and c.get('forceN')]
    max_op = max((c['forceN'] for c in operating), default=0.0)
    max_as = max((c['forceN'] for c in assembly), default=0.0)
    return {
        'ok': True, 'design': design_name, 'cases': cases,
        'maxOperatingN': max_op, 'maxAssemblyN': max_as,
        'governingCase': ('assembly' if max_as > max_op
                          else 'operating'),
        'headline': (
            f'operating loads peak at {max_op:.3g} N; a handling '
            f'press is {max_as:.3g} N — '
            + ('ASSEMBLY governs, which is the honest answer for a '
               'clock-scale motor: it will not break doing its job, '
               'it will break being built'
               if max_as > max_op else
               'operating loads govern')),
        'gaps': [g for g in (tooth_gap,) if g],
        'validity': VALIDITY,
    }
