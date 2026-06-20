"""
Standalone self-test for the MatrixEquationOperation no-code state + the
'array' / 'element' value-source kinds. No server, no sudo.

Run from polari-framework/:
    python3 -m polariNoCode.selftest_matrixop

Proves the no-code engine can: build a vector from scalars (array source),
invoke a MatrixEquationDefinition (the 2D→3D embedding) via the new state,
and extract components (element source) — the full vector-authoring path.
"""

from types import SimpleNamespace

from polariNoCode.SolutionExecutionEngine import (
    SolutionExecutionEngine, StepConfig, _resolve_value_source_config,
)
from simulations.simulation_runner import _extract_final_context


class FakeManager:
    def __init__(self):
        self.objectTables = {
            'MatrixEquationDefinition': {},
            'MatrixDefinition': {},
            'EquationDefinition': {},
        }


def _mgr():
    m = FakeManager()
    # The 2D→3D embedding as a matrix equation: world = x·normalize(cross(Yup,n)) + y·Yup
    m.objectTables['MatrixEquationDefinition']['pendulum-embed'] = SimpleNamespace(
        name='pendulum-embed', latex='',
        operation_json='{"kind":"expr","expr":"x * normalize(cross(Yup, n)) + y * Yup"}',
        operands_json='{"x":"x","y":"y","n":"n","Yup":"Yup"}', tags='')
    return m


def _src_obj(path):
    return {'sourceType': 'from_source_object', 'sourceObjectPath': path}


def _embedding_solution():
    """InitialState → MatrixEquationOperation(world_vec) → ReturnValue."""
    def state(name, cls, fields, out_to=None):
        slots = [{'index': 0, 'stateName': name, 'isInput': True, 'label': 'In', 'connectors': []}]
        out = {'index': 1, 'stateName': name, 'isInput': False, 'label': 'Out', 'connectors': []}
        if out_to:
            out['connectors'].append({'id': 1, 'sourceSlot': 1, 'targetStateName': out_to, 'sinkSlot': 0})
        slots.append(out)
        return {
            'stateName': name, 'id': f'{name}-state', 'index': 0,
            'stateClass': cls, 'boundObjectClass': cls,
            'boundObjectFieldValues': fields, 'slots': slots,
        }

    embed_fields = {
        'matrixEquationName': 'pendulum-embed',
        'resultTarget': 'result_variable',
        'resultVariableName': 'world_vec',
        'operandBindings': [
            {'symbol': 'x', 'source': _src_obj('self.x')},
            {'symbol': 'y', 'source': _src_obj('self.y')},
            # n assembled from the three scalar normal fields (array source):
            {'symbol': 'n', 'source': {'sourceType': 'array', 'elements': [
                _src_obj('self.plane_nx'), _src_obj('self.plane_ny'), _src_obj('self.plane_nz')]}},
            # Yup constant (array of literals):
            {'symbol': 'Yup', 'source': {'sourceType': 'array', 'elements': [0, 1, 0]}},
        ],
    }
    return {
        'solutionName': 'pendulum-embed-test',
        'stateInstances': [
            state('Start', 'InitialState', {'inputParams': []}, out_to='Embed'),
            state('Embed', 'MatrixEquationOperation', embed_fields, out_to='Done'),
            state('Done', 'ReturnValue', {'returnValue': 'world_vec'}),
        ],
    }


PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, got, expected, tol=1e-6):
    ok = False
    try:
        if isinstance(expected, (list, tuple)):
            ok = len(got) == len(expected) and all(abs(float(g) - float(e)) <= tol for g, e in zip(got, expected))
        else:
            ok = abs(float(got) - float(expected)) <= tol
    except Exception as e:
        got = f'<err: {e}>'
    results.append(ok)
    print(f'  [{PASS if ok else FAIL}] {label}  → {got}')


def run_embed(mgr, x, y, normal):
    fields = {
        'self.x': x, 'self.y': y,
        'self.plane_nx': normal[0], 'self.plane_ny': normal[1], 'self.plane_nz': normal[2],
    }
    engine = SolutionExecutionEngine(manager=mgr)
    trace = engine.execute(
        solution_data=_embedding_solution(), input_params={},
        config=StepConfig(mode='step', record_context=True),
        target_runtime='python_backend', instance_fields=fields)
    final = _extract_final_context(trace)
    return final.get('world_vec')


def main():
    print('MatrixEquationOperation + array/element no-code self-test\n')

    # --- resolver: array + element kinds ---
    ctx = {'a': 2, 'b': 3, 'c': 4}
    arr = _resolve_value_source_config(
        {'sourceType': 'array', 'elements': [_src_obj('a'), _src_obj('b'), _src_obj('c')]}, ctx)
    check('array source builds [2,3,4]', arr, [2, 3, 4])
    el = _resolve_value_source_config(
        {'sourceType': 'element', 'index': 1,
         'source': {'sourceType': 'array', 'elements': [_src_obj('a'), _src_obj('b')]}}, ctx)
    check('element source extracts index 1', el, 3)

    # --- full no-code embedding via the new state ---
    mgr = _mgr()
    check('embed default n=(0,0,1) → (0.5,-0.866,0)', run_embed(mgr, 0.5, -0.866, [0, 0, 1]),
          [0.5, -0.866, 0.0])
    check('embed n=(1,0,0) → (0,-0.866,-0.5)', run_embed(mgr, 0.5, -0.866, [1, 0, 0]),
          [0.0, -0.866, -0.5])

    print()
    n = sum(1 for r in results if r)
    print(f'{n}/{len(results)} checks passed')
    return 0 if n == len(results) else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
