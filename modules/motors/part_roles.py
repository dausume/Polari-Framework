"""
@module motors.part_roles

mag-17: ACTIVE MECHANICAL ROLES — what a part DOES decides what it
must survive (Dustin 2026-07-30: "different parts perform different
kinds of generic active roles ... almost all moving parts we need to
account for almost all kinds of stresses and fatigues ... a
colliding part like a gear that hits another gear would be another
role ... being a mechanical part in a magnetic motor you need to try
and not interact with the magnetic or electric fields").

This is mag-2r's role taxonomy extended from MAGNETIC roles to
ACTIVE MECHANICAL ones, and it closes a real hole the fatigue work
exposed: substitution_search ranked materials by fatigue alone and
happily proposed a COPPER pinion — which passes fatigue and would
then wear away, and which is conductive so it would drag eddy
currents through the very gap it sits in. Fatigue was the only
question being asked. It is not the only question.

THE MODEL: a part declares the roles it ACTIVELY performs. Each role
brings REQUIRED PROPERTIES and PREDICATES. A material is viable for
the part only if it satisfies the UNION of its roles — and a
property nobody has measured makes the answer UNASSESSED, never a
pass. Same discipline as mag-2r: viability is DERIVED, never
stamped.

THE ROLES, and why each exists:

  moving          it accelerates and reverses, so it sees the whole
                  stress catalogue AND fatigue — Dustin's point
                  that almost all moving parts need almost all of
                  it. Requires a fatigue class.
  colliding       tooth strikes tooth. This is CONTACT stress
                  (Hertzian), not bending: the load lives in a tiny
                  patch and the surface fails before the body does.
                  Requires hardness. Softness here is the copper
                  pinion's second disqualification.
  field-transparent  a mechanical part inside a magnetic machine
                  must NOT participate. High mu steals flux from
                  the working gap; high sigma carries EDDY CURRENTS
                  that both drag and heat. Requires LOW mu_r AND
                  LOW sigma — and copper fails on sigma by ~13
                  orders of magnitude.
  sliding         rubs against another surface: wear and friction,
                  not strength, decide its life.
  press-fitted    assembled by force — and mag-15 found assembly is
                  what governs a clock-scale part, so this role
                  carries the handling load explicitly.
  static-structural  holds position and takes load without moving:
                  the ONE role that does not need fatigue data.

@consumers motors.motor_api, motors.motor_fatigue,
           motors.selftest_motors
"""

from magnetics.magnet_analysis import _named, _rows
from motors.motor_stress import _prop

#: Roles are grouped by PHYSICAL DOMAIN (Dustin 2026-07-30:
#: "electrical and magnetic have different roles, mechanical also
#: have different roles, then we have intersectional roles like ones
#: specialized to be mechanical but buffered against and
#: non-magnetic").
#:
#: A domain is the physics a role answers to. An INTERSECTIONAL role
#: spans two, and it exists because the honest answer to some
#: questions is not a material property at all: brass fails a strict
#: field-inert test on conductivity, yet every real clock uses a
#: brass pinion — because the pinion sits OUTSIDE the working gap
#: where dB/dt is small. That is a GEOMETRY argument, and a
#: property-only screen cannot make it. So the buffered role exists,
#: and it DEMANDS the geometry be stated rather than assumed —
#: otherwise it is just a loophole for materials we like.
DOMAINS = ('mechanical', 'magnetic', 'electrical', 'thermal',
           'intersectional')

