"""selftest_crude_delete_blast — deleting ONE row must not empty the class (ledger §51 addendum 2).

The defect this pins: `DELETE /AppPermissionProfile` with
`targetInstance={"name": "<one row>"}` answered 200 and the next
`GET /AppPermissionProfile` returned `[]` — every sibling gone. It
destroyed the three demo `AppPermissionProfile` rows, twice.

ROOT CAUSE (objectTreeManagerDecorators.py):
`getListOfInstancesByAttributes` handed the query engine
`self.objectTables[className]` **itself**, and
`dictAttributeRequirementsForQuery` narrows by `pop()`-ing the
non-matches out of the dict it is handed. So *resolving the delete
target* permanently removed every other row of the class from the live
tree; `deleteTreeNode` then removed the one survivor, and the next
`persistTree()` wrote the empty table to disk. Nothing in
`deleteTreeNode` was at fault — the damage was done by the lookup.

The fix is one word: the query engine works on a COPY.

Also pinned here: the legacy CRUDE access matrix must never grant an
ANONYMOUS caller more than an AUTHENTICATED one (it used to give
anonymous C/R/U/D/E and a real login only R/E, so a delete with an
admin bearer 405'd while the same delete with no bearer succeeded).

Run:  PYTHONPATH=.:modules python3 polariApiServer/selftest_crude_delete_blast.py
"""
import json
import os
import sqlite3
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label,
                            extra if not cond else ''))


class _Row:
    """A stand-in AppPermissionProfile row."""

    def __init__(self, rowId, name):
        self.id = rowId
        self.name = name


# ------------------------------------------------------- the query engine ---
def _probe(rows):
    """A bare object carrying the REAL manager query methods over a real
    objectTables dict — no server, no DB, no tree."""
    from objectTreeManagerDecorators import managerObject
    p = types.SimpleNamespace()
    p.objectTables = {'AppPermissionProfile': dict(rows)}
    for name in ('getListOfInstancesByAttributes',
                 'dictAttributeRequirementsForQuery',
                 'listConditionalRequirementsForQuery'):
        setattr(p, name, getattr(managerObject, name).__get__(p))
    return p


def test_query_does_not_mutate():
    print('[the query engine narrows a COPY, never the live class table]')
    rows = {'a': _Row('a', 'journalist'),
            'b': _Row('b', 'throwaway-1'),
            'c': _Row('c', 'throwaway-2')}

    p = _probe(rows)
    res = p.getListOfInstancesByAttributes(
        className='AppPermissionProfile',
        attributeQueryDict={'name': 'throwaway-1'})
    check('a name query resolves exactly the one row',
          sorted(res) == ['b'], sorted(res))
    check('the OTHER TWO rows are still in objectTables after the '
          'lookup (this is the whole defect)',
          sorted(p.objectTables['AppPermissionProfile']) == ['a', 'b', 'c'],
          sorted(p.objectTables['AppPermissionProfile']))

    p = _probe(rows)
    res = p.getListOfInstancesByAttributes(
        className='AppPermissionProfile', attributeQueryDict={'id': 'b'})
    check('an id query resolves one row', sorted(res) == ['b'], sorted(res))
    check('an id query leaves the class table whole',
          sorted(p.objectTables['AppPermissionProfile']) == ['a', 'b', 'c'],
          sorted(p.objectTables['AppPermissionProfile']))

    p = _probe(rows)
    res = p.getListOfInstancesByAttributes(
        className='AppPermissionProfile', attributeQueryDict={'name': 'nope'})
    check('an unmatched query resolves NOTHING (never everything)',
          res == {}, res)
    check('an unmatched query leaves the class table whole',
          sorted(p.objectTables['AppPermissionProfile']) == ['a', 'b', 'c'],
          sorted(p.objectTables['AppPermissionProfile']))

    p = _probe(rows)
    res = p.getListOfInstancesByAttributes(
        className='AppPermissionProfile', attributeQueryDict='*')
    check('"*" still returns every row', sorted(res) == ['a', 'b', 'c'],
          sorted(res))
    res.pop('a', None)
    check('mutating what "*" returned does not touch objectTables',
          sorted(p.objectTables['AppPermissionProfile']) == ['a', 'b', 'c'],
          sorted(p.objectTables['AppPermissionProfile']))


