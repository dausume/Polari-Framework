"""
@module board.custom.bench_interactions

sim-3 (HARDWARE_BENCH_CONVERGENCE_PLAN.md sections 3 and 8; D-hbc-4): what a person did on the sim bench, as BenchInteraction rows, and the one door that turns a session's
interactions into a ScenarioRun of kind `attested` - the person's own record, never promoted to a proof by this code.

    record(manager, session_row, cmd, reply, who, meta)  one row per accepted-or-refused command (watch, status and run are set-up, not actions, and are not recorded)
    listing(manager, session)                              the session's rows in order, as dicts for a configured table
    evidence(manager, session_row, who, outcome, observed) write the ScenarioRun (kind attested); returns {run, interactions}

The twin cycle comes from the twin's own acknowledgement: `set` and `reset` acks carry it; `adc` acks do not, so an adc row says -1 ("the twin did not report a cycle"), never a guess.
"""
import json
import time

CLASS = 'BenchInteraction'
_FALLBACK = {}
KINDS = ('press', 'release', 'toggle', 'adc', 'reset', 'set', 'other')
SCENARIO_PREFIX = 'bench-session:'


def _table(manager):
    tabs = getattr(manager, 'objectTables', None)
    return tabs.setdefault(CLASS, {}) if tabs is not None else _FALLBACK


def _rows(manager, session=None):
    rows = [r for r in _table(manager).values() if getattr(r, 'name', '')]
    if session is not None:
        rows = [r for r in rows if r.session == session]
    return sorted(rows, key=lambda r: (r.session, r.seq))


def _view(r):
    return {'name': r.name, 'session': r.session, 'seq': r.seq, 'who': r.who, 'part': r.part, 'what': r.what, 'kind': r.kind, 'pin': r.pin, 'value': r.value, 'at': r.at,
            'at_text': time.strftime('%H:%M:%S', time.gmtime(r.at)) + ' UTC' if r.at else '', 'twin_cycle': r.twin_cycle,
            'twin_cycle_text': str(r.twin_cycle) if r.twin_cycle >= 0 else 'not reported by the twin', 'ok': bool(r.ok), 'reply': r.reply}


def listing(manager, session):
    return [_view(r) for r in _rows(manager, session)]


def listing_all(manager):
    return [_view(r) for r in _rows(manager)]


def evidence_rows(manager):
    """The ScenarioRun rows made from bench sessions (side bench-session), newest first."""
    t = ((getattr(manager, 'objectTables', None) or {}).get('ScenarioRun') or {})
    rows = [r for r in (t.values() if isinstance(t, dict) else t) if getattr(r, 'side', '') == 'bench-session']
    keys = ('name', 'scenario', 'outcome', 'kind', 'attested_by', 'firmware_sha256', 'board_instance', 'ran_at', 'verdict_words')
    return [{k: getattr(r, k, '') for k in keys} for r in sorted(rows, key=lambda r: getattr(r, 'ran_at', ''), reverse=True)]


def _describe(cmd, meta):
    part = meta.get('part') or ''
    who_part = (' on %s' % part) if part else ''
    if 'set' in cmd:
        lvl = cmd['level']
        kind = meta.get('kind') if meta.get('kind') in KINDS else 'set'
        verb = {'press': 'pressed', 'release': 'released', 'toggle': 'switched'}.get(kind, 'set')
        return kind, '%s%s: %s driven to %d' % (verb, who_part, cmd['set'], lvl), cmd['set'], float(lvl)
    if 'adc' in cmd:
        return 'adc', 'analog input %d held at %d mV%s' % (cmd['adc'], cmd['mv'], who_part), 'ADC%d' % cmd['adc'], float(cmd['mv'])
    if cmd.get('reset'):
        return 'reset', 'the board was reset', '', 0.0
    return 'other', json.dumps(cmd, sort_keys=True), '', 0.0


