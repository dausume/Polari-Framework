"""
Self-test for the display event/validation runtime bridge (P4).

Run from polari-framework/:
    python3 -m polariNoCode.selftest_display_flow

Authors real state graphs (the editor's persisted dict shape) and runs
them through the REAL SolutionExecutionEngine:

  * FormValidation — per-field rules (required / type / range / length /
    pattern), verdicts in context, and BRANCHING: valid → "All Valid"
    (first output slot); invalid → the first invalid field's own wired
    slot, or a wired generic second slot in the simple shape, or the
    flow ENDS — an invalid form never proceeds down "All Valid".
  * The full authored display chain: FormSubscription → FormValidation
    → [valid] StateChangeCommit → EmitEvent — persists + emits on valid
    input; binds a ValidationResult verdict WITHOUT committing on
    invalid input.
  * StateChangeCommit — updates an existing fake-manager instance via
    the standard path; plain-language errors for missing targets.
  * EmitFrontendEvent — terminal, channel='frontend', documented shape.
"""

from types import SimpleNamespace

from polariNoCode.SolutionExecutionEngine import (
    COMMITTED_CHANGES_KEY,
    EMITTED_EVENTS_KEY,
    FORM_VALIDATION_KEY,
    SolutionExecutionEngine,
)
from polariNoCode.stepping import StepConfig

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


# ---------------------------------------------------------------------------
# Graph-authoring helpers (mirroring selftest_turing's shapes, plus
# explicit slot indices where FormValidation's per-field routing needs
# the seed-style absolute `index` values).
# ---------------------------------------------------------------------------

def node(name, cls, fields=None, outs=None, index=0):
    slots = [{'isInput': True, 'connectors': [], 'index': 0}]
    for i, targets in enumerate(outs if outs is not None else [[]]):
        slots.append({
            'isInput': False, 'index': i + 1,
            'connectors': [{'targetStateName': t} for t in targets],
        })
    return {
        'stateName': name, 'stateClass': cls, 'boundObjectClass': cls,
        'boundObjectFieldValues': fields or {}, 'slots': slots,
        'index': index,
    }


def solution(name, *states):
    return {'solutionName': name,
            'stateInstances': [dict(s, index=i) for i, s in enumerate(states)]}


def run(sol, params=None, manager=None):
    engine = SolutionExecutionEngine(manager=manager)
    return engine.execute(
        solution_data=sol, input_params=params or {},
        config=StepConfig(mode='step', record_context=True),
        target_runtime='python_backend',
    )


def final_context(trace):
    if not trace.steps:
        return {}
    variables = trace.steps[-1].context_after.variables
    return {k: (v.get('value') if isinstance(v, dict) and 'value' in v else v)
            for k, v in variables.items()}


def assign(name, var, value, nxt):
    return node(name, 'VariableAssignment',
                {'variableName': var, 'value': value},
                outs=[[nxt] if nxt else []])


FIELDS_SIMPLE = [
    {'fieldName': 'label', 'displayName': 'Label', 'fieldType': 'str',
     'enabled': True, 'required': True, 'maxLength': 10},
    {'fieldName': 'amount', 'displayName': 'Amount', 'fieldType': 'float',
     'enabled': True, 'required': True, 'minValue': 0, 'maxValue': 100},
    {'fieldName': 'code', 'displayName': 'Code', 'fieldType': 'str',
     'enabled': True, 'required': False, 'pattern': r'^[A-Z]{3}$'},
]


def form_validation(name, fields, outs):
    return node(name, 'FormValidation', {'fields': fields}, outs=outs)


# ---------------------------------------------------------------------------
# 1. FormValidation rules + branching
# ---------------------------------------------------------------------------

