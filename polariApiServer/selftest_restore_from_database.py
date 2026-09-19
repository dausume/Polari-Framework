"""
selftest_restore_from_database — THE OTHER RESTORE PATH (§66 addendum 5,
2026-09-19).

    PYTHONPATH=.:modules python3 polariApiServer/selftest_restore_from_database.py

§66e made `polariServer._restoreDefinitionInstances` MERGE instead of skip.
It left the main path — `objectTreeManagerDecorators.restoreFromDatabase` →
`_restoreTableRows` → `identifySeedDBIds` — untouched, on the belief that it
"skips by matching ids, so it looks sound". It does not skip by id, and it was
not sound. Two defects, both of them the same root cause as §66e: lazy boot
serves requests WHILE the restore walks the tree.

  1. **It crashed the admission worker.** `identifySeedDBIds` walked the LIVE
     `objectTables` dict. A request that creates a row of a class nobody had
     touched yet adds a KEY mid-walk, and python raises
     `RuntimeError: dictionary changed size during iteration` straight out of
     `restoreTables()`. Seen live on `polari-lean` on two consecutive boots —
     `[LazyBoot] islemesh FAILED: dictionary changed size during iteration`,
     then `polariapps`, which blocked `appstore` and `iso` behind it and left
     every `/api/apps/security/*` door answering 503. The same hazard sits on
     the inner loop, where an observer bumping a counter creates a SIBLING
     instance of the very class being fingerprinted.

  2. **It leaves a duplicate the merge then refused to fold.** At module
     admission `lazy_boot._admit` runs `restoreTables()` FIRST and
     `ensureDefinitionTables()` (the merge) second. The table restore has no
     name logic at all, so it happily inserts the persisted row beside a
     boot-time row of the same name; the merge then saw the persisted id
     already in `objectTables`, counted it "already restored" and moved on
     WITHOUT folding. Two rows for one subject — the §66d duplicate, arriving
     from the restore rather than from the observer. The fold now runs on that
     branch too.

  3. **The two paths disagreed about what "already here" means.** The seed
     FINGERPRINT (`identifySeedDBIds`, a >=60% property match) drops a
     persisted row that merely RESEMBLES a live one — so a row that has
     DIVERGED from its boot-time twin, which is exactly what a person's
     `confirmed` ruling beside an observer's `suggested` guess looks like, was
     dropped as if it were a re-created seed. Live every boot on `polari-lean`:
     `[DB] Found 1 seed IDs for InboundPolicy`, and no restore of that table.
     Where the merge runs afterwards it puts the row back; where it does not —
     a module whose admission died between `restoreTables()` and
     `ensureDefinitionTables()`, which defect 1 did four times — the ruling is
     gone and the next persist writes the half-booted tree over it.

     So for the classes the MERGE governs (`polariServer.defClassList`,
     published to `manager.mergeGovernedClasses()`) one rule now decides it on
     both paths: restore by id, fold the boot-time twin by name. Every other
     class keeps the fingerprint exactly as it was — a pure seed whose code
     definition changed must still lose to the code, and only the merge knows
     how to make that call by name.

No server, no database, no network: a fake `db` answers `getAllInTable` the way
the real one does, and the REAL methods are bound to a double.
"""

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'modules'))

PASSED, FAILED = [], []


def check(name, cond, detail=''):
    (PASSED if cond else FAILED).append(name if cond else f'{name} :: {detail}')


# ---- the doubles --------------------------------------------------------

COLUMNS = ['_branch_path', 'id', 'name', 'state', 'confirmed_by', 'count']

# SecurityDecision's real column set (modules/polariapps/objects/apps_security/
# SecurityDecision.py). It is the shape the fingerprint gets WRONG: converge
# recomputes the descriptive half identically, so a persisted row differs from
# its boot-time twin only in the ruling half and clears 60% easily.
DECISION_COLUMNS = ['_branch_path', 'id', 'name', 'app', 'app_version',
                    'release', 'kind', 'subject', 'evidence_json',
                    'derived_from', 'state', 'confirmed_by', 'confirmed_at']


