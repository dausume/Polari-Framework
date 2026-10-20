"""board_firmware_state_selftest — fst-0..2 (called by board.board_selftest): THE FIRMWARE STATE-OBJECTS PAGE, derived never typed.

On uno-light: the wire struct LightState with its seven fields (tags, C types), `led_on` written by BOTH mutators (apply_command, led_toggle) and read by the
follow task (led_follow_state) and the report (LightState_encode, handed over by telemetry_send), command+telemetry, controls D6 through led_follow_state;
`boot_session` persisted in EEPROM through boot_session_mint; the two enums (SOURCE, STATUS) with their meanings and who sets each value; the rx parser
struct with its fields written by polari_rx_feed (handed over by main); every static of the app, its defs header and the hal; the local static
led_follow_state.pin; the EEPROM record; the presence bits and framing constants. On uno-blink-only: a field nobody writes beyond zeroing (pwm_duty) is a
FINDING. The doors answer rows; the page is configured tables with five tabs and scope seeded from ?config=; the rows persist on a manager.

    PYTHONPATH=.:modules python3 -m board.board_firmware_state_selftest      # from polari-framework/
"""
import json
import sys


def _by(rows, key, val):
    return next((r for r in rows if r.get(key) == val), None)


def run_firmware_state(check):
    from board.custom import firmware_state as FS
    print('  -- firmware state objects (fst-0..2)')
    try:
        FS.derive('no-such-config', cache=False)
        check('fst: an unknown config is refused in words', False)
    except FS.StateRefused as e:
        check('fst-0 REFUSAL: an unknown config is refused in words that list the configs (404)', 'uno-light' in str(e) and e.status.startswith('404'))
    doc = FS.derive('uno-light', cache=False)
    objs, fields, enums, finds = doc['objects'], doc['fields'], doc['enums'], doc['findings']
    kinds = {o['kind'] for o in objs}
    check('fst-0 uno-light: %d objects of every kind — wire-struct, struct (rx), static, local-static, enum, enum-defines, eeprom; %d fields, %d enum values' % (len(objs), len(fields), len(enums)),
          kinds >= {'wire-struct', 'struct', 'static', 'local-static', 'enum', 'enum-defines', 'eeprom'} and len(fields) >= 14 and len(enums) >= 15, sorted(kinds))
    ws = _by(objs, 'name', 'wire:LightState')
    check('fst-0 the WIRE STRUCT: LightState_t state, 91 B (seven fields, AVR widths), declared in main.c from the generated header with the pinned contract named (v1 e05aeb148924b730)',
          ws is not None and ws['size_bytes'] == 91 and ws['fields_count'] == 7 and 'e05aeb148924b730' in ws['declared_in'] and 'lightstate_packets.h' in ws['declared_in'], ws)
    wf = {f['field']: f for f in fields if f['object'] == 'wire:LightState'}
    check('fst-0 wire fields: tags 1..7 in the contract\'s order with the generator\'s C types (boot_session int64_t, led_on uint8_t, name char[64], source/status uint8_t enums)',
          [wf[k]['tag'] for k in ('boot_session', 'led_on', 'name', 'seq', 'source', 'status', 'toggles')] == [1, 2, 3, 4, 5, 6, 7]
          and wf['boot_session']['c_type'] == 'int64_t' and wf['led_on']['c_type'] == 'uint8_t' and wf['name']['c_type'] == 'char[64]' and wf['name']['size_bytes'] == 64
          and wf['source']['enum'] == 'LIGHTSTATE_SOURCE_*' and wf['status']['enum'] == 'LIGHTSTATE_STATUS_*', {k: (v['tag'], v['c_type']) for k, v in wf.items()})
    led = wf['led_on']
    check('fst-2 led_on is WRITTEN by both mutators (apply_command, led_toggle) and READ by the follow task (led_follow_state) and the report (LightState_encode, handed over by telemetry_send)',
          'apply_command' in led['writers'] and 'led_toggle' in led['writers'] and 'led_follow_state' in led['readers'] and 'LightState_encode (via telemetry_send hands it over)' in led['readers'],
          (led['writers'], led['readers']))
    check('fst-2 led_on is command+telemetry (the host sets it through a decoded frame AND the board reports it); the other wire fields are telemetry only; name says it is omitted when SEND_NAME is 0',
          led['direction'] == 'command+telemetry' and all(wf[k]['direction'] == 'telemetry' for k in ('boot_session', 'seq', 'source', 'status', 'toggles'))
          and wf['name']['direction'].startswith('telemetry') and 'SEND_NAME' in wf['name']['direction'], {k: v['direction'] for k, v in wf.items()})
    check('fst-2 the struct controls the hardware: led_on CONTROLS D6 (LED_PIN) via led_follow_state (the atom\'s `uses` annotation + the knob LED_PIN 6 -> D6); no other field controls a pin',
          led['controls'] == 'D6 (LED_PIN) via led_follow_state' and not any(wf[k]['controls'] for k in wf if k != 'led_on'), {k: v['controls'] for k, v in wf.items()})
    check('fst-0 boot_session is PERSISTED: EEPROM_BOOT_SESSION_ADDR through boot_session_mint (eeprom_read_dword + eeprom_write_dword), written by main, read by the report',
          'EEPROM_BOOT_SESSION_ADDR' in wf['boot_session']['persisted'] and 'boot_session_mint' in wf['boot_session']['persisted'] and 'eeprom_write_dword' in wf['boot_session']['persisted']
          and 'main' in wf['boot_session']['writers'], wf['boot_session'])
    check('fst-0 toggles / source / status are written by both mutators; the zeroing memset in main is named as zeroing, not as a write',
          all('apply_command' in wf[k]['writers'] and 'led_toggle' in wf[k]['writers'] for k in ('toggles', 'source', 'status')) and 'zeroed at init' in wf['toggles']['writers'], wf['toggles']['writers'])
    src = {e['name']: e for e in enums if e['enum'] == 'enum:LIGHTSTATE_SOURCE'}
    st = {e['name']: e for e in enums if e['enum'] == 'enum:LIGHTSTATE_STATUS'}
    check('fst-0 the two ENUMS with their meanings from the EnumMapping (0 = unknown, 1 = command, 2 = button; 0 = unknown, 1 = idle, 2 = active) and WHO SETS each value: '
          'SOURCE_COMMAND by apply_command, SOURCE_BUTTON by led_toggle, STATUS_IDLE by main, STATUS_ACTIVE by both mutators',
          [src[k]['value'] for k in ('LIGHTSTATE_SOURCE_UNKNOWN', 'LIGHTSTATE_SOURCE_COMMAND', 'LIGHTSTATE_SOURCE_BUTTON')] == [0, 1, 2]
          and src['LIGHTSTATE_SOURCE_COMMAND']['set_by'] == 'apply_command' and src['LIGHTSTATE_SOURCE_BUTTON']['set_by'] == 'led_toggle'
          and 'source = button' in src['LIGHTSTATE_SOURCE_BUTTON']['meaning'] and st['LIGHTSTATE_STATUS_IDLE']['set_by'] == 'main'
          and st['LIGHTSTATE_STATUS_ACTIVE']['set_by'] == 'apply_command, led_toggle', {k: v['set_by'] for k, v in list(src.items()) + list(st.items())})
    bits = [e for e in enums if e['enum'] == 'defines:LIGHTSTATE_F_*']
    check('fst-0 the presence bits LIGHTSTATE_F_* (seven + F_ALL) as enum-like defines, each with the header\'s own comment, used by the encode/decode and apply_command (LED_ON)',
          len(bits) == 8 and _by(bits, 'name', 'LIGHTSTATE_F_LED_ON')['meaning'] == 'led_on (bool)' and 'apply_command' in _by(bits, 'name', 'LIGHTSTATE_F_LED_ON')['compared_by']
          and all('LightState_encode' in b['compared_by'] for b in bits), [(b['name'], b['compared_by']) for b in bits])
    wire = {e['name']: e for e in enums if e['enum'] == 'defines:LIGHTSTATE_wire'}
    check('fst-0 the framing constants: MSG_TYPE 1u (compared by main and LightState_frame), WIRE_VERSION 2u, PAYLOAD_MAX, PRELUDE_BYTES, HASH_V2',
          wire['LIGHTSTATE_MSG_TYPE']['value'] == '1u' and 'main' in wire['LIGHTSTATE_MSG_TYPE']['compared_by'] and wire['LIGHTSTATE_WIRE_VERSION']['value'] == '2u'
          and set(wire) == {'LIGHTSTATE_MSG_TYPE', 'LIGHTSTATE_WIRE_VERSION', 'LIGHTSTATE_PAYLOAD_MAX', 'LIGHTSTATE_PRELUDE_BYTES', 'LIGHTSTATE_HASH_V2'}, sorted(wire))
    rx = _by(objs, 'name', 'struct:rx')
    rxf = {f['field']: f for f in fields if f['object'] == 'struct:rx'}
    check('fst-2 the rx parser: polari_rx_t rx (126 B, 9 fields) WRITTEN by polari_rx_feed through the pointer main hands it (and zeroed by main), READ by apply_command and main; '
          'rx.msg_type read directly by main; rx.device_id and rx.sequence are FINDINGS (written, never read)',
          rx is not None and rx['size_bytes'] == 126 and rx['fields_count'] == 9 and 'polari_rx_feed (via main hands it over)' in rx['writers'] and 'apply_command (via main hands it over)' in rx['readers']
          and rxf['msg_type']['readers'] == 'main' and rxf['have']['writers'] == 'polari_rx_feed (via main hands it over)'
          and {f['about'] for f in finds if f['kind'] == 'field'} == {'struct:rx.device_id', 'struct:rx.sequence'}, (rx, finds))
    statics = {o['name']: o for o in objs if o['kind'] == 'static'}
    check('fst-0 the statics: the app\'s g_sensed (main), the defs header\'s g_seq (telemetry_send), payload + wire (handed to the encoder and the USART), the hal\'s ring (rx_ring written by the RX ISR, '
          'read by hal_rx_pop), the sense route\'s counters (hal_sense_poll.c) — each with where it is declared and its group',
          statics['static:g_sensed']['writers'] == 'main' and statics['static:g_seq']['writers'] == 'telemetry_send' and 'light_defs.h (defs header)' == statics['static:g_seq']['declared_in']
          and statics['static:rx_ring']['writers'] == '__polari_isr_USART_RX_vect' and statics['static:rx_ring']['readers'] == 'hal_rx_pop' and 'hal.c (hal)' == statics['static:rx_ring']['declared_in']
          and 'static:g_sense_rises' in statics and 'hal_sense_poll.c' in statics['static:g_sense_rises']['declared_in']
          and 'LightState_encode (via telemetry_send hands it over)' in statics['static:payload']['writers'], {k: (v['writers'], v['readers']) for k, v in statics.items()})
    ls = _by(objs, 'name', 'local-static:led_follow_state.pin')
    check('fst-0 a LOCAL static is state too: led_follow_state.pin (uint8_t, the level last written to the pin), its words from the atom\'s role',
          ls is not None and ls['c_type'] == 'uint8_t' and 'differs from the value last written to the pin' in ls['words'], ls)
    ee = _by(objs, 'name', 'eeprom:EEPROM_BOOT_SESSION_ADDR')
    check('fst-0 the EEPROM record: EEPROM_BOOT_SESSION_ADDR, 4 B, read and written by boot_session_mint, declared in light_defs.h',
          ee is not None and ee['size_bytes'] == 4 and ee['writers'] == 'boot_session_mint' and ee['readers'] == 'boot_session_mint' and ee['declared_in'] == 'light_defs.h', ee)
    check('fst-0 every row names its SOURCE (contract / header text / parsed TU) and the document says it is derived, never typed; no problems from the parser',
          all(o.get('source') for o in objs) and all(f['source'] for f in fields) and 'never typed' in doc['derived_by'] and not doc['problems'], doc['problems'])
    blink = FS.derive('uno-blink-only', cache=False)
    bf = {f['about']: f for f in blink['findings'] if f['kind'] == 'field'}
    check('fst-2 FINDING on uno-blink-only: pwm_duty and temp_c are written by nobody beyond the zeroing memset (no PWM, no ADC compiled in) — the report always carries 0 for them',
          set(bf) == {'wire:SimRigState.pwm_duty', 'wire:SimRigState.temp_c'} and 'beyond zeroing' in bf['wire:SimRigState.pwm_duty']['finding'], sorted(bf))
    check('fst-2 uno-blink-only: a wire field main reads is NOT said to control the pin (main does everything; only a dedicated reader atom with `uses` or a hal pin call is)',
          not any(f['controls'] for f in blink['fields']), [f['controls'] for f in blink['fields'] if f['controls']])
    # ---- rows on a manager + the live door
    from board.board_installer_selftest import _M
    from board.board_basis import LightState, FirmwareStateObject, FirmwareStateField, BOARD_CLASSES
    m = _M('FirmwareStateObject', 'FirmwareStateField', 'LightState', 'TwinSession', 'FirmwareVariant')
    doc2 = FS.derive('uno-light', m, cache=False)
    check('fst-0 rows: FirmwareStateObject + FirmwareStateField are BOARD_CLASSES members; deriving with a manager upserts one row per object and per field (%d / %d)' % (len(doc2['objects']), len(doc2['fields'])),
          FirmwareStateObject in BOARD_CLASSES and FirmwareStateField in BOARD_CLASSES and len(m.objectTables['FirmwareStateObject']) == len(doc2['objects'])
          and len(m.objectTables['FirmwareStateField']) == len(doc2['fields']) and 'persist_note' not in doc2, doc2.get('persist_note'))
    lv = FS.live(m, 'uno-light')
    check('fst-2 LIVE with no row yet: one row per wire field, live blank with the note that no LightState row named uno-light exists on this server yet',
          lv['rig'] == 'uno-light' and len(lv['rows']) == 7 and all(r['live'] == '' and 'no LightState row named uno-light' in r['live_note'] for r in lv['rows']), lv['rows'][:1])
    LightState(manager=m, name='uno-light', led_on=True, toggles=3, source='button', status='active', boot_session=7, seq=41)
    lv = FS.live(m, 'uno-light')
    byf = {r['field']: r for r in lv['rows']}
    check('fst-2 LIVE with the row: led_on True, toggles 3, source button beside the static picture (direction, controls, writers, readers)',
          byf['led_on']['live'] == 'True' and byf['toggles']['live'] == '3' and byf['source']['live'] == 'button' and byf['led_on']['controls'] == 'D6 (LED_PIN) via led_follow_state'
          and 'apply_command' in byf['led_on']['writers'], {k: v['live'] for k, v in byf.items()})
    # ---- the page + the doors' shape
    from board.firmware_state_page import FIRMWARE_STATE_PAGES as PG
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as ALL
    d = json.loads(PG[0]['definition'])
    comps = {it['componentProps']['componentName'] for row in d['rows'] + [r for t in d['tabs'] for r in t['rows']] for it in row['items']}
    paths = [it['componentProps']['inputs'].get('dataPath', '') for t in d['tabs'] for row in t['rows'] for it in row['items']]
    check('fst-1 /display/firmware-state: configured tables ONLY (no new component), five tabs Structs · Fields · Enums · Live · Findings, scope seeded from ?config= and ?session=, '
          'every tab door = /api/firmware-state/{scope:config}[/fields|/enums|/live?session=|/findings]; exported with the board pages',
          PG[0]['pageRoute'] == 'firmware-state' and comps == {'class-rows-table'} and [t['key'] for t in d['tabs']] == ['structs', 'fields', 'enums', 'live', 'findings']
          and d['scope_from_query'] == ['config', 'session'] and all(p.startswith('/api/firmware-state/{scope:config}') for p in paths)
          and any(p['pageRoute'] == 'firmware-state' for p in ALL), (comps, paths))
    check('fst-1 the page\'s tables say what they are for in plain words (every table has a description; no api-json-panel)',
          all(it.get('description') for t in d['tabs'] for row in t['rows'] for it in row['items']) and 'api-json-panel' not in PG[0]['definition'])
    from board.firmware_state_api import FirmwareStateAPI
    import types
    api = FirmwareStateAPI(polServer=None, manager=m)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_fields(None, resp, 'uno-light')
    check('fst-1 door GET /api/firmware-state/uno-light/fields answers `rows` (one per field) + counts', resp.media['ok'] and len(resp.media['rows']) == len(doc2['fields']) and resp.media['counts']['fields'] == len(doc2['fields']))
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_doc(None, resp, 'nope')
    check('fst-1 door: an unknown config answers 404 with the words', resp.status.startswith('404') and 'nope' in resp.media['error'])
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_doc(None, resp, 'undefined')
    check('fst-1 door: an unresolved page scope (`undefined`) answers 400 with how to name the config', resp.status.startswith('400') and '?config=' in resp.media['error'])
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_configs(None, resp)
    check('fst-1 door GET /api/firmware-state/configs lists the UNO configs for the picker (uno-light among them)', any(r['name'] == 'uno-light' for r in resp.media['rows']))


if __name__ == '__main__':
    from board import board_selftest as S
    run_firmware_state(S.check)
    print('\n%d/%d checks passed' % (S.passed, S.total))
    sys.exit(0 if S.passed == S.total else 1)
