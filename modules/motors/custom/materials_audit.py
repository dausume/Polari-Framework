"""
@module motors.custom.materials_audit

mq-4 (Dustin 2026-08-01: "the calculations should be using the
real material (or those derived from material science simulation)
properties to perform and tune their part roles"): the ENGINE
NUMBER AUDIT, as a payload.

Every number the M1 engines compute with is traced to exactly one
of four sources, LIVE at request time:
- material-row: read from a MagneticMaterialOption property entry,
  with that entry's own provenance and note attached (measured,
  literature, or materials-science simulation — the entry says
  which; msci FEM homogenization counts as derived-real);
- design-row: a MotorDesignDefinition parameter (a design choice,
  tunable, not a physical claim);
- requirement-row: a PrinterAxisRequirement prior that already
  names the measurement retiring it (m1-5's discipline);
- named-prior: a constant in code, listed HERE with its value,
  why it exists, and what retires it. An unlisted constant is the
  failure mode this module exists to end.

The audit REFUSES to call itself clean if any material-row trace
fails to resolve — a missing property is a hole in the data, not
a pass. The output is an accountability report per engine, not a
code comment.

@consumers motors.motor_api (/api/motors/materials-audit),
selftest_m1
"""

import json

M1_DESIGN = 'reluctance-6s4p-m1'
PROV = 'mq-4'

#: Every in-code constant the M1 engines use, named with its
#: retirement. Adding a constant to an engine without adding it
#: here is caught by the selftest sweep.
NAMED_PRIORS = [
    {'engine': 'm1_sequencing', 'symbol': 'core_path_m',
     'value': 0.03,
     'why': 'lumped core flux-path length prior (0.02 stator + '
            '0.01 rotor), shared verbatim with torque_curve — '
            'two modules, one prior',
     'retirement': 'derive the mean flux path FROM the shape '
                   'equations (the yoke annulus + tooth + pole '
                   'quadrics carry the geometry now — an mq-5 '
                   'candidate), or measure L per phase (m1-7) '
                   'and back the path length out'},
    {'engine': 'm1_sequencing', 'symbol': 'SETTLE_GRID_DEG',
     'value': 0.25,
     'why': 'quasi-static settle resolution — numerical, not '
            'physical',
     'retirement': 'none needed: halving it must not change any '
                   'suite verdict (a convergence check, not a '
                   'measurement)'},
    {'engine': 'local_route/m1_sequencing', 'symbol':
     'DRIVE_MARGIN', 'value': 1.5,
     'why': 'design margin over the bisected threshold — a KNOB '
            'with a name, never buried in a formula',
     'retirement': 'stays a knob; the bench (m1-7) informs its '
                   'size, never replaces it'},
    {'engine': 'motor_designer/_phase_coenergy', 'symbol':
     'yoke_path_prior_m', 'value': 0.03,
     'why': 'the SAME 0.03 m core prior in the torque curve',
     'retirement': 'same as core_path_m — one fact, listed '
                   'twice because two engines carry it'},
    {'engine': 'm1_positioning', 'symbol': 'screw_relation',
     'value': 'T = F·L/(2π·η)',
     'why': 'the standard power-screw torque relation — physics, '
            'with the lossy η carried as its own requirement row',
     'retirement': 'measure torque-to-force on the real axis '
                   '(axis-drive-efficiency row already names it)'},
]

#: The design-row parameters the m1 engines read (an explicit
#: statement, so the audit can say which knobs are design choices
#: rather than physical claims).
DESIGN_PARAMS_USED = [
    'slots', 'poles', 'gap_base_m', 'tooth_area_m2',
    'coil_turns', 'coil_amps', 'saliency_ratio', 'wire_awg',
    'bobbin_window_mm2', 'mean_turn_length_mm',
]

#: (material slot in params_json, property, which engines use it)
MATERIAL_TRACES = [
    ('stator_material', 'mu_r_eff',
     'm1_sequencing geometry; torque_curve; axis duty verdicts'),
    ('rotor_material', 'mu_r_eff',
     'm1_sequencing geometry (rotor leg of the core path)'),
]


def materials_audit(manager, design_name=M1_DESIGN):
    from magnetics.custom.magnet_analysis import _named
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no design "{design_name}"'}
    try:
        params = json.loads(design.params_json)
    except (TypeError, ValueError):
        return {'ok': False, 'refusal': 'params_json unreadable'}
    entries, holes = [], []
    for slot, prop, used_by in MATERIAL_TRACES:
        mat = params.get(slot, '')
        opt = _named(manager, 'MagneticMaterialOption', mat)
        entry = None
        if opt is not None:
            try:
                entry = json.loads(getattr(opt, 'properties_json',
                                           '') or '{}').get(prop)
            except (TypeError, ValueError):
                entry = None
        if not isinstance(entry, dict) \
                or entry.get('value') is None:
            holes.append(f'{slot}={mat}: property "{prop}" does '
                         f'not resolve')
            entries.append({'source': 'material-row',
                            'slot': slot, 'material': mat,
                            'property': prop, 'ok': False,
                            'usedBy': used_by})
            continue
        entries.append({
            'source': 'material-row', 'slot': slot,
            'material': mat, 'property': prop,
            'value': entry.get('value'),
            'unit': entry.get('unit', ''),
            'provenance': entry.get('provenance', ''),
            'note': entry.get('note', ''),
            'realizationLevel': getattr(opt, 'realization_level',
                                        ''),
            'usedBy': used_by, 'ok': True})
    for key in DESIGN_PARAMS_USED:
        entries.append({'source': 'design-row', 'param': key,
                        'value': params.get(key),
                        'ok': key in params,
                        'note': 'a design CHOICE — tunable, not '
                                'a physical claim'})
        if key not in params:
            holes.append(f'design param "{key}" absent')
    req_rows = list(((getattr(manager, 'objectTables', None)
                      or {}).get('PrinterAxisRequirement', {})
                     or {}).values())
    for r in req_rows:
        entries.append({
            'source': 'requirement-row',
            'name': getattr(r, 'name', ''),
            'value': getattr(r, 'value', None),
            'unit': getattr(r, 'unit', ''),
            'basis': getattr(r, 'basis', ''),
            'retirement': getattr(r, 'replaces_with', ''),
            'ok': bool(getattr(r, 'replaces_with', ''))})
        if not getattr(r, 'replaces_with', ''):
            holes.append(f'requirement '
                         f'"{getattr(r, "name", "?")}" names no '
                         f'retiring measurement')
    for p in NAMED_PRIORS:
        entries.append({'source': 'named-prior', **p, 'ok': True})
    return {
        'ok': True, 'design': design_name,
        'entries': entries,
        'counts': {s: sum(1 for e in entries
                          if e['source'] == s)
                   for s in ('material-row', 'design-row',
                             'requirement-row', 'named-prior')},
        'holes': holes,
        'allTraced': not holes,
        'note': 'every engine number is a material-row value '
                '(with ITS provenance — measured, literature, or '
                'materials-science simulation), a design choice, '
                'a requirement prior with its retiring '
                'measurement, or a NAMED in-code prior listed '
                'with what retires it. A hole here is a hole in '
                'the data, said out loud.'}
