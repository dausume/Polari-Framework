"""
@module islemesh.islemesh_ingest_concurrency_selftest

Regression controls for the islemesh ingest doors under concurrency and persistence failure
(handoff 2026-11-09 item B; live evidence core 84, 2026-11-08: overlapping ingests for one device
raised KeyError in _replace_device_rows and the registry replacement answered 500 half-applied).

Isolated: fake manager (objectTables dict), fake DB, real row classes, real handlers, no Falcon
server, no network, no files. Run from polari-framework/:

  PYTHONPATH=.:modules python3 -m islemesh.islemesh_ingest_concurrency_selftest
"""
import json
import os
import tempfile
import threading
import time
from types import SimpleNamespace

from islemesh import islemesh_api
from islemesh.islemesh_api import IsleMeshAPI, _MUTATION_LOCK
from islemesh.custom import islemesh_engines

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra and not cond else ''))


class _Sink:
    def __init__(self):
        self.status = '200 OK'
        self.media = None


class FakeDB:
    """Records every save/delete; optional hooks make a call slow, refuse, or raise."""

    def __init__(self, save=None, delete=None, delete_hook=None):
        self.saves, self.deletes = [], []
        self._save, self._delete, self._delete_hook = save, delete, delete_hook
        self.lock = threading.Lock()

    def saveInstanceInDB(self, row):
        with self.lock:
            self.saves.append((type(row).__name__, getattr(row, 'name', None)))
        if self._save is not None:
            return self._save(row)
        return True

    def deleteRowsWhere(self, cls, column, value):
        if self._delete_hook is not None:
            self._delete_hook(cls, value)
        with self.lock:
            self.deletes.append((cls, value))
        if self._delete is not None:
            return self._delete(cls, value)
        return 1


def api_for(db):
    manager = SimpleNamespace(objectTables={}, db=db, idList=[], objectTyping=[])
    api = IsleMeshAPI.__new__(IsleMeshAPI)
    api.manager = manager
    return api, manager


def registry(apps):
    return {'domains': {}, 'subdomains': {},
            'apps': {name: {'domain': name + '.isle', 'modes': ['local'], 'updated_at': '',
                            'services': [{'name': name + '-api', 'subdomain': 'api', 'container': name + '-1',
                                          'port': 9000 + i, 'protocol': 'http'}]}
                     for i, name in enumerate(apps)}}


def post(api, suffix, payload):
    sink = _Sink()
    getattr(api, 'on_post_ingest_' + suffix)(IsleMeshAPI._FakeRequest(payload), sink)
    return sink


def rows(manager, cls):
    return list(manager.objectTables.get(cls, {}).values())


