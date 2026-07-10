"""
@cross-cutting
@module polariDataTyping.schema_stability
@tags @xc:bindings

The schema-stabilization engine (mirrors StepCostProfile's
stat-freezing rule — observation consolidates itself away, reality
can always reopen it):

  LEARNING   every save counts; a new type deviation resets the
             clean-save counter (polyTypedVariable.updateTypingDicts
             already classifies deviations — REUSED, not rebuilt).
  STABILIZED clean_saves >= threshold with no new deviation → the
             class's schema is trusted: per-instance typing analysis
             is SKIPPED (polyTyping.analyzeInstance fast-path) — the
             first concrete step of typing work moving out of the
             object tree.
  OOPS       a stabilized schema rejects real data at the DB (strict
             MariaDB throws on e.g. str→bigint): the payload is
             CAPTURED into a SchemaDeviationEvent, the profile flips
             back to destabilized, the schema ADAPTS (widen the named
             column where the dialect can, else coerce values), the
             write is RETRIED — and only if that still fails is the
             payload quarantined in the event row. Never silent loss.

All hooks are failure-isolated: an exception here can never break a
save that would otherwise succeed.

@consumers
  - polariDBmanagement.managedDB.saveInstanceInDB
  - polariDataTyping.polyTyping.analyzeInstance (fast-path)
  - polariDataTyping.schema_stability_api
@see /OVERLAP_MAP.md
"""

import json
import re
from datetime import datetime, timezone

#: Persist the profile row every N clean saves (write throttling).
PERSIST_EVERY = 10
#: Default clean-save threshold; per-class knob on the profile row.
DEFAULT_THRESHOLD = 50
#: Payload capture cap (chars) — events must stay small rows.
PAYLOAD_CAP = 4000

#: (id(manager), className) -> status string. O(1) hot-path lookup;
#: every status change writes through here.
_STATUS_CACHE = {}

#: MariaDB/MySQL error shapes that name the offending column —
#: handles both bare and backtick-dotted forms
#: ("for column 'count'" and "for column `db`.`t`.`count`").
_COLUMN_RE = re.compile(
    r"for column\s+(?:[`'\"]?[A-Za-z0-9_]+[`'\"]?\.)*"
    r"[`'\"]?([A-Za-z0-9_]+)[`'\"]?",
    re.IGNORECASE)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return (tables.get(class_name) or {})


