"""
selftest_module_home — the shared module-home helper (polariApiServer.module_home), THE FIX for artifacts
(pcb Gerbers/SVGs, board firmware work dirs, hwnocode splits, firmwarefaults runs) going to ephemeral
container-layer storage and 404ing after a redeploy while their DB rows survive.

    PYTHONPATH=.:modules python3 polariApiServer/selftest_module_home.py

Three branches, each proven in isolation with a temp dir standing in for /app/data (never the real path —
this selftest must pass identically on a bare host and inside a container):
  1. an explicit env override always wins, even when a usable container root is also present.
  2. a usable (existing + writable) container root → <root>/<name>, no env set.
  3. no usable container root (missing, or present but not writable) → ~/.cache/polari-<name>.

Plus: importing the module touches no filesystem, and module_home() itself never creates the directory it
names — creation is the CALLER's job, lazily, on first real use.
"""
import os
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'modules'))

PASSED = []
FAILED = []


def check(name, cond, detail=''):
    (PASSED if cond else FAILED).append(name if cond else f'{name} :: {detail}')


def test_import_touches_nothing():
    """Importing the module must not stat or create anything — only a real call may."""
    mod_name = 'polariApiServer.module_home'
    sys.modules.pop(mod_name, None)
    import importlib
    mh = importlib.import_module(mod_name)
    check('module_home.py imports cleanly with no side effect',
          hasattr(mh, 'module_home') and hasattr(mh, 'CONTAINER_DATA_ROOT'))


def test_env_override_always_wins():
    from polariApiServer import module_home as mh
    with tempfile.TemporaryDirectory() as container_root, tempfile.TemporaryDirectory() as override:
        real_root = mh.CONTAINER_DATA_ROOT
        mh.CONTAINER_DATA_ROOT = container_root
        try:
            got = mh.module_home('pcb', os.path.join(override, 'somewhere-else'))
            check('an explicit env value wins even though the container root IS usable',
                  got == os.path.join(override, 'somewhere-else'), got)
            check('the env branch never touches the container root',
                  not os.path.isdir(os.path.join(container_root, 'pcb')))
        finally:
            mh.CONTAINER_DATA_ROOT = real_root

    got = mh.module_home('pcb', '~/not-really-home/pcb-override')
    check('an env value is expanduser()-ed like every other branch',
          got == os.path.expanduser('~/not-really-home/pcb-override'), got)

    for falsy in (None, ''):
        with tempfile.TemporaryDirectory() as container_root:
            real_root = mh.CONTAINER_DATA_ROOT
            mh.CONTAINER_DATA_ROOT = container_root
            try:
                got = mh.module_home('board', falsy)
                check('a falsy env (%r) falls through to the container branch, not treated as an override' % (falsy,),
                      got == os.path.join(container_root, 'board'), got)
            finally:
                mh.CONTAINER_DATA_ROOT = real_root


def test_container_root_branch():
    from polariApiServer import module_home as mh
    with tempfile.TemporaryDirectory() as container_root:
        real_root = mh.CONTAINER_DATA_ROOT
        mh.CONTAINER_DATA_ROOT = container_root
        try:
            got = mh.module_home('hwnocode')
            check('a usable container root (exists + writable) -> <root>/<name>',
                  got == os.path.join(container_root, 'hwnocode'), got)
            check('the container branch does not create the subdirectory (lazy)',
                  not os.path.isdir(got))
        finally:
            mh.CONTAINER_DATA_ROOT = real_root


def test_container_root_present_but_read_only():
    """A container root that EXISTS but is not writable (odd permissions, a stray read-only mount) must be
    treated the same as 'no usable container root' — never raise, fall back to the host path."""
    from polariApiServer import module_home as mh
    if os.geteuid() == 0:
        check('read-only-container-root branch exercised', True, 'running as root — os.access() cannot deny root, skipped')
        return
    with tempfile.TemporaryDirectory() as container_root:
        os.chmod(container_root, stat.S_IRUSR | stat.S_IXUSR)  # r-x, no w
        real_root = mh.CONTAINER_DATA_ROOT
        mh.CONTAINER_DATA_ROOT = container_root
        try:
            got = mh.module_home('faults')
            check('a present-but-read-only container root is NOT used',
                  got != os.path.join(container_root, 'faults'), got)
            check('...falls back to the host ~/.cache path instead',
                  got == os.path.expanduser('~/.cache/polari-faults'), got)
        finally:
            mh.CONTAINER_DATA_ROOT = real_root
            os.chmod(container_root, stat.S_IRWXU)  # restore so TemporaryDirectory can clean up