#: role -> what it demands. `checks` are (property, test, threshold,
#: why) and a MISSING property yields UNASSESSED, never a pass.
#: `requires_evidence` names a non-property fact the part row must
#: state — the anti-loophole on intersectional roles.
ROLE_REQUIREMENTS = {
    'moving': {
        'domain': 'mechanical',
        'summary': 'accelerates and reverses — sees every stress '
                   'mode AND fatigue',
        'checks': [
            ('fatigue_class', 'present', None,
             'a moving part is loaded millions of times; without a '
             'fatigue class there is no defensible life estimate'),
            ('tensile_mpa', 'present', None,
             'needs a strength to judge any stress against'),
        ],
        'analyses': ['part_stress', 'part_fatigue'],
    },
    'colliding': {
        'domain': 'mechanical',
        'summary': 'strikes another part (gear tooth on gear '
                   'tooth) — CONTACT stress, not bending',
        'checks': [
            ('hardness_hv', 'present', None,
             'contact load lives in a tiny patch: the SURFACE '
             'fails long before the body does, and hardness is '
             'what resists it'),
            ('hardness_hv', 'min', 100.0,
             'a soft face brinells and then wears; below ~100 HV a '
             'gear tooth does not hold its profile'),
        ],
        'analyses': ['contact-stress (NOT YET BUILT — Hertzian '
                     'contact is named as a gap, not silently '
                     'skipped)'],
    },
    'field-inert': {
        'domain': 'intersectional',
        'summary': 'a mechanical part inside a magnetic machine '
                   'that must NOT participate in the fields',
        'checks': [
            ('mu_r_eff', 'max', 1.2,
             'high permeability offers the flux a parallel path '
             'and steals it from the working gap'),
            ('sigma_s_m', 'max', 1.0e3,
             'a conductor moving in a changing field carries EDDY '
             'CURRENTS: drag on the rotor and heat in the part. '
             'Copper at 6e7 S/m fails this by ~5 orders of '
             'magnitude'),
        ],
        'analyses': ['eddy-current drag (NOT BUILT — named)'],
    },
    'field-buffered': {
        'domain': 'intersectional',
        'summary': 'MECHANICAL first, and field-isolated by '
                   'GEOMETRY rather than by material — the brass '
                   'pinion case',
        'checks': [
            ('mu_r_eff', 'max', 1.2,
             'still must not be FERROMAGNETIC: distance does not '
             'save you from a part that offers the flux a whole '
             'parallel path'),
        ],
        'requires_evidence': [
            ('field_buffer_mm',
             'how far this part sits from the working gap. A '
             'conductive part is only acceptable where dB/dt is '
             'small, and that is a GEOMETRY fact the part row must '
             'STATE — without it this role is a loophole, not an '
             'argument'),
        ],
        'analyses': ['eddy drag at the stated buffer (NOT BUILT — '
                     'named)'],
    },
    'flux-carrying': {
        'domain': 'magnetic',
        'summary': 'ACTIVELY carries flux — the opposite demand to '
                   'field-inert, and the same material can be '
                   'excellent here and disqualified there',
        'checks': [
            ('mu_r_eff', 'min', 100.0,
             'a flux path wants the HIGHEST permeability available; '
             'our mu~2 castings are three orders below the '
             'laminated steel a commercial movement uses'),
        ],
        'analyses': ['magnetic-netlist solve (mag-3)'],
    },
    'current-carrying': {
        'domain': 'electrical',
        'summary': 'carries the drive current',
        'checks': [
            ('sigma_s_m', 'min', 1.0e7,
             'conductivity decides how many amp-turns a given '
             'voltage buys; our ferrite-CNT conductor is ~5 orders '
             'short and cannot do this job'),
        ],
        'analyses': ['winding_report (mag-9)'],
    },
    'sliding': {
        'domain': 'mechanical',
        'summary': 'rubs against another surface — wear and '
                   'friction decide its life, not strength',
        'checks': [
            ('friction_coefficient', 'present', None,
             'without a friction pair value there is no wear or '
             'self-locking answer'),
        ],
        'analyses': ['wear rate (NOT BUILT — named)'],
    },
    'press-fitted': {
        'domain': 'mechanical',
        'summary': 'assembled by force — and assembly is what '
                   'governs a clock-scale part (mag-15)',
        'checks': [
            ('tensile_mpa', 'present', None,
             'the hoop stress of a press fit is tensile, which is '
             'exactly where brittle parts fail'),
        ],
        'analyses': ['part_stress (handling case)'],
    },
    'static-structural': {
        'domain': 'mechanical',
        'summary': 'holds position under load without moving',
        'checks': [
            ('tensile_mpa', 'present', None,
             'needs a strength'),
        ],
        'analyses': ['part_stress'],
    },
}

#: Which roles each seeded Lavet part actually performs. This is
#: the join that was missing: the pinion is not merely "a part", it
#: is moving AND colliding AND field-transparent AND press-fitted,
#: and it must satisfy all four.
PART_ROLE_ASSIGNMENTS = {
    'lavet-v2-stator': ['static-structural',
                        'flux-carrying'],
    'lavet-v2-rotor-magnet': ['moving', 'press-fitted'],
    # The pinion is mechanical FIRST and field-isolated by
    # GEOMETRY (it sits above the plate, clear of the gap) — the
    # intersectional case, and it must STATE its buffer.
    'lavet-v2-pinion': ['moving', 'colliding', 'field-buffered',
                        'press-fitted'],
    'lavet-v2-bobbin-flanges': ['static-structural',
                                'field-inert'],
    'lavet-v2-coil': ['static-structural',
                      'current-carrying'],
    'lavet-v2-leads': ['static-structural'],
}


def _check(value, test, threshold):
    if value is None:
        return 'unassessed'
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 'pass' if test == 'present' else 'unassessed'
    if test == 'present':
        return 'pass'
    if test == 'min':
        return 'pass' if v >= threshold else 'fail'
    if test == 'max':
        return 'pass' if v <= threshold else 'fail'
    return 'unassessed'


