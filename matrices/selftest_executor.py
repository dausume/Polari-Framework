"""
Standalone self-test for the matrix executor — no server, no sudo, no DB.

Run from polari-framework/:
    python3 -m matrices.selftest_executor

Builds SimpleNamespace stand-ins for the seed matrices (so it also validates
the seed data), wires a fake manager, and asserts the resolved arrays. Covers
all element/computation kinds: numeric literals, matrix-of-matrices
composition, equation-typed elements, elementwise equations, matrix_op.
"""

from types import SimpleNamespace

import numpy as np

from matrices.matrix_executor import evaluate, MatrixEvalError
from matrices.matrix_validator import validate
from matrices.seed_data import SEED_MATRICES


class FakeManager:
    """Minimal manager: just the objectTables the executor reads."""
    def __init__(self):
        self.objectTables = {'MatrixDefinition': {}, 'EquationDefinition': {}}

    def add_matrix(self, seed):
        ns = SimpleNamespace(**{k: v for k, v in seed.items()})
        self.objectTables['MatrixDefinition'][seed['name']] = ns
        return ns


def _mgr_with_seeds():
    mgr = FakeManager()
    for seed in SEED_MATRICES:
        mgr.add_matrix(seed)
    return mgr


PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, got, expected):
    try:
        ok = np.allclose(np.asarray(got, dtype=complex), np.asarray(expected, dtype=complex))
    except Exception as e:
        ok = False
        got = f'<error: {e}>'
    results.append(ok)
    print(f'  [{PASS if ok else FAIL}] {label}')
    if not ok:
        print(f'        expected:\n{np.asarray(expected)}')
        print(f'        got:\n{np.asarray(got)}')


def by_name(mgr, name, bindings=None):
    return evaluate(mgr.objectTables['MatrixDefinition'][name], binding_values=bindings, manager=mgr)


def main():
    mgr = _mgr_with_seeds()
    print('Matrix executor self-test\n')

    # --- numeric literals ---
    check('identity-3x3 == eye(3)', by_name(mgr, 'identity-3x3'), np.eye(3))
    check('mat-a-2x2', by_name(mgr, 'mat-a-2x2'), [[1, 2], [3, 4]])

    # --- matrix-of-matrices composition → 4×4 ---
    A = np.array([[1, 2], [3, 4]])
    I = np.eye(2)
    expected_block = np.block([[A, I], [I, A]])
    check('block-4x4 composition', by_name(mgr, 'block-4x4'), expected_block)

    # --- equation-typed elements ---
    check('eq-elements-2x2 (x^2 per cell)', by_name(mgr, 'eq-elements-2x2'),
          [[1, 4], [9, 16]])

    # (matrix operations now live in MatrixEquationDefinition — see
    #  matrices.selftest_equations)

    # --- mixed (per-cell self-describing) elements ---
    mixed_scalars = SimpleNamespace(
        name='_mixed_s', shape_json='[2,2]', element_type='mixed',
        element_matrix_ref='', computation_json='{"kind":"literal"}',
        values_json='[{"kind":"number","value":5},'
                    '{"kind":"equation","latex":"x^2","bindings":{"x":3}},'
                    '{"kind":"number","value":7},'
                    '{"kind":"equation","latex":"2*y","bindings":{"y":4}}]')
    check('mixed number+equation cells', evaluate(mixed_scalars, manager=mgr),
          [[5, 9], [7, 8]])

    mixed_blocks = SimpleNamespace(
        name='_mixed_b', shape_json='[1,2]', element_type='mixed',
        element_matrix_ref='', computation_json='{"kind":"literal"}',
        values_json='[{"kind":"matrix","matrixRef":"identity-2x2"},'
                    '{"kind":"matrix","matrixRef":"mat-a-2x2"}]')
    check('mixed all-matrix cells → 2×4 block',
          evaluate(mixed_blocks, manager=mgr),
          np.block([[np.eye(2), np.array([[1, 2], [3, 4]])]]))

    mixed_bad = SimpleNamespace(
        name='_mixed_x', shape_json='[1,2]', element_type='mixed',
        element_matrix_ref='', computation_json='{"kind":"literal"}',
        values_json='[{"kind":"number","value":1},'
                    '{"kind":"matrix","matrixRef":"identity-2x2"}]')
    try:
        evaluate(mixed_bad, manager=mgr)
        mixed_err = False
    except MatrixEvalError:
        mixed_err = True
    results.append(mixed_err)
    print(f"  [{PASS if mixed_err else FAIL}] mixing scalar + matrix cells raises MatrixEvalError")

    # --- validator sanity ---
    v_ok = validate(mgr.objectTables['MatrixDefinition']['block-4x4'], manager=mgr)
    results.append(v_ok['valid'])
    print(f"  [{PASS if v_ok['valid'] else FAIL}] validate(block-4x4) → valid={v_ok['valid']} "
          f"composedShape={v_ok.get('composedShape')}")

    bad = SimpleNamespace(
        name='_bad', shape_json='[2,2]', element_type='float',
        element_matrix_ref='', values_json='[1, 2, 3]',  # too few
        computation_json='{"kind":"literal"}', is_template=False)
    v_bad = validate(bad, manager=mgr)
    bad_caught = (not v_bad['valid']) and len(v_bad['errors']) > 0
    results.append(bad_caught)
    print(f"  [{PASS if bad_caught else FAIL}] validate(bad count) → errors={v_bad['errors']}")

    # --- cycle detection ---
    cyc = SimpleNamespace(
        name='cyc', shape_json='[1,1]', element_type='matrix',
        element_matrix_ref='cyc', values_json='["cyc"]',
        computation_json='{"kind":"literal"}', is_template=False)
    mgr.objectTables['MatrixDefinition']['cyc'] = cyc
    try:
        evaluate(cyc, manager=mgr)
        cycle_caught = False
    except MatrixEvalError:
        cycle_caught = True
    results.append(cycle_caught)
    print(f"  [{PASS if cycle_caught else FAIL}] cyclic reference raises MatrixEvalError")

    # --- transitive cycle detection in the validator (A → B → A) ---
    cyc_a = SimpleNamespace(
        name='cyc-a', shape_json='[1,1]', element_type='mixed', element_matrix_ref='',
        values_json='[{"kind":"matrix","matrixRef":"cyc-b"}]', computation_json='{"kind":"literal"}',
        is_template=False)
    cyc_b = SimpleNamespace(
        name='cyc-b', shape_json='[1,1]', element_type='mixed', element_matrix_ref='',
        values_json='[{"kind":"matrix","matrixRef":"cyc-a"}]', computation_json='{"kind":"literal"}',
        is_template=False)
    mgr.objectTables['MatrixDefinition']['cyc-a'] = cyc_a
    mgr.objectTables['MatrixDefinition']['cyc-b'] = cyc_b
    v_cyc = validate(cyc_a, manager=mgr)
    cyc_caught = (not v_cyc['valid']) and any('recursive' in e for e in v_cyc['errors'])
    results.append(cyc_caught)
    print(f"  [{PASS if cyc_caught else FAIL}] validator detects A→B→A cycle: {v_cyc['errors']}")

    print()
    n_pass = sum(1 for r in results if r)
    print(f'{n_pass}/{len(results)} checks passed')
    return 0 if n_pass == len(results) else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