def _save_row(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass


def get_profile(manager, class_name, create=False, factory=None):
    for row in _rows(manager, 'SchemaStabilityProfile').values():
        if getattr(row, 'subject_class', '') == class_name:
            return row
    if not create:
        return None
    if factory is None:
        from polariDataTyping.schema_stability_basis import (
            SchemaStabilityProfile,
        )
        factory = SchemaStabilityProfile
    # every field passed explicitly so duck-typed factories (selftests)
    # get the same shape the real treeObject defaults provide
    return factory(name=f'{class_name}-schema-stability',
                   subject_class=class_name, status='unstable',
                   stabilize_threshold=DEFAULT_THRESHOLD,
                   clean_saves=0, total_saves=0, deviation_count=0,
                   destabilize_count=0, field_summary_json='{}',
                   stabilized_at='', destabilized_at='',
                   skipped_analyses=0, notes='', manager=manager)


def _set_status(manager, profile, status):
    profile.status = status
    _STATUS_CACHE[(id(manager),
                   getattr(profile, 'subject_class', ''))] = status


def is_stabilized(manager, class_name):
    """O(1) hot-path check (analyzeInstance runs on every instance)."""
    key = (id(manager), class_name)
    cached = _STATUS_CACHE.get(key)
    if cached is None:
        profile = get_profile(manager, class_name)
        cached = getattr(profile, 'status', 'unstable') \
            if profile is not None else 'unstable'
        _STATUS_CACHE[key] = cached
    return cached == 'stabilized'


def note_skipped_analysis(manager, class_name):
    """Count a skipped per-instance analysis (the measurable win)."""
    profile = get_profile(manager, class_name)
    if profile is not None:
        profile.skipped_analyses = int(
            getattr(profile, 'skipped_analyses', 0) or 0) + 1


def field_snapshot(manager, class_name):
    """Per-field deviation summaries from the live polyTyping."""
    typing_obj = (getattr(manager, 'objectTypingDict', None)
                  or {}).get(class_name)
    if typing_obj is None:
        return {}
    out = {}
    for name, var in (getattr(typing_obj, 'polyTypedVarsDict', None)
                      or {}).items():
        try:
            out[name] = var.getDeviationSummary()
        except Exception:
            out[name] = {'error': 'summary failed'}
    return out


def record_clean_save(manager, class_name, factory=None):
    """A save landed without incident — progress toward stabilization.

    Flips the profile to 'stabilized' when clean_saves crosses the
    threshold, snapshotting WHAT was trusted (field summaries).
    Throttled persistence: the row is written every PERSIST_EVERY
    increments or on a status change.
    """
    if class_name in ('SchemaStabilityProfile', 'SchemaDeviationEvent'):
        return None  # never meta-track the tracker
    profile = get_profile(manager, class_name, create=True,
                          factory=factory)
    if profile is None:
        return None
    profile.total_saves = int(getattr(profile, 'total_saves', 0)) + 1
    profile.clean_saves = int(getattr(profile, 'clean_saves', 0)) + 1
    changed = False
    if (profile.status != 'stabilized'
            and profile.clean_saves >= int(
                getattr(profile, 'stabilize_threshold',
                        DEFAULT_THRESHOLD) or DEFAULT_THRESHOLD)):
        _set_status(manager, profile, 'stabilized')
        profile.stabilized_at = _now()
        profile.field_summary_json = json.dumps(
            field_snapshot(manager, class_name), default=str)
        changed = True
    if changed or profile.clean_saves % PERSIST_EVERY == 0:
        _save_row(manager, profile)
    return profile


def record_deviation(manager, class_name, field='', expected_type='',
                     actual_type='', payload=None, db_error='',
                     action='', resolved=False, factory=None,
                     event_factory=None):
    """Record an OOPS + destabilize. Returns (profile, event)."""
    profile = get_profile(manager, class_name, create=True,
                          factory=factory)
    was_stabilized = getattr(profile, 'status', '') == 'stabilized' \
        if profile is not None else False
    if profile is not None:
        profile.deviation_count = int(
            getattr(profile, 'deviation_count', 0)) + 1
        profile.clean_saves = 0
        if was_stabilized:
            profile.destabilize_count = int(
                getattr(profile, 'destabilize_count', 0)) + 1
            profile.destabilized_at = _now()
        _set_status(manager, profile,
                    'destabilized' if was_stabilized else 'unstable')
        _save_row(manager, profile)
    if event_factory is None:
        from polariDataTyping.schema_stability_basis import (
            SchemaDeviationEvent,
        )
        event_factory = SchemaDeviationEvent
    stamp = _now()
    try:
        payload_json = json.dumps(payload or {}, default=str)
    except Exception:
        payload_json = json.dumps({'repr': repr(payload)[:1000]})
    event = event_factory(
        name=f'{class_name}@{stamp}', subject_class=class_name,
        field=field, expected_type=expected_type,
        actual_type=actual_type,
        attempted_payload_json=payload_json[:PAYLOAD_CAP],
        db_error=str(db_error)[:1000], action=action,
        resolved=resolved, occurred_at=stamp, manager=manager)
    _save_row(manager, event)
    return profile, event


def parse_mismatch_column(db_error):
    """The column MariaDB named in its type error, or ''."""
    m = _COLUMN_RE.search(str(db_error))
    return m.group(1) if m else ''


def handle_save_mismatch(manager, class_name, columns, values,
                         db_error, adapt_column=None, retry=None,
                         reanalyze=True, factory=None,
                         event_factory=None):
    """The smooth OOPS path. Called by saveInstanceInDB when an
    insert throws.

    1. CAPTURE the attempted data (column -> value) into an event.
    2. DESTABILIZE the class's schema (back to learning mode).
    3. ADAPT: re-analyze the offending values through polyTyping
       (the deviation machinery learns the new shape), then widen
       the named column via `adapt_column(colName)` where the
       dialect can; else coerce every value to str (affinity-style).
    4. RETRY via `retry(columns, values)`; on success the event says
       so — only a second failure quarantines the payload (which the
       event preserves either way).

    Returns {'saved': bool, 'action': str, 'event': row}.
    """
    payload = {c: repr(v)[:200] for c, v in zip(columns, values)}
    field = parse_mismatch_column(db_error)
    actual = ''
    if field and field in columns:
        actual = type(values[columns.index(field)]).__name__

    # learn the new shape (updates typingDicts deviation counts)
    if reanalyze:
        try:
            typing_obj = (getattr(manager, 'objectTypingDict', None)
                          or {}).get(class_name)
            if typing_obj is not None:
                for c, v in zip(columns, values):
                    typing_obj.analyzeVariableValue(varName=c, varVal=v)
        except Exception:
            pass

    widened = False
    if field and adapt_column is not None:
        try:
            widened = bool(adapt_column(field))
        except Exception:
            widened = False

    attempt_values = values
    if not widened:
        attempt_values = [v if isinstance(v, (str, bytes, type(None)))
                          else str(v) for v in values]

    saved = False
    if retry is not None:
        try:
            saved = bool(retry(columns, attempt_values))
        except Exception:
            saved = False

    if saved and widened:
        action = 'adapted-widened+saved'
    elif saved:
        action = 'adapted-coerced+saved'
    else:
        action = 'quarantined'
    _, event = record_deviation(
        manager, class_name, field=field,
        expected_type='(column type; see db_error)',
        actual_type=actual, payload=payload, db_error=db_error,
        action=action, resolved=saved, factory=factory,
        event_factory=event_factory)
    return {'saved': saved, 'action': action, 'event': event}


def set_status_knob(manager, class_name, action, threshold=None,
                    factory=None):
    """Manual knob: stabilize / destabilize / set-threshold."""
    profile = get_profile(manager, class_name, create=True,
                          factory=factory)
    if profile is None:
        return {'ok': False, 'error': 'no profile'}
    if action == 'stabilize':
        _set_status(manager, profile, 'stabilized')
        profile.stabilized_at = _now()
        profile.field_summary_json = json.dumps(
            field_snapshot(manager, class_name), default=str)
        profile.notes = (profile.notes or '') + ' | manually stabilized'
    elif action == 'destabilize':
        _set_status(manager, profile, 'unstable')
        profile.clean_saves = 0
        profile.notes = (profile.notes or '') + ' | manually destabilized'
    elif action == 'set-threshold' and threshold is not None:
        profile.stabilize_threshold = max(1, int(threshold))
    else:
        return {'ok': False,
                'error': f'unknown action "{action}" (stabilize | '
                         'destabilize | set-threshold)'}
    _save_row(manager, profile)
    return {'ok': True, 'class': class_name,
            'status': profile.status,
            'threshold': profile.stabilize_threshold}


def stabilization_report(manager):
    """Every tracked class + where it stands."""
    rows = []
    for p in _rows(manager, 'SchemaStabilityProfile').values():
        rows.append({
            'class': getattr(p, 'subject_class', ''),
            'status': getattr(p, 'status', 'unstable'),
            'cleanSaves': getattr(p, 'clean_saves', 0),
            'threshold': getattr(p, 'stabilize_threshold',
                                 DEFAULT_THRESHOLD),
            'totalSaves': getattr(p, 'total_saves', 0),
            'deviations': getattr(p, 'deviation_count', 0),
            'destabilizations': getattr(p, 'destabilize_count', 0),
            'skippedAnalyses': getattr(p, 'skipped_analyses', 0),
            'stabilizedAt': getattr(p, 'stabilized_at', ''),
            'destabilizedAt': getattr(p, 'destabilized_at', ''),
        })
    events = len(_rows(manager, 'SchemaDeviationEvent'))
    return {'ok': True,
            'profiles': sorted(rows, key=lambda r: r['class']),
            'stabilized': sum(1 for r in rows
                              if r['status'] == 'stabilized'),
            'events': events}