class Row:
    """A row shaped like the policy/decision rows: `name` is the dedup key,
    `state`/`confirmed_by` are a person's, `count` is an observation."""

    def __init__(self, manager=None, id='', name='', state='',
                 confirmed_by='', count=0, **_ignored):
        self.manager = manager
        self.id = id
        self.name = name
        self.state = state
        self.confirmed_by = confirmed_by
        self.count = int(count or 0)
        if manager is not None:
            manager.objectTables.setdefault(
                type(self).__name__, {})[id or name] = self


class Decision:
    """A row with a wide descriptive half and a narrow ruling half."""

    def __init__(self, manager=None, id='', name='', app='', app_version='',
                 release='', kind='', subject='', evidence_json='',
                 derived_from='', state='', confirmed_by='', confirmed_at='',
                 **_ignored):
        self.manager = manager
        self.id = id
        self.name = name
        self.app = app
        self.app_version = app_version
        self.release = release
        self.kind = kind
        self.subject = subject
        self.evidence_json = evidence_json
        self.derived_from = derived_from
        self.state = state
        self.confirmed_by = confirmed_by
        self.confirmed_at = confirmed_at
        if manager is not None:
            manager.objectTables.setdefault(
                type(self).__name__, {})[id or name] = self


class Typing:
    def __init__(self, cls):
        self.cls = cls
        self.identifiers = ['id']

    def getCreateMethod(self):
        return self.cls

    def deserializeColumnValue(self, colName, value):
        return value


class FakeDb:
    """`onRead` is the REQUEST arriving mid-restore: the live stack's health
    probe, ct-9's traffic middleware, ct-8's converge-on-read."""

    def __init__(self, rows, onRead=None, columns=None):
        self.rows = rows
        self.tables = list(rows)
        self.onRead = onRead
        self.columns = columns or COLUMNS
        self.reads = 0

    def getAllInTable(self, className):
        self.reads += 1
        if self.onRead is not None:
            self.onRead(self.reads, className)
        return self.columns, list(self.rows.get(className, []))


class FakeManager:
    """Only what the two restore paths touch. The real methods are bound on,
    so the code under test is the shipped code."""

    def __init__(self, db, classes, merged=()):
        self.db = db
        self.objectTables = {}
        self.objectTypingDict = {name: Typing(cls)
                                 for name, cls in classes.items()}
        self.tombstoned = []
        from objectTreeManagerDecorators import managerObject
        for method in ('identifySeedDBIds', '_restoreTableRows',
                       'mergeGovernedClasses'):
            setattr(self, method,
                    getattr(managerObject, method).__get__(self, type(self)))
        # what polariServer._noteMergeGovernedClasses publishes at boot
        self.mergeGovernedClasses().update(merged)

    def noteTreeDeletion(self, className, instanceId):
        self.tombstoned.append((className, instanceId))
        return 1


def persisted(rowId, name, state, by, count):
    return [None, rowId, name, state, by, count]


def decision(rowId, state, by, at):
    """One subject, twice: the descriptive half is what converge recomputes
    identically on every read, the last three are the ruling."""
    return [None, rowId, 'app-policy|v1|owner-policy|MealEntry', 'app-policy',
            'v1', 'set-862f3c1e', 'owner-policy', 'MealEntry',
            '{"policy_row": false}', 'enumerate', state, by, at]


def server_with(manager):
    from polariApiServer.polariServer import polariServer
    obj = types.SimpleNamespace(manager=manager)
    for method in ('_restoreDefinitionInstances', '_mergeRestoredRows',
                   '_foldNameDuplicates', '_foldBootRow'):
        setattr(obj, method,
                getattr(polariServer, method).__get__(obj, type(obj)))
    return obj


def rows_of(manager, className):
    return list((manager.objectTables.get(className) or {}).values())


# ---- 1. the crash -------------------------------------------------------

