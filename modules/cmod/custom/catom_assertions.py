"""
@module cmod.custom.catom_assertions

hsp-3a (HARDWARE_SYSTEM_PINS_PLAN.md §7; D-hsp-7 + D-hsp-8 ruled 2026-10-28): Catom assertions on the uno-light atoms, checked against the committed cycle
record, and the pin <-> struct-field bindings DERIVED from them.

  SEED_ASSERTIONS / SEED_STRUCT_OBJECT_MAPS    the rows (declared unverified; the record sets the status on read)
  verify(a, rec)                -> (status, why)   verified | unverified | false, by the cycle record of the assertion's variant
  assertions(variant, rows)     -> the rows with status recomputed
  struct_pin_bindings(...)      -> one row per (pin, field) an assertion couples: direction, event, lane, updater, stamps, the asserting atom, its status
  gaps(variant, rows)           -> struct fields no catom asserts a change of + the notebook draft's fields the struct does not have - named, never hidden

HIS DRAFT vs THE FIRMWARE (light.c, read 2026-10-29): the struct is LightState_t {name, seq, boot_session, led_on, toggles, source, status}. Draft LedOn = led_on;
lastUpdater = source (button = HW, command = US); HardSwitch = no field - the INT0 ISR sets the GLOBAL g_toggle_pending and led_toggle (main loop) changes the struct;
UIswitch = no field - SET_LED writes led_on (apply_command); LightId, timestampHW, timestampUS = not in the struct (gaps). The light is D6 = PD6, the button D2 =
PD2 (INT0), the UART PD0 (RXD) / PD1 (TXD).

What a cycle record can verify (the honest part): it carries per-function call counts and cycles, per-vector takes and the UART bytes logged - not memory
writes. So a bridge assertion is VERIFIED when the record shows the traffic (bytes out of USART0 / RX takes); a field assertion is exercised but UNVERIFIED
(a frame-decoding twin run verifies it, hsp-3c); an assertion naming a function the record's build does not have is FALSE.
"""
import json

KINDS = ('changes-struct', 'changes-field', 'reads-field', 'sends-to-bridge', 'receives-from-bridge', 'defines-role')   # defines-role: hsp-3d, derived from a CatomVariable
LANES = ('isr', 'loop', 'task', 'userspace', 'init')     # D-hsp-5 (recommended): the Task Plan's lane words + userspace
EVENTS = ('edge-rise', 'edge-fall', 'level', 'poll', 'uart-rx', 'uart-tx', 'ui', 'boot')
STATUSES = ('verified', 'unverified', 'false')

VARIANT = 'uno-light'
STRUCT = 'LightState_t'
MAP = 'LightState_t->LightState'
BRIDGE = 'uno-1-bridge'
#: LightState_t's fields, in the wire order of the LightState class (board.objects.board.LightState)
STRUCT_FIELDS = {STRUCT: ('name', 'seq', 'boot_session', 'led_on', 'toggles', 'source', 'status')}
_MUTATED = 'led_on,toggles,source,status'
_SRC = 'modules/board/custom/firmware/uno/apps/light.c'

#: his notebook draft's struct (2026-10-28) -> the firmware's field ('' = none: a gap)
DRAFT_FIELDS = [
    ('LedOn', 'led_on', 'the light; also the command'),
    ('lastUpdater', 'source', 'button = HW, command = US'),
    ('HardSwitch', '', 'INT0_vect sets the global g_toggle_pending; led_toggle (main loop) changes the struct'),
    ('UIswitch', '', 'SET_LED writes led_on through apply_command'),
    ('LightId', '', 'not in the struct (one light per board today)'),
    ('timestampHW', '', 'not in the struct'),
    ('timestampUS', '', 'not in the struct'),
]


def _a(atom, kind, fields='', pins='', lane='loop', event='', updater='', bridge='', basis='', notes=''):
    return {'name': '%s:%s:%s' % (VARIANT, atom, kind), 'variant': VARIANT, 'atom': atom, 'kind': kind, 'struct': STRUCT, 'fields': fields, 'bridge': bridge,
            'pins': pins, 'lane': lane, 'event': event, 'updater': updater, 'stamps': 'none', 'object_map': MAP, 'status': 'unverified', 'status_why': '',
            'basis': basis or '%s (the atom\'s body + its POLARI_NODE role)' % _SRC, 'notes': notes}


