"""
@module cmod.cmod_pin_profile_page

pp-0: /display/pin-profiles - what each Purpose needs from a pin, BEFORE any pin is chosen, as CONFIGURED tables over the derived doors (no raw JSON,
no new component). Three tables: the profiles per Purpose, the same rolled up for the light Mission (the same need on the same role counts once),
and the tasks that gave no profile today and why. Reads GET /api/pin-profiles (cmod.custom.pin_profile_doors).
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_API = '/api/pin-profiles'
_LIGHT = 'initialization,ensure-button-controls-light,ensure-polari-observes-hardware-state,ensure-polari-can-control-light'

PIN_PROFILE_PAGES = [
    _page('pin-profiles', 'pin-profiles',
          'Pin profiles - what each Purpose needs from a pin before any pin is chosen. Every profile is worked out from the Purpose\'s own tasks (the atoms '
          'they run), the bench circuit (the LED, its resistor, the button) and the Purpose\'s numbers (debounce, latency); nothing is typed in. A profile keeps '
          'two things apart: the SIGNAL (which end outputs and which inputs, and what kind of line it is) and the DRIVE (the electricity: whether the pin must '
          'source or sink current, the load it feeds, the pull it needs). A number that no row cites reads `undetermined` and says why. A person\'s correction '
          'is a recorded override (who, when, why) shown beside the derived value. From the command line: pol capability pins <purpose>.',
          'CapabilityDefinition', [
              _row(0, [_table('pp-purposes', 0, 12, 'Pin profiles per Purpose - one row = one thing a Purpose needs from one pin', '',
                              description='What this is for: the pin needs of every Purpose that runs C tasks on a board. One row = one profile. Columns: purpose, role '
                                          '(which part the pin serves: the button, the LED, the sense line, the transport), kind (the kind of pin task, from the board '
                                          'compatibility table), signal (direction and family), drive (the electrical need: source or sink current, a pull-up, high impedance; '
                                          'the load; the current or why it is undetermined), timing (edge, debounce, latency, rate - from the Purpose\'s criteria, undetermined '
                                          'when it has none), phases (init, runtime), reserved (the pin belongs to the USB transport), origin (task = a task of the Purpose; '
                                          'bench = wired on the bench but no task of the Purpose reads it), corrections (a person\'s overrides, with who and why), evidence '
                                          '(where each field came from). GET %s.' % _API,
                              columns='purpose,role,kind,signal,drive,timing,phases,reserved,origin,count,corrections,evidence', data_path=_API)]),
              _row(1, [_table('pp-mission', 0, 12, 'Rolled up for the light Mission - the same need on the same role counts once', '',
                              description='What this is for: the pins the four light Purposes need together. One row = one pin need after merging: a need shared by several '
                                          'Purposes (the LED, the transport) is one row listing them in `purpose`. Columns as above plus importance (the strongest of the '
                                          'Purposes\' importance in the Mission; required when the Mission says nothing) and reserved (the transport pins the USB cable '
                                          'reserves, from the board\'s lifecycle rows). GET %s?view=mission&purposes=... (repoint to ?mission=<name> once a Hardware Mission '
                                          'row exists).' % _API,
                              columns='role,kind,importance,signal,drive,timing,phases,reserved,purpose,origin,count,evidence',
                              data_path='%s?view=mission&purposes=%s' % (_API, _LIGHT))]),
              _row(2, [_table('pp-unresolved', 0, 12, 'Tasks that gave no pin profile today, and why', '',
                              description='What this is for: honesty about the gaps. One row = one task of a Purpose that did not become a profile (a peripheral, a memory '
                                          'field, a task with no hardware touch, a pin the board cannot give the task\'s kind). Columns: purpose, task, why. GET %s?view=unresolved.' % _API,
                              columns='purpose,task,why', data_path='%s?view=unresolved' % _API)]),
          ], title='Pin profiles'),
]