def test_a_request_adding_a_CLASS_does_not_crash_the_restore():
    """The live failure: a request creates the first row of a class nobody
    had touched, so a KEY appears in objectTables while the fingerprint walks
    it. Before the fix this raised RuntimeError out of restoreTables() and
    failed the whole module admission."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='boot-1', name='a', state='suggested', count=1)

    class Latecomer(Row):
        pass

    m.objectTypingDict['Latecomer'] = Typing(Latecomer)
    db.tables.append('Latecomer')
    db.rows['Latecomer'] = []
    # The request lands on the first table read — mid-walk, exactly as the
    # health probe did on polari-lean.
    db.onRead = lambda n, cls: (Latecomer(manager=m, id='req-1', name='new')
                                if n == 1 else None)
    try:
        seeds = m.identifySeedDBIds()
        crashed = ''
    except Exception as exc:                                   # noqa: BLE001
        seeds, crashed = None, f'{type(exc).__name__}: {exc}'
    check('a class created by a request mid-restore does not blow the '
          'fingerprint up', crashed == '', crashed)
    check('the walk still answered for the classes it did see',
          isinstance(seeds, dict), repr(seeds))


def test_a_request_adding_an_INSTANCE_does_not_crash_the_restore():
    """The same hazard one level in: an observer bumping a counter creates a
    sibling instance of the class being fingerprinted."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5)]})
    m = FakeManager(db, {'Row': Row})
    racer = Row(manager=m, id='boot-1', name='a', state='suggested', count=1)

    class Racing(Row):
        """Reading a column is where the inner loop spends its time, so that
        is where the sibling arrives."""
        _fired = False

        @property
        def state(self):
            if not Racing._fired:
                Racing._fired = True
                Row(manager=self.manager, id='req-2', name='b',
                    state='suggested', count=1)
            return self._state

        @state.setter
        def state(self, value):
            self._state = value

    racer.__class__ = Racing
    try:
        m.identifySeedDBIds()
        crashed = ''
    except Exception as exc:                                   # noqa: BLE001
        crashed = f'{type(exc).__name__}: {exc}'
    check('an instance created by a request mid-fingerprint does not blow '
          'the fingerprint up', crashed == '', crashed)


# ---- 2. what the path actually does with the persisted rows -------------

def test_table_restore_never_deletes_a_boot_time_row():
    """The path is additive: it constructs instances and sets columns on
    them. It never pops objectTables, never tombstones, never writes. So a
    boot-time row is never overwritten — it is left standing BESIDE the
    persisted one, which is the duplicate the merge has to clean up."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='boot-1', name='a', state='suggested', count=1)
    m._restoreTableRows(['Row'])
    rows = {r.id: r for r in rows_of(m, 'Row')}
    check('the boot-time row is still there, untouched',
          'boot-1' in rows and rows['boot-1'].state == 'suggested',
          repr(sorted(rows)))
    check('nothing was tombstoned by the table restore', m.tombstoned == [],
          repr(m.tombstoned))


def test_admission_order_leaves_ONE_row_per_name():
    """`lazy_boot._admit` runs restoreTables() and THEN the merge. Run them in
    that order over a class a request already wrote during boot: the table
    restore inserts the persisted row beside the boot-time one, and the merge
    must fold the duplicate away even though the persisted id is already in
    the tree ("already restored")."""
    db = FakeDb({'Row': [persisted('db-1', 'anonymous|anonymous', 'confirmed',
                                   'sub-9', 14)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='boot-1', name='anonymous|anonymous', state='suggested',
        confirmed_by='', count=7)
    m._restoreTableRows(['Row'])            # the path §66e did not touch
    before = len(rows_of(m, 'Row'))
    server_with(m)._restoreDefinitionInstances([Row])   # the merge
    rows = rows_of(m, 'Row')
    check('the table restore really does produce the duplicate (this is what '
          'the merge has to clean up)', before == 2, before)
    check('after the merge ONE row survives, not two', len(rows) == 1,
          repr([(r.id, r.state, r.count) for r in rows]))
    if not rows:
        return
    row = rows[0]
    check('it is the PERSISTED row, with the person\'s ruling intact',
          row.id == 'db-1' and row.state == 'confirmed'
          and row.confirmed_by == 'sub-9',
          f'{row.id}/{row.state}/{row.confirmed_by}')
    check('the boot-time observations are summed in, not thrown away',
          row.count == 21, row.count)
    check('the boot-time row is TOMBSTONED so a persist in flight cannot '
          'write it back', ('Row', 'boot-1') in m.tombstoned,
          repr(m.tombstoned))


def test_admission_order_is_idempotent():
    """The merge runs again on later passes. Nothing may be folded twice and
    no counter may be summed into itself."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 14)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='boot-1', name='a', state='suggested', count=7)
    m._restoreTableRows(['Row'])
    srv = server_with(m)
    srv._restoreDefinitionInstances([Row])
    srv._restoreDefinitionInstances([Row])
    srv._restoreDefinitionInstances([Row])
    rows = rows_of(m, 'Row')
    check('three merge passes leave one row with the count summed ONCE',
          len(rows) == 1 and rows[0].count == 21,
          repr([(r.id, r.count) for r in rows]))
    check('the boot-time row is tombstoned exactly once',
          m.tombstoned.count(('Row', 'boot-1')) == 1, repr(m.tombstoned))


