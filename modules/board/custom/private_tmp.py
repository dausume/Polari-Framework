"""
@module board.custom.private_tmp

A per-run temp root for the "leaves no temp directory behind" checks (econ's 2b sweep, 2026-11-13): those checks diffed the
whole system temp dir, so two suites run in parallel each saw the other's live dirs as a leak. Inside `private_tmp()` every
tempfile call in this process (and TMPDIR for the engines it starts) lands in one fresh directory of this run's own, so a leak
check only sees what THIS run made - and a real leak still fails it.

  with private_tmp('smp') as root: ...      root = the private directory
  leftovers(root)                           -> sorted names still in it ([] = nothing left behind)
"""
import contextlib
import os
import shutil
import tempfile


@contextlib.contextmanager
def private_tmp(tag):
    root = tempfile.mkdtemp(prefix='%s-run-' % tag)
    saved_dir, saved_env = tempfile.tempdir, os.environ.get('TMPDIR')
    tempfile.tempdir, os.environ['TMPDIR'] = root, root
    try:
        yield root
    finally:
        tempfile.tempdir = saved_dir
        if saved_env is None:
            os.environ.pop('TMPDIR', None)
        else:
            os.environ['TMPDIR'] = saved_env


def leftovers(root):
    """What the run left in its private root; the root itself is removed afterwards by the caller (cleanup())."""
    return sorted(os.listdir(root)) if os.path.isdir(root) else []


def cleanup(root):
    shutil.rmtree(root, ignore_errors=True)
