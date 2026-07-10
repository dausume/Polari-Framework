"""
Selftest for polariDataTyping.schema_stability.

Run from polari-framework/:
  python3 -m polariDataTyping.selftest_schema_stability

Stdlib-only, fake manager + injected factories. Covers the whole
lifecycle: learning (clean saves count toward the threshold),
stabilization (flag flips + field snapshot taken + analysis skipped),
the OOPS (a mismatch CAPTURES the payload, destabilizes, adapts —
widen on a capable dialect, coerce otherwise — retries, and records
the action), quarantine when the retry also fails (payload preserved,
never silent loss), deviation column parsing from real MariaDB error
text, throttled persistence, the manual knobs, and the report.
"""

import json
import types

from polariDataTyping import schema_stability as ss

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _factory(**fields):
    fields.pop('manager', None)
    return types.SimpleNamespace(**fields)


class FakeDB:
    def __init__(self):
        self.saved = []

    def saveInstanceInDB(self, row):
        self.saved.append(row)


class FakeVar:
    def __init__(self):
        self.analyzed = []

    def getDeviationSummary(self):
        return {'dominantType': 'int', 'schemaStrategy': 'typed'}


class FakeTyping:
    def __init__(self):
        self.var = FakeVar()
        self.polyTypedVarsDict = {'count': self.var}
        self.analyzed = []

    def analyzeVariableValue(self, varName, varVal):
        self.analyzed.append((varName, varVal))


def _mgr():
    mgr = types.SimpleNamespace(
        objectTables={'SchemaStabilityProfile': {},
                      'SchemaDeviationEvent': {}},
        objectTypingDict={'Widget': FakeTyping()},
        db=FakeDB())
    return mgr


def _track(mgr, row, table):
    mgr.objectTables[table][getattr(row, 'name', str(id(row)))] = row


