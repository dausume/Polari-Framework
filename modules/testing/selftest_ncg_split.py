"""
Selftest — ncg-7: the ncg levels split honestly across small nodes.

Run from polari-framework/:
    python3 -m testing.selftest_ncg_split

Dustin's directive (2026-07-16): the digital level, the circuit
level, and the judicial client must be able to ride DIFFERENT small
devices (like this 3-machine setup). Each leg boots a REAL gated
instance in a subprocess (POLARI_MODULES names one level) and the
probe asserts the assigned level is fully present while the others
are fully absent — classes, tables, and the new gated routes. The
compiler seam (polariNoCode, core) must be everywhere.

NOTE: two real boots (~40s each).
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from testing.check_catalog import FRAMEWORK_ROOT

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _probe(level):
    env = dict(os.environ)
    env.pop('POLARI_TEST_BUILD', None)
    env['POLARI_MODULES'] = level
    env['NCG_PROBE_EXPECT'] = level
    env['PYTHONPATH'] = FRAMEWORK_ROOT
    proc = subprocess.run(
        [sys.executable, '-m', 'testing.ncg_split_probe'],
        cwd=FRAMEWORK_ROOT, env=env, timeout=600,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = '\n'.join((proc.stdout or '').strip().splitlines()[-3:])
    return proc.returncode, tail


def main():
    print('gating sanity (no boot)')
    from polariApiServer.module_gating import module_enabled
    saved = os.environ.pop('POLARI_MODULES', None)
    try:
        os.environ['POLARI_MODULES'] = 'hwdigital'
        check('hwdigital-only knob: electrodevice + scoring gated '
              'out', module_enabled('hwdigital')
              and not module_enabled('electrodevice')
              and not module_enabled('scoring'))
        check('the seam stays core under any knob',
              module_enabled('polariNoCode'))
    finally:
        if saved is None:
            os.environ.pop('POLARI_MODULES', None)
        else:
            os.environ['POLARI_MODULES'] = saved

    for level in ('hwdigital', 'electrodevice'):
        print(f'{level}-only node (real gated boot, ~40s)')
        code, tail = _probe(level)
        check(f'{level}-only instance: assigned level present, '
              f'others absent', code == 0, tail)

    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