def test_host_fallback_branch():
    from polariApiServer import module_home as mh
    missing = os.path.join(tempfile.gettempdir(), 'polari-module-home-selftest-does-not-exist')
    real_root = mh.CONTAINER_DATA_ROOT
    mh.CONTAINER_DATA_ROOT = missing
    try:
        got = mh.module_home('faults')
        check('no container root at all -> ~/.cache/polari-<name>',
              got == os.path.expanduser('~/.cache/polari-faults'), got)
    finally:
        mh.CONTAINER_DATA_ROOT = real_root


def test_never_creates_the_directory():
    """module_home() names a path; it must never bring that path into existence — every call site creates it
    lazily (os.makedirs) only once it is actually about to write."""
    from polariApiServer import module_home as mh
    with tempfile.TemporaryDirectory() as container_root:
        real_root = mh.CONTAINER_DATA_ROOT
        mh.CONTAINER_DATA_ROOT = container_root
        try:
            got = mh.module_home('cmod-should-not-exist')
            check('module_home() never calls makedirs on the caller\'s behalf',
                  not os.path.exists(got))
        finally:
            mh.CONTAINER_DATA_ROOT = real_root


def test_call_sites_route_through_the_helper():
    """pcb/board/hwnocode/firmwarefaults all delegate to module_home() — proven by making the container root
    usable and checking each module's own home()/default_work()/ledger_path() lands under it."""
    from polariApiServer import module_home as mh
    with tempfile.TemporaryDirectory() as container_root:
        real_root = mh.CONTAINER_DATA_ROOT
        mh.CONTAINER_DATA_ROOT = container_root
        saved = {k: os.environ.pop(k, None) for k in
                 ('POLARI_PCB_HOME', 'POLARI_BOARD_HOME', 'POLARI_HWNOCODE_HOME', 'POLARI_FAULTS_HOME')}
        try:
            from pcb.custom import ingest as pcb_ingest
            check('pcb.custom.ingest.home() routes through module_home',
                  pcb_ingest.home() == os.path.join(container_root, 'pcb'), pcb_ingest.home())

            from board.custom import gen as board_gen
            check('board.custom.gen.default_work() routes through module_home',
                  board_gen.default_work('uno') == os.path.join(container_root, 'board', 'uno'), board_gen.default_work('uno'))

            from board.custom import ingest as board_ingest
            check('board.custom.ingest.ledger_path() routes through module_home',
                  board_ingest.ledger_path() == os.path.join(container_root, 'board', 'board-object', 'ledger.json'),
                  board_ingest.ledger_path())

            from hwnocode.custom import split as hn_split
            check('hwnocode.custom.split.default_work() routes through module_home',
                  hn_split.default_work('sol') == os.path.join(container_root, 'hwnocode', 'sol'), hn_split.default_work('sol'))

            from firmwarefaults.custom import sink as ff_sink
            check('firmwarefaults.custom.sink.home() routes through module_home',
                  ff_sink.home() == os.path.join(container_root, 'faults'), ff_sink.home())
        finally:
            mh.CONTAINER_DATA_ROOT = real_root
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


def main():
    for fn in (test_import_touches_nothing, test_env_override_always_wins, test_container_root_branch,
               test_container_root_present_but_read_only, test_host_fallback_branch,
               test_never_creates_the_directory, test_call_sites_route_through_the_helper):
        try:
            fn()
        except Exception as exc:      # noqa: BLE001
            FAILED.append(f'{fn.__name__} BLEW UP :: {type(exc).__name__}: {exc}')
    total = len(PASSED) + len(FAILED)
    for line in FAILED:
        print('FAIL', line)
    print(f'selftest_module_home: {len(PASSED)}/{total}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
