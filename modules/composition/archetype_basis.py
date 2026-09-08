"""
@module composition.archetype_basis

arch-5: PART ARCHETYPES — the machine-elements schema (practice map
§3: every Shigley chapter is one of these). An archetype joins the
two halves that already existed separately:

  role_refs       the MATERIAL-facing half (composition.custom.part_roles
                  — predicates, graded thresholds, evidence demands)
  equation_refs   the BEHAVIOUR-facing half (EquationDefinition
                  rows via motors.physics_equations_seed — DATA
                  references, reachable by name without importing)

plus its parameter set, its characteristic failure modes, its
selection procedure as ordered data, and its DESIGN MATRIX (which
knobs move which outcomes, and in what order to tune).

@consumers polariServer seed passes, composition.composition_seed,
composition.composition_selftest
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from composition.custom.data_refs import named, resolve_named
from composition.design_matrix_basis import matrix_report
from composition.custom.part_roles import ROLE_REQUIREMENTS

#: Which level of the hierarchy each equation speaks to — the
#: handover §2 levelling, carried per reference.
EQUATION_LEVELS = ('component', 'part', 'assembly', 'product')


class PartArchetypeDefinition(treeObject):
    """One recurring kind of part, with everything needed to size,
    select for, and distrust it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', summary='',
                 parameter_set_json='[]', equation_refs_json='[]',
                 failure_mode_refs_json='[]', role_refs_json='[]',
                 selection_procedure_json='[]', design_matrix_ref='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.summary = summary
        #: [{'name', 'unit', 'summary'}] — the knobs.
        self.parameter_set_json = parameter_set_json
        #: [{'name': EquationDefinition name, 'level':
        #:   EQUATION_LEVELS}] — behaviour half, by reference.
        self.equation_refs_json = equation_refs_json
        #: FailureModeDefinition names this archetype is prone to.
        self.failure_mode_refs_json = failure_mode_refs_json
        #: composition.custom.part_roles names — material half.
        self.role_refs_json = role_refs_json
        #: Ordered checks as data: [{'step', 'what', 'refuses_on'}].
        self.selection_procedure_json = selection_procedure_json
        self.design_matrix_ref = design_matrix_ref
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


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