SEED_ASSERTIONS = [
    _a('apps/light.led_toggle', 'changes-field', _MUTATED, 'PD2', 'loop', 'edge-fall', 'HW',
       notes='deferred from INT0_vect (D2 falling edge sets g_toggle_pending); the change itself runs in the main loop; writes no timestamp (the struct has none)'),
    _a('apps/light.apply_command', 'changes-field', _MUTATED, 'PD0', 'loop', 'uart-rx', 'US', BRIDGE,
       notes='SET_LED from the host: a real change counts and says source = command'),
    _a('apps/light.led_follow_state', 'reads-field', 'led_on', 'PD6', 'loop', 'poll', notes='the struct controls the light: the only caller of hal_led'),
    _a('apps/light.telemetry_send', 'sends-to-bridge', '', 'PD1', 'loop', 'uart-tx', 'HW', BRIDGE, notes='one LightState frame (TELEMETRY_MASK) per period'),
    _a('apps/light.telemetry_send', 'changes-field', 'seq', '', 'loop', 'poll', 'HW', notes='state.seq = g_seq before the frame'),
    _a('hal.USART_RX_vect', 'receives-from-bridge', '', 'PD0', 'isr', 'uart-rx', '', BRIDGE, basis='modules/board/custom/firmware/uno/hal.c (the RX ring buffer ISR)',
       notes='bytes into the ring buffer; hal_rx_pop + polari_rx_feed + apply_command take them in the loop'),
    _a('apps/light.boot_session_mint', 'changes-field', 'boot_session', '', 'init', 'boot', 'HW', notes='main() stores its return in state.boot_session'),
]

SEED_STRUCT_OBJECT_MAPS = [{
    'name': MAP, 'struct': STRUCT, 'polari_class': 'LightState',
    'fields_json': json.dumps([{'field': f, 'attribute': f, 'note': ''} for f in STRUCT_FIELDS[STRUCT]]),
    'wire': 'lightstate_packets.h (GENERATED by c_twin target=avr; the LightState wire contract)',
    'basis': 'board.objects.board.LightState (the Polari class) + the generated packets header: the same seven fields by name',
    'notes': 'D-hsp-8: one definition at the Polari level; bridges reference it by name',
}]


def _short(atom):
    return atom.split(':', 1)[1] if ':' in atom else atom


def verify(a, rec):
    """(status, why) for one assertion dict against a cycle record (None = no record)."""
    if rec is None:
        return 'unverified', 'no cycle record for variant %r' % a.get('variant')
    atom = _short(a['atom'])
    vec = atom.rsplit('.', 1)[-1]
    fn = (rec.get('functions') or {}).get(atom)
    isr = (rec.get('isrs') or {}).get(vec) if vec.endswith('_vect') else None
    if fn is None and isr is None:
        if vec.endswith('_vect'):
            return 'unverified', '%s was never taken in the record\'s stimulus (record %s)' % (vec, rec.get('record_sha256', '')[:12])
        return 'false', 'the record\'s build has no function %s (record %s): the atom this assertion names does not exist there' % (atom, rec.get('record_sha256', '')[:12])
    n = (fn or isr).get('n', 0)
    if n <= 0:
        return 'unverified', '%s did not run in the record\'s stimulus: not exercised' % atom
    kind = a['kind']
    if kind == 'sends-to-bridge':
        sent = (rec.get('uart') or {}).get('bytes_logged', -1)
        if sent > 0:
            return 'verified', '%s ran %d times and the record logged %d bytes out of USART0 (%s)' % (atom, n, sent, ', '.join(a['pins'].split(',')) or 'TXD')
        return 'false', '%s ran %d times but the record logged no UART bytes' % (atom, n)
    if kind == 'receives-from-bridge':
        return 'verified', '%s taken %d times: bytes arrived from the host on %s' % (vec, n, a['pins'] or 'RXD')
    return 'unverified', ('exercised: %s ran %d times under the stimulus; the record carries cycles, not memory writes - a frame-decoding twin run verifies the '
                          'field change (hsp-3c)' % (atom, n))


def _get(o, k, d=''):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _rows(variant, rows):
    src = SEED_ASSERTIONS if rows is None else rows
    return [{k: _get(r, k) for k in SEED_ASSERTIONS[0]} for r in src if _get(r, 'variant') == variant]


