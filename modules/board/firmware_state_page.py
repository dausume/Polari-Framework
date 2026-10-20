"""
@module board.firmware_state_page

fst-1 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §12): `/display/firmware-state?config=<config>[&session=<twin session>]` — THE FIRMWARE STATE-OBJECTS PAGE. His words:
"a page dedicated to tracking all state objects in a particular piece of firmware (Structs, Enums, etc)". Configured tables only (no new component), bound by
the page scope `config` (seeded from the URL, or picked in the configs table) and `session` (a running twin session, for the Live tab):

    Structs tab   every state object: the wire struct, the rx parser, every static, each local static, the EEPROM record — kind, C type, size, where declared,
                  who writes / who reads it
    Fields tab    every field: C type, size, wire tag + proto type, direction (command | telemetry | both | internal), the pin it controls, persistence,
                  WRITERS and READERS (pointer hand-offs followed), the enum its values come from, a finding
    Enums tab     every enum value and enum-like define with its meaning, who sets it and who compares against it
    Live tab      the wire fields with their live values (the class row this config reports into), beside the picked twin session's status and bridge
    Findings tab  what nobody writes or nobody reads

Everything on it is DERIVED from the config's sources by board.custom.firmware_state on every read; nothing here is typed by hand.
"""
from polariApiServer.module_pages_seed import _page, _row, _tab, _table

ROUTE = 'firmware-state'
DOOR = '/api/firmware-state/{scope:config}'

_TEXT = ('Firmware state objects - every piece of memory one firmware keeps, read out of its own source code: the struct it reports and takes commands in, the frame '
         'parser, every static counter and flag, the values a static keeps inside a function, the number saved in EEPROM, and every enum and enum-like define with what '
         'its values mean. For each field: its C type and size, whether the screen can set it (command) or only read it (telemetry), which pin it moves, whether it '
         'survives a reset, and which functions write it and which read it. Nothing on this page is typed by hand: it is derived from the firmware config\'s rendered '
         'sources, the pinned wire contract and the generated header each time it is read. Pick a config in the first table (or open the page with ?config=), and a '
         'running twin session for the Live tab.')

_OBJ_COLS = 'kind,name,c_type,size_bytes,declared_in,fields_count,writers,readers,words,finding'
_FIELD_COLS = 'name,c_type,size_bytes,tag,proto_type,direction,controls,persisted,writers,readers,enum,finding'
_ENUM_COLS = 'name,enum,field,value,meaning,set_by,compared_by,finding'
_LIVE_COLS = 'class,row,field,direction,live,live_note,controls,writers,readers'
_FINDING_COLS = 'kind,about,finding'


def _picker():
    return _row(0, [
        _table('fst-configs', 0, 5, 'Firmware configs - click one to read its state objects', '', data_path='/api/firmware-state/configs',
               select_field='name', select_scope='config', selected_value='{scope:config}',
               description='What this is for: which firmware to read. One row = one firmware config (a variant the installer can build). Click a row to bind every table on '
                           'this page to it (the URL\'s ?config= does the same); click again, or press Escape, to unbind.',
               columns='name,title,app', max_height=320),
        _table('fst-sessions', 1, 7, 'Twin sessions - click one for the Live tab', '', data_path='/api/board/twins',
               select_field='name', select_scope='session', selected_value='{scope:session}',
               description='What this is for: a running simulated board whose live values the Live tab shows beside the static picture. One row = one twin session '
                           '(/display/sim-bench starts them). Click to bind; click again or press Escape to unbind. The Live tab reads the class row this config reports '
                           'into even with no session picked.',
               columns='name,config,participant,state,remaining_s', max_height=320),
    ], css_class='side-by-side', min_height=260)


def _structs_rows():
    return [_row(0, [_table('fst-objects', 0, 12, 'State objects of {scope:config} - structs, statics, enums, the EEPROM record', 'FirmwareStateObject', data_path=DOOR,
                            empty_text='Pick a config above (or open this page with ?config=<config>) to read its state objects.',
                            description='What this is for: every state object of the picked firmware, derived from its sources. One row = one object. kind: wire-struct (the class '
                                        'the board reports and takes commands in), struct (another struct instance, e.g. the frame parser rx), static (a file-scope variable), '
                                        'local-static (a value a function keeps between calls), enum / enum-defines (a value set with its meanings), eeprom (a record that '
                                        'survives resets). c_type and size_bytes are the C type and its AVR size; declared_in says which file (and group: the app, its defs '
                                        'header, the hal, the generated header); writers / readers are the functions whose bodies touch it - "(via X hands it over)" means '
                                        'the object was handed to X as a pointer and X did the touching; finding is set when nobody writes or nobody reads it.',
                            columns=_OBJ_COLS, max_height=720)], min_height=420)]


