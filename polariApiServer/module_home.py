"""
@module polariApiServer.module_home

ONE shared helper for "where does this hardware module's working data live" — pcb (`POLARI_PCB_HOME`), board
(`POLARI_BOARD_HOME`), hwnocode (`POLARI_HWNOCODE_HOME`), firmwarefaults (`POLARI_FAULTS_HOME`), and any future
module home, all route through `module_home()` so they share ONE fallback ladder instead of each hand-rolling
`os.environ.get(VAR, '~/.cache/polari-<name>')`.

THE BUG this fixes: `pol pcb ingest`/render wrote SVG/Gerber artifacts under `~/.cache/polari-pcb` by default.
On the host that is a real home dir; INSIDE the backend container it is ephemeral container-layer storage (only
`/app/data` is the persistent named volume), so a redeploy drops the files while the FabricationExport rows
(committed to the DB) survive — `GET /api/pcb/artifacts/...` then answers 404 until someone re-ingests. The same
shape existed for board/hwnocode/firmwarefaults.

The ladder, in order:
  1. an explicit env override (`env`, or the module's own env var when the caller passes `env=os.environ.get('POLARI_PCB_HOME')`
     — see note below) — always wins, this is what a deployer sets to point somewhere else (e.g. the eventual
     SeaweedFS-backed path, AI-Notes/ledgers/TESTING_OWED.md).
  2. `/app/data/<name>` when `/app/data` exists AND is writable — true inside every backend container (the
     persistent named volume), false on a bare host checkout.
  3. `~/.cache/polari-<name>` — the host fallback (CLI-only use, `pol board gen` run straight on a dev box).

The directory is created LAZILY (on first real use, by the caller after it gets the path back — never at import
time and never inside this function) so importing a module never touches the filesystem and a read-only root
(permission probes, CI) never raises on `import`.
"""
import os

#: /app/data — the ONE path every backend compose service mounts as its persistent named volume (see README §7's
#: root-owned-artifacts gotcha: this is also why that volume's owner must be the host UID, not root).
CONTAINER_DATA_ROOT = '/app/data'


def _container_data_root_usable(root=None):
    """True when `root` exists, is a directory, and this process can write under it — the container tell.

    `root` defaults to the CURRENT value of the module-level `CONTAINER_DATA_ROOT` (looked up each call, not
    bound at def-time) so a selftest can monkeypatch it with a temp dir standing in for `/app/data`.
    """
    root = CONTAINER_DATA_ROOT if root is None else root
    return os.path.isdir(root) and os.access(root, os.W_OK | os.X_OK)


def module_home(name, env=None):
    """The home dir for module `name` ('pcb', 'board', 'hwnocode', 'faults', …) — never creates it.

    `env`: the module's own env-var VALUE if the caller already read one (e.g. `os.environ.get('POLARI_PCB_HOME')`),
    so each module keeps its own knob NAME (POLARI_PCB_HOME, POLARI_BOARD_HOME, …) while sharing this ladder; pass
    `None` (the default) or `''` to fall through to the container/host split below. A falsy `env` of any kind
    (None, '') falls through — only a real path wins outright.
    """
    if env:
        return os.path.expanduser(env)
    if _container_data_root_usable():
        return os.path.join(CONTAINER_DATA_ROOT, name)
    return os.path.expanduser(os.path.join('~/.cache/polari-%s' % name))