# ------------------------------------------------------ the real handler ----
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
        self.context = types.SimpleNamespace(user_info=None, roles=[],
                                             auth_failed=False)

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
    inheritsFrom = {}


class _FileDB:
    """A real sqlite file standing in for the persisted table, with the
    two methods the delete path touches."""

    def __init__(self, path):
        self.path = path
        conn = sqlite3.connect(path)
        conn.execute('CREATE TABLE AppPermissionProfile '
                     '(id TEXT PRIMARY KEY, name TEXT)')
        conn.commit()
        conn.close()
        self.tables = ['AppPermissionProfile']

    def seed(self, rows):
        conn = sqlite3.connect(self.path)
        conn.executemany('INSERT OR REPLACE INTO AppPermissionProfile '
                         '(id, name) VALUES (?, ?)',
                         [(r.id, r.name) for r in rows.values()])
        conn.commit()
        conn.close()

    def deleteRowsWhere(self, tableName, column, value):
        conn = sqlite3.connect(self.path)
        conn.execute(f'DELETE FROM {tableName} WHERE {column} = ?', (value,))
        conn.commit()
        conn.close()

    def ids(self):
        conn = sqlite3.connect(self.path)
        out = sorted(r[0] for r in
                     conn.execute('SELECT id FROM AppPermissionProfile'))
        conn.close()
        return out


class _Crude:
    """The REAL polariCRUDE.on_delete body, run against the REAL manager
    query engine and a real sqlite file."""

    def __init__(self, manager, db):
        self.manager = manager
        self.db = db
        self.apiObject = 'AppPermissionProfile'
        self.objTyping = _Typing()
        self.persisted = []

    def _guard_purged(self, response):
        return False

    def _refuse(self, response, status, error):
        response.status = status
        response.media = {'error': error}
        return None

    def _form_parts(self, request, response):
        return request.get_media()

    def _check_object_lock(self, instance, className=None):
        return None

    def _notify_ws_subscribers(self, operation, instanceIds=None):
        pass

    def _deleteFromDB(self, targetId, instancesDeleted):
        from polariApiServer.polariCRUDE import polariCRUDE
        return polariCRUDE._deleteFromDB(self, targetId, instancesDeleted)

    def getUsersObjectAccessPermissions(self, userAuthInfo):
        from polariApiServer.polariCRUDE import polariCRUDE
        return polariCRUDE.getUsersObjectAccessPermissions(self, userAuthInfo)

    def on_delete(self, request, response):
        from polariApiServer.polariCRUDE import polariCRUDE
        return polariCRUDE.on_delete(self, request, response)


def _manager_with_tree(rows):
    """The probe, plus the minimum `deleteTreeNode` contract (pop the one
    node) so the handler can run end to end."""
    p = _probe(rows)

    def deleteTreeNode(className=None, nodePolariId=None, **kw):
        (p.objectTables.get(className) or {}).pop(nodePolariId, None)
        return ([nodePolariId], [])

    p.deleteTreeNode = deleteTreeNode
    p.objectTypingDict = {'AppPermissionProfile': _Typing()}
    p.getChildInstancesReferencingParent = lambda *a, **k: {}
    p.persistTree = lambda progress=None: None
    return p


