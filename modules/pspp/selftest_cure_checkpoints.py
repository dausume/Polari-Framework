"""
Self-test for pspp-8 cure-checkpoint promotion: plan-first rows,
TRANSFORMATIVE execution + child state + reactionExtent claim,
honest refusals (unmeasured cures, unknown materials, duplicates),
and apply writing exactly the planned rows.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_cure_checkpoints
"""

import json
import sys
from types import SimpleNamespace

from pspp.cure_checkpoints import (
    apply_cure_checkpoint, plan_cure_checkpoint,
)

PASS = 0
FAIL = 0
GP = 'metakaolin-geopolymer'


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def _manager():
    return SimpleNamespace(
        objectTables={
            'MaterialsScienceMaterial': {
                'm1': SimpleNamespace(name=GP)},
            'MaterialState': {},
        },
        idList=[], db=None)


def test_plan():
    print('[plan: the exact rows, nothing written]')
    m = _manager()
    plan = plan_cure_checkpoint(m, GP, 1.83)
    check('plan ok for the measured MR=1.83 @ 80C cure', plan['ok'])
    rows = plan['plan']
    check('execution is the sealed-cure TRANSFORMATIVE edge',
          rows['execution']['definition_name'] == 'sealed-cure'
          and json.loads(rows['execution']['output_state_ids_json'])
          == [rows['state']['name']])
    check('child state parents the canonical state (I1 default)',
          json.loads(rows['state']['parent_state_ids_json'])
          == [f'{GP}#as-defined'])
    check('child state is a cured-solid with the producing edge',
          rows['state']['processing_stage'] == 'cured-solid'
          and rows['state']['producing_execution_id']
          == rows['execution']['name'])
    check('reactionExtent rides as a StructureClaim, never a bare '
          'value (I4)',
          rows['claim']['descriptor_name'] == 'reactionExtent'
          and rows['claim']['value'] == 1.0
          and rows['claim']['evidence_method'])
    check('claim assumptions carry the linear-ramp honesty note',
          any('placeholder' in a
              for a in json.loads(rows['claim']['assumptions_json'])))
    check('plan never writes', not m.objectTables['MaterialState'])
    check('plan suggests the apply knob (never auto-applies)',
          'apply' in plan['suggestion'])

    scaled = plan_cure_checkpoint(m, GP, 1.83, cure_temperature_c=60.0)
    check('60C cure plans via the Fig 8.20 exotherm ladder '
          '(interpolated evidence)',
          scaled['ok'] and scaled['evidence']['method']
          == 'interpolated')
    check('scaled completion is longer than the 80C reference',
          json.loads(scaled['plan']['schedule_json']
                     if 'schedule_json' in scaled['plan']
                     else scaled['plan']['execution']['schedule_json'])
          [0]['hours'] > 4.0)


def test_refusals():
    print('[honest refusals]')
    m = _manager()
    never = plan_cure_checkpoint(m, GP, 2.85)
    check('setting-class cure with no completion time refuses with '
          'the data ask', never['ok'] is False
          and 'no checkpoint to promote' in never['refusal']
          and 'DigitizedDataset' in never['suggestion'])
    ghost = plan_cure_checkpoint(m, 'unobtainium-gp', 1.83)
    check('unknown material refused through state resolution (I1)',
          ghost['ok'] is False and 'unknown material' in
          ghost['refusal'])
    badTemp = plan_cure_checkpoint(m, GP, 1.23,
                                   cure_temperature_c=60.0)
    check('temperature scaling off MR=1.83 refuses naming Fig 8.20',
          badTemp['ok'] is False and '8.20' in badTemp['refusal'])
    check('apply without a manager refuses and writes nothing',
          apply_cure_checkpoint(None, GP, 1.83)['ok'] is False)


def test_apply():
    print('[apply: planned rows land in the tree]')
    m = _manager()
    result = apply_cure_checkpoint(m, GP, 1.83)
    check('apply ok', result['ok'])
    states = [r for r in m.objectTables.get('MaterialState',
                                            {}).values()]
    executions = [r for r in
                  m.objectTables.get('MaterialProcessExecution',
                                     {}).values()]
    claims = [r for r in m.objectTables.get('StructureClaim',
                                            {}).values()]
    check('one MaterialState row created with the planned key',
          len(states) == 1
          and states[0].name == result['created']['state'])
    check('execution row status flipped to executed',
          len(executions) == 1 and executions[0].status == 'executed')
    check('reactionExtent claim row created',
          len(claims) == 1
          and claims[0].subject_state_key == states[0].name)
    duplicate = apply_cure_checkpoint(m, GP, 1.83)
    check('re-apply refuses the duplicate state (never silently '
          'overwritten)', duplicate['ok'] is False
          and 'already' in duplicate['refusal'])
    named = apply_cure_checkpoint(m, GP, 1.83,
                                  state_name='7-day-reference')
    check('a differently named checkpoint applies beside it',
          named['ok']
          and named['created']['state'] == f'{GP}#7-day-reference')


def main():
    test_plan()
    test_refusals()
    test_apply()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
