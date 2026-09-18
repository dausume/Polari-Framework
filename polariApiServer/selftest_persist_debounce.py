"""selftest_persist_debounce — a CRUDE write reaches DISK, not just memory (ledger §51).

The defect this proves fixed: an `AppPermissionProfile` a permissions admin concreted through CRUDE was
silently lost when the stack was redeployed four minutes later, because the tree only reached
`/app/data/managerObject_DB.db` on a later flush that never came. Now every successful create / update /
delete schedules ONE trailing `persistTree()` per burst, and SIGTERM flushes once before the process dies.

Run:  PYTHONPATH=.:modules python3 polariApiServer/selftest_persist_debounce.py
"""
import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


# ---------------------------------------------------------------- doubles ---
class _Manager:
    """The smallest thing CRUDE needs: tables, no DB (so the row's own save is a no-op) and a countable
    persistTree — the flush whose absence lost the profile."""

    def __init__(self, className='Thing'):
        self.className = className
        self.objectTables = {className: {}}
        self.objectTypingDict = {className: object()}
        self.db = None
        self.persists = []

    def persistTree(self, progress=None):
        self.persists.append({k: dict(v) for k, v in self.objectTables.items()})

    def getJSONdictForClass(self, passedInstances=None):
        return [{'id': getattr(i, 'id', '')} for i in (passedInstances or [])]

    def getListOfInstancesByAttributes(self, className=None, attributeQueryDict=None):
        rows = self.objectTables.get(className) or {}
        if not attributeQueryDict:
            return dict(rows)
        return {i: r for i, r in rows.items()
                if all(getattr(r, k, None) == v for k, v in attributeQueryDict.items())}

    def deleteTreeNode(self, className=None, nodePolariId=None):
        (self.objectTables.get(className) or {}).pop(nodePolariId, None)
        return ([nodePolariId], [])


class _Part:
    def __init__(self, name, value):
        self.name = name
        self.content_type = 'application/json'
        self.data = value.encode('utf-8')


class _Req:
    auth = None
    query_string = ''
    content_type = 'multipart/form-data; boundary=x'

    def __init__(self, parts):
        self._parts = parts
        self.context = types.SimpleNamespace(user_info=None, roles=[], auth_failed=False)

    def get_media(self):
        return self._parts


class _Res:
    def __init__(self):
        self.status = ''
        self.media = None
        self.headers = {}

    def set_header(self, k, v):
        self.headers[k] = v


class _Typing:
    isMultiInheritanceClass = False
    inheritedByClasses = {}
    inheritanceCascade = 'prevent'
    kwRequiredParams = ['name']
    kwDefaultParams = ['id']
    inheritsFrom = {}

    def __init__(self, manager, className):
        self.manager = manager
        self.className = className

    def getCreateMethod(self, returnTupWithParams=False):
        def create(manager=None, **kw):
            inst = types.SimpleNamespace(**kw)
            inst.id = kw.get('id') or ('id-' + str(kw.get('name')))
            manager.objectTables[self.className][inst.id] = inst
            return inst
        return create


class _Crude:
    """A polariCRUDE stand-in: the REAL on_post / on_put / on_delete bodies run against it (they are plain
    functions on the class), with the surrounding machinery stubbed to the minimum."""

    def __init__(self, manager, className='Thing'):
        self.manager = manager
        self.apiObject = className
        self.objTyping = _Typing(manager, className)
        self.notified = []

    # the bits of polariCRUDE the handlers lean on
    def _guard_purged(self, response):
        return False

    def _refuse(self, response, status, error):
        response.status = status
        response.media = {'ok': False, 'error': error}
        return None

    def _form_parts(self, request, response):
        return request.get_media()

    def _check_object_lock(self, instance, className=None):
        return None

    def _deleteFromDB(self, targetId, instancesDeleted):
        return None

    def _notify_ws_subscribers(self, operation, instanceIds=None):
        self.notified.append((operation, list(instanceIds or [])))

    def getUsersObjectAccessPermissions(self, userAuthInfo):
        q = {v: {self.apiObject: {}} for v in ('C', 'R', 'U', 'D', 'E')}
        return (q, {v: {self.apiObject: {}} for v in ('C', 'R', 'U', 'D', 'E')})