def test_a_clean_boot_restores_exactly_as_before():
    """No boot-time writer: the two paths together must behave like the table
    restore always did — every row in, nothing folded, nothing tombstoned."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5),
                         persisted('db-2', 'b', 'suggested', '', 2)]})
    m = FakeManager(db, {'Row': Row})
    m._restoreTableRows(['Row'])
    server_with(m)._restoreDefinitionInstances([Row])
    rows = sorted(rows_of(m, 'Row'), key=lambda r: r.name)
    check('both persisted rows are restored with their own fields',
          [(r.id, r.name, r.state, r.count) for r in rows]
          == [('db-1', 'a', 'confirmed', 5), ('db-2', 'b', 'suggested', 2)],
          repr([(r.id, r.name, r.state, r.count) for r in rows]))
    check('nothing was tombstoned', m.tombstoned == [], repr(m.tombstoned))


def test_persist_bookkeeping_table_is_never_restored():
    """`polari_persist_state` holds "is a flush in flight", not objects. A
    restore that turned it into instances would resurrect bookkeeping as
    data."""
    db = FakeDb({'polari_persist_state': [persisted('p-1', 'flush', '', '', 0)],
                 'Row_variant': [persisted('v-1', 'v', '', '', 0)]})
    m = FakeManager(db, {'polari_persist_state': Row, 'Row_variant': Row})
    m._restoreTableRows(['polari_persist_state', 'Row_variant'])
    check('neither the persist marker nor a variant side table becomes an '
          'instance', m.objectTables == {}, repr(m.objectTables))


# ---- 3. the fingerprint, and the line the fix draws --------------------

def _decision_case(merged):
    """The live shape: a person's `confirmed` ruling in the database and the
    boot-time `open` row converge-on-read wrote for the same subject."""
    db = FakeDb({'Decision': [decision('db-1', 'confirmed', 'sub-9',
                                       '2026-09-19T02:15:01')]},
                columns=DECISION_COLUMNS)
    m = FakeManager(db, {'Decision': Decision}, merged=merged)
    Decision(manager=m, id='boot-1',
             name='app-policy|v1|owner-policy|MealEntry', app='app-policy',
             app_version='v1', release='set-862f3c1e', kind='owner-policy',
             subject='MealEntry', evidence_json='{"policy_row": false}',
             derived_from='enumerate', state='open')
    return db, m


def test_a_confirmed_row_of_a_MERGED_class_survives_the_fingerprint():
    """D2. The persisted row matches its boot-time twin on 8 of 11 comparable
    columns — 72%, well over the 60% the fingerprint calls a seed. For a class
    the merge governs it must be restored anyway, and the twin folded."""
    db, m = _decision_case({'Decision'})
    seeds = m.identifySeedDBIds()
    check('a merge-governed class is exempt from the fingerprint entirely',
          not seeds.get('Decision'), f'seeds={seeds}')
    m._restoreTableRows(['Decision'])
    check('so the table restore actually loads the confirmed row',
          any(r.state == 'confirmed'
              for r in rows_of(m, 'Decision')),
          repr([(r.id, r.state) for r in rows_of(m, 'Decision')]))
    server_with(m)._restoreDefinitionInstances([Decision])
    rows = rows_of(m, 'Decision')
    check('and the merge leaves ONE row — the person\'s ruling, intact',
          len(rows) == 1 and rows[0].id == 'db-1'
          and rows[0].state == 'confirmed'
          and rows[0].confirmed_by == 'sub-9',
          repr([(r.id, r.state, r.confirmed_by) for r in rows]))
    check('the boot-time twin is tombstoned',
          ('Decision', 'boot-1') in m.tombstoned, repr(m.tombstoned))


def test_the_ruling_survives_an_admission_that_dies_before_the_merge():
    """Why the exemption matters rather than being cosmetic. `_admit` is
    `restoreTables()` then `ensureDefinitionTables()`; defect 1 killed the
    worker BETWEEN them four times on `polari-lean`. With the fingerprint in
    charge the only copy of the ruling was dropped and the next persist wrote
    the half-booted tree over it. The table restore alone must now be enough."""
    db, m = _decision_case({'Decision'})
    m._restoreTableRows(['Decision'])          # ...and then the worker dies
    states = {r.state for r in rows_of(m, 'Decision')}
    check('the confirmed ruling is in the tree with no merge pass at all',
          'confirmed' in states, repr(states))


def test_the_same_row_of_a_NON_merge_class_is_STILL_dropped():
    """The bound of the fix, stated rather than implied: nothing changes for a
    class the merge does not govern. It is still the fingerprint's call, and
    the fingerprint still drops this row — which is why the exemption is the
    fix and not a tweak to the threshold."""
    db, m = _decision_case(())
    seeds = m.identifySeedDBIds()
    check('a class outside the merge keeps today\'s fingerprint behaviour '
          '(the row IS taken for a seed)',
          'db-1' in seeds.get('Decision', set()), f'seeds={seeds}')


def test_a_pure_seed_duplicate_of_a_NON_merge_class_is_still_dropped():
    """What the fingerprint is FOR: a seed instance the code re-creates every
    boot with a fresh id, and last boot's row for it in the database. Dropping
    that row is correct — the code's definition of a seed is the truth, and
    restoring it would duplicate the seed on every boot forever."""
    db = FakeDb({'Row': [persisted('seed-old', 'a pure seed', 'fixed', '', 0)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='seed-new', name='a pure seed', state='fixed',
        confirmed_by='', count=0)
    seeds = m.identifySeedDBIds()
    check('last boot\'s row for a re-created seed is recognised as a seed',
          'seed-old' in seeds.get('Row', set()), f'seeds={seeds}')
    m._restoreTableRows(['Row'])
    rows = rows_of(m, 'Row')
    check('so the seed is NOT duplicated by the restore',
          len(rows) == 1 and rows[0].id == 'seed-new',
          repr([(r.id, r.name) for r in rows]))


def test_a_pure_seed_of_a_MERGED_class_is_not_duplicated_either():
    """The exemption must not reintroduce the duplicate the fingerprint was
    protecting against. For a merge-governed class the persisted row IS
    restored — and then the merge folds the code-created seed into it by name,
    so there is still exactly one row."""
    db = FakeDb({'Row': [persisted('seed-old', 'a pure seed', 'fixed', '', 0)]})
    m = FakeManager(db, {'Row': Row}, merged={'Row'})
    Row(manager=m, id='seed-new', name='a pure seed', state='fixed',
        confirmed_by='', count=0)
    m._restoreTableRows(['Row'])
    server_with(m)._restoreDefinitionInstances([Row])
    rows = rows_of(m, 'Row')
    check('one row, not two — the merge deduplicates by name where the '
          'fingerprint used to deduplicate by resemblance',
          len(rows) == 1 and rows[0].id == 'seed-old',
          repr([(r.id, r.name) for r in rows]))
    check('the code-created seed is tombstoned, not left as a ghost',
          ('Row', 'seed-new') in m.tombstoned, repr(m.tombstoned))


def main():
    for fn in (test_a_request_adding_a_CLASS_does_not_crash_the_restore,
               test_a_request_adding_an_INSTANCE_does_not_crash_the_restore,
               test_table_restore_never_deletes_a_boot_time_row,
               test_admission_order_leaves_ONE_row_per_name,
               test_admission_order_is_idempotent,
               test_a_clean_boot_restores_exactly_as_before,
               test_persist_bookkeeping_table_is_never_restored,
               test_a_confirmed_row_of_a_MERGED_class_survives_the_fingerprint,
               test_the_ruling_survives_an_admission_that_dies_before_the_merge,
               test_the_same_row_of_a_NON_merge_class_is_STILL_dropped,
               test_a_pure_seed_duplicate_of_a_NON_merge_class_is_still_dropped,
               test_a_pure_seed_of_a_MERGED_class_is_not_duplicated_either):
        try:
            fn()
        except Exception as exc:                               # noqa: BLE001
            FAILED.append(
                f'{fn.__name__} BLEW UP :: {type(exc).__name__}: {exc}')
    for line in FAILED:
        print('FAIL', line)
    total = len(PASSED) + len(FAILED)
    print(f'selftest_restore_from_database: {len(PASSED)}/{total}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
