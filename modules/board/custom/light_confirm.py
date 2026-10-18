"""
@module board.custom.light_confirm

fgm-6a (FIRMWARE_GENERATION_MODULE_PLAN.md section 10, his ruling 7.8.3): COMMAND CONFIRMATION for the v2 light, in the backend.

A command is confirmed by the board's own answer and nothing else:

  send        mint a command_id (a u16, 1..65535, going up by one per BACKEND start, never equal to the number the board last answered
              - a stale `last_command_id` already on the wire can therefore never confirm a new command), write command_id + led_on on
              the LightStateV2 row (the row write is what rides the Commands stream down) and record a LightCommand (id, the board's
              boot_session AT SEND, sent_at). Refused by name when no report from the board has been seen yet (its boot_session is
              unknown, so "the same boot" cannot be checked).
  on a report a LightStateV2 frame applied to the row (grpcbridge.custom.wire_contract.observe_frame):
                - boot_session differs from the one the command was sent into     -> `unknown-resend` (the board restarted; the command
                  may or may not have been done - it is NEVER shown as done)
                - last_command_id == the command's id (same boot_session)           -> `confirmed` when last_command_result is applied,
                  `rejected-invalid` / `rejected-busy` when the board refused it (named, the light was not changed by it)
                - any other report (the button, the 10 Hz tick, an older answer)    -> nothing: only the command's own number counts
  timeout     a command still pending past its timeout (default 2 s) is `unconfirmed`, named; a late matching answer from the same boot
              still resolves it (marked late), a restart still turns it `unknown-resend`.

The door (GET/POST /api/board/light-v2) exposes `pending_command` {id, sent_at, status, ...} - the newest command not finished, else
the newest. Pure functions over duck-typed command objects (attributes of LightCommand) so the same rules run in the selftest, the twin
proof and the server.
"""
import time

CLASS = 'LightStateV2'
LEDGER = 'LightCommand'
DEFAULT_LIGHT = 'uno-light-v2'
DEFAULT_TIMEOUT_S = 2.0
ID_MAX = 65535
OPEN = ('pending', 'unconfirmed')          # statuses a later report can still resolve
RESULT_STATUS = {'applied': 'confirmed', 'rejected-invalid': 'rejected-invalid', 'rejected-busy': 'rejected-busy'}
BACKEND_SESSION = int(time.time())          # picked anew every time this backend starts: ids are monotonic within it
_LAST_ID = {}                               # light name -> the last id minted in this backend session


class ConfirmRefused(ValueError):
    pass


# ------------------------------------------------------------------ pure rules
def next_id(last_minted, board_echoed=0):
    """The next command id: last_minted + 1, wrapping 65535 -> 1, never 0 and never the number the board is echoing now."""
    n = int(last_minted or 0)
    for _ in range(ID_MAX + 1):
        n = n + 1 if n < ID_MAX else 1
        if n != int(board_echoed or 0):
            return n
    raise ConfirmRefused('no free command id')


def _set(cmd, **kw):
    for k, v in kw.items():
        setattr(cmd, k, v)


def observe_report(commands, report, now=None):
    """Apply ONE report {boot_session, last_command_id, last_command_result} to the open commands (oldest first). Returns the commands
    whose status changed. This is the whole confirmation rule - nothing else can resolve a command."""
    now = time.time() if now is None else now
    sess, echoed, result = int(report.get('boot_session') or 0), int(report.get('last_command_id') or 0), str(report.get('last_command_result') or '')
    changed = []
    for c in sorted(commands, key=lambda c: (float(c.sent_at), int(c.command_id))):
        if c.status not in OPEN:
            continue
        if sess != int(c.device_session_at_send):
            _set(c, status='unknown-resend', resolved_at=now,
                 detail='the board restarted (boot_session %d -> %d) before it answered command %d: it may or may not have been done - send it again'
                        % (int(c.device_session_at_send), sess, int(c.command_id)))
            changed.append(c)
        elif echoed == int(c.command_id):
            late = c.status == 'unconfirmed'
            status = RESULT_STATUS.get(result)
            if status is None:   # an echo with no known result word: the board named the command but did not say how it went
                _set(c, status='unconfirmed', result=result, detail='the board named command %d but gave no known result (%r)' % (int(c.command_id), result))
            else:
                _set(c, status=status, result=result, resolved_at=now,
                     detail=('the board answered command %d: %s%s' % (int(c.command_id), result, ' (late: after the %.1f s timeout)' % float(c.timeout_s) if late else '')))
            changed.append(c)
    return changed


def expire(commands, now=None):
    """Pending commands older than their timeout become `unconfirmed` (named). Returns the ones changed."""
    now = time.time() if now is None else now
    out = []
    for c in commands:
        if c.status == 'pending' and now - float(c.sent_at) > float(c.timeout_s):
            _set(c, status='unconfirmed', resolved_at=0.0,
                 detail='no report named command %d within %.1f s - not confirmed (the board may not have heard it)' % (int(c.command_id), float(c.timeout_s)))
            out.append(c)
    return out


def view(c):
    return {'id': int(c.command_id), 'led_on': bool(c.led_on_requested), 'sent_at': float(c.sent_at), 'status': c.status, 'result': c.result,
            'device_session_at_send': int(c.device_session_at_send), 'backend_session': int(c.backend_session),
            'resolved_at': float(c.resolved_at), 'detail': c.detail}


