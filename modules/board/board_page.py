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
                                  'The UNO pin map, drawn — the four headers, every pin named, coloured by role (PWM, ADC, UART, I2C/SPI, power)',
                                  '/api/board/arduino-uno-r3/pinmap.svg',
                                  description='What this is for: THE PIN ASSIGNMENT drawn straight from brd-bo\'s own rows (board.custom.'
                                              'pinmap_svg) — not a screenshot, not hand-drawn: `pol board assign <board> <role> <pin>` moves a '
                                              'net to a different pin and this drawing changes with it, the same rows every other view (KiCad, '
                                              'Zephyr, bare C) renders from. Hover a pin for its SoC pin, net and C firmware symbol.')], min_height=300),
              _row(1, [_table('boards-usable', 0, 12,
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
              _row(2, [_table('boards-tracked', 0, 12,
                              'Tracked for later — roads, nothing runnable yet', 'BoardDefinition',
                              description='What this is for: every other tracked device, with what is MISSING to become usable (readiness_why '
                                          'names it) and the Road\'s own status for context. One row = one BoardDefinition with readiness='
                                          'partial or tracked. Columns: readiness (partial has at least one of twin/template/solution; tracked '
                                          'has none — a register row only), readiness_why (what is missing), road_status (todo | in-progress | '
                                          'done — the PLAN; it does not by itself change readiness, only a real twin/template/solution does).',
                              columns='name,readiness,readiness_why,road_status,register_status,device_class,soc,isa,usb_route,adapter_needed,usb_rule',
                              data_path='/api/board/boards/readiness', filter_field='readiness', filter_value='partial,tracked')]),
              _row(3, [_table('boards-adapters', 0, 12, 'Adapters and programmers (register §1a) — the host side is always USB', 'AdapterDefinition',
                              description='What this is for: the USB adapters that close the RULE-1 gap for boards that are not natively USB. '
                                          'One row = one AdapterDefinition. Columns: kind/chip (the adapter hardware), usb_connector/usb_ids_json '
                                          '(how the host sees it), targets (which boards it can reach), engine (the flashing tool), '
                                          'hardware_open/firmware_open (licence openness), origin.',
                              columns='name,kind,chip,usb_connector,usb_ids_json,targets,engine,hardware_open,firmware_open,origin',
                              column_formats='name:ref:AdapterDefinition')]),
              _row(4, [_table('boards-roads', 0, 6, 'Roads — todo | in-progress | done per device', 'Road',
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
              _row(5, [_table('boards-instances', 0, 7, 'Seen plugged in (pol board detect)', 'BoardInstance',
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
              _row(6, [_table('boards-bindings', 0, 12, 'Hardware-interface bindings — which row is which interface: bridge, instance index '
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
              _row(7, [_table('boards-socs', 0, 12, 'SoCs — package, ISA, clock, where each fact came from (the board object\'s SoC layer)', 'SocDefinition',
                              description='What this is for: THE BOARD OBJECT\'s SoC identity layer — one row per chip a board is built '
                                          'around. One row = one SocDefinition. Columns: package/isa/cpu_clock_hz/pin_count (the chip itself), '
                                          'vendor_target/zephyr_soc (build-system identifiers), source (where the facts came from), '
                                          'undetermined (named gaps, never guessed).',
                              columns='name,title,package,isa,cpu_clock_hz,pin_count,vendor_target,zephyr_soc,source,undetermined')]),
              _row(8, [_table('boards-pins', 0, 12, 'Pins — named ONCE: the canonical name every view uses (KiCad, Zephyr, ESP-IDF, bare C) ↔ SoC pin ↔ net ↔ '
                              'connector pin, the function / peripheral / signal, the C symbol, where it came from', 'BoardPin',
                              description='What this is for: the ONE pin assignment every view (KiCad, Zephyr, ESP-IDF, bare C) renders from — '
                                          'change a row here and every view changes with it (`pol board assign <board> <role> <pin>`). One row '
                                          '= one named pin. Columns: canonical (the name every view uses) ↔ soc_pin/net/connector_pin (the '
                                          'physical identity), function/peripheral/signal (what it does), firmware_symbol (the C name), origin, '
                                          'undetermined.',
                              columns='board,canonical,soc_pin,net,connector_pin,function,peripheral,signal,firmware_symbol,alias,origin,undetermined',
                              column_formats='board:ref:BoardDefinition')]),
              _row(9, [_table('boards-runtime', 0, 12, 'Runtime profiles — per firmware_runtime: supported (console, tick, twin) or REFUSED with the reason',
                              'RuntimeProfile',
                              description='What this is for: which firmware runtimes (bare-c | freertos | esp-idf | zephyr) a board actually '
                                          'supports, and why the others are refused rather than silently unavailable. One row = one board x '
                                          'runtime pair. Columns: supported (bool), refusal (the reason when not), console_uart/clock_hz/'
                                          'tick_hz/heap_bytes (what that runtime gets), twin (its simulator), origin.',
                              columns='board,runtime,supported,refusal,console_uart,clock_hz,tick_hz,heap_bytes,twin,origin',
                              column_formats='board:ref:BoardDefinition')]),
              _row(10, [_table('boards-views', 0, 7, 'Views — rendered out / ingested in, each by sha256 with the board sha at that moment (refusals too)',
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
          ]),
]

#: the module's one page export (manifest `pages`): /display/boards + /display/firmware-installer
SEED_BOARD_PAGE_DISPLAYS = _BOARDS_PAGES + INSTALLER_PAGES
