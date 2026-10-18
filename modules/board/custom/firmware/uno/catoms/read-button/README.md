# read-button (catom) - the UNO's button isotopes

One job - know when a person presses the button - done in different ways. Each way is an ISOTOPE of the catom; the catalogue
row it implements is `read-button:<route>` (`cmod.custom.isotope_variants_seeds`).

| isotope | file it renders | how it is built | FirmwareVariant that uses it |
|---|---|---|---|
| `int0` (the shipped one) | - (hal.c, hand-written) | INT0 on D2, falling edge, lockout debounce | uno-light, uno-button-clock |
| `pin-change-interrupt` | `hal_button_pcint.c` | `isotopes/pin-change-interrupt/template.c.j2` | uno-light-pcint (button on D4) |
| `analog-threshold` | `hal_button_adc.c` | `isotopes/analog-threshold/template.c.j2` | uno-light-analog (button on A0) |

Each rendered file supplies the three functions `hal.h` declares for a button (`hal_button_init`, `hal_presses`,
`hal_take_toggle_pending`) and switches hal.c's INT0 block off with `HAL_BUTTON_ROUTE` (board_config.h), so the app (light.c) is
unchanged and the existing variants' bytes are unchanged (the identical-hex gate).

- `catom.json` - the contract and the HAL variables (families: drive / register / protocol / signal / execution, plan 5b).
- `isotopes/<iso>/isotope.json` - what it claims, which variant row and FirmwareVariant it belongs to.
- `isotopes/<iso>/substitutions.json` - where every number in the template comes from (a knob, or a cited row).
- `_common.j2` - the banner and the lockout debounce shared by the templates.

Rendering: `board.custom.button_routes.render(route, knobs)` through the generator environment
(`cmod.custom.generator.env`: StrictUndefined + the refusing C filters). No timestamp is written, so the same knobs always give the
same bytes. A status (declared / compiles / proven-on-twin) is never stored in these files: it is derived.

Where this lives and why: plan section 5b puts catoms under `modules/<module>/firmware/catoms/`. The manifests selftest allows only
`objects/`, `custom/` and `initialData/` as module subfolders, so the same layout is kept under
`board/custom/firmware/uno/catoms/` (the board module owns the UNO's HAL). Extending the manifest rule for `firmware/` is ed-0's call.

The analog route assumes a pull-up resistor (10 kohm by default) holds the pin at 5 V and the switch pulls it to ground; the
internal pull-up is switched off. Thresholds are in millivolts and converted with ADC = Vin * 1024 / Vref (Vref = AVcc = 5 V).