def main():
    from polariApiServer import persist_debounce as P
    from polariApiServer.polariCRUDE import polariCRUDE

    # ------------------------------------------------ the debounce itself ---
    m = _Manager()
    P.reset(m)
    check('a manager with no persistTree is a stated no-op, never a crash',
          P.schedule_persist(types.SimpleNamespace()) is False
          and P.flush_now(None) is False)

    check('delay 0 flushes inline (the test idiom) and counts it',
          P.schedule_persist(m, delay=0) is True and len(m.persists) == 1
          and P.stats(m)['flushed'] == 1)

    P.reset(m)
    m.persists = []
    started = [P.schedule_persist(m, delay=0.15) for _ in range(6)]
    check('a BURST of 6 writes schedules exactly ONE flush, and it is pending',
          started == [True, False, False, False, False, False]
          and P.pending(m) is True and m.persists == [])
    time.sleep(0.45)
    check('the burst is on disk one window later — once, not six times',
          len(m.persists) == 1 and P.stats(m) ==
          {'pending': False, 'scheduled': 1, 'flushed': 1, 'failed': 0},
          P.stats(m))
    check('a write AFTER the window opens a new burst',
          P.schedule_persist(m, delay=0) is True and len(m.persists) == 2)

    boom = _Manager()
    boom.persistTree = lambda progress=None: (_ for _ in ()).throw(RuntimeError('disk on fire'))
    check('a failing flush is reported and counted, never raised into the request',
          P.flush_now(boom, reason='test') is False and P.stats(boom)['failed'] == 1)

    check('the window is a knob',
          P.delay_seconds() == P.DEFAULT_DELAY and P.DELAY_ENV == 'POLARI_PERSIST_DEBOUNCE_SECONDS')

    # ---------------------------------- a row created THROUGH CRUDE, §51 ----
    old = dict(os.environ)
    os.environ['POLARI_APP_PERMISSIONS'] = 'off'
    os.environ['POLARI_POSTURE'] = 'production'
    os.environ['POLARI_PERSIST_DEBOUNCE_SECONDS'] = '0'   # flush inline so the test is deterministic
    try:
        mgr = _Manager()
        P.reset(mgr)
        crude = _Crude(mgr)
        res = _Res()
        polariCRUDE.on_post(crude, _Req([_Part('initParamSets', '[{"name": "throwaway-profile"}]')]), res)
        check('CRUDE create: 201, the row is in the table, and the tree was PERSISTED '
              '(§51 — this is the write that used to be lost to a redeploy)',
              res.status == '201 Created' and 'id-throwaway-profile' in mgr.objectTables['Thing']
              and len(mgr.persists) == 1
              and 'id-throwaway-profile' in mgr.persists[-1]['Thing'],
              (res.status, len(mgr.persists)))

        res = _Res()
        polariCRUDE.on_put(crude, _Req([_Part('polariId', 'id-throwaway-profile'),
                                        _Part('updateData', '{"name": "renamed"}')]), res)
        check('CRUDE update: 200, the change persisted',
              res.status == '200 OK' and len(mgr.persists) == 2
              and mgr.objectTables['Thing']['id-throwaway-profile'].name == 'renamed',
              (res.status, len(mgr.persists)))

        res = _Res()
        polariCRUDE.on_delete(crude, _Req([_Part('targetInstance', '{"id": "id-throwaway-profile"}')]), res)
        check('CRUDE delete: 200, the row is gone from the table AND from the persisted snapshot',
              res.status == '200 OK' and len(mgr.persists) == 3
              and mgr.persists[-1]['Thing'] == {},
              (res.status, len(mgr.persists)))

        # a refusal must NOT claim a write
        mgr2 = _Manager()
        P.reset(mgr2)
        res = _Res()
        polariCRUDE.on_post(_Crude(mgr2), _Req([]), res)
        check('a refused create (no payload) persists nothing',
              res.status == '400 Bad Request' and mgr2.persists == [], res.status)
    finally:
        os.environ.clear()
        os.environ.update(old)

    # ------------------------------------------- the flush on SIGTERM -------
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        marker = os.path.join(td, 'flushed')
        script = (
            'import os, signal, sys\n'
            'sys.path.insert(0, %r)\n'
            'from polariApiServer.persist_debounce import install_sigterm_flush\n'
            'class M:\n'
            '    def persistTree(self, progress=None):\n'
            '        open(%r, "w").write("flushed")\n'
            'assert install_sigterm_flush(M()) is True\n'
            'os.kill(os.getpid(), signal.SIGTERM)\n'
            'print("STILL ALIVE")\n'
        ) % (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), marker)
        proc = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=60)
        check('SIGTERM (what `docker service update --force` sends): the tree is flushed ONCE, '
              'then the default handler kills the process exactly as before',
              os.path.exists(marker) and proc.returncode in (-15, 143)
              and 'STILL ALIVE' not in proc.stdout,
              (proc.returncode, proc.stdout[-200:], proc.stderr[-200:]))

        os.environ['POLARI_PERSIST_ON_SIGTERM'] = 'off'
        try:
            check('the shutdown flush is a knob that can be turned off',
                  install_off() is False)
        finally:
            os.environ.pop('POLARI_PERSIST_ON_SIGTERM', None)

    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


def install_off():
    from polariApiServer.persist_debounce import install_sigterm_flush
    class M:
        def persistTree(self, progress=None):
            pass
    return install_sigterm_flush(M())


if __name__ == '__main__':
    sys.exit(main())
