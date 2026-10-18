"""
@module board.pin_view_page

pv-0 (PIN_VIEW_PLAN.md 2.9): the pin view's DATA VIEWS beside the d3 view — three configured pages (tables only: no raw JSON, no new component): Pins, Connections, Surfaces. Each table reads one of
the row doors `GET /api/board/<board>/pin-view/{pins|connections|surfaces}`; a table's stage / protocol / system / binding are fixed in its data path (the generic table filters by a column, it
does not send query parameters), and each page's text says which other values the door takes. Plain words only; the pages are fixed to the UNO and its light demo, the way /display/hardware-chain
is fixed to one binding. The d3 view (pv-1) selects together with these tables.

pv-1: `/display/pin-view` — the d3 view itself, ONE item mounting the registered component `hardware-pin-view` (his explicit exception to "no new custom components", PIN_VIEW_PLAN
2.9/§4 D-pv-1); the three table pages above are its data views and are named on it. The component takes board / system / binding / stage as inputs (and the same names as route query).
"""
from polariApiServer.module_pages_seed import _page, _row, _table

BOARD = 'arduino-uno-r3'
SYSTEM = 'uno-light-system'
BINDING = 'uno-light@arduino-uno-r3'
DOOR = '/api/board/%s/pin-view' % BOARD
_Q = '?system=%s&binding=%s' % (SYSTEM, BINDING)
STAGES_TEXT = ('The stage says how far the pins have been configured: base (the parts as composed, before any init: chip blank, board as delivered), after-init (only the Initialization '
               'Purpose\'s claims), tasks-assigned (the tasks of a firmware solution have claimed pins: proposed), firmware-committed (the firmware\'s own register settings make the claims committed). '
               'A pin is unassigned (nothing to give), available (it reaches a header and nothing has claimed it), proposed or committed.')
DOOR_TEXT = ('The door takes ?system= ?binding= ?stage= ?phase= ?protocol= ?mission= (and level= surface= kind= for rows); to see another stage or protocol, ask the door (GET %s/pins?stage=firmware-committed'
             '&system=%s&binding=%s) or use `pol board pin-view pins %s --stage firmware-committed`.' % (DOOR, SYSTEM, BINDING, BOARD))

_PIN_COLS = 'owner,level,label,number,kind,canonical,families,drive_class,stage,stage_why,consumers,bonded,lit,lit_why,notes'
_CONN_COLS = 'a_owner,a_label,b_owner,b_label,kind,via,drive,signal,use,stage,lit'
_SURF_COLS = 'title,kind,level,parent,shape,pin_count,unassigned,available,proposed,committed'

