"""
Selftest — ncg-0: the no-code capability matrix (the acct-4 sliver).

Run from polari-framework/:
    python3 -m testing.selftest_nocode_matrix

Covers: the catalog carries one variant row per node type from the
container-stable set (registry ∪ engine dispatch) plus the sweep
summary and the TS parity leg; the regression-gate criticality
overrides are applied; the drift judge fails a lying entry and passes
truthful stub labels; frontend legs skip-honest (with the suggestion)
when the Angular tree is unreachable; the dynamic per-class callables
resolve. The sweep's live VERDICT is the matrix row's job, not this
selftest's — here we prove the machinery.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _catalog_rows():
    from testing.check_catalog import catalog_checks
    print('catalog registration')
    rows = {e['name']: e for e in catalog_checks()}
    variants = [n for n in rows if n.startswith('nocode:variant-')
                and n != 'nocode:variant-sweep']
    check('>=30 per-node variant rows registered',
          len(variants) >= 30, f'{len(variants)} rows')
    check('sweep summary row present and blocking',
          rows.get('nocode:variant-sweep', {}).get('criticality')
          == 'blocking')
    check('ts-parity row present and blocking',
          rows.get('nocode:ts-parity', {}).get('criticality')
          == 'blocking')
    gates = ['turing', 'composition', 'parity', 'display_flow',
             'matrixop', 'engine_model_op', 'pendulum_embed']
    flipped = [g for g in gates
               if rows.get(f'selftest:polariNoCode.{g}',
                           {}).get('criticality') == 'blocking']
    check('all 7 engine regression gates flipped to blocking',
          len(flipped) == 7, f'{len(flipped)}/7')
    check('this selftest is itself a blocking row',
          rows.get('selftest:testing.nocode_matrix',
                   {}).get('criticality') == 'blocking')
    check('every variant row is a callable runner',
          all(rows[n]['runner_kind'] == 'callable' for n in variants))


def _inventory():
    from testing.nocode_checks import (variant_inventory,
                                       variant_class_names)
    print('inventory (live sources)')
    names = variant_class_names()
    inventory = variant_inventory()
    check('inventory covers the stable class set exactly',
          sorted(inventory) == names, f'{len(names)} classes')
    chain = inventory.get('ConditionalChain') or {}
    check('ConditionalChain: registry real + engine dispatches it',
          chain.get('registry_status') == 'real'
          and chain.get('python_dispatched') is True)
    retired = inventory.get('FunctionCall') or {}
    check('FunctionCall carries a truthful non-real label',
          retired.get('registry_status') in ('authoring-only', 'stub'),
          f"status={retired.get('registry_status')}")


def _judging():
    from testing.nocode_checks import _judge, check_variant
    print('drift judge')
    lying = {'registry_status': 'real', 'registry_runtime': None,
             'python_dispatched': False, 'palette': None,
             'palette_status': None, 'ts_client': None,
             'ts_backend_only': None}
    ok, evidence = _judge('Imaginary', lying)
    check('claimed-real-but-never-dispatched FAILS',
          not ok and 'DRIFT' in evidence)
    truthful_stub = dict(lying, registry_status='stub')
    ok, _ = _judge('Imaginary', truthful_stub)
    check('truthful stub label PASSES (visible debt, not a lie)', ok)
    contradictory = dict(lying, registry_status=None,
                         ts_client=True, ts_backend_only=True)
    ok, evidence = _judge('Imaginary', contradictory)
    check('backend-only AND client-capable at once FAILS',
          not ok and 'BOTH' in evidence)
    row = check_variant('NoSuchNodeType')
    check('unknown class = stale-catalog failure, not a crash',
          row['status'] == 'fail' and 'stale' in row['evidence'])


def _dynamic_callables():
    import testing.nocode_checks as mod
    print('dynamic per-class callables')
    fn = mod.check_variant_ConditionalChain
    row = fn()
    check('check_variant_ConditionalChain resolves and runs',
          row['status'] in ('pass', 'fail') and 'registry='
          in row['evidence'], row['status'])
    try:
        mod.not_a_check_name
        resolved = True
    except AttributeError:
        resolved = False
    check('non-check attributes still raise AttributeError',
          not resolved)


def _honesty_paths():
    from testing.nocode_checks import (check_variant_sweep,
                                       check_ts_parity, check_variant)
    print('honesty paths (Angular tree unreachable)')
    os.environ['POLARI_ANGULAR_ROOT'] = '/nonexistent-angular'
    try:
        sweep = check_variant_sweep()
        check('sweep still judges backend legs and says legs skipped',
              sweep['status'] in ('pass', 'fail')
              and 'frontend legs skipped' in sweep['evidence'])
        check('sweep names the knob in its suggestion',
              'POLARI_ANGULAR_ROOT' in sweep['evidence'])
        row = check_variant('ConditionalChain')
        check('per-node row notes the skipped frontend legs',
              'frontend legs skipped' in row['evidence'])
        ts = check_ts_parity()
        check('ts-parity skip-honests without the checkout',
              ts['status'] == 'skip-honest'
              and 'npm run parity' in ts['evidence'])
    finally:
        del os.environ['POLARI_ANGULAR_ROOT']
    sweep = check_variant_sweep()
    check('sweep well-formed on real sources (verdict = matrix row)',
          sweep['status'] in ('pass', 'fail')
          and sweep.get('total') and 'swept' in sweep['evidence'],
          sweep['status'])


def main():
    _catalog_rows()
    _inventory()
    _judging()
    _dynamic_callables()
    _honesty_paths()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