def main():
    ss._STATUS_CACHE.clear()
    mgr = _mgr()

    # --- learning -> stabilized -----------------------------------------
    profile = None
    for i in range(4):
        profile = ss.record_clean_save(mgr, 'Widget', factory=_factory)
        if i == 0:
            profile.stabilize_threshold = 4  # small threshold for test
            _track(mgr, profile, 'SchemaStabilityProfile')
    check('learning: clean saves counted',
          profile.clean_saves == 4 and profile.total_saves == 4)
    check('stabilized at threshold + timestamp + snapshot',
          profile.status == 'stabilized' and profile.stabilized_at
          and 'typed' in profile.field_summary_json)
    check('is_stabilized: O(1) cache says yes',
          ss.is_stabilized(mgr, 'Widget'))
    ss.note_skipped_analysis(mgr, 'Widget')
    ss.note_skipped_analysis(mgr, 'Widget')
    check('skipped analyses counted (the moved-out-of-tree win)',
          profile.skipped_analyses == 2)
    check('meta classes never self-track',
          ss.record_clean_save(mgr, 'SchemaStabilityProfile') is None)

    # --- error-column parsing (real MariaDB shapes) -----------------------
    err = ("(1366, \"Incorrect integer value: 'abc' for column "
           "`polari_objects`.`Widget`.`count` at row 1\")")
    check('parse: MariaDB names the column',
          ss.parse_mismatch_column(err) == 'count')
    check('parse: unparseable error -> empty string',
          ss.parse_mismatch_column('boom') == '')

    # --- OOPS: widen + retry succeeds --------------------------------------
    widened = []

    def adapt_ok(col):
        widened.append(col)
        return True

    retries = []

    def retry_ok(cols, vals):
        retries.append((cols, list(vals)))
        return True

    report = ss.handle_save_mismatch(
        mgr, 'Widget', ['name', 'count'], ['w1', 'abc'],
        db_error=err, adapt_column=adapt_ok, retry=retry_ok,
        factory=_factory, event_factory=_factory)
    event = report['event']
    _track(mgr, event, 'SchemaDeviationEvent')
    check('OOPS: payload CAPTURED in the event',
          'abc' in event.attempted_payload_json
          and 'w1' in event.attempted_payload_json)
    check('OOPS: named column widened, action says so, resolved',
          widened == ['count'] and report['saved']
          and report['action'] == 'adapted-widened+saved'
          and event.resolved)
    check('OOPS: original values retried after widening (no coercion)',
          retries[0][1][1] == 'abc')
    check('OOPS: schema destabilized + counters honest',
          profile.status == 'destabilized'
          and profile.clean_saves == 0
          and profile.destabilize_count == 1
          and profile.deviation_count == 1)
    check('is_stabilized: cache flipped off',
          not ss.is_stabilized(mgr, 'Widget'))
    check('OOPS: offending values re-analyzed (typing learns)',
          ('count', 'abc') in mgr.objectTypingDict['Widget'].analyzed)

    # --- OOPS on a dialect that cannot widen: coerce ------------------------
    report2 = ss.handle_save_mismatch(
        mgr, 'Widget', ['name', 'count'], ['w2', {'a': 1}],
        db_error=err, adapt_column=lambda col: False, retry=retry_ok,
        factory=_factory, event_factory=_factory)
    check('OOPS (no widen): values coerced to str + saved',
          report2['action'] == 'adapted-coerced+saved'
          and isinstance(retries[-1][1][1], str))

    # --- OOPS where the retry ALSO fails: quarantine -------------------------
    report3 = ss.handle_save_mismatch(
        mgr, 'Widget', ['name', 'count'], ['w3', 'bad'],
        db_error='boom', adapt_column=None,
        retry=lambda c, v: False, factory=_factory,
        event_factory=_factory)
    check('quarantine: unresolved event still holds the payload',
          report3['action'] == 'quarantined'
          and not report3['saved']
          and 'bad' in report3['event'].attempted_payload_json
          and not report3['event'].resolved)

    # --- relearning: clean saves after destabilization re-stabilize ----------
    for _ in range(4):
        ss.record_clean_save(mgr, 'Widget', factory=_factory)
    check('relearning: clean traffic re-stabilizes after an OOPS',
          profile.status == 'stabilized'
          and ss.is_stabilized(mgr, 'Widget'))

    # --- throttled persistence ------------------------------------------------
    saves_before = len(mgr.db.saved)
    for _ in range(ss.PERSIST_EVERY):
        ss.record_clean_save(mgr, 'Widget', factory=_factory)
    check('persistence throttled (1 row write per PERSIST_EVERY saves)',
          len(mgr.db.saved) == saves_before + 1)

    # --- manual knobs -----------------------------------------------------------
    knob = ss.set_status_knob(mgr, 'Widget', 'destabilize')
    check('knob: manual destabilize',
          knob['ok'] and knob['status'] == 'unstable'
          and not ss.is_stabilized(mgr, 'Widget'))
    knob2 = ss.set_status_knob(mgr, 'Widget', 'stabilize')
    check('knob: manual stabilize',
          knob2['ok'] and ss.is_stabilized(mgr, 'Widget'))
    knob3 = ss.set_status_knob(mgr, 'Widget', 'set-threshold',
                               threshold=7)
    check('knob: threshold set', knob3['threshold'] == 7)
    check('knob: unknown action refused',
          not ss.set_status_knob(mgr, 'Widget', 'zap')['ok'])

    # --- report -------------------------------------------------------------------
    rep = ss.stabilization_report(mgr)
    widget = [r for r in rep['profiles'] if r['class'] == 'Widget'][0]
    check('report: profile row with honest lifetime counters',
          rep['ok'] and widget['deviations'] == 3
          and widget['destabilizations'] >= 1
          and rep['stabilized'] == 1)

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks '
          f'passed' + (f'; FAILURES: {failures}' if failures else ''))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
