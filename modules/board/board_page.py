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
from polariApiServer.module_pages_seed import _page, _row, _table

_BOARDS_PAGES = [
    _page('boards', 'boards',
          'Boards — every device the board arc tracks (track all, simulate few: the UNO in simavr and, since sc-3, the ESP32-C3 in Espressif\'s QEMU fork), how each is '
          'reached from the Polari host over USB (directly or through a known adapter), and the road still to walk for it',
          'BoardDefinition', [
              _row(0, [_table('boards-devices', 0, 12, 'Devices (register §1) — RULE 1: USB from the host, directly or via an adapter', 'BoardDefinition',
                              columns='name,device_class,register_status,soc,isa,usb_route,programmer,adapter_needed,usb_rule,simulated,twin,road_status',
                              column_formats='name:ref:BoardDefinition')]),
              _row(1, [_table('boards-adapters', 0, 12, 'Adapters and programmers (register §1a) — the host side is always USB', 'AdapterDefinition',
                              columns='name,kind,chip,usb_connector,usb_ids_json,targets,engine,hardware_open,firmware_open,origin',
                              column_formats='name:ref:AdapterDefinition')]),
              _row(2, [_table('boards-roads', 0, 6, 'Roads — todo | in-progress | done per device', 'Road',
                              columns='name,board,status,steps_json,concept_node', column_formats='name:ref:Road,board:ref:BoardDefinition'),
                       _table('boards-programmers', 1, 6, 'Programmer kinds — engine, adapter, the DRY-RUN argv', 'ProgrammerKind',
                              columns='name,engine,engine_kind,adapter_kind,dry_run_template,placement', column_formats='name:ref:ProgrammerKind')]),
              _row(3, [_table('boards-instances', 0, 7, 'Seen plugged in (pol board detect)', 'BoardInstance',
                              columns='name,definition,definition_kind,state,host,usb_id,by_id_path,possible_targets_json,last_seen_at'),
                       _table('boards-facts', 1, 5, 'Datasheet facts (cited)', 'DatasheetFact',
                              columns='board,fact_key,value,unit,document,page_table,url')]),
              # brd-wire (grpc-j4): which Polari row IS which hardware interface — the chain of one instance is
              # GET /api/board/instances/<instance>/interface
              _row(4, [_table('boards-bindings', 0, 12, 'Hardware-interface bindings — which row is which interface: bridge, instance index '
                              '(ceil(log2 n) bits on the wire), port, the wire contract hash v2, frames applied / refused',
                              'HardwareInterfaceBinding',
                              columns='name,bridge_name,object_class,object_name,board_instance,board_definition,interface_kind,interface_name,'
                                      'port,instance_index,wire_version,contract_hash_v2,frames_seen,refused_frames,last_seen_at',
                              column_formats='board_definition:ref:BoardDefinition')]),
              # brd-bo: THE BOARD OBJECT (PCB_FROM_SCRATCH_PLAN §2b) — the SoCs, the ONE pin assignment every view renders from,
              # the runtime profiles (supported or refused, with why), the views by sha and the conflicts (never auto-resolved)
              _row(5, [_table('boards-socs', 0, 12, 'SoCs — package, ISA, clock, where each fact came from (the board object\'s SoC layer)', 'SocDefinition',
                              columns='name,title,package,isa,cpu_clock_hz,pin_count,vendor_target,zephyr_soc,source,undetermined')]),
              _row(6, [_table('boards-pins', 0, 12, 'Pins — named ONCE: the canonical name every view uses (KiCad, Zephyr, ESP-IDF, bare C) ↔ SoC pin ↔ net ↔ '
                              'connector pin, the function / peripheral / signal, the C symbol, where it came from', 'BoardPin',
                              columns='board,canonical,soc_pin,net,connector_pin,function,peripheral,signal,firmware_symbol,alias,origin,undetermined',
                              column_formats='board:ref:BoardDefinition')]),
              _row(7, [_table('boards-runtime', 0, 12, 'Runtime profiles — per firmware_runtime: supported (console, tick, twin) or REFUSED with the reason',
                              'RuntimeProfile', columns='board,runtime,supported,refusal,console_uart,clock_hz,tick_hz,heap_bytes,twin,origin',
                              column_formats='board:ref:BoardDefinition')]),
              _row(8, [_table('boards-views', 0, 7, 'Views — rendered out / ingested in, each by sha256 with the board sha at that moment (refusals too)',
                              'BoardView', columns='board,kind,direction,sha256,board_sha,refused,refusal,conflicts,fields_carried,at'),
                       _table('boards-conflicts', 1, 5, 'Conflicts — a view disagreed with the rows; shown, never auto-resolved', 'BoardConflict',
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
          'and see each one\'s effect: detect → the builds that fit → DRY-RUN → confirm → install → the rows arriving',
          'FirmwareVariant', [
              _row(0, [_panel('fi-flow', 0, 12, 'Install a variant — pick, build, read the command, confirm, watch it run, try another')], min_height=520),
              _row(1, [_table('fi-variants', 0, 12, 'Variants — each one a different thing to test on the UNO (add your own row here)', 'FirmwareVariant',
                              columns='name,title,app,classes_json,features_json,knobs_json,what_to_watch,origin',
                              column_formats='name:ref:FirmwareVariant')]),
              _row(2, [_table('fi-builds', 0, 12, 'Builds — sizes measured (avr-size), the .hex sha256, the header sha + wire order the compat check uses',
                              'FirmwareBuild', columns='name,variant,state,size_text,size_data,size_bss,artifact_sha256,header_sha256,tag_order_json,flashed_to,built_at',
                              column_formats='name:ref:FirmwareBuild')]),
              _row(3, [_table('fi-devices', 0, 7, 'Seen plugged in (pol board detect) — boards, and adapters waiting for a target', 'BoardInstance',
                              columns='name,definition,definition_kind,state,host,by_id_path,target_board,firmware_sha,last_flash_at'),
                       _table('fi-programmers', 1, 5, 'How each kind of device is flashed — engine, adapter, the DRY-RUN template', 'ProgrammerKind',
                              columns='name,engine,adapter_kind,dry_run_template,placement')]),
              _row(4, [_table('fi-plans', 0, 12, 'Plans (DRY-RUN) — the exact command, where it runs, compatibility, what will be stamped', 'InstallPlan',
                              columns='name,variant,instance,target_kind,argv_text,engine,engine_how,compat,will_stamp,state,planned_at')]),
              _row(5, [_table('fi-records', 0, 12, 'Installs — verdict, what was read back, the firmware now on the device, the bridge, frames/s', 'InstallRecord',
                              columns='name,variant,instance,target_kind,verdict,verify,firmware_sha,elapsed_s,bridge_state,row_class,row_name,frames_per_s,started_at')]),
          ]),
]

#: the module's one page export (manifest `pages`): /display/boards + /display/firmware-installer
SEED_BOARD_PAGE_DISPLAYS = _BOARDS_PAGES + INSTALLER_PAGES