def _record(variant):
    try:
        from board.custom import cycle_records as CR
        return CR.load(variant)
    except Exception:  # noqa: BLE001 - board absent: no record here
        return None


def assertions(variant=VARIANT, rows=None, rec=False):
    """The variant's assertions with status + status_why recomputed from its cycle record (`rec` False = load it; None = none)."""
    rec = _record(variant) if rec is False else rec
    out = []
    for a in _rows(variant, rows):
        a['status'], a['status_why'] = verify(a, rec)
        out.append(a)
    return out


def _fields_of(a):
    return [f.strip() for f in (a['fields'] or '').split(',') if f.strip()] or ['*']


def struct_pin_bindings(variant=VARIANT, rows=None, rec=False):
    """One row per (pin, field) an assertion couples. direction: in (the pin's event changes the field) | out (the field drives the pin) | to-bridge | from-bridge."""
    direction = {'changes-field': 'in', 'changes-struct': 'in', 'reads-field': 'out', 'sends-to-bridge': 'to-bridge', 'receives-from-bridge': 'from-bridge'}
    out = []
    for a in assertions(variant, rows, rec):
        for pin in [p.strip() for p in (a['pins'] or '').split(',') if p.strip()]:
            for f in _fields_of(a):
                out.append({'struct': a['struct'], 'field': f, 'pin': pin, 'direction': direction[a['kind']], 'event': a['event'], 'lane': a['lane'],
                            'updater': a['updater'], 'stamps': a['stamps'], 'bridge': a['bridge'], 'atom': a['atom'], 'assertion': a['name'], 'status': a['status'],
                            'basis': 'derived from the catom assertion %s' % a['name']})
    return out


def gaps(variant=VARIANT, rows=None):
    """[{struct, field, gap}] - the struct fields no catom asserts a change of, then the notebook draft's fields with no struct field."""
    rs = _rows(variant, rows)
    out = []
    for struct in sorted({a['struct'] for a in rs}):
        changed = {f for a in rs if a['struct'] == struct and a['kind'] in ('changes-field', 'changes-struct') for f in _fields_of(a)}
        whole = '*' in changed
        for f in STRUCT_FIELDS.get(struct, ()):
            if not whole and f not in changed:
                out.append({'struct': struct, 'field': f, 'gap': 'no catom asserts a change of %s.%s' % (struct, f)})
    if variant == VARIANT:
        for draft, field, why in DRAFT_FIELDS:
            if not field:
                out.append({'struct': STRUCT, 'field': draft, 'gap': 'the notebook draft\'s %s has no field in %s: %s' % (draft, STRUCT, why)})
    return out


def draft_rows():
    return [{'draft_field': d, 'firmware_field': f or '(none)', 'note': why} for d, f, why in DRAFT_FIELDS]


def map_rows(rows=None):
    src = SEED_STRUCT_OBJECT_MAPS if rows is None else rows
    out = []
    for m in src:
        for p in json.loads(_get(m, 'fields_json') or '[]'):
            out.append({'map': _get(m, 'name'), 'struct': _get(m, 'struct'), 'polari_class': _get(m, 'polari_class'), 'field': p['field'], 'attribute': p['attribute']})
    return out


def problems(a):
    """Static vocabulary check of one assertion dict ([] = holds)."""
    out = []
    if a.get('kind') not in KINDS:
        out.append('kind must be one of %s' % (KINDS,))
    if a.get('lane') not in LANES:
        out.append('lane must be one of %s' % (LANES,))
    if a.get('event') and a['event'] not in EVENTS:
        out.append('event must be one of %s' % (EVENTS,))
    if a.get('kind') in ('sends-to-bridge', 'receives-from-bridge') and not a.get('bridge'):
        out.append('%s names no bridge' % a['kind'])
    if a.get('kind') in ('changes-field', 'reads-field') and not a.get('fields'):
        out.append('%s names no fields' % a['kind'])
    return out


VIEWS = {'assertions': lambda v, rows: assertions(v, rows), 'bindings': lambda v, rows: struct_pin_bindings(v, rows), 'gaps': lambda v, rows: gaps(v, rows),
         'draft': lambda v, rows: draft_rows(), 'maps': lambda v, rows: map_rows()}
