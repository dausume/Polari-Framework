"""@module voron.voron_page — /display/voron (structured panel + tables only, no raw JSON)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_VORON_PAGE_DISPLAYS = [
    _page('voron', 'voron',
          'Voron 3D printer as a hardware app: Klipper + Moonraker + Mainsail in a Debian KVM guest with the printer boards passed '
          'through (mode real) or Klipper\'s Linux host MCU with no printer (mode sim — the stack runs, no motion physics). Rows '
          'define, printer.cfg and the provisioner are rendered from them, the isle applies (isle vm).',
          'PrinterDefinition',
          [_row(0, [_sapi('voron-summary', 0, 12, 'Printers + guest readiness', '/api/voron/summary', pick='printers')]),
           _row(1, [_table('voron-printers', 0, 12, 'Printers', 'PrinterDefinition',
                           columns='name,model,mode,bed_x_mm,bed_y_mm,bed_z_mm,toolhead,extruder,probe,hardware_app,max_velocity,max_accel')]),
           _row(2, [_table('voron-boards', 0, 7, 'Boards (MCUs)', 'PrinterBoard',
                           columns='name,printer,role,model,mcu_name,connection,serial_by_id,canbus_uuid,firmware_flashed'),
                    _table('voron-state', 1, 5, 'Reported by the guest', 'PrinterState',
                           columns='printer,klipper_state,moonraker_ok,mainsail_url,print_job,progress_pct,observed_at,is_mock')])]),
]