_TABLE_PAGES = [
    _page('pin-view-pins', 'pin-view-pins',
          'Pins — every pin at every level of the UNO: the silicon pads of the ATmega328P and the ATmega16U2, the legs of their packages, the header pins of the board, the pins of the parts on the board '
          'and the bench parts. One row is one pin. Colour in the picture is the protocol family; here the family is a word. %s %s' % (STAGES_TEXT, DOOR_TEXT),
          'BoardPin', [
              _row(0, [_table('pv-pins-base', 0, 12, 'Every pin — base composition (before any init)', '',
                              description='What this is for: all pins as composed, nothing claimed. One row = one pin. Columns: owner (the surface it belongs to), level (die = silicon pad, package = leg, board = header pin, part = a part '
                                          'on the board, bench = a bench part), label, number, kind, canonical (the board\'s own name, D0 .. A5), families (the protocols it can carry), drive_class (the pad class '
                                          'whose electrical limits apply: a name, the numbers are in the electrical view), stage, stage_why, consumers (what takes the line: a task, a Purpose, a part), bonded '
                                          '(brought out by the package), notes.',
                              columns=_PIN_COLS + ',view', column_formats='view:view:/display/pin-view?pin={id}', data_path=DOOR + '/pins')]),
              _row(1, [_table('pv-pins-unassigned', 0, 6, 'Pins nothing has claimed yet (available)', '',
                              description='What this is for: the pins a no-code task could still take — they reach a header and no task claims them. Same columns as above, filtered to stage available at the base composition.',
                              columns='owner,level,label,canonical,families,drive_class,stage_why,view', column_formats='view:view:/display/pin-view?pin={id}', data_path=DOOR + '/pins', filter_field='stage', filter_value='available'),
                       _table('pv-pins-proposed', 1, 6, 'Pins the light firmware\'s tasks have claimed (tasks assigned)', '',
                              description='What this is for: the pins the tasks of the light demo\'s firmware claim, at stage tasks-assigned (proposed), with the task and the Purpose that need each pin.',
                              columns='owner,level,label,canonical,families,stage,consumers,view', column_formats='view:view:/display/pin-view?pin={id}', data_path=DOOR + '/pins' + _Q + '&stage=tasks-assigned', filter_field='stage', filter_value='proposed,committed')]),
              _row(2, [_table('pv-pins-spi', 0, 12, 'Pins able to carry SPI (SCK, MOSI, MISO, SS) — with the availability ladder\'s verdict', '',
                              description='What this is for: the protocol filter. A pin is listed when its chip can do one of the children of SPI; lit_why gives the availability ladder\'s verdict for that child in this '
                                          'context (blocked at which rung, or available with which conditions). The filter rows are the same on every level: pad, leg, header pin.',
                              columns='owner,level,label,canonical,families,lit,lit_why,view', column_formats='view:view:/display/pin-view?pin={id}', data_path=DOOR + '/pins' + _Q + '&protocol=spi', filter_field='lit', filter_value='lit')]),
          ], title='Pins'),
    _page('pin-view-connections', 'pin-view-connections',
          'Connections — every pin-to-pin connection of the UNO and the bench, one row each: the two ends, what kind of connection it is (pad to leg inside a package, a leg to a header, a leg to a part on '
          'the board, chip to chip, a header to the bench), what sits in the path (a word: series resistor, buffer, capacitor), and three separate summaries. Drive is the electricity: which end supplies, '
          'sources and sinks or returns current, the rail and domain, the pull, and the class of the limit (within-recommended, undetermined, over, or unchecked when no check has run) — never a number. '
          'Signal is the signal: which end outputs and which inputs, the protocol signal it carries and its family. Use is who claims it: the tasks and the Purposes. %s' % DOOR_TEXT,
          'BoardPin', [
              _row(0, [_table('pv-conn-all', 0, 12, 'Every connection — the light firmware\'s tasks assigned', '',
                              description='What this is for: all connections with the stage of the light demo\'s tasks applied. One row = one connection between two pins. Columns: a/b (owner and pin), kind, via, drive, '
                                          'signal, use, stage. A connection\'s stage is the higher of its two ends.',
                              columns=_CONN_COLS + ',view', column_formats='view:view:/display/pin-view?connection={id}', data_path=DOOR + '/connections' + _Q + '&stage=tasks-assigned')]),
              _row(1, [_table('pv-conn-chips', 0, 6, 'Chip to chip — the ATmega328P and the USB bridge', '',
                              description='What this is for: the lines between the two chips (the serial pair and the auto-reset line), with the part in the path. Filter: kind chip-to-chip.',
                              columns='a_label,b_label,via,drive,signal,use,view', column_formats='view:view:/display/pin-view?connection={id}', data_path=DOOR + '/connections' + _Q + '&stage=tasks-assigned', filter_field='kind', filter_value='chip-to-chip'),
                       _table('pv-conn-bench', 1, 6, 'To the bench — the wires of the light demo\'s circuit', '',
                              description='What this is for: the board\'s header pins joined to the bench parts (resistor, LED, button) and the jumper between D6 and D3. Filter: kind to-bench.',
                              columns='a_label,b_label,via,drive,signal,use,view', column_formats='view:view:/display/pin-view?connection={id}', data_path=DOOR + '/connections' + _Q + '&stage=tasks-assigned', filter_field='kind', filter_value='to-bench')]),
              _row(2, [_table('pv-conn-parts', 0, 12, 'To a part on the board — buffers, clock parts, connectors, test pads', '',
                              description='What this is for: the legs that end on a part of the board (the L LED buffer on D13, the 16 MHz parts, the USB connector, the ICSP header of the bridge, the test pads). Filter: kind to-board-part.',
                              columns='a_label,b_owner,b_label,via,drive,signal,use,view', column_formats='view:view:/display/pin-view?connection={id}', data_path=DOOR + '/connections' + _Q, filter_field='kind', filter_value='to-board-part')]),
          ], title='Connections'),
    _page('pin-view-surfaces', 'pin-view-surfaces',
          'Surfaces — the things a person can click in the pin view: the board, the chip packages (enclosures), the silicon (SoC dies), the parts on the board and the bench parts. One row is one surface with '
          'its pin counts by stage. %s %s' % (STAGES_TEXT, DOOR_TEXT),
          'BoardPin', [
              _row(0, [_table('pv-surf-base', 0, 12, 'Every surface — base composition', '',
                              description='What this is for: what the design is made of and how many pins each piece has. One row = one surface. Columns: kind (board, enclosure, soc, board-part, bench-part), level, parent (what it sits '
                                          'inside: the die inside its package inside the board), shape (its math-defined outline row), pin_count, then the pins by stage.',
                              columns=_SURF_COLS + ',view', column_formats='view:view:/display/pin-view?surface={id}', data_path=DOOR + '/surfaces')]),
              _row(1, [_table('pv-surf-tasks', 0, 12, 'Every surface — the light firmware\'s tasks assigned', '',
                              description='What this is for: the same surfaces with the light demo\'s tasks assigned, so the proposed counts show where the firmware reaches.',
                              columns=_SURF_COLS + ',view', column_formats='view:view:/display/pin-view?surface={id}', data_path=DOOR + '/surfaces' + _Q + '&stage=tasks-assigned')]),
          ], title='Surfaces'),
]



