"""selftest_posture — the posture reader and the ci-13 pipeline-test marker.

Run: PYTHONPATH=.:modules python3 moduleService/selftest_posture.py

The pipeline-test marker (his ruling 2026-09-20) is a statement about the INSTALLATION — "this Polari was set
up for pipeline testing" — written by the throwaway isle's install as /etc/polari/pipeline-test and passed as
POLARI_PIPELINE_TEST=1 through the isle compose. It changes no gate; it lets health, the cicd app and a person
tell a pipeline's test instance from a real one. These checks pin: env wins, the file counts, absence is False,
and a broken path never raises.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from moduleService.posture import pipeline_test, is_dev  # noqa: E402

PASSED = 0
FAILED = 0


def check(label, ok, detail=''):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print('  [PASS] %s' % label)
    else:
        FAILED += 1
        print('  [FAIL] %s %s' % (label, detail))


def main():
    with tempfile.TemporaryDirectory() as td:
        absent = os.path.join(td, 'pipeline-test')
        check('no env, no file → not a pipeline test', pipeline_test(env={}, path=absent) is False)
        for v in ('1', 'true', 'yes'):
            check('env POLARI_PIPELINE_TEST=%s → pipeline test' % v,
                  pipeline_test(env={'POLARI_PIPELINE_TEST': v}, path=absent) is True)
        check('env POLARI_PIPELINE_TEST=0 → not a pipeline test', pipeline_test(env={'POLARI_PIPELINE_TEST': '0'}, path=absent) is False)
        with open(absent, 'w') as f:
            f.write('{"pipelineTest": true}\n')
        check('the marker file alone → pipeline test', pipeline_test(env={}, path=absent) is True)
        check('a directory where the file should be → False, never raises', pipeline_test(env={}, path=td) is False)
        check('the marker does not change the posture (still production by default)',
              is_dev(env={'POLARI_PIPELINE_TEST': '1'}, path=os.path.join(td, 'nope.json')) is False)
    print('\n%d/%d checks passed' % (PASSED, PASSED + FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
