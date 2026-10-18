# sense-led-line (catom) - the UNO's sense-pin isotopes

One job - notice that the LED line really switched, on a pin of its own wired FROM the LED pin - done in different ways. Each way is an ISOTOPE of the catom; the
catalogue row it implements is `sense-led-line:<route>` (`cmod.custom.isotope_variants_seeds`). Built exactly like `catoms/read-button` (fgm-5a).

| isotope | file it renders | how it is built | FirmwareVariant that uses it |
|---|---|---|---|
| `int1` (the shipped one) | - (hal.c, hand-written) | INT1 on D3, any edge, an ISR counts and stamps | uno-button-clock |
| `gpio-poll` | `hal_sense_poll.c` | `isotopes/gpio-poll/template.c.j2` - the main loop reads the pin once per pass | uno-light-sense-poll (sense on D3) |
| `pin-change-interrupt` | `hal_sense_pcint.c` | `isotopes/pin-change-interrupt/template.c.j2` - a PCINT ISR counts and stamps | uno-light-sense-pcint (sense on D8, wired from D6) |

Each rendered file supplies the two functions `hal.h` declares for a sense pin (`hal_sense_init`, `hal_sense_read`) and switches hal.c's INT1 block off with
`HAL_SENSE_ROUTE` (board_config.h), so the app (button_clock.c) is unchanged and the existing variants' bytes are unchanged (the identical-hex gate).

- `catom.json` - the contract and the HAL variables (families: drive / register / protocol / signal / execution, plan 5b).
- `isotopes/<iso>/isotope.json` - what it claims, which variant row and FirmwareVariant it belongs to.
- `isotopes/<iso>/substitutions.json` - where every number in the template comes from (a knob, or a cited row).
- `_common.j2` - the banner shared by the templates.

Rendering: `board.custom.sense_routes.render(route, knobs)` through the generator environment (`cmod.custom.generator.env`: StrictUndefined + the refusing C
filters). No timestamp is written, so the same knobs always give the same bytes. A status (declared / compiles / proven-on-twin) is never stored in these files:
it is derived.

The polled route can miss an edge when the line changes twice between two looks at the pin (it sees at most one change per main-loop pass); the pin-change route
sees both. The layout stays under `board/custom/firmware/uno/catoms/` for the same reason as read-button (the manifests rule).
