"""
@module hwnocode.light_page

/display/uno-core-demo — THE LIGHT TEST's page (slice ucd-light): ONE configured table of LightState rows (no raw JSON, no new
component). The `name` column links to the row's own page (the `ref:LightState` format). The description says, in plain words,
how to switch the light from the screen and how the board's button shows up. The readiness of the whole composition is on its
own page (/display/uno-core-demo-readiness, module uno_core_demo).
"""
from polariApiServer.module_pages_seed import _page, _row, _table

ROUTE = 'uno-core-demo'

LIGHT_PAGES = [
    _page(ROUTE, ROUTE,
          'The light test: one light on the board, switched two ways, with the board always telling this screen what the light is '
          'doing. To switch the light from this screen, run the solution light-toggle (it turns the light on if it is off, and '
          'off if it is on) or change led_on on the row below; the board follows within a moment. To switch it from the board, '
          'press the pushbutton: the light flips, toggles goes up by one and source reads button. When source reads command, '
          'the last change came from this screen. If both directions work, data and signals are travelling both ways between '
          'Polari and the board.',
          'LightState', [
              _row(0, [_table('light-state', 0, 12, 'The light — its state right now and who last changed it', 'LightState',
                              description='One row is one light on one board. name is the board\'s name (click it to open the row). '
                                          'led_on says whether the light is on. toggles counts every change since the board '
                                          'started. source says who made the last change: command (this screen) or button (the '
                                          'pushbutton on the board). seq counts the reports the board has sent, boot_session is '
                                          'a number the board picks each time it starts (a new number means the board restarted), '
                                          'and status reads idle until the light first changes, then active.',
                              columns='name,led_on,toggles,source,seq,boot_session,status',
                              column_formats='name:ref:LightState')], min_height=200),
          ]),
]
