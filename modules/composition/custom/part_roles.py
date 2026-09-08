"""
@module composition.custom.part_roles

The ROLE VOCABULARY — extracted from motors.custom.part_roles (arch-2,
PART_ARCHETYPES_PLAN §3.3) because it was always domain-general:
roles span 5 domains, carry predicate checks whose missing data is
UNASSESSED (never a pass), graded thresholds (functional floor /
good target, penalty stated), and requires_evidence facts the part
row must state. The roles ARE the archetype's material-facing half.

Motor-specific pieces (PART_ROLE_ASSIGNMENTS, part_role_report,
screen_candidates over MotorPartDefinition) stayed in
motors.custom.part_roles, which re-exports these names so every existing
import keeps working. History and the full rationale per role:
see the original mag-17 docstring, preserved in motors.custom.part_roles.

@consumers motors.custom.part_roles (shim), motors.custom.local_route,
composition.archetype_basis, composition.composition_selftest
"""

from composition.custom.data_refs import material_prop


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
            ('b_r_t', 'max-if-stated', 0.01,
             'REMANENCE, not just permeability. A sintered ceramic '
             'magnet has mu_rec ~1.1 and would sail through a '
             'permeability-only check while being the most '
             'magnetically active object in the machine — it '
             'carries its own field and will pull on the rotor '
             'whatever its permeability says. A route search '
             'genuinely proposed a permanent magnet as the PINION '
             'through exactly this hole.'),
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
            ('b_r_t', 'max-if-stated', 0.01,
             'REMANENCE, not just permeability. A sintered ceramic '
             'magnet has mu_rec ~1.1 and would sail through a '
             'permeability-only check while being the most '
             'magnetically active object in the machine — it '
             'carries its own field and will pull on the rotor '
             'whatever its permeability says. A route search '
             'genuinely proposed a permanent magnet as the PINION '
             'through exactly this hole.'),
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
    'torque-magnet-active': {
        'domain': 'magnetic',
        'summary': 'IS the permanent magnet — it supplies the field '
                   'the machine works against',
        'checks': [
            ('b_r_t', 'min', 0.05,
             'remanence IS the torque; below ~0.05 T there is not '
             'enough field to step a rotor against any detent'),
            ('h_c_ka_m', 'min', 100.0,
             'coercivity is what stops the drive coil from '
             'demagnetising it — the mag-2r hard/soft split, and '
             'the reason a soft ferrite fails here outright'),
        ],
        'analyses': ['clock_sim (mag-5)', 'torque_parity'],
    },
    'flux-carrying': {
        'domain': 'magnetic',
        'summary': 'ACTIVELY carries flux — the opposite demand to '
                   'field-inert, and the same material can be '
                   'excellent here and disqualified there',
        # GRADED, not binary. An earlier pass demanded mu >= 100 and
        # thereby declared that no local material can build a
        # stator — which is false: the M0 clock sim demonstrably
        # STEPS at mu~2.2. The physics here is continuous, so the
        # role reports DEGREE. Below `functional` it genuinely does
        # not work; between functional and good it works with a
        # stated penalty; above good it is efficient.
        'checks': [
            ('mu_r_eff', 'min', 1.5,
             'below mu~1.5 the core offers no advantage over air '
             'and the machine does not step at all — this is the '
             'REAL disqualifier'),
        ],
        'graded': ('mu_r_eff', 1.5, 100.0,
                   'functional from mu 1.5; GOOD from mu 100. Our '
                   'castings sit at 2.2-2.5, so they work and cost '
                   'roughly 40x the current a laminated-steel '
                   'movement needs. That penalty is the honest '
                   'price of a local stator, not a reason to call '
                   'it unbuildable.'),
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

def _check(value, test, threshold):
    if value is None:
        # A DISQUALIFIER asks "does this material declare something
        # that rules it out?". Silence is not evidence of guilt: a
        # structural ceramic states no remanence because it is not
        # a magnet, and demanding the property would make every
        # honest non-magnet unassessable. Contrast 'max', which
        # asks a material to PROVE it stays under a limit.
        return 'not-applicable' if test == 'max-if-stated' \
            else 'unassessed'
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 'pass' if test == 'present' else 'unassessed'
    if test == 'present':
        return 'pass'
    if test == 'min':
        return 'pass' if v >= threshold else 'fail'
    if test in ('max', 'max-if-stated'):
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
            value, prov = material_prop(manager, material, prop)
            verdict = _check(value, test, thr)
            checks.append({
                'role': role, 'property': prop, 'test': test,
                'threshold': thr, 'value': value,
                'provenance': prov, 'verdict': verdict,
                'why': why})
    grades = []
    for role in roles:
        req = ROLE_REQUIREMENTS.get(role) or {}
        g = req.get('graded')
        if not g:
            continue
        prop, functional, good, why = g
        value, _ = material_prop(manager, material, prop)
        if value is None:
            continue
        v = float(value)
        grade = ('good' if v >= good else
                 'functional-with-penalty' if v >= functional
                 else 'below-functional')
        grades.append({'role': role, 'property': prop,
                       'value': v, 'functionalMin': functional,
                       'goodMin': good, 'grade': grade,
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
        'verdict': overall, 'checks': checks, 'grades': grades,
        'degraded': [g for g in grades
                     if g['grade'] == 'functional-with-penalty'],
        'failedOn': [f'{c["role"]}/{c["property"]}' for c in fails],
        'unassessedOn': [f'{c["role"]}/{c["property"]}'
                         for c in unassessed],
        'note': ('UNASSESSED is not a pass — a property nobody has '
                 'measured cannot clear a requirement'
                 if unassessed and not fails else
                 'every requirement of every role was tested'),
    }