def role_viability(manager, material, roles, part_row=None):
    """Is this material viable for a part performing THESE roles?

    UNASSESSED is not a pass. A property nobody measured cannot
    clear a requirement, and saying otherwise is how a copper
    pinion gets recommended."""
    checks = []
    for role in roles:
        req = ROLE_REQUIREMENTS.get(role)
        if req is None:
            checks.append({'role': role, 'verdict': 'unknown-role',
                           'why': f'"{role}" is not a defined '
                                  f'active role'})
            continue
        for field, why in req.get('requires_evidence', ()):
            stated = getattr(part_row, field, None) if part_row \
                else None
            checks.append({
                'role': role, 'property': field,
                'test': 'stated-on-part', 'threshold': None,
                'value': stated, 'provenance': 'part row',
                'verdict': ('pass' if stated not in (None, '', 0)
                            else 'unassessed'),
                'why': why})
        for prop, test, thr, why in req['checks']:
            value, prov = _prop(manager, material, prop)
            verdict = _check(value, test, thr)
            checks.append({
                'role': role, 'property': prop, 'test': test,
                'threshold': thr, 'value': value,
                'provenance': prov, 'verdict': verdict,
                'why': why})
    fails = [c for c in checks if c.get('verdict') == 'fail']
    unassessed = [c for c in checks
                  if c.get('verdict') == 'unassessed']
    if fails:
        overall = 'unviable'
    elif unassessed:
        overall = 'unassessed'
    else:
        overall = 'viable'
    return {
        'ok': True, 'material': material, 'roles': list(roles),
        'verdict': overall, 'checks': checks,
        'failedOn': [f'{c["role"]}/{c["property"]}' for c in fails],
        'unassessedOn': [f'{c["role"]}/{c["property"]}'
                         for c in unassessed],
        'note': ('UNASSESSED is not a pass — a property nobody has '
                 'measured cannot clear a requirement'
                 if unassessed and not fails else
                 'every requirement of every role was tested'),
    }


def part_role_report(manager, part_name):
    """What this part DOES, what that demands, and whether its
    current material meets it."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition named '
                           f'"{part_name}"'}
    roles = PART_ROLE_ASSIGNMENTS.get(part_name)
    if roles is None:
        return {'ok': False,
                'refusal': f'"{part_name}" has no active roles '
                           f'assigned — what a part DOES is what '
                           f'decides what it must survive, so this '
                           f'refuses rather than assuming',
                'suggestion': {'knob': 'PART_ROLE_ASSIGNMENTS',
                               'action': 'declare its roles'}}
    material = getattr(part, 'material_ref', '')
    via = role_viability(manager, material, roles,
                         part_row=part)
    return {
        'ok': True, 'part': part_name, 'material': material,
        'roles': [{'role': r,
                   'domain': ROLE_REQUIREMENTS[r].get('domain', ''),
                   'summary': ROLE_REQUIREMENTS[r]['summary'],
                   'analyses': ROLE_REQUIREMENTS[r]['analyses']}
                  for r in roles if r in ROLE_REQUIREMENTS],
        'viability': via,
        'honesty': 'a part is judged against the UNION of its '
                   'roles. Ranking candidates on ONE axis (fatigue) '
                   'is what proposed a copper pinion: it passes '
                   'fatigue, then wears away as a tooth face and '
                   'drags eddy currents through the gap it sits '
                   'in.',
    }


def screen_candidates(manager, part_name, candidates=None):
    """Filter a material list by the part's ROLES — the missing
    gate on substitution_search."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition named '
                           f'"{part_name}"'}
    roles = PART_ROLE_ASSIGNMENTS.get(part_name, [])
    if not roles:
        return {'ok': False,
                'refusal': f'"{part_name}" has no active roles — '
                           f'nothing to screen against'}
    names = candidates or [getattr(o, 'name', '')
                           for o in _rows(manager,
                                          'MagneticMaterialOption')]
    out = []
    for n in names:
        v = role_viability(manager, n, roles, part_row=part)
        out.append({'material': n, 'verdict': v['verdict'],
                    'failedOn': v['failedOn'],
                    'unassessedOn': v['unassessedOn']})
    viable = [o for o in out if o['verdict'] == 'viable']
    return {
        'ok': True, 'part': part_name, 'roles': roles,
        'screened': out, 'count': len(out),
        'viable': [o['material'] for o in viable],
        'viableCount': len(viable),
        'note': 'run this BEFORE ranking by fatigue: a material '
                'that fails a role is not a candidate however good '
                'its fatigue number is.',
    }
