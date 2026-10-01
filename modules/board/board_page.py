"""
@module board.board_page
/display/boards — the board arc as CONFIGURED tables only (no custom component, no raw JSON): every tracked device with
its USB route, adapter and road status; the adapters; the roads; the programmer kinds with their DRY-RUN templates; the
boards and adapters seen plugged in; the cited datasheet facts.
"""
from polariApiServer.module_pages_seed import _page, _row, _table

SEED_BOARD_PAGE_DISPLAYS = [
    _page('boards', 'boards',
          'Boards — every device the board arc tracks (track all, simulate few: only the UNO is simulated), how each is '
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
          ]),
]