def test_delete_blast_radius(tmpdir):
    print('[DELETE of one row through the REAL handler]')
    rows = {'a': _Row('a', 'journalist'),
            'b': _Row('b', 'throwaway-1'),
            'c': _Row('c', 'throwaway-2')}
    db = _FileDB(os.path.join(tmpdir, 'blast.db'))
    db.seed(rows)
    manager = _manager_with_tree(rows)
    manager.db = db

    crude = _Crude(manager, db)
    # the exact request shape the API accepts: multipart, one
    # `targetInstance` form field holding a JSON attribute query.
    req = _Req([_Part('targetInstance', json.dumps({'name': 'throwaway-1'}))])
    res = _Res()
    crude.on_delete(req, res)

    check('the delete answered 200', str(res.status).startswith('200'),
          res.status)
    live = sorted(manager.objectTables['AppPermissionProfile'])
    check('the target is gone from the live table', 'b' not in live, live)
    check('BOTH SURVIVORS are still in the live table',
          live == ['a', 'c'], live)
    onDisk = db.ids()
    check('the target is gone from the persisted table',
          'b' not in onDisk, onDisk)
    check('BOTH SURVIVORS are still in the persisted table',
          onDisk == ['a', 'c'], onDisk)

    # and a second delete of a sibling still resolves — it could not,
    # before, because the siblings were already gone.
    req = _Req([_Part('targetInstance', json.dumps({'name': 'throwaway-2'}))])
    res = _Res()
    crude.on_delete(req, res)
    live = sorted(manager.objectTables['AppPermissionProfile'])
    check('deleting the second throwaway leaves the real row alone',
          str(res.status).startswith('200') and live == ['a'],
          f'{res.status} {live}')
    check('and the real row survives on disk too', db.ids() == ['a'],
          db.ids())


def test_unmatched_target_is_a_404(tmpdir):
    print('[an unmatched target is a 404, never a class wipe]')
    rows = {'a': _Row('a', 'journalist'), 'b': _Row('b', 'throwaway-1')}
    db = _FileDB(os.path.join(tmpdir, 'blast2.db'))
    db.seed(rows)
    manager = _manager_with_tree(rows)
    manager.db = db
    crude = _Crude(manager, db)
    req = _Req([_Part('targetInstance', json.dumps({'name': 'not-a-row'}))])
    res = _Res()
    crude.on_delete(req, res)
    check('unresolved target -> 404', str(res.status).startswith('404'),
          res.status)
    check('nothing was removed from the live table',
          sorted(manager.objectTables['AppPermissionProfile']) == ['a', 'b'],
          sorted(manager.objectTables['AppPermissionProfile']))
    check('nothing was removed from disk', db.ids() == ['a', 'b'], db.ids())


# ------------------------------------------------- the access matrix -------
def test_access_matrix_not_inverted():
    print('[the legacy access matrix: authenticated >= anonymous]')
    from polariApiServer.polariCRUDE import polariCRUDE
    shim = types.SimpleNamespace(apiObject='AppPermissionProfile')
    anonAccess, anonPerms = polariCRUDE.getUsersObjectAccessPermissions(
        shim, None)
    authAccess, authPerms = polariCRUDE.getUsersObjectAccessPermissions(
        shim, {'username': 'demo-admin', 'roles': ['polari-admin']})
    check('an anonymous caller is not granted a verb an authenticated '
          'caller lacks',
          set(anonAccess) <= set(authAccess),
          f'anon={sorted(anonAccess)} auth={sorted(authAccess)}')
    check('the same holds for the variable-permission matrix',
          set(anonPerms) <= set(authPerms),
          f'anon={sorted(anonPerms)} auth={sorted(authPerms)}')
    check('an authenticated caller may DELETE (the 405 that made an '
          'admin bearer weaker than no bearer at all)',
          'D' in authAccess, sorted(authAccess))


def main():
    tmpdir = tempfile.mkdtemp(prefix='crude-delete-blast-')
    test_query_does_not_mutate()
    test_delete_blast_radius(tmpdir)
    test_unmatched_target_is_a_404(tmpdir)
    test_access_matrix_not_inverted()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