def _validation():
    print('Display bridge — FormValidation rules + branching\n')

    def two_slot(fields):
        # slot layout: [input, All Valid -> MarkValid, Invalid -> MarkInvalid]
        return solution(
            'validate-two-slot',
            node('Start', 'FormSubscription', {}, outs=[['Validate']]),
            form_validation('Validate', fields,
                            outs=[['MarkValid'], ['MarkInvalid']]),
            assign('MarkValid', 'route', "'valid'", None),
            assign('MarkInvalid', 'route', "'invalid'", None),
        )

    # Valid payload → All Valid branch.
    t = run(two_slot(FIELDS_SIMPLE),
            params={'label': 'ok', 'amount': 42, 'code': 'ABC'})
    ctx = final_context(t)
    check('valid form branches down "All Valid"',
          t.status == 'completed' and ctx.get('route') == 'valid'
          and ctx.get('form_valid') is True,
          f"route={ctx.get('route')}")

    # Required missing → invalid branch + message.
    t = run(two_slot(FIELDS_SIMPLE), params={'amount': 42})
    ctx = final_context(t)
    v = (ctx.get(FORM_VALIDATION_KEY) or {}).get('label', {})
    check('missing required field branches invalid with a plain message',
          ctx.get('route') == 'invalid' and ctx.get('form_valid') is False
          and 'Label is required.' in v.get('errors', []),
          f"errors={v.get('errors')}")

    # Range violation.
    t = run(two_slot(FIELDS_SIMPLE),
            params={'label': 'ok', 'amount': 250, 'code': 'ABC'})
    ctx = final_context(t)
    v = (ctx.get(FORM_VALIDATION_KEY) or {}).get('amount', {})
    check('numeric range rule enforced (max 100)',
          ctx.get('route') == 'invalid'
          and any('at most 100' in e for e in v.get('errors', [])),
          f"errors={v.get('errors')}")

    # Type rule.
    t = run(two_slot(FIELDS_SIMPLE),
            params={'label': 'ok', 'amount': 'not-a-number'})
    ctx = final_context(t)
    v = (ctx.get(FORM_VALIDATION_KEY) or {}).get('amount', {})
    check('type rule enforced (float)',
          ctx.get('route') == 'invalid'
          and any('must be a number' in e for e in v.get('errors', [])))

    # Pattern rule (optional field, present but malformed).
    t = run(two_slot(FIELDS_SIMPLE),
            params={'label': 'ok', 'amount': 10, 'code': 'abc'})
    ctx = final_context(t)
    v = (ctx.get(FORM_VALIDATION_KEY) or {}).get('code', {})
    check('pattern rule enforced on optional-but-present field',
          ctx.get('route') == 'invalid'
          and any('expected format' in e for e in v.get('errors', [])))

    # No invalid branch wired → flow ENDS with the verdict; never valid-route.
    sol = solution(
        'validate-unwired-invalid',
        node('Start', 'FormSubscription', {}, outs=[['Validate']]),
        form_validation('Validate', FIELDS_SIMPLE, outs=[['MarkValid'], []]),
        assign('MarkValid', 'route', "'valid'", None),
    )
    t = run(sol, params={'amount': 42})
    ctx = final_context(t)
    check('invalid form with no invalid branch ENDS (never "All Valid")',
          t.status == 'completed' and ctx.get('route') is None
          and ctx.get('form_valid') is False,
          f"route={ctx.get('route')}")

    # Per-field routing (seed pattern): email's own slot wins.
    fields_pf = [
        {'fieldName': 'username', 'fieldType': 'str', 'enabled': True,
         'required': True, 'outputSlotIndex': 2},
        {'fieldName': 'email', 'fieldType': 'str', 'enabled': True,
         'required': True, 'pattern': r'@', 'outputSlotIndex': 3},
    ]
    sol = solution(
        'validate-per-field',
        node('Start', 'FormSubscription', {}, outs=[['Validate']]),
        # slots: [in(0), AllValid(1), username(2), email(3)]
        form_validation('Validate', fields_pf,
                        outs=[['MarkValid'], ['FixUsername'], ['FixEmail']]),
        assign('MarkValid', 'route', "'valid'", None),
        assign('FixUsername', 'route', "'fix-username'", None),
        assign('FixEmail', 'route', "'fix-email'", None),
    )
    t = run(sol, params={'username': 'dustin', 'email': 'no-at-sign'})
    ctx = final_context(t)
    check("per-field routing follows the invalid field's own slot",
          ctx.get('route') == 'fix-email', f"route={ctx.get('route')}")


# ---------------------------------------------------------------------------
# 2. StateChangeCommit
# ---------------------------------------------------------------------------

def _fake_manager():
    target = SimpleNamespace(name='pref-row-1', theme='light', volume=3)
    m = SimpleNamespace(
        objectTables={'UserPreference': {'pref-row-1': target}},
        db=None,
    )
    return m, target


def _commit():
    print('\nDisplay bridge — StateChangeCommit\n')
    m, target = _fake_manager()
    sol = solution(
        'commit-prefs',
        node('Start', 'FormSubscription', {}, outs=[['Commit']]),
        node('Commit', 'StateChangeCommit', {
            'targetClassName': 'UserPreference',
            'instanceRef': 'pref-row-1',
            'changeType': 'update',
            'fieldMappings': [
                {'fieldName': 'theme',
                 'valueSource': {'sourceType': 'from_source_object',
                                 'sourceObjectPath': 'theme'}},
            ],
        }, outs=[[]]),
    )
    t = run(sol, params={'theme': 'dark'}, manager=m)
    ctx = final_context(t)
    committed = (ctx.get(COMMITTED_CHANGES_KEY) or [{}])[0]
    check('commit updates the existing instance through the standard path',
          t.status == 'completed' and target.theme == 'dark'
          and committed.get('className') == 'UserPreference'
          and committed.get('fields', {}).get('theme') == 'dark',
          f'theme={target.theme}')

    # Missing instance → plain-language error, trace errored.
    m2, _ = _fake_manager()
    sol_bad = solution(
        'commit-missing',
        node('Start', 'FormSubscription', {}, outs=[['Commit']]),
        node('Commit', 'StateChangeCommit', {
            'targetClassName': 'UserPreference',
            'instanceRef': 'nope',
            'fieldMappings': [{'fieldName': 'theme', 'valueSource': {
                'sourceType': 'from_source_object',
                'sourceObjectPath': 'theme'}}],
        }, outs=[[]]),
    )
    t = run(sol_bad, params={'theme': 'dark'}, manager=m2)
    check('missing target instance fails with a plain-language error',
          t.status == 'errored'
          and "no UserPreference instance matching 'nope'"
          in (t.error_summary or ''),
          f'err={t.error_summary}')

    # Unsupported changeType stated clearly.
    sol_del = solution(
        'commit-delete',
        node('Start', 'FormSubscription', {}, outs=[['Commit']]),
        node('Commit', 'StateChangeCommit', {
            'targetClassName': 'UserPreference', 'instanceRef': 'pref-row-1',
            'changeType': 'delete',
            'fieldMappings': [{'fieldName': 'theme', 'valueSource': {
                'sourceType': 'from_source_object',
                'sourceObjectPath': 'theme'}}],
        }, outs=[[]]),
    )
    m3, _ = _fake_manager()
    t = run(sol_del, params={'theme': 'dark'}, manager=m3)
    check("create/delete are honestly deferred to the data-access nodes",
          t.status == 'errored' and 'not supported yet' in (t.error_summary or ''))


