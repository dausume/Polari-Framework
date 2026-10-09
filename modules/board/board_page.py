"""
@module board.board_page
/display/boards — the board arc as CONFIGURED tables only (no custom component, no raw JSON): every tracked device with
its USB route, adapter and road status; the adapters; the roads; the programmer kinds with their DRY-RUN templates; the
boards and adapters seen plugged in; the cited datasheet facts; (brd-bo) THE BOARD OBJECT — SoCs, pins, runtime profiles, views,
conflicts.

/display/firmware-installer — THE FIRMWARE INSTALLER APP's page (brd-fi, plan §7a). His intent: "that way we can test
different kinds of things on the arduino uno to see if it works".

Everything here is a CONFIGURED table over rows (variants, builds, devices seen, programmer kinds, plans, records), plus
exactly ONE new component, `firmware-installer-panel`, justified the way `pipeline-setup-panel` was for `pol jenkins
setup`: no configured table can carry the FLOW — pick a variant → build → DRY-RUN (the plan's argv shown verbatim) →
a confirm that stays disabled until a plan exists → the result (frames/s, the row's fields live over STOMP) → "try
another variant". The panel never composes a command: it sends a build NAME, a target NAME and a plan NAME to the
local server's installer doors (/api/board/installer/…), and the server runs the argv it fixed in the plan row, on its
own host only (the host holding the port). No raw JSON anywhere on the page.
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _svg_panel

_BOARDS_PAGES = [
    _page('boards', 'boards',
          'Boards — every device the board arc tracks (track all, simulate few: the UNO in simavr and, since sc-3, the ESP32-C3 in Espressif\'s '
          'QEMU fork), how each is reached from the Polari host over USB (directly or through a known adapter), and the road still to walk for '
          'it. Readiness (usable / partial / tracked) is DERIVED from whether a board has a twin, a firmware template and something that runs '
          'it — never hand-set (`pol board detect`; `pol board pins <board>`). Goes with /display/firmware-installer (install firmware on a '
          'usable board) and /display/hardware-solutions (no-code on a usable board); the physical layers (SoCs, pins, runtime profiles, '
          'views, conflicts) are THE BOARD OBJECT, brd-bo.',
          'BoardDefinition', [
              _row(0, [_svg_panel('boards-pinmap-svg', 0, 12,
                                  'Pin map, drawn — pick a board; its headers (or, with none modelled, its bare pin list) named, '
                                  'coloured by role (PWM, ADC, UART, I2C/SPI, power, ground, GPIO, button, LED)',
                                  '/api/board/pinmaps',
                                  description='What this is for: THE PIN ASSIGNMENT drawn straight from brd-bo\'s own rows (board.custom.'
                                              'pinmap_svg) for ANY board that has BoardPin rows — not a screenshot, not hand-drawn, not one '
                                              'board wired into the page: GET /api/board/pinmaps lists every modelled board and this panel\'s '
                                              'own selector switches between them. `pol board assign <board> <role> <pin>` moves a net to a '
                                              'different pin and the drawing changes with it, the same rows every other view (KiCad, Zephyr, '
                                              'bare C) renders from. Hover a pin for its SoC pin, net and C firmware symbol.')], min_height=300),
              _row(1, [_table('boards-pin-roles', 0, 12,
                              'Pin roles — what each kind is for (arduino-uno-r3)', '',
                              description='What this is for: one row per pin ROLE the UNO actually uses (adc, gpio, ground, i2c, led, power, '
                                          'pwm, spi, uart), what it is, how it is used on this board, which pins carry it (derived from the '
                                          'BoardPin/Connector rows, board.custom.pinmap_svg.pins_by_role), and a cited `learn more` link '
                                          '(Arduino\'s UNO R3 docs, the ATmega328P datasheet, or Wikipedia — board.custom.pin_roles). GET '
                                          '/api/board/arduino-uno-r3/pin-roles computes it fresh on every load; the same door works for any '
                                          'other modelled board by name.',
                              columns='role,description,usage,pins,learn_more', column_formats='learn_more:link',
                              data_path='/api/board/arduino-uno-r3/pin-roles')]),
              _row(2, [_table('boards-usable', 0, 12,
                              'Usable now — simulate, install, no-code (sorted readiness first)', 'BoardDefinition',
                              description='What this is for: the boards you can actually DO something with today — run a twin, build and '
                                          'install firmware, or run a no-code solution. One row = one BoardDefinition with readiness=usable '
                                          '(a twin AND a firmware template AND a no-code solution or fault scenario target it). Columns: name '
                                          '(the BoardDefinition row), readiness_why (which of the three it has), twin (renode:/simavr:/… or '
                                          'empty), simulated (picked for simulation), usb_route/programmer/adapter_needed (how it is flashed), '
                                          'road_status (the plan, for reference only — it does not change readiness). GET /api/board/boards/'
                                          'readiness computes this on every load from live BoardDefinition + FirmwareVariant + HardwareSolution '
                                          '+ Scenario rows.',
                              columns='name,readiness_why,twin,simulated,device_class,soc,isa,usb_route,programmer,adapter_needed,road_status',
                              data_path='/api/board/boards/readiness', filter_field='readiness', filter_value='usable')]),
              _row(3, [_table('boards-tracked', 0, 12,
                              'Tracked for later — roads, nothing runnable yet', 'BoardDefinition',
                              description='What this is for: every other tracked device, with what is MISSING to become usable (readiness_why '
                                          'names it) and the Road\'s own status for context. One row = one BoardDefinition with readiness='
                                          'partial or tracked. Columns: readiness (partial has at least one of twin/template/solution; tracked '
                                          'has none — a register row only), readiness_why (what is missing), road_status (todo | in-progress | '
                                          'done — the PLAN; it does not by itself change readiness, only a real twin/template/solution does).',
                              columns='name,readiness,readiness_why,road_status,register_status,device_class,soc,isa,usb_route,adapter_needed,usb_rule',
                              data_path='/api/board/boards/readiness', filter_field='readiness', filter_value='partial,tracked')]),
              _row(4, [_table('boards-adapters', 0, 12, 'Adapters and programmers (register §1a) — the host side is always USB', 'AdapterDefinition',
                              description='What this is for: the USB adapters that close the RULE-1 gap for boards that are not natively USB. '
                                          'One row = one AdapterDefinition. Columns: kind/chip (the adapter hardware), usb_connector/usb_ids_json '
                                          '(how the host sees it), targets (which boards it can reach), engine (the flashing tool), '
                                          'hardware_open/firmware_open (licence openness), origin.',
                              columns='name,kind,chip,usb_connector,usb_ids_json,targets,engine,hardware_open,firmware_open,origin',
                              column_formats='name:ref:AdapterDefinition')]),
              _row(5, [_table('boards-roads', 0, 6, 'Roads — todo | in-progress | done per device', 'Road',
                              description='What this is for: the ordered PLAN per tracked device — facts, definition, twin, firmware template, '
                                          'flashed, measured. One row = one Road (one per board). Columns: status (the road\'s overall state), '
                                          'steps_json (each step\'s own todo/in-progress/done + note), concept_node (its node on the '
                                          'board-roads tech tree). A step turning done here does not by itself flip a board to usable above — '
                                          'readiness needs the real twin/template/solution rows to exist.',
                              columns='name,board,status,steps_json,concept_node', column_formats='name:ref:Road,board:ref:BoardDefinition'),
                       _table('boards-programmers', 1, 6, 'Programmer kinds — engine, adapter, the DRY-RUN argv', 'ProgrammerKind',
                              description='What this is for: HOW a board family is flashed. One row = one ProgrammerKind (e.g. avrdude-arduino, '
                                          'esptool). Columns: engine/engine_kind (the flashing tool and its kind), adapter_kind (which '
                                          'AdapterDefinition it rides over), dry_run_template (the argv template shown verbatim before any '
                                          'install runs), placement (where it runs: host | bridge).',
                              columns='name,engine,engine_kind,adapter_kind,dry_run_template,placement', column_formats='name:ref:ProgrammerKind')]),
              _row(6, [_table('boards-instances', 0, 7, 'Seen plugged in (pol board detect)', 'BoardInstance',
                              description='What this is for: actual hardware the host has SEEN on USB, via `pol board detect`. One row = one '
                                          'physical device instance. Columns: definition/definition_kind (which BoardDefinition or '
                                          'AdapterDefinition it matched, or unadmitted), state, host (which machine saw it), usb_id/by_id_path '
                                          '(how it is addressed), possible_targets_json (candidate boards when ambiguous), last_seen_at.',
                              columns='name,definition,definition_kind,state,host,usb_id,by_id_path,possible_targets_json,last_seen_at'),
                       _table('boards-facts', 1, 5, 'Datasheet facts (cited)', 'DatasheetFact',
                              description='What this is for: numbers about a board that are CITED, never guessed. One row = one fact. Columns: '
                                          'fact_key/value/unit (the number), document/page_table (where it came from), url (the source).',
                              columns='board,fact_key,value,unit,document,page_table,url')]),
              # brd-wire (grpc-j4): which Polari row IS which hardware interface — the chain of one instance is
              # GET /api/board/instances/<instance>/interface
              _row(7, [_table('boards-bindings', 0, 12, 'Hardware-interface bindings — which row is which interface: bridge, instance index '
                              '(ceil(log2 n) bits on the wire), port, the wire contract hash v2, frames applied / refused',
                              'HardwareInterfaceBinding',
                              description='What this is for: the live wiring chain — which Polari object row IS which physical/bridge '
                                          'interface, and how many frames have crossed it. One row = one HardwareInterfaceBinding. Columns: '
                                          'bridge_name/port (the transport), object_class/object_name (the Polari row bound), instance_index '
                                          '(its bit-packed slot on the wire), wire_version/contract_hash_v2 (the frame format proven against), '
                                          'frames_seen/refused_frames (traffic since binding). GET /api/board/instances/<instance>/interface '
                                          'walks this same chain for one instance.',
                              columns='name,bridge_name,object_class,object_name,board_instance,board_definition,interface_kind,interface_name,'
                                      'port,instance_index,wire_version,contract_hash_v2,frames_seen,refused_frames,last_seen_at',
                              column_formats='board_definition:ref:BoardDefinition')]),
              # brd-bo: THE BOARD OBJECT (PCB_FROM_SCRATCH_PLAN §2b) — the SoCs, the ONE pin assignment every view renders from,
              # the runtime profiles (supported or refused, with why), the views by sha and the conflicts (never auto-resolved)
              _row(8, [_table('boards-socs', 0, 12, 'SoCs — package, ISA, clock, where each fact came from (the board object\'s SoC layer)', 'SocDefinition',
                              description='What this is for: THE BOARD OBJECT\'s SoC identity layer — one row per chip a board is built '
                                          'around. One row = one SocDefinition. Columns: package/isa/cpu_clock_hz/pin_count (the chip itself), '
                                          'vendor_target/zephyr_soc (build-system identifiers), source (where the facts came from), '
                                          'undetermined (named gaps, never guessed).',
                              columns='name,title,package,isa,cpu_clock_hz,pin_count,vendor_target,zephyr_soc,source,undetermined')]),
              _row(9, [_table('boards-pins', 0, 12, 'Pins — named ONCE: the canonical name every view uses (KiCad, Zephyr, ESP-IDF, bare C) ↔ SoC pin ↔ net ↔ '
                              'connector pin, the function / peripheral / signal, the C symbol, where it came from', 'BoardPin',
                              description='What this is for: the ONE pin assignment every view (KiCad, Zephyr, ESP-IDF, bare C) renders from — '
                                          'change a row here and every view changes with it (`pol board assign <board> <role> <pin>`). One row '
                                          '= one named pin. Columns: canonical (the name every view uses) ↔ soc_pin/net/connector_pin (the '
                                          'physical identity), function/peripheral/signal (what it does), firmware_symbol (the C name), origin, '
                                          'undetermined.',
                              columns='board,canonical,soc_pin,net,connector_pin,function,peripheral,signal,firmware_symbol,alias,origin,undetermined,links_refs_json',
                              column_formats='board:ref:BoardDefinition,name:ref:BoardPin,links_refs_json:refs')]),
              _row(10, [_table('boards-runtime', 0, 12, 'Runtime profiles — per firmware_runtime: supported (console, tick, twin) or REFUSED with the reason',
                              'RuntimeProfile',
                              description='What this is for: which firmware runtimes (bare-c | freertos | esp-idf | zephyr) a board actually '
                                          'supports, and why the others are refused rather than silently unavailable. One row = one board x '
                                          'runtime pair. Columns: supported (bool), refusal (the reason when not), console_uart/clock_hz/'
                                          'tick_hz/heap_bytes (what that runtime gets), twin (its simulator), origin.',
                              columns='board,runtime,supported,refusal,console_uart,clock_hz,tick_hz,heap_bytes,twin,origin',
                              column_formats='board:ref:BoardDefinition')]),
              _row(11, [_table('boards-views', 0, 7, 'Views — rendered out / ingested in, each by sha256 with the board sha at that moment (refusals too)',
                              'BoardView',
                              description='What this is for: every time the board object was rendered OUT to a view (KiCad, Zephyr DTS, …) or '
                                          'ingested IN from one, with the sha of both the view and the board rows at that moment — so a stale '
                                          'view is detectable. One row = one render/ingest event. Columns: direction (out|in), sha256/board_sha '
                                          '(the two fingerprints compared), refused/refusal, conflicts (count), fields_carried.',
                              columns='board,kind,direction,sha256,board_sha,refused,refusal,conflicts,fields_carried,at'),
                       _table('boards-conflicts', 1, 5, 'Conflicts — a view disagreed with the rows; shown, never auto-resolved', 'BoardConflict',
                              description='What this is for: a view (KiCad, Zephyr, …) disagreed with the board rows on a pin or field — shown '
                                          'for a person to resolve, never auto-picked. One row = one disagreement. Columns: pin/field (what '
                                          'disagreed), rows_value/view_value (the two answers), state (open | resolved), detected_at.',
                              columns='board,view_kind,pin,field,rows_value,view_value,state,detected_at')]),
              # fs-2a (his ruling 2026-10-06): compatibility between a firmware task's target kind and a board's pin
              # roles/capabilities — "a clear indicator of when we click on a target what ones are valid targets"
              _row(12, [_table('boards-target-compat', 0, 12, 'Target compatibility — which pin roles satisfy each firmware task target kind (cited)',
                              'TargetCompatibilityRule',
                              description='What this is for: THE COMPATIBILITY TABLE a pin-map drag checks before accepting a drop (board.custom.'
                                          'target_compat.compatible(), POST /api/firmware/solutions/{name}/assign). One row = one task target kind '
                                          '(analog-in, pwm-out, uart-rx/tx, i2c-sda/scl, spi-mosi/miso/sck/ss, digital-in/out, interrupt-in, power/'
                                          'ground). Columns: roles (the board.custom.pin_roles roles this kind draws on), matches (which pins '
                                          'qualify, in plain words — e.g. the UNO\'s A0-A5 for analog-in), source_label/source_url (the Arduino '
                                          'docs / ATmega328P datasheet / Wikipedia citation), notes (e.g. a PCINT-only pin is undetermined, not '
                                          'refused — its PCICR/PCMSKn bank is not modeled yet). power/ground rows are never assignable, no '
                                          'exception. GET /api/board/target-compat computes this fresh (global, not per-board); GET /api/board/'
                                          '<board>/pins/<pin> and GET /api/firmware/solutions/<name>/tasks/<task>/valid-targets check ONE pin or '
                                          'ONE task against it.',
                              columns='kind,title,roles,description,matches,source_label,source_url,notes', column_formats='source_url:link',
                              data_path='/api/board/target-compat')]),
              # fs-2d (his ask: "the power pins have no definitions at all" + his follow-up: "these are all the
              # parts in our kit, we will be wanting to use these as reference for how we make our sample
              # firmwares") — the kit parts register a sample FirmwareSolution/Capability is built FROM.
              _row(13, [_table('boards-kit-parts', 0, 12, 'Kit parts — what each part is, how it wires to a pin, and which sample firmware (if '
                              'any) already uses it (cited: Arduino Starter Kit book, "Parts in your kit" pp. 6-9 + "The Arduino Board" p.11)',
                              'KitPart',
                              description='What this is for: the physical parts register a sample firmware is BUILT FROM (his follow-up ask, '
                                          'verbatim). One row = one KitPart. Columns: interface_kind (the board-pin kind it wants: analog-in | '
                                          'digital-in | digital-out | pwm-out | uart | i2c | spi | servo-pwm | via-driver | empty for a part '
                                          'with no pin interface of its own), driver_needed (empty when it wires straight to a pin — a DC '
                                          'motor needs an H-bridge, an LED needs a series resistor), pin_count/pin_roles (which physical pin '
                                          'of the PART does what), electrical_notes/polarity/kit_quantity (cited, or undetermined naming the '
                                          'missing fact), sample_capabilities (DERIVED: which of today\'s Capabilities already use this part '
                                          '— temp-sensor-to-os names the TMP36, blink-on-command names the LED). A BLANK sample_capabilities '
                                          'cell is "a part without a sample yet" — the backlog for future sample firmwares; GET '
                                          '/api/board/kit-parts also names that list explicitly as parts_without_sample.',
                              columns='kit,title,what_it_is,interface_kind,driver_needed,pin_count,pin_roles,connects_to,electrical_notes,'
                                      'polarity,kit_quantity,sample_capabilities,source',
                              data_path='/api/board/kit-parts')]),
          ]),
]


# ---------------------------------------------------------------- brd-fi: the Firmware Installer App
def _panel(item_id, index, segments, title, path='/api/board/installer', board='arduino-uno-r3'):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False, 'cssClass': '',
        'componentProps': {'componentName': 'firmware-installer-panel', 'inputs': {'path': path, 'board': board}},
        'item': None, 'nestedRows': [],
    }



# ucd-0a/0f (his ruling 2026-10-08: "The page has been overwhelmed with the tables. We should keep them for more specialized or
# tabular displays we can open"): THE HARDWARE CHAIN has its own page; /display/boards is the readiness page it was.
_CHAIN_PAGES = [
    _page('hardware-chain', 'hardware-chain',
          'The hardware chain — Board → Pin → SoC Pin → PinFunction → PeripheralSignal → Peripheral → Register → RegisterField, as '
          'rows derived from the register snapshot and cited to the datasheet, navigable both ways (every link opens that row\'s own '
          'page; every `_refs` chip is a reverse link). Start with the D3 walk; `pol board chain <board> <pin>` prints the same.',
          'BoardPin', [
              # ucd-0a: THE HARDWARE CHAIN (UNO_CORE_DEMO_PLAN.md §5f/§5g — his measure of success: "a novice can inspect the model and
              # understand why that firmware configures the hardware the way it does"). Every table below is a configured table over
              # derived+cited rows; every `:ref:` column is a link to that row's own object page, every `:refs` list the reverse links —
              # Board → Pin → SoC Pin → PinFunction → PeripheralSignal → Peripheral → Register → RegisterField, and back, no custom component.
              _row(0, [_table('boards-chain-d3', 0, 12, 'The hardware chain of ONE pin, walked — Arduino D3 (pick any other pin: GET /api/board/<board>/chain/<pin>, '
                              '`pol board chain arduino-uno-r3 D3`)', '',
                              description='What this is for: the whole chain for one pin, in order, so a person new to hardware can read D3 top '
                                          'to bottom: the board pin (net, connector, C symbol) → its SoC pin (port/bit, package pin) → every '
                                          'function that pin can take (GPIO, INT1, OC2B, PCINT19) → the peripheral signals behind them → the '
                                          'peripherals (External Interrupts, Timer/Counter2, Pin Change Interrupts, Port D) → their registers '
                                          '(the ones holding bits for THIS pin first) → the cited bit fields that configure this pin, each with '
                                          'its values and what they mean. One row = one hop; `ref` opens the hop\'s own page. Computed on every '
                                          'load from the same rows the tables below show.',
                              columns='hop,kind,name,what,detail,ref', column_formats='ref:refs',
                              data_path='/api/board/arduino-uno-r3/chain/D3')]),
              _row(1, [_table('boards-peripherals', 0, 12, 'Peripherals — the chip\'s functional blocks: what each does, its chapter, its signals and registers',
                              'Peripheral',
                              description='What this is for: one row per functional block of the SoC (a timer, the serial port, an I/O port, '
                                          'the ADC, the external-interrupt unit). Columns: kind, title (the datasheet chapter), chapter (the '
                                          'citation, or undetermined when that chapter was not read), description (plain words), '
                                          'signals_refs_json (the signals it can put on pins — links), registers_refs_json (the registers '
                                          'that configure it — links), pin_functions_refs_json (every pin function that reaches it — links). '
                                          'Derived from the register snapshot\'s grouping rules and the datasheet port tables; never typed in.',
                              columns='name,peripheral,kind,title,chapter,description,signals_refs_json,registers_refs_json,pin_functions_refs_json,origin,undetermined',
                              column_formats='name:ref:Peripheral,signals_refs_json:refs,registers_refs_json:refs,pin_functions_refs_json:refs')]),
              _row(2, [_table('boards-peripheral-signals', 0, 6, 'Peripheral signals — one line a block can drive or read through a pin (OC2B, INT1, RXD, ADC0, PD3 as GPIO)',
                              'PeripheralSignal',
                              description='What this is for: the peripheral\'s side of the pin ↔ peripheral link. One row = one signal of one '
                                          'peripheral. Columns: peripheral (link), signal, channel, direction (in | out | inout | undetermined — '
                                          'derived from the signal family, said so), pin_functions_refs_json (which pin functions carry it — '
                                          'links), notes (which register fields configure it, when cited). Derived from the datasheet port '
                                          'tables (one row per alternate-function name) + one GPIO signal per port bit.',
                              columns='name,peripheral,signal,channel,direction,description,pin_functions_refs_json,notes,undetermined',
                              column_formats='name:ref:PeripheralSignal,peripheral:ref:Peripheral,pin_functions_refs_json:refs'),
                       _table('boards-pin-functions', 1, 6, 'Pin functions — what each SoC pin CAN do (available; a firmware activates one as a SignalRoute)',
                              'PinFunction',
                              description='What this is for: the pin\'s side of the link. One row = one (SoC pin × function): PD3 has GPIO, '
                                          'INT1, OC2B, PCINT19. Columns: soc_pin (link), function, signal (link), peripheral (link), routing '
                                          '(fixed on the AVR — one pin per function; mux/matrix reserved for chips that choose), overrides_gpio '
                                          '(§14.3: an enabled alternate function overrides DDR/PORT), exclusive_group (undetermined until '
                                          'cited), board_pins_refs_json (which board pins expose this SoC pin — links back up the chain).',
                              columns='name,soc_pin,function,signal,peripheral,routing,overrides_gpio,exclusive_group,description,board_pins_refs_json,undetermined',
                              column_formats='name:ref:PinFunction,soc_pin:ref:SocPin,signal:ref:PeripheralSignal,peripheral:ref:Peripheral,board_pins_refs_json:refs')]),
              _row(3, [_table('boards-registers', 0, 5, 'Registers — every register of the SoC: address, I/O vs data space, its peripheral, its cited bit fields',
                              'Register',
                              description='What this is for: the chip\'s register map as rows, one per register the toolchain\'s own header '
                                          'defines (avr-libc <avr/io.h>, read with avr-gcc -dM — the snapshot\'s sha is in origin). Columns: '
                                          'register, peripheral (link), addr (the address avr-libc defines), addr_mem (the data-space address '
                                          'for an I/O-space register: io + 0x20, as the datasheet prints both), space (io | mem), width_bytes, '
                                          'reset_value (cited), description (the datasheet\'s register title, cited), fields_refs_json (its '
                                          'cited bit fields — links; undetermined names the registers whose fields are not captured yet).',
                              columns='name,register,peripheral,addr,addr_mem,space,width_bytes,reset_value,description,page_table,fields_refs_json,undetermined',
                              column_formats='name:ref:Register,peripheral:ref:Peripheral,fields_refs_json:refs'),
                       _table('boards-register-fields', 1, 7, 'Register fields — each bit field, its values and what they mean, how it may be accessed (rw | r | w1c | w-strobe | rw-toggle), cited to the page',
                              'RegisterField',
                              description='What this is for: the last hop — the bits themselves, cited one by one to the ATmega328P datasheet '
                                          '(DS40002061B, section/table/page in page_table). One row = one bit field of one register. Columns: '
                                          'register (link), field, bit_hi/bit_lo/width, access (rw plain; r read-only; w1c = a flag cleared by '
                                          'writing a ONE to it — never read-modify-write; w-strobe = writing acts, reads zero; rw-toggle = '
                                          'writing one toggles another register\'s bit), reset_value, description (the datasheet\'s bit '
                                          'title), values_json (each value → the datasheet\'s own sentence), affects_signal / affects_pin '
                                          '(the signal or pin this field configures — links), page_table (the citation).',
                              columns='name,register,field,bit_hi,bit_lo,width,access,reset_value,description,values_json,affects_signal,affects_pin,page_table,notes',
                              column_formats='name:ref:RegisterField,register:ref:Register,affects_signal:ref:PeripheralSignal,affects_pin:ref:SocPin')]),
              # ucd-0b2a: address space as rows (UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9) — the alias Register.addr/
              # addr_mem used to carry as two columns is now rows: AddressSpace (io | data) + RegisterAddressMapping
              # (one per register per space it is reachable in); RegisterBlock makes the datasheet's own register-
              # summary grouping a row (+ shared blocks, e.g. MCUCR.PUD for every GPIO port); MemoryRegion the three
              # memories. AddressSpace/MemoryRegion rows open from their own object page (/object/AddressSpace/<name>,
              # /object/MemoryRegion/<name>) or by following a link below — no separate table needed for two-and-three rows.
              _row(4, [_table('boards-address-mappings', 0, 6, 'Address spaces + mappings — every register, by which address space(s) it is reachable through',
                              'RegisterAddressMapping',
                              description='What this is for: the AVR\'s two address spaces (io: IN/OUT, 0x00-0x3F; data: LD/ST/LDS/STS/'
                                          'LDD/STD, the SAME io registers at +0x20, plus the extended I/O 0x60-0xFF that has no io alias) '
                                          'as ROWS, cited DS40002061B §8.5 "I/O Memory", p.30. One row = one (register × address space) '
                                          'it is reachable through — an io-space register carries BOTH an @io and an @data row (EIMSK: '
                                          '0x1D and 0x3D); a mem-space register carries only @data. Columns: register (link), '
                                          'address_space (link — open it for the space\'s own range/instructions), address (hex), how '
                                          '(the instruction family), origin.',
                              columns='name,register,address_space,address,how,origin,undetermined',
                              column_formats='name:ref:RegisterAddressMapping,register:ref:Register,address_space:ref:AddressSpace'),
                       _table('boards-register-blocks', 1, 6, 'Register blocks + memory regions — the datasheet\'s own register-summary grouping, and the three memories',
                              'RegisterBlock',
                              description='What this is for: one row per Peripheral\'s own register-summary grouping (RegisterBlock — '
                                          'today one block per peripheral); `registers_refs_json` lists every Register in it, '
                                          '`shared_with_refs_json` names OTHER peripherals that configure THROUGH this block (cited: '
                                          'MCUCR.PUD disables every GPIO port\'s pull-ups regardless of DDxn/PORTxn, §14.4.1 p.100 — the '
                                          'CPU block\'s only shared case this slice). The chip\'s three memories (flash/sram/eeprom) are '
                                          'MemoryRegion rows, open from Register.block\'s own peripheral page or by name '
                                          '(/object/MemoryRegion/atmega328p:flash|sram|eeprom) — sram shares the data AddressSpace the '
                                          'table above shows; flash is program memory and eeprom is reached through EEAR/EEDR, neither '
                                          'addressed through io/data at all (said so in each row\'s own `undetermined`).',
                              columns='name,peripheral,title,registers_refs_json,shared_with_refs_json,origin',
                              column_formats='name:ref:RegisterBlock,peripheral:ref:Peripheral,registers_refs_json:refs,shared_with_refs_json:refs')]),
          ]),
]

INSTALLER_PAGES = [
    _page('firmware-installer', 'firmware-installer',
          'Firmware Installer — build and install DIFFERENT Polari firmware variants on the one UNO (or its simavr twin) '
          'and see each one\'s effect: detect → the builds that fit → DRY-RUN → confirm → install → the rows arriving. '
          'Defaults to arduino-uno-r3 — today\'s only board with a twin, a firmware template AND real installs (see '
          '/display/boards for the full usable/tracked split). Variants come from here; /display/c-atoms is where a '
          'variant\'s C gets read as atoms, /display/hardware-solutions is the no-code path over the same board.',
          'FirmwareVariant', [
              _row(0, [_panel('fi-flow', 0, 12, 'Install a variant — pick, build, read the command, confirm, watch it run, try another')], min_height=520),
              _row(1, [_table('fi-variants', 0, 12, 'Variants — each one a different thing to test on the UNO (add your own row here)', 'FirmwareVariant',
                              description='What this is for: named firmware RECIPES to try (his words: "test different kinds of things on the '
                                          'arduino uno to see if it works"). One row = one FirmwareVariant. Columns: app (the template: sim_rig | '
                                          'blink | analog | echo), classes_json (which Polari classes it speaks), features_json/knobs_json (what '
                                          'is compiled in and tunable), what_to_watch (the effect to look for when it runs), origin (seeded | '
                                          'person).',
                              columns='name,title,app,classes_json,features_json,knobs_json,what_to_watch,origin',
                              column_formats='name:ref:FirmwareVariant')]),
              _row(2, [_table('fi-builds', 0, 12, 'Builds — sizes measured (avr-size), the .hex sha256, the header sha + wire order the compat check uses',
                              'FirmwareBuild',
                              description='What this is for: one compiled artifact per variant, with the measurements the installer checks '
                                          'before flashing. One row = one FirmwareBuild. Columns: size_text/size_data/size_bss (avr-size, vs the '
                                          'board\'s flash/RAM), artifact_sha256 (the .hex), header_sha256/tag_order_json (the wire contract the '
                                          'compat check matches against the server), flashed_to, built_at.',
                              columns='name,variant,state,size_text,size_data,size_bss,artifact_sha256,header_sha256,tag_order_json,flashed_to,built_at',
                              column_formats='name:ref:FirmwareBuild')]),
              _row(3, [_table('fi-devices', 0, 7, 'Seen plugged in (pol board detect) — boards, and adapters waiting for a target', 'BoardInstance',
                              description='What this is for: physical devices the host has actually SEEN on USB (not every tracked board — see '
                                          '/display/boards for that split). One row = one BoardInstance. Columns: definition/definition_kind '
                                          '(which BoardDefinition or AdapterDefinition it matched), target_board (an adapter\'s chosen target, '
                                          'never overwritten by a re-scan), firmware_sha/last_flash_at (what is on it now).',
                              columns='name,definition,definition_kind,state,host,by_id_path,target_board,firmware_sha,last_flash_at'),
                       _table('fi-programmers', 1, 5, 'How each kind of device is flashed — engine, adapter, the DRY-RUN template', 'ProgrammerKind',
                              description='What this is for: the flashing recipe per device family — see /display/boards "Programmer kinds" '
                                          'for the same table with its full description.',
                              columns='name,engine,adapter_kind,dry_run_template,placement')]),
              _row(4, [_table('fi-plans', 0, 12, 'Plans (DRY-RUN) — the exact command, where it runs, compatibility, what will be stamped', 'InstallPlan',
                              description='What this is for: the DRY-RUN the panel above shows before anything is flashed — the exact argv, '
                                          'never composed live. One row = one InstallPlan. Columns: argv_text (verbatim), engine/engine_how '
                                          '(the tool and how it reaches the device), compat (the wire-contract check\'s verdict), will_stamp '
                                          '(what success will write back to the instance), state (planned | confirmed | ran).',
                              columns='name,variant,instance,target_kind,argv_text,engine,engine_how,compat,will_stamp,state,planned_at')]),
              _row(5, [_table('fi-records', 0, 12, 'Installs — verdict, what was read back, the firmware now on the device, the bridge, frames/s', 'InstallRecord',
                              description='What this is for: what actually happened when a plan ran. One row = one InstallRecord. Columns: '
                                          'verdict/verify (pass/fail and what was read back to confirm it), firmware_sha (now on the device), '
                                          'bridge_state/frames_per_s (the live link once flashed), elapsed_s.',
                              columns='name,variant,instance,target_kind,verdict,verify,firmware_sha,elapsed_s,bridge_state,row_class,row_name,frames_per_s,started_at')]),
              # fs-1 item 4 FALLBACK (DEMONSTRABLES_PLAN.md §9): wiring the live validate->build->run(mode) door into
              # firmware-installer-panel (above) was judged to exceed fs-1b's time box — this described table + a
              # documented command column is what shipped instead. /display/firmware-solutions is the live panel
              # (the three-part canvas with the pin-map drag); this row is a pointer FROM the installer TO it, plus
              # the exact command a person runs themselves (never composed/run by this page).
              _row(6, [_table('fi-firmware-solutions', 0, 12, 'Firmware Solutions — validate -> build -> run(mode), '
                              'by hand (DRY-RUN default: digital-twin, never hardware unless named)', 'FirmwareSolution',
                              description='What this is for: every FirmwareSolution (fs-0/fs-1, /display/firmware-solutions '
                                          'has the live canvas), with the command that runs it. One row = one FirmwareSolution. '
                                          'Columns: validation/validation_why (board resolved, targets bound-or-named, no pin '
                                          'conflicts — the same validate() the command itself gates on), run_command (verbatim '
                                          '`pol firmware run <name> --mode digital-twin` — the digital-twin mode never touches '
                                          'real hardware; `--mode hardware` is a person\'s own, separate choice).',
                              columns='name,title,graph,board_resolved,runtime,validation,validation_why,task_count,run_command',
                              data_path='/api/firmware/solutions/for-installer')]),
          ]),
]

#: the module's one page export (manifest `pages`): /display/boards + /display/firmware-installer
SEED_BOARD_PAGE_DISPLAYS = _BOARDS_PAGES + _CHAIN_PAGES + INSTALLER_PAGES   # ucd-0a: + /display/hardware-chain
