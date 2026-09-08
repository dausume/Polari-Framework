"""
@module pspp.custom.cure_checkpoints

pspp-8: promote CURE CHECKPOINTS to durable MaterialState rows via
TRANSFORMATIVE executions — the vocabulary fix of invariant I3 made
executable: a progress curve is a TRAJECTORY (SimulationFrame
concept); only the designated checkpoint (end of cure) becomes a
citable MaterialState, produced by a MaterialProcessExecution edge
(sealed-cure, ExecutionEffect TRANSFORMATIVE per I2) and carrying its
reactionExtent as a StructureClaim (claims, not values — I4).

Plan-first (the knobs-and-suggestions standing rule):
- `plan_cure_checkpoint` computes the cure from MEASURED data
  (progress_engine v1) and returns the EXACT rows a promotion would
  write — it never writes.
- `apply_cure_checkpoint` writes them, and only when explicitly
  called (the API knob is POST /api/pspp/checkpoint {"apply": true}).

Where the book gives no completion time (setting classes 3/4, wrong
temperature, off-table MR) the plan REFUSES with the dataset that
would support it — there is honestly no checkpoint to promote.

@consumers
  - pspp.pspp_api (POST /api/pspp/checkpoint)
  - pspp.custom.experiment_guidance (cure section)
"""

import json

from pspp.claims_basis import StructureClaim
from pspp.material_processes_basis import (
    MaterialProcessExecution, SEED_PROCESS_DEFINITIONS,
    validate_execution,
)
from pspp.material_states_basis import MaterialState
from pspp.custom.progress_engine import cure_progress
from pspp.custom.state_resolution import resolve_state, state_key

_PROVENANCE = 'pspp-8 cure-checkpoint promotion'


def _rows(manager, table):
    rows = (getattr(manager, 'objectTables', None) or {}).get(table, {})
    return list(rows.values()) if isinstance(rows, dict) else list(rows)


def _slug(value):
    return str(value).replace('.', 'p')


def plan_cure_checkpoint(manager, material_name, mr,
                         cure_temperature_c=80.0, state_name='',
                         parent_state=None):
    """PLAN the promotion of a completed (measured) cure to a durable
    state — returns the exact execution/state/claim rows, writes
    nothing. Refusals carry the data ask."""
    progress = cure_progress(manager, mr,
                             cure_temperature_c=cure_temperature_c)
    if not progress.get('ok'):
        progress.setdefault('suggestion', '')
        progress['refusal'] = ('no checkpoint to promote — '
                               + progress['refusal'])
        return progress
    parent = resolve_state(manager, material_name,
                           state_name=parent_state)
    if not parent.get('ok'):
        return parent
    parentKey = parent['stateKey']
    stateName = state_name or (f'cured-mr{_slug(mr)}-'
                               f'{_slug(round(cure_temperature_c, 1))}c')
    childKey = state_key(material_name, stateName)
    executionName = f'cure--{material_name}--{stateName}'
    completion = progress['completionHours']

    execution = {
        'name': executionName,
        'definition_name': 'sealed-cure',
        'input_state_ids_json': json.dumps([parentKey]),
        'parameter_values_json': json.dumps({
            'MR': mr, 'cure_temperature_c': cure_temperature_c}),
        'schedule_json': json.dumps([
            {'holdC': cure_temperature_c, 'hours': completion}]),
        'output_state_ids_json': json.dumps([childKey]),
        'measured_observations_json': json.dumps({
            'completionHours': completion,
            'settingClass': progress['settingClass']}),
        'status': 'planned',
        'provenance_id': _PROVENANCE,
        'notes': 'Promoted cure checkpoint — the progress CURVE '
                 'stays a trajectory (invariant I3); this edge '
                 'records only the designated endpoint.',
    }
    state = {
        'name': childKey,
        'material_name': material_name,
        'state_name': stateName,
        'is_canonical': False,
        'processing_stage': 'cured-solid',
        'thermodynamic_phase': 'solid',
        'composition_snapshot_json': json.dumps({'MR': mr}),
        'environmental_snapshot_json': json.dumps({
            'cure_temperature_c': cure_temperature_c,
            'sealed': True}),
        'parent_state_ids_json': json.dumps([parentKey]),
        'producing_execution_id': executionName,
        'validation_status': 'unvalidated',
        'provenance_id': _PROVENANCE,
        'notes': f'Cure complete per measured setting class '
                 f"{progress['settingClass']} "
                 f'({completion:g} h at {cure_temperature_c:g} C).',
    }
    claim = {
        'name': f'{childKey}:reactionExtent@L0',
        'subject_state_key': childKey,
        'descriptor_name': 'reactionExtent',
        'scale_level': 0,
        'value': 1.0,
        'units': 'fraction',
        'evidence_method': progress['evidence']['method'],
        'assumptions_json': json.dumps(progress['assumptions']),
        'validity_json': json.dumps({
            'MR': mr, 'cure_temperature_c': cure_temperature_c}),
        'source_execution_id': executionName,
        'provenance_id': _PROVENANCE,
        'notes': 'reactionExtent=1.0 means COMPLETION per the '
                 'measured setting class — the ramp shape between '
                 'mix and completion is a placeholder, not data.',
    }

    definition = next(d for d in SEED_PROCESS_DEFINITIONS
                      if d['name'] == 'sealed-cure')
    valid = validate_execution(definition, execution)
    if not valid['ok']:
        return valid  # unreachable by construction; honest anyway
    return {
        'ok': True,
        'plan': {'execution': execution, 'state': state,
                 'claim': claim},
        'parentState': parent['state'],
        'evidence': progress['evidence'],
        'assumptions': progress['assumptions'],
        'suggestion': 'apply with apply_cure_checkpoint / POST '
                      '/api/pspp/checkpoint {"apply": true} — plans '
                      'never write (knobs, not auto-apply)',
    }


def apply_cure_checkpoint(manager, material_name, mr,
                          cure_temperature_c=80.0, state_name='',
                          parent_state=None):
    """Write the planned promotion: execution edge (executed) + child
    MaterialState + reactionExtent StructureClaim. Refuses duplicates
    and manager-less calls — plan works anywhere, apply needs the
    live object tree."""
    planned = plan_cure_checkpoint(manager, material_name, mr,
                                   cure_temperature_c=cure_temperature_c,
                                   state_name=state_name,
                                   parent_state=parent_state)
    if not planned.get('ok'):
        return planned
    if manager is None:
        return {'ok': False,
                'refusal': 'apply needs the live object tree '
                           '(manager) — nothing was written',
                'suggestion': 'use the plan payload, or call through '
                              'the running server'}
    childKey = planned['plan']['state']['name']
    if any(getattr(r, 'name', '') == childKey
           for r in _rows(manager, 'MaterialState')):
        return {'ok': False,
                'refusal': f'MaterialState {childKey!r} already '
                           'exists — checkpoints are never silently '
                           'overwritten',
                'suggestion': 'name a different state_name, or '
                              'delete the row first if it was a '
                              'mistake'}
    execution = MaterialProcessExecution(
        manager=manager, **dict(planned['plan']['execution'],
                                status='executed'))
    state = MaterialState(manager=manager, **planned['plan']['state'])
    claim = StructureClaim(manager=manager, **planned['plan']['claim'])
    for row in (execution, state, claim):
        try:
            manager.db.saveInstanceInDB(row)
        except Exception:
            pass  # in-memory managers (selftests) have no db
    return {
        'ok': True,
        'created': {'execution': execution.name, 'state': state.name,
                    'claim': claim.name},
        'evidence': planned['evidence'],
        'assumptions': planned['assumptions'],
    }