# ---------------------------------------------------------------- pv-1: the d3 view (the ONE sanctioned new component for pins)
_VIEW_TEXT = ('Pin view — a picture of the UNO and its parts with their pins. The board is the outline, each chip sits on it as a package (its legs on the edge) with the silicon die inside '
              '(its pads in a ring), and the other parts of the board and the bench parts sit beside them. Colour is the signal family (GPIO, PWM, analog, UART, SPI, I2C, USB, clock, reset, '
              'power, ground); the symbol says what a pin does; a hollow ring is a pin nothing has been assigned to yet, a tinted one is proposed by a task, a solid one is committed by the '
              'firmware, a hatched one is blocked or undetermined on the availability ladder. Nothing is wired until you pick something: click a board, a package, the silicon or a part to see '
              'its pin-to-pin connections and its pins grouped by kind; click a pin to see what it connects to; click a connection for three separate readings — Drive (the electricity: current '
              'and supply, no numbers), Signal (which end outputs or inputs, the protocol it carries) and Use (the tasks and Purposes that claim it). Click again, or press Escape, to clear. '
              'The stage selector shows the same parts as composed (base, before any init), after init, with the tasks assigned, or with the firmware committed; the protocol filter dims every '
              'pin that cannot carry it (SPI means SCK, MOSI, MISO and SS). The same data as tables: Pins (/display/pin-view-pins), Connections (/display/pin-view-connections), '
              'Surfaces (/display/pin-view-surfaces).')


def _view_item(item_id='pin-view-d3', index=0, segments=12, board=BOARD, system=SYSTEM, binding='', stage='base'):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': 'Pin view — boards, chips and parts with their pins',
        'description': 'What this is for: seeing which pins exist at every level (die pad, package leg, board pin, board part, bench part), what each can do, and what is connected to what. '
                       'Nothing here is edited; it only reads GET %s.' % DOOR,
        'visible': True, 'collapsed': False, 'cssClass': '',
        'componentProps': {'componentName': 'hardware-pin-view', 'inputs': {'board': board, 'system': system, 'binding': binding, 'stage': stage}},
        'item': None, 'nestedRows': [],
    }


_VIEW_PAGE = _page('pin-view', 'pin-view', _VIEW_TEXT, 'BoardPin', [_row(0, [_view_item()], min_height=640)], title='Pin view')

# ---------------------------------------------------------------- pv-5: the configuration events as a configured table (the event timeline in words; the picture opens at the event)
EVENTS_DOOR = '/api/board/%s/config-events' % BOARD
_EVENTS_PAGE = _page('config-events', 'config-events',
                     'Configuration events - the real-world changes that alter which pins are doing what: firmware flashed, a wire added or removed, a shield attached or detached, a binding chosen, a board reset. '
                     'One row is one event: its kind, when it happened (or "time not recorded" - an install record or a canvas wire stores no time and no person, and that is said, not guessed), who did it, '
                     'the cause in plain words, and how many pins it changed. Use "view" to open the pin view at that event: the timeline there highlights the pins it changed, with the before and after of each. '
                     'Events read from the install and wiring records are never copied; events recorded by a person or a bridge are ConfigurationEvent rows (POST %s, or `pol board events %s`). '
                     'The pins-changed count is worked out from the pin view itself, so the table can take a few seconds to load.' % (EVENTS_DOOR, BOARD),
                     'BoardPin', [
                         _row(0, [_table('pv-config-events', 0, 12, 'Every configuration event of the UNO', '',
                                         description='What this is for: the timeline of real-world changes to the board, oldest first (events with no recorded time come first). One row = one event. Columns: kind, when, who, cause, '
                                                     'pins_changed (how many pins changed state), instance (which physical board, or the design), source (read from the records, or recorded by a person or a bridge).',
                                         columns='seq,kind,when,who,cause,pins_changed,instance,source,view', column_formats='view:view:/display/pin-view?event={id}', data_path=EVENTS_DOOR)]),
                     ], title='Configuration events')

#: the pin view's pages: the d3 view first, then its three table pages, then the configuration events
PIN_VIEW_PAGES = [_VIEW_PAGE] + _TABLE_PAGES + [_EVENTS_PAGE]