def main():
    # ---- 1. the doors are serialized: a slow replace blocks a competing ingest for the same device ----
    started, order = threading.Event(), []
    release = threading.Event()

    def slow_first_delete(cls, value):
        if cls == 'IsleApp' and not started.is_set():
            started.set()
            release.wait(5)          # hold the lock inside the first replacement
    db = FakeDB(delete_hook=slow_first_delete)
    api, manager = api_for(db)
    check('seed registry accepted', post(api, 'registry', {'device': 'pol-core', 'registry': registry(['a', 'b'])}).media['ok'])

    def first():
        order.append(('first-start', time.monotonic()))
        post(api, 'registry', {'device': 'pol-core', 'registry': registry(['c'])})
        order.append(('first-end', time.monotonic()))

    def second():
        started.wait(5)
        order.append(('second-start', time.monotonic()))
        post(api, 'registry', {'device': 'pol-core', 'registry': registry(['d', 'e'])})
        order.append(('second-end', time.monotonic()))
    t1, t2 = threading.Thread(target=first), threading.Thread(target=second)
    t1.start(); t2.start()
    started.wait(5); time.sleep(0.2); release.set(); t1.join(5); t2.join(5)
    names = {o[0]: o[1] for o in order}
    check('both ingests completed', 'first-end' in names and 'second-end' in names)
    check('second replacement ran only after the first finished (lock held across replace+insert)',
          names.get('second-end', 0) > names.get('first-end', 0) and
          all(n for n in names) and names['first-end'] <= names['second-end'])
    apps = sorted(getattr(r, 'name', '') for r in rows(manager, 'IsleApp'))
    check('last writer wins, no mixed snapshot', apps == ['d', 'e'], str(apps))
    check('services follow their apps', sorted(getattr(r, 'app_name', '') for r in rows(manager, 'IsleAppService')) == ['d', 'e'])

    # ---- 2. stress: many overlapping ingests of three kinds for one device, no exception, consistent end ----
    db = FakeDB(delete_hook=lambda cls, value: time.sleep(0.0005))
    api, manager = api_for(db)
    errors, oks = [], []

    def worker(i):
        try:
            kind = i % 3
            if kind == 0:
                sink = post(api, 'registry', {'device': 'econ-core', 'registry': registry(['w%d' % i, 'x'])})
            elif kind == 1:
                sink = post(api, 'device', {'device': 'econ-core', 'uplinks': [{'interface': 'eth%d' % i, 'kind': 'ethernet', 'link_up': True}]})
            else:
                sink = post(api, 'fragments', {'device': 'econ-core', 'fragments': {}})
            oks.append(bool((sink.media or {}).get('ok')))
        except Exception as exc:  # noqa: BLE001 - the test records it
            errors.append('%s: %s' % (type(exc).__name__, exc))
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
    for t in threads: t.start()
    for t in threads: t.join(10)
    check('30 overlapping ingests: no exception (was KeyError on core 84)', not errors, '; '.join(errors[:3]))
    check('30 overlapping ingests: every answer ok', len(oks) == 30 and all(oks))
    pairs = [(getattr(r, 'name', ''), getattr(r, 'device_name', '')) for r in rows(manager, 'IsleApp')]
    check('(name, device) pairs unique after the storm', len(pairs) == len(set(pairs)))
    check('exactly one registry snapshot survives (two apps)', len(pairs) == 2, str(pairs))
    check('exactly one uplink survives (replace semantics)', len(rows(manager, 'IsleUplink')) == 1)
    check('one device row', len(rows(manager, 'IsleDevice')) == 1)

    # ---- 3. a key that vanished between snapshot and pop is not an error ----
    api, manager = api_for(FakeDB())
    post(api, 'registry', {'device': 'd1', 'registry': registry(['p', 'q'])})
    table = manager.objectTables['IsleApp']
    victim = next(k for k, r in table.items() if getattr(r, 'name', '') == 'p')
    del table[victim]                                    # someone else removed it first
    sink = post(api, 'registry', {'device': 'd1', 'registry': registry(['r'])})
    check('vanished key tolerated, ingest ok', sink.media['ok'] and sink.status == '200 OK')
    check('vanished key: table holds only the new snapshot', sorted(getattr(r, 'name', '') for r in rows(manager, 'IsleApp')) == ['r'])

    # ---- 4. persistence truth: refused save -> 500, persisted false, words; memory still updated ----
    api, manager = api_for(FakeDB(save=lambda row: False))
    sink = post(api, 'registry', {'device': 'd2', 'registry': registry(['s'])})
    check('refused save answers 500', sink.status.startswith('500'), sink.status)
    check('refused save: ok false + persisted false + words', sink.media.get('ok') is False and sink.media.get('persisted') is False
          and 'not persisted' in sink.media.get('error', ''), json.dumps(sink.media)[:200])
    check('refused save: counts still reported for the retry', sink.media.get('counts') == {'IsleApp': 1, 'IsleAppService': 1})
    api, manager = api_for(FakeDB(save=lambda row: (_ for _ in ()).throw(RuntimeError('disk full'))))
    sink = post(api, 'device', {'device': 'd3', 'uplinks': []})
    check('raising save on device ingest answers 500 with the exception words', sink.status.startswith('500') and 'disk full' in sink.media.get('error', ''))
    sink = post(api, 'fragments', {'device': 'd3', 'fragments': {}})
    check('raising save on fragments ingest answers 500', sink.status.startswith('500'))
    # a delete the DB could not perform is a failure too (the row would return on restart)
    api, manager = api_for(FakeDB())
    post(api, 'registry', {'device': 'd4', 'registry': registry(['t'])})
    api.manager.db = FakeDB(delete=lambda cls, value: -1)
    sink = post(api, 'registry', {'device': 'd4', 'registry': registry(['u'])})
    check('unavailable delete (-1) answers 500 persisted false', sink.status.startswith('500') and sink.media.get('persisted') is False)
    api.manager.db = FakeDB(delete=lambda cls, value: (_ for _ in ()).throw(OSError('locked')))
    post(api, 'registry', {'device': 'd4', 'registry': registry(['v'])})
    sink = post(api, 'registry', {'device': 'd4', 'registry': registry(['w'])})
    check('raising delete answers 500 with words', sink.status.startswith('500') and 'locked' in sink.media.get('error', ''))
    # healthy DB: green, persisted implicit, no failure key
    api, manager = api_for(FakeDB())
    sink = post(api, 'registry', {'device': 'd5', 'registry': registry(['y'])})
    check('healthy DB answers 200 ok without persisted:false', sink.status == '200 OK' and sink.media['ok'] and 'persisted' not in sink.media)
    sink = post(api, 'device', {'device': 'd5', 'retire': True})
    check('retire answers ok on a healthy DB', sink.media.get('ok') and sink.media.get('retired') is True)
    check('retire removed the device rows', not rows(manager, 'IsleApp') and not rows(manager, 'IsleDevice'))

    # ---- 5. one module RLock, owned by islemesh_engines, wrapped around the right doors ----
    check('mutation lock is reentrant (mock re-posts through the doors)', 'RLock' in repr(_MUTATION_LOCK))
    check('the API doors and the registry consumer share ONE lock object', _MUTATION_LOCK is islemesh_engines.MUTATION_LOCK)
    for name in ('on_post_ingest_registry', 'on_post_ingest_fragments', 'on_post_ingest_device',
                 'on_post_mock', 'on_post_ingest_engine'):
        check('%s is serialized' % name, hasattr(getattr(IsleMeshAPI, name), '__wrapped__'))
    check('on_post_engines_sync is NOT wrapped (its fetch must run outside the lock; sync locks its apply)',
          not hasattr(IsleMeshAPI.on_post_engines_sync, '__wrapped__'))
    for name in ('on_get_devices', 'on_get_engines', 'on_get_summary'):
        check('%s stays lock-free' % name, not hasattr(getattr(IsleMeshAPI, name, None), '__wrapped__'))
    check('tracker is cleared after a door returns', getattr(islemesh_api._TRACKING, 'failures', None) is None)

    # ---- 6. sync_from_registry (every caller, incl. boot after_boot): fetch OUTSIDE the lock, apply UNDER it ----
    def held_by_someone_else():
        """True when another thread holds the lock (probe from a fresh thread; RLock is per-thread)."""
        result = {}
        def probe():
            got = _MUTATION_LOCK.acquire(blocking=False)
            result['free'] = got
            if got:
                _MUTATION_LOCK.release()
        t = threading.Thread(target=probe); t.start(); t.join(2)
        return not result.get('free', False)
    seen = {}
    def fetch(origin):
        seen['fetch_locked'] = held_by_someone_else()
        return [{'name': 'w@board', 'app': 'w', 'provides': 'board', 'url': 'https://w.isle', 'device': 'econ-core'}], ''
    def save(row):
        seen.setdefault('save_locked', held_by_someone_else())
        return True
    m = SimpleNamespace(objectTables={}, idList=[], objectTyping=[SimpleNamespace(className='EngineProviderBinding')], db=None)
    result = islemesh_engines.sync_from_registry(m, save=save, delete=lambda row: True, fetch=fetch,
                                                 env={'ISLE_CORE_API': 'https://api.polari.isle'})
    check('sync: registry fetch runs with the lock FREE (a slow core never stalls ingests)', seen.get('fetch_locked') is False)
    check('sync: apply phase (binds/records) runs with the lock HELD', seen.get('save_locked') is True)
    check('sync: result ok and bound', result['ok'] and result['bound'], result.get('words'))
    check('sync: lock released afterwards', not held_by_someone_else())

    # ---- 7. the REAL managedDatabase on a temporary sqlite: healthy tables save True / delete >= 0; a missing table is False ----
    from polariDBmanagement.managedDB import managedDatabase
    with tempfile.TemporaryDirectory() as tmp:
        db = managedDatabase(name='islemesh-concurrency-selftest')
        db.Path = tmp
        db.createFile()
        conn = db.adapter.connect()
        cur = conn.cursor()
        classes = {'IsleApp': islemesh_api.IsleApp, 'IsleAppService': islemesh_api.IsleAppService,
                   'IsleDevice': islemesh_api.IsleDevice, 'IsleUplink': islemesh_api.IsleUplink,
                   'IsleProtocolPermit': islemesh_api.IsleProtocolPermit, 'IsleIngestReceipt': islemesh_api.IsleIngestReceipt,
                   'IsleEngine': islemesh_api.IsleEngine, 'MeshAppRealization': islemesh_api.MeshAppRealization}
        fake_manager = SimpleNamespace(objectTables={}, db=None, idList=[], objectTyping=[])
        for cls_name, cls in classes.items():
            sample = cls(manager=fake_manager)
            cols = [k for k, v in sample.__dict__.items()
                    if not k.startswith('_') and isinstance(v, (str, int, float, bool, bytes, type(None), list, dict))
                    and k not in ('manager', 'polServer')]
            if 'id' not in cols:
                cols.insert(0, 'id')
            cur.execute('CREATE TABLE %s (%s)' % (cls_name, ', '.join(
                ('"%s" TEXT PRIMARY KEY' % c) if c == 'id' else '"%s" TEXT' % c for c in cols)))
        conn.commit(); conn.close()
        db.tables = list(classes)          # what jumpstart/ensureDefinitionTables would have registered
        api, manager = api_for(db)
        for cls_name, cls in classes.items():
            row = cls(manager=manager, name='probe-' + cls_name.lower()) if cls_name != 'IsleUplink' else cls(manager=manager, name='probe@eth0', device_name='probe')
            check('real sqlite: saveInstanceInDB(%s) is True on a healthy table' % cls_name, api._save(row) is True)
            check('real sqlite: deleteRowsWhere(%s) is >= 0 on a healthy table' % cls_name,
                  (db.deleteRowsWhere(cls_name, 'id', getattr(row, 'id', '')) or 0) >= 0)
        sink = post(api, 'registry', {'device': 'real-db', 'registry': registry(['r1'])})
        check('real sqlite: a full registry ingest answers 200 ok with no persisted:false', sink.status == '200 OK' and sink.media['ok'] and 'persisted' not in sink.media, json.dumps(sink.media)[:200])
        sink = post(api, 'device', {'device': 'real-db', 'uplinks': [{'interface': 'eth0', 'kind': 'ethernet', 'link_up': True}]})
        check('real sqlite: a device ingest answers 200 ok', sink.status == '200 OK' and sink.media['ok'])
        db.tables = [t for t in db.tables if t != 'IsleAppService']   # a lazy-boot ordering gap: table not registered yet
        sink = post(api, 'registry', {'device': 'real-db', 'registry': registry(['r2'])})
        check('real sqlite: an unregistered table is reported as not persisted (500), by design', sink.status.startswith('500') and 'IsleAppService' in sink.media.get('error', ''))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
