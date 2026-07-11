"""
@module testing.twin_checks

acct-3: the twin:rehearsal matrix row — wraps
`python3 -m testing.twin_rehearsal` (throwaway core+m+n containers,
full coherence ladder, guaranteed teardown) with the environment
honesty the compose kind requires: no docker or no backend image ->
skip-honest naming what would make it runnable.
"""

import re
import shutil
import subprocess

from testing.check_catalog import FRAMEWORK_ROOT
from testing.twin_fixtures import image_name

_COUNTS = re.compile(r'(\d+)\s*/\s*(\d+)\s+passed')


def _image_present(image):
    try:
        proc = subprocess.run(
            ['docker', 'image', 'inspect', image],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=15)
        return proc.returncode == 0
    except Exception:
        return False


def check_twin_rehearsal(timeout=900):
    if shutil.which('docker') is None:
        return {'status': 'skip-honest',
                'evidence': 'needs docker to boot the throwaway '
                            'core+m+n fixtures. Run on the staging '
                            'host, or set POLARI_TWIN_IMAGE + '
                            'docker.'}
    image = image_name()
    if not _image_present(image):
        return {'status': 'skip-honest',
                'evidence': f'backend image {image} not present — '
                            'build it (polari-rf-node staging '
                            'compose) or set POLARI_TWIN_IMAGE.'}
    try:
        proc = subprocess.run(
            ['python3', '-m', 'testing.twin_rehearsal'],
            cwd=FRAMEWORK_ROOT, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True)
    except subprocess.TimeoutExpired:
        return {'status': 'fail',
                'evidence': f'rehearsal exceeded {timeout}s'}
    output = proc.stdout or ''
    counts = _COUNTS.search(output.strip().splitlines()[-1]
                            if output.strip() else '')
    passed, total = ((int(counts.group(1)), int(counts.group(2)))
                     if counts else (None, None))
    if proc.returncode == 0:
        return {'status': 'pass', 'passed': passed, 'total': total,
                'evidence': f'{passed}/{total} coherence checks '
                            '(boot, gating, directory routing, '
                            'rung-4 traversal, refusal, leased '
                            'dual-journal write, zombie fencing, '
                            'clean teardown)'}
    failing = [line.strip() for line in output.splitlines()
               if 'FAIL' in line][:4]
    return {'status': 'fail', 'passed': passed, 'total': total,
            'evidence': f'exit {proc.returncode}; '
                        + ' | '.join(failing)}