def _fields_rows():
    return [_row(0, [_table('fst-fields', 0, 12, 'Fields of {scope:config} - type, direction, the pin it controls, who writes and who reads it', 'FirmwareStateField',
                            data_path=DOOR + '/fields', empty_text='Pick a config above to read its fields.',
                            description='What this is for: one row per struct member of the picked firmware. tag / proto_type are the wire contract\'s (blank for a field that '
                                        'never goes on the wire); direction says command (the host sets it through a decoded frame), telemetry (the board reports it), '
                                        'command+telemetry (both - led_on), or internal; controls names the pin a reader drives from it (the struct controls the hardware: '
                                        'led_on controls D6 through led_follow_state); persisted says where it survives a reset and through which function; writers / readers '
                                        'are the functions that touch it ("the whole struct" = a memset or encode of the struct as one); enum names the value set its '
                                        'values come from; finding says when nobody writes it beyond zeroing, or nobody reads it.',
                            columns=_FIELD_COLS, max_height=720)], min_height=420)]


def _enums_rows():
    return [_row(0, [_table('fst-enums', 0, 12, 'Enums and enum-like defines of {scope:config} - every value with its meaning, who sets it, who compares against it', '',
                            data_path=DOOR + '/enums', empty_text='Pick a config above to read its enums.',
                            description='What this is for: the named values the firmware uses. One row = one value. enum groups them (an enum block such as '
                                        'LIGHTSTATE_SOURCE, the presence bits LIGHTSTATE_F_*, the framing constants); field is the struct field the enum belongs to; '
                                        'meaning comes from the wire contract\'s EnumMapping labels or the generated header\'s own comment; set_by are the functions that '
                                        'assign the value, compared_by the functions that test against it; a value nobody sets or compares is a finding.',
                            columns=_ENUM_COLS, max_height=720)], min_height=420)]


def _live_rows():
    return [_row(0, [_table('fst-live', 0, 12, 'Live values of {scope:config} - the class row this firmware reports into, and the picked twin session', '',
                            data_path=DOOR + '/live?session={scope:session}', empty_text='Pick a config above to see its live values.',
                            description='What this is for: the wire fields beside what the server holds for them right now. One row = one wire field (then the twin '
                                        'session\'s status line and its bridge, when a session is picked). live is the value of the class row this firmware reports into '
                                        '(its rig name - the bridge writes it from each report; blank with a note when no report has arrived); direction, controls, writers '
                                        'and readers are the static picture from the Fields tab, so you can read a live value next to who changes it. Press "Turn the light '
                                        'on / off" on the sim bench and watch led_on and source change here.',
                            columns=_LIVE_COLS, max_height=720)], min_height=420)]


def _findings_rows():
    return [_row(0, [_table('fst-findings', 0, 12, 'Findings for {scope:config} - what nobody writes or nobody reads', '', data_path=DOOR + '/findings',
                            empty_text='No findings for this config: every state object is both written and read.',
                            description='What this is for: the holes the derivation found. One row = one finding: a wire field nobody writes beyond zeroing it at init (the '
                                        'report always carries 0 for it), a field or static nobody reads, an enum value no function sets or compares. A finding is a fact '
                                        'about the code as written, not a verdict: a value the host reads but the board never needs is fine to leave; a field the board '
                                        'never fills is usually a mistake.',
                            columns=_FINDING_COLS, max_height=720)], min_height=320)]


FIRMWARE_STATE_PAGES = [
    _page(ROUTE, ROUTE, _TEXT, 'FirmwareStateObject', [_picker()], title='Firmware state', scope_query=['config', 'session'],
          tabs=[_tab('structs', 'Structs', _structs_rows(), 'Every state object of the picked firmware: structs, statics, enums, the EEPROM record.'),
                _tab('fields', 'Fields', _fields_rows(), 'Every field: type, direction, the pin it controls, who writes it and who reads it.'),
                _tab('enums', 'Enums', _enums_rows(), 'Every enum value and enum-like define, with its meaning.'),
                _tab('live', 'Live', _live_rows(), 'The wire fields with their live values, beside the picked twin session.'),
                _tab('findings', 'Findings', _findings_rows(), 'What nobody writes or nobody reads.')]),
]