def record(manager, session_row, cmd, reply, who='', meta=None):
    """Write the row for one command; -> the row view, or None for a command that is set-up rather than an action."""
    if not cmd or not any(k in cmd for k in ('set', 'adc', 'reset')):
        return None
    from board.objects.board.BenchInteraction import BenchInteraction
    meta = meta or {}
    seq = 1 + max([r.seq for r in _rows(manager, session_row.name)] or [0])
    kind, what, pin, value = _describe(cmd, meta)
    if meta.get('what'):
        what = str(meta['what'])[:200]
    ok = reply.get('t') != 'refused'
    reply_words = reply.get('why') if reply.get('t') == 'refused' else 'the twin acknowledged it'
    cyc = reply.get('cycle')
    row = BenchInteraction(manager=manager, name='%s#%d' % (session_row.name, seq), session=session_row.name, seq=seq, who=who or '', part=str(meta.get('part') or '')[:40],
                           what=what, kind=kind, pin=pin, value=value, at=time.time(), twin_cycle=int(cyc) if isinstance(cyc, (int, float)) else -1,
                           ok=ok, reply=str(reply_words or ''))
    if getattr(manager, 'objectTables', None) is None:
        _FALLBACK[row.name] = row
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass
    return _view(row)


def evidence(manager, session_row, who='', outcome='', observed=''):
    """Save the session's interactions as a ScenarioRun of kind attested. Nothing is judged unless the person says so: the default outcome is `undetermined`."""
    from board.custom.twin_sessions import SessionRefused
    rows = _rows(manager, session_row.name)
    if not rows:
        raise SessionRefused('session %s has no recorded interactions yet - press or turn something on the bench first, then record it' % session_row.name, 409)
    if outcome and outcome not in ('passed', 'failed', 'undetermined'):
        raise SessionRefused("outcome must be 'passed', 'failed' or 'undetermined' (a person's judgement)", 400)
    if manager is None or getattr(manager, 'objectTables', None) is None:
        raise SessionRefused('no live manager on this server to store the evidence on', 422)
    try:
        from firmwarefaults.custom.sink import ManagerSink
    except Exception as e:  # noqa: BLE001
        raise SessionRefused('the firmware-faults module is not loaded here, so a ScenarioRun cannot be stored (%s)' % e, 422)
    ran_at = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())
    actions = '; '.join('%d. %s' % (r.seq, r.what) for r in rows[:12]) + (' ... (%d in all)' % len(rows) if len(rows) > 12 else '')
    judged = outcome or 'undetermined'
    words = observed.strip() or ('a person recorded %d bench interaction(s) on twin session %s (firmware %s, locked): %s. Nobody has judged pass or fail yet.'
                                 % (len(rows), session_row.name, (session_row.hex_sha256 or '')[:12], actions))
    who_words = who if who else 'an unauthenticated request (no signed-in person on this request)'
    run = {'name': '%s@bench@%s' % (session_row.name, ran_at), 'scenario': SCENARIO_PREFIX + session_row.config, 'side': 'bench-session', 'variant': session_row.config,
           'outcome': judged, 'verdict_words': 'attested by %s: %s' % (who_words, words), 'kind': 'attested', 'attested_by': who or '', 'observed': words,
           'board_instance': session_row.participant, 'firmware_sha256': session_row.hex_sha256, 'ran_at': ran_at,
           'repro_json': json.dumps({'mode': 'digital-twin', 'session': session_row.name, 'config': session_row.config, 'hex_sha256': session_row.hex_sha256,
                                     'interactions': [{'seq': r.seq, 'kind': r.kind, 'pin': r.pin, 'value': r.value, 'twin_cycle': r.twin_cycle, 'at': r.at} for r in rows],
                                     'attested': True}, sort_keys=True),
           'notes': "a person's manual bench session (sim-3) - recorded, never promoted to a proof by itself"}
    ManagerSink(manager).upsert('ScenarioRun', run)
    return {'ok': True, 'run': run['name'], 'scenario': run['scenario'], 'kind': 'attested', 'outcome': judged, 'interactions': len(rows), 'words': run['verdict_words']}