# ---------------------------------------------------------------------------
# 3. The full authored display chain + EmitFrontendEvent
# ---------------------------------------------------------------------------

def _full_chain():
    print('\nDisplay bridge — the full form chain\n')

    def chain_solution():
        return solution(
            'demo-form-save',
            node('Watch Form', 'FormSubscription', {}, outs=[['Validate']]),
            form_validation('Validate', [
                {'fieldName': 'theme', 'fieldType': 'str', 'enabled': True,
                 'required': True},
                {'fieldName': 'volume', 'fieldType': 'int', 'enabled': True,
                 'required': True, 'minValue': 0, 'maxValue': 11},
            ], outs=[['Commit'], ['Verdict']]),
            node('Commit', 'StateChangeCommit', {
                'targetClassName': 'UserPreference',
                'instanceRef': 'pref-row-1',
                'fieldMappings': [
                    {'fieldName': 'theme', 'valueSource': {
                        'sourceType': 'from_source_object',
                        'sourceObjectPath': 'theme'}},
                    {'fieldName': 'volume', 'valueSource': {
                        'sourceType': 'from_source_object',
                        'sourceObjectPath': 'volume'}},
                ],
            }, outs=[['Saved']]),
            node('Saved', 'EmitEvent', {
                'eventName': 'refreshDisplay',
                'payload': {'reason': {'sourceType': 'direct_assignment',
                                       'directValue': 'preferences saved',
                                       'directValueType': 'str'}},
            }, outs=[]),
            node('Verdict', 'ValidationResult', {
                'outcome': 'invalid',
                'reason': {'sourceType': 'direct_assignment',
                           'directValue': 'Please fix the highlighted fields.',
                           'directValueType': 'str'},
            }, outs=[]),
        )

    # VALID: commits + emits.
    m, target = _fake_manager()
    t = run(chain_solution(), params={'theme': 'dark', 'volume': 7}, manager=m)
    ctx = final_context(t)
    events = ctx.get(EMITTED_EVENTS_KEY) or []
    check('valid submission commits AND emits (the whole authored chain)',
          t.status == 'completed' and target.theme == 'dark'
          and target.volume == 7 and len(events) == 1
          and events[0]['name'] == 'refreshDisplay'
          and events[0]['channel'] == 'backend',
          f'events={[e["name"] for e in events]}')

    # INVALID: verdict bound, NOTHING committed.
    m2, target2 = _fake_manager()
    t = run(chain_solution(), params={'theme': 'dark', 'volume': 99},
            manager=m2)
    ctx = final_context(t)
    check('invalid submission binds the verdict and commits NOTHING',
          t.status == 'completed' and target2.volume == 3
          and ctx.get('outcome') == 'invalid'
          and ctx.get('reason') == 'Please fix the highlighted fields.'
          and not ctx.get(COMMITTED_CHANGES_KEY),
          f'volume={target2.volume} outcome={ctx.get("outcome")}')

    # EmitFrontendEvent: terminal, channel='frontend'.
    sol = solution(
        'frontend-ping',
        node('Start', 'InitialState', {}, outs=[['Ping']]),
        node('Ping', 'EmitFrontendEvent', {
            'eventName': 'showToast',
            'payload': {'message': {'sourceType': 'direct_assignment',
                                    'directValue': 'saved!',
                                    'directValueType': 'str'}},
        }, outs=[]),
    )
    t = run(sol)
    ctx = final_context(t)
    events = ctx.get(EMITTED_EVENTS_KEY) or []
    check("EmitFrontendEvent is terminal with channel='frontend'",
          t.status == 'completed' and len(events) == 1
          and events[0]['channel'] == 'frontend'
          and events[0]['name'] == 'showToast'
          and events[0]['payload'] == {'message': 'saved!'},
          f'events={events}')


if __name__ == '__main__':
    _validation()
    _commit()
    _full_chain()
    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
