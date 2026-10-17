"""
@module board.pin_view_page

pv-0 (PIN_VIEW_PLAN.md 2.9): the pin view's DATA VIEWS beside the d3 view — three configured pages (tables only: no raw JSON, no new component): Pins, Connections, Surfaces. Each table reads one of
the row doors `GET /api/board/<board>/pin-view/{pins|connections|surfaces}`; a table's stage / protocol / system / binding are fixed in its data path (the generic table filters by a column, it
does not send query parameters), and each page's text says which other values the door takes. Plain words only; the pages are fixed to the UNO and its light demo, the way /display/hardware-chain
is fixed to one binding. The d3 view (pv-1) selects together with these tables.
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

PIN_VIEW_PAGES = [
    _page('pin-view-pins', 'pin-view-pins',
          'Pins — every pin at every level of the UNO: the silicon pads of the ATmega328P and the ATmega16U2, the legs of their packages, the header pins of the board, the pins of the parts on the board '
          'and the bench parts. One row is one pin. Colour in the picture is the protocol family; here the family is a word. %s %s' % (STAGES_TEXT, DOOR_TEXT),
          'BoardPin', [
              _row(0, [_table('pv-pins-base', 0, 12, 'Every pin — base composition (before any init)', '',
                              description='What this is for: all pins as composed, nothing claimed. One row = one pin. Columns: owner (the surface it belongs to), level (die = silicon pad, package = leg, board = header pin, part = a part '
                                          'on the board, bench = a bench part), label, number, kind, canonical (the board\'s own name, D0 .. A5), families (the protocols it can carry), drive_class (the pad class '
                                          'whose electrical limits apply: a name, the numbers are in the electrical view), stage, stage_why, consumers (what takes the line: a task, a Purpose, a part), bonded '
                                          '(brought out by the package), notes.',
                              columns=_PIN_COLS, data_path=DOOR + '/pins')]),
              _row(1, [_table('pv-pins-unassigned', 0, 6, 'Pins nothing has claimed yet (available)', '',
                              description='What this is for: the pins a no-code task could still take — they reach a header and no task claims them. Same columns as above, filtered to stage available at the base composition.',
                              columns='owner,level,label,canonical,families,drive_class,stage_why', data_path=DOOR + '/pins', filter_field='stage', filter_value='available'),
                       _table('pv-pins-proposed', 1, 6, 'Pins the light firmware\'s tasks have claimed (tasks assigned)', '',
                              description='What this is for: the pins the tasks of the light demo\'s firmware claim, at stage tasks-assigned (proposed), with the task and the Purpose that need each pin.',
                              columns='owner,level,label,canonical,families,stage,consumers', data_path=DOOR + '/pins' + _Q + '&stage=tasks-assigned', filter_field='stage', filter_value='proposed,committed')]),
              _row(2, [_table('pv-pins-spi', 0, 12, 'Pins able to carry SPI (SCK, MOSI, MISO, SS) — with the availability ladder\'s verdict', '',
                              description='What this is for: the protocol filter. A pin is listed when its chip can do one of the children of SPI; lit_why gives the availability ladder\'s verdict for that child in this '
                                          'context (blocked at which rung, or available with which conditions). The filter rows are the same on every level: pad, leg, header pin.',
                              columns='owner,level,label,canonical,families,lit,lit_why', data_path=DOOR + '/pins' + _Q + '&protocol=spi', filter_field='lit', filter_value='lit')]),
          ]),
    _page('pin-view-connections', 'pin-view-connections',
          'Connections — every pin-to-pin connection of the UNO and the bench, one row each: the two ends, what kind of connection it is (pad to leg inside a package, a leg to a header, a leg to a part on '
          'the board, chip to chip, a header to the bench), what sits in the path (a word: series resistor, buffer, capacitor), and three separate summaries. Drive is the electricity: which end supplies, '
          'sources and sinks or returns current, the rail and domain, the pull, and the class of the limit (within-recommended, undetermined, over, or unchecked when no check has run) — never a number. '
          'Signal is the signal: which end outputs and which inputs, the protocol signal it carries and its family. Use is who claims it: the tasks and the Purposes. %s' % DOOR_TEXT,
          'BoardPin', [
              _row(0, [_table('pv-conn-all', 0, 12, 'Every connection — the light firmware\'s tasks assigned', '',
                              description='What this is for: all connections with the stage of the light demo\'s tasks applied. One row = one connection between two pins. Columns: a/b (owner and pin), kind, via, drive, '
                                          'signal, use, stage. A connection\'s stage is the higher of its two ends.',
                              columns=_CONN_COLS, data_path=DOOR + '/connections' + _Q + '&stage=tasks-assigned')]),
              _row(1, [_table('pv-conn-chips', 0, 6, 'Chip to chip — the ATmega328P and the USB bridge', '',
                              description='What this is for: the lines between the two chips (the serial pair and the auto-reset line), with the part in the path. Filter: kind chip-to-chip.',
                              columns='a_label,b_label,via,drive,signal,use', data_path=DOOR + '/connections' + _Q + '&stage=tasks-assigned', filter_field='kind', filter_value='chip-to-chip'),
                       _table('pv-conn-bench', 1, 6, 'To the bench — the wires of the light demo\'s circuit', '',
                              description='What this is for: the board\'s header pins joined to the bench parts (resistor, LED, button) and the jumper between D6 and D3. Filter: kind to-bench.',
                              columns='a_label,b_label,via,drive,signal,use', data_path=DOOR + '/connections' + _Q + '&stage=tasks-assigned', filter_field='kind', filter_value='to-bench')]),
              _row(2, [_table('pv-conn-parts', 0, 12, 'To a part on the board — buffers, clock parts, connectors, test pads', '',
                              description='What this is for: the legs that end on a part of the board (the L LED buffer on D13, the 16 MHz parts, the USB connector, the ICSP header of the bridge, the test pads). Filter: kind to-board-part.',
                              columns='a_label,b_owner,b_label,via,drive,signal,use', data_path=DOOR + '/connections' + _Q, filter_field='kind', filter_value='to-board-part')]),
          ]),
    _page('pin-view-surfaces', 'pin-view-surfaces',
          'Surfaces — the things a person can click in the pin view: the board, the chip packages (enclosures), the silicon (SoC dies), the parts on the board and the bench parts. One row is one surface with '
          'its pin counts by stage. %s %s' % (STAGES_TEXT, DOOR_TEXT),
          'BoardPin', [
              _row(0, [_table('pv-surf-base', 0, 12, 'Every surface — base composition', '',
                              description='What this is for: what the design is made of and how many pins each piece has. One row = one surface. Columns: kind (board, enclosure, soc, board-part, bench-part), level, parent (what it sits '
                                          'inside: the die inside its package inside the board), shape (its math-defined outline row), pin_count, then the pins by stage.',
                              columns=_SURF_COLS, data_path=DOOR + '/surfaces')]),
              _row(1, [_table('pv-surf-tasks', 0, 12, 'Every surface — the light firmware\'s tasks assigned', '',
                              description='What this is for: the same surfaces with the light demo\'s tasks assigned, so the proposed counts show where the firmware reaches.',
                              columns=_SURF_COLS, data_path=DOOR + '/surfaces' + _Q + '&stage=tasks-assigned')]),
          ]),
]

