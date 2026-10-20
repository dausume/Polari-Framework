"""
@module hwnocode.light_page

/display/uno-core-demo — THE LIGHT TEST's page (slice ucd-light): ONE configured table of LightState rows (no raw JSON, no new
component). The `name` column links to the row's own page (the `ref:LightState` format). The description says, in plain words,
how to switch the light from the screen and how the board's button shows up. The readiness of the whole composition is on its
own page (/display/uno-core-demo-readiness, module uno_core_demo).
"""
from polariApiServer.module_pages_seed import _page, _row, _table

ROUTE = 'uno-core-demo'

def light_state_table(item_id='light-state', index=0, segments=12, data_path=''):
    """THE LightState row table of the light test - also EMBEDDED (not copied) on the sim bench page (D-hbc-5: one App UI, two places). `data_path` (optional) reads a rows
    door instead of the class, so the table can fetch again when a page scope changes; empty = the class, exactly as the demo page has always done."""
    return _table(item_id, index, segments, 'The light — its state right now and who last changed it', 'LightState',
                  description='One row is one light on one board. name is the board\'s name (click it to open the row). '
                              'led_on says whether the light is on. toggles counts every change since the board '
                              'started. source says who made the last change: command (this screen) or button (the '
                              'pushbutton on the board). seq counts the reports the board has sent, boot_session is '
                              'a number the board picks each time it starts (a new number means the board restarted), '
                              'and status reads idle until the light first changes, then active.',
                  columns='name,led_on,toggles,source,seq,boot_session,status',
                  column_formats='name:ref:LightState',
                  data_path=data_path,
                  # his ruling 2026-10-18: the Polari-side button ALTERS THE STRUCT; the change is what reaches the board.
                  # `{led_on}` alone keeps its boolean type (class-rows-action.fillBody).
                  row_action={'label': 'Turn the light on / off', 'method': 'POST', 'path': '/executeSolutionStepped',
                              'body_template': {'solutionName': 'light-toggle',
                                                'inputParams': {'object': '{name}', 'led_on': '{led_on}'}}})


LIGHT_PAGES = [
    _page(ROUTE, ROUTE,
          'The light test: one light on the board, switched two ways, with the board always telling this screen what the light is '
          'doing. To switch the light from this screen, press "Turn the light on / off" on the light\'s row: it runs the solution '
          'light-toggle, which changes led_on on the row (the struct) - that change is what is sent to the board, and the board '
          'follows within a moment. To switch it from the board, '
          'press the pushbutton: the light flips, toggles goes up by one and source reads button. When source reads command, '
          'the last change came from this screen. If both directions work, data and signals are travelling both ways between '
          'Polari and the board.',
          'LightState', [
              _row(0, [light_state_table()], min_height=200),
              _row(1, [_table('light-downloads', 0, 12, 'Downloads: the firmware and the app', 'FirmwareExport',
                              description='Everything you need to put the demo on a real board, one row per file. The form column says '
                                          'which file it is: install-bundle is the firmware to flash (the program and the notes for '
                                          'flashing it); demo-bundle is the firmware plus the bridge program, its settings and the '
                                          'Hardware App\'s definition, all in one folder; bridge-app-deb is the Hardware App '
                                          'installer for this demo; shell-core-deb is the shared program the Hardware App runs on, '
                                          'which it needs. Click download_url to fetch a row\'s file. tar_sha256 is the file\'s '
                                          'fingerprint, to compare after downloading; parity says whether the two ways of building '
                                          'the firmware gave the same bytes; created_at is when the file was made. Only the newest file of each kind is '
                                          'listed here (an older build stays on the server, but it is not offered beside today\'s).',
                              columns='form,download_url,tar_sha256,parity,created_at',
                              column_formats='download_url:link',
                              filter_field='solution', filter_value='uno-light',
                              data_path='/api/firmware/exports?solution=uno-light&latest_per_form=1')], min_height=220),
          ]),
]
