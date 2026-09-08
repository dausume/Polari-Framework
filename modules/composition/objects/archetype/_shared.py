"""@module composition.objects.archetype._shared — what the archetype row classes share (constants, seeds, helpers); split from archetype_basis.py (sap-2c)."""
from composition.custom.part_roles import ROLE_REQUIREMENTS
import json
from composition.design_matrix_basis import matrix_report
from composition.custom.data_refs import named, resolve_named

EQUATION_LEVELS = ('component', 'part', 'assembly', 'product')
def _loads(text, default):
    try:
        return json.loads(text or '')
    except (TypeError, ValueError):
        return default
def archetype_report(manager, archetype_name):
    """The whole archetype, cross-checked: unknown roles, missing
    failure modes and an unclassified matrix are named, not
    absorbed."""
    row, refusal = resolve_named(manager, 'PartArchetypeDefinition',
                                 archetype_name)
    if refusal:
        return {'ok': False, **refusal}
    roles = _loads(getattr(row, 'role_refs_json', ''), [])
    unknown_roles = [r for r in roles if r not in ROLE_REQUIREMENTS]
    modes = _loads(getattr(row, 'failure_mode_refs_json', ''), [])
    missing_modes = [f for f in modes
                     if named(manager, 'FailureModeDefinition', f)
                     is None]
    equations = _loads(getattr(row, 'equation_refs_json', ''), [])
    matrix_ref = getattr(row, 'design_matrix_ref', '')
    matrix = (matrix_report(manager, matrix_ref) if matrix_ref
              else {'ok': False,
                    'refusal': 'no design matrix — without the '
                               'knob→outcome structure the tuning '
                               'order is folklore'})
    problems = []
    if unknown_roles:
        problems.append(f'unknown roles: {unknown_roles}')
    if missing_modes:
        problems.append(f'failure modes not in catalogue: '
                        f'{missing_modes}')
    bad_levels = [e for e in equations
                  if e.get('level') not in EQUATION_LEVELS]
    if bad_levels:
        problems.append(f'equation refs with unknown level: '
                        f'{[e.get("name") for e in bad_levels]}')
    return {
        'ok': not problems, 'archetype': archetype_name,
        'summary': getattr(row, 'summary', ''),
        'parameters': _loads(getattr(row, 'parameter_set_json', ''),
                             []),
        'equationsByLevel': {
            level: [e['name'] for e in equations
                    if e.get('level') == level]
            for level in EQUATION_LEVELS
            if any(e.get('level') == level for e in equations)},
        'roles': [{'role': r,
                   'domain': ROLE_REQUIREMENTS[r]['domain'],
                   'summary': ROLE_REQUIREMENTS[r]['summary']}
                  for r in roles if r in ROLE_REQUIREMENTS],
        'failureModes': modes,
        'selectionProcedure': _loads(
            getattr(row, 'selection_procedure_json', ''), []),
        'designMatrix': matrix,
        'problems': problems,
        'note': 'the archetype is the join: roles screen the '
                'material, equations size the part, the matrix '
                'orders the tuning, and the failure modes say what '
                'to distrust.',
    }