def pending_command(commands):
    """The newest command still open, else the newest of all, else None - the one thing a screen shows beside the light."""
    cs = sorted(commands, key=lambda c: (float(c.sent_at), int(c.command_id)))
    open_ = [c for c in cs if c.status in OPEN]
    pick = open_[-1] if open_ else (cs[-1] if cs else None)
    return view(pick) if pick is not None else None


# ------------------------------------------------------------------ rows
def _tables(manager, cls):
    return (getattr(manager, 'objectTables', None) or {}).setdefault(cls, {}) if manager is not None else {}


def light_row(manager, name=DEFAULT_LIGHT):
    for r in list(_tables(manager, CLASS).values()):
        if getattr(r, 'name', '') == name:
            return r
    return None


def commands_of(manager, name=DEFAULT_LIGHT):
    return [c for c in _tables(manager, LEDGER).values() if getattr(c, 'light', '') == name]


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 -- an in-memory manager has no db
        pass


def _fan_out(manager, row):
    """The row write rides the Commands stream (the transport mux) exactly like a REST update; absent in a selftest."""
    try:
        from grpcbridge.custom.transport_mux import publish_crude_change
        publish_crude_change(manager, CLASS, 'update', [str(getattr(row, 'id', '') or '')])
    except Exception:  # noqa: BLE001
        pass


def send(manager, name=DEFAULT_LIGHT, led_on=None, now=None, timeout_s=DEFAULT_TIMEOUT_S):
    """Mint a command id and send SET_LED (led_on None = toggle). Returns view(command). Raises ConfirmRefused by name."""
    row = light_row(manager, name)
    if row is None:
        raise ConfirmRefused('no LightStateV2 row named %r' % name)
    sess = int(getattr(row, 'boot_session', 0) or 0)
    if sess <= 0:
        raise ConfirmRefused('no report from %r has arrived yet (its boot_session is unknown), so a confirmation could not tell one board start '
                             'from the next - wait for its first report' % name)
    now = time.time() if now is None else now
    want = (not bool(getattr(row, 'led_on', False))) if led_on is None else bool(led_on)
    cid = next_id(_LAST_ID.get(name, 0), getattr(row, 'last_command_id', 0))
    _LAST_ID[name] = cid
    expire(commands_of(manager, name), now)
    from board.objects.board.LightCommand import LightCommand
    cmd = LightCommand(manager=manager, name='%s#%d.%d' % (name, BACKEND_SESSION, cid), light=name, command_id=cid, led_on_requested=want,
                       backend_session=BACKEND_SESSION, device_session_at_send=sess, status='pending', sent_at=now, timeout_s=timeout_s,
                       detail='sent; waiting for a report that names command %d' % cid)
    _tables(manager, LEDGER).setdefault(getattr(cmd, 'id', None) or cmd.name, cmd)
    row.command_id, row.led_on = cid, want
    _save(manager, cmd)
    _save(manager, row)
    _fan_out(manager, row)
    return view(cmd)


def on_report(manager, cls, row, now=None):
    """The frame observer: a LightStateV2 report was applied to `row` - resolve the commands it answers."""
    name = getattr(row, 'name', '')
    cmds = commands_of(manager, name)
    if not cmds:
        return []
    ch = observe_report(cmds, {'boot_session': getattr(row, 'boot_session', 0), 'last_command_id': getattr(row, 'last_command_id', 0),
                               'last_command_result': getattr(row, 'last_command_result', '')}, now)
    for c in ch:
        _save(manager, c)
    return ch


def state(manager, name=DEFAULT_LIGHT, now=None, recent=10):
    """The light's state and the confirmation of its commands: {light, pending_command, commands (newest first)}."""
    row = light_row(manager, name)
    if row is None:
        raise ConfirmRefused('no LightStateV2 row named %r' % name)
    cmds = commands_of(manager, name)
    for c in expire(cmds, now):
        _save(manager, c)
    ordered = sorted(cmds, key=lambda c: (float(c.sent_at), int(c.command_id)), reverse=True)
    return {'ok': True, 'light': {k: getattr(row, k, None) for k in ('name', 'led_on', 'toggles', 'source', 'status', 'seq', 'boot_session',
                                                                     'command_id', 'last_command_id', 'last_command_result')},
            'pending_command': pending_command(cmds), 'commands': [view(c) for c in ordered[:recent]]}


def analysis_send(manager, object='', led_on=None, **_):
    """The AnalysisCall callable of the `light-toggle-v2` solution (`fn(manager, **params) -> dict`): the v2 SET_LED, with a minted command id.
    `object` = the LightStateV2 row (default uno-light-v2), `led_on` absent = toggle."""
    try:
        cmd = send(manager, str(object or DEFAULT_LIGHT), None if led_on in (None, '') else bool(led_on))
    except ConfirmRefused as e:
        return {'ok': False, 'error': str(e)}
    return {'ok': True, 'command_id': cmd['id'], 'command_status': cmd['status'], 'device_session_at_send': cmd['device_session_at_send'],
            'pending_command': cmd}


def register():
    from grpcbridge.custom.wire_contract import register_frame_observer
    register_frame_observer(CLASS, on_report)


register()
