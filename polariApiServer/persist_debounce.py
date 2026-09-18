"""polariApiServer.persist_debounce — ONE trailing persist per burst of writes, plus a flush on SIGTERM.

Why this exists (ledger §51, 2026-09-17): an `AppPermissionProfile` a permissions admin concreted through
CRUDE was **silently lost** when the stack was redeployed four minutes later. CRUDE's own
`db.saveInstanceInDB()` covers the row's own table, but anything that write touched elsewhere in the tree
(and any class whose table was not ready at that moment) only reached
`/app/data/managerObject_DB.db` on a LATER `persistTree()` — of which there was none before the redeploy.
A person creating a row through the API has no way to know that.

The contract:

    schedule_persist(manager)   a full persistTree() runs `delay` seconds from now, ONCE, no matter how many
                                writes land inside that window (a burst of 500 CRUDE creates = one flush).
                                Never blocks the request thread, never raises, daemon timer (a pending flush
                                never holds the process open — SIGTERM handles the tail).
    flush_now(manager)          persist once, synchronously, guarded. What SIGTERM and shutdown paths call.
    install_sigterm_flush(mgr)  on SIGTERM: flush once, then hand the signal back to whatever handler was
                                installed before (the default = terminate). So `docker service update
                                --force` cannot lose the last seconds of writes.

The debounce is a WINDOW, deliberately, not a restart-on-every-write trailing edge: a continuous stream of
writes must not starve the flush forever. Every write is on disk within `delay` seconds of itself.

Knobs:
    POLARI_PERSIST_DEBOUNCE_SECONDS   the window (default 3.0; 0 = flush inline, for tests)
    POLARI_PERSIST_ON_SIGTERM         'off' to skip the shutdown flush (default on)

This helper is CORE-resident so polariCRUDE can import it unconditionally; `security_observe._schedule_persist`
(which invented the pattern) now delegates here so there is exactly one implementation.
"""

import os
import threading

DEFAULT_DELAY = 3.0
DELAY_ENV = 'POLARI_PERSIST_DEBOUNCE_SECONDS'
SIGTERM_ENV = 'POLARI_PERSIST_ON_SIGTERM'

_LOCK = threading.Lock()
_STATE = {}          # id(manager) -> counters (see stats())
_SIGTERM = {'installed': False, 'flushed': False}


def delay_seconds():
    raw = (os.environ.get(DELAY_ENV) or '').strip()
    if not raw:
        return DEFAULT_DELAY
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_DELAY


def _state_for(manager):
    return _STATE.setdefault(id(manager), {'pending': False, 'scheduled': 0,
                                           'flushed': 0, 'failed': 0})


def stats(manager):
    """What this manager's debounce has done — the selftest's evidence, and a cheap thing to print."""
    with _LOCK:
        st = dict(_state_for(manager))
    st.pop('timer', None)
    return st


def reset(manager):
    """Forget a manager's counters (test doubles are short-lived and id() is reused)."""
    with _LOCK:
        _STATE.pop(id(manager), None)


def schedule_persist(manager, delay=None, reason=''):
    """Schedule the trailing persist for this burst. True = this call started the timer (or flushed inline
    with delay=0); False = one is already pending, or the manager cannot persist. Never raises."""
    try:
        if manager is None or not hasattr(manager, 'persistTree'):
            return False
        wait = delay_seconds() if delay is None else max(0.0, float(delay))
        with _LOCK:
            st = _state_for(manager)
            if st['pending']:
                return False
            st['pending'] = True
            st['scheduled'] += 1
        if wait == 0.0:
            _run(manager, reason)
            return True

        timer = threading.Timer(wait, _run, args=(manager, reason))
        timer.daemon = True
        with _LOCK:
            _state_for(manager)['timer'] = timer
        timer.start()
        return True
    except Exception:
        return False


def _run(manager, reason=''):
    with _LOCK:
        _state_for(manager)['pending'] = False
    flush_now(manager, reason=reason)


def flush_now(manager, reason=''):
    """persistTree() once, right now, guarded. True on success."""
    if manager is None or not hasattr(manager, 'persistTree'):
        return False
    try:
        manager.persistTree()
    except Exception as exc:                                   # noqa: BLE001
        with _LOCK:
            _state_for(manager)['failed'] += 1
        print(f'[Persist] flush FAILED ({reason or "scheduled"}): '
              f'{exc.__class__.__name__}: {exc}', flush=True)
        return False
    with _LOCK:
        _state_for(manager)['flushed'] += 1
    return True


def pending(manager):
    return stats(manager)['pending']


def install_sigterm_flush(manager, signum=None):
    """Flush the tree once on SIGTERM, then let the previous handler (the default = terminate) have it.

    Called from the main thread at boot. Returns True when the handler was installed. Idempotent; a second
    manager does not replace the first. `POLARI_PERSIST_ON_SIGTERM=off` skips it entirely."""
    if (os.environ.get(SIGTERM_ENV) or '').strip().lower() in ('off', '0', 'false', 'no'):
        print('[Persist] SIGTERM flush disabled by '
              f'{SIGTERM_ENV} — the last writes of a burst can be lost on stop', flush=True)
        return False
    if _SIGTERM['installed'] or manager is None or not hasattr(manager, 'persistTree'):
        return False
    import signal
    sig = signal.SIGTERM if signum is None else signum
    try:
        if threading.current_thread() is not threading.main_thread():
            return False
        previous = signal.getsignal(sig)
    except (ValueError, AttributeError, OSError):
        return False

    def handler(received, frame):
        if not _SIGTERM['flushed']:
            _SIGTERM['flushed'] = True
            print('[Persist] SIGTERM — flushing the object tree before we go', flush=True)
            flush_now(manager, reason='SIGTERM')
        if callable(previous):
            return previous(received, frame)
        # re-raise with the DEFAULT disposition so the process dies exactly as it would have
        try:
            signal.signal(sig, signal.SIG_DFL)
            os.kill(os.getpid(), sig)
        except Exception:                                      # noqa: BLE001
            os._exit(143)

    try:
        signal.signal(sig, handler)
    except (ValueError, OSError):
        return False
    _SIGTERM['installed'] = True
    print('[Persist] SIGTERM flush armed — a stop/redeploy persists the tree first', flush=True)
    return True
