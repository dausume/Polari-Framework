"""voron_selftest — the printer rows, the printer.cfg renderer (sim + real), the provisioner's pin gate, the store row's plan."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from voron.voron_basis import (PrinterDefinition, PrinterBoard, PrinterState, SEED_PRINTERS, SEED_PRINTER_BOARDS,
                                   SEED_VORON_HARDWARE_APPS, SEED_VORON_CATALOG, VORON_SEED_PAIRS, VORON_CLASSES)
    from voron.custom.printer_cfg import render_printer_cfg
    from voron.custom import provision
    from voron.custom.provision import render_provision
    from islemesh.islemesh_catalog import install_plan
    check('three row classes', VORON_CLASSES == [PrinterDefinition, PrinterBoard, PrinterState] and len(VORON_SEED_PAIRS) == 3)
    printer = PrinterDefinition(**SEED_PRINTERS[0])
    boards = [PrinterBoard(**b) for b in SEED_PRINTER_BOARDS]
    state = PrinterState(name='s', printer=printer.name)
    check('seeds construct (sim printer, 3 boards, a state)', printer.mode == 'sim' and len(boards) == 3 and state.klipper_state == 'unknown')

    cfg, ref = render_printer_cfg(printer, boards)
    check('sim printer.cfg renders: kinematics none + the linux host mcu, no stepper sections',
          not ref and 'kinematics: none' in cfg and '[mcu]\nserial: /tmp/klipper_host_mcu' in cfg and '[stepper' not in cfg
          and 'SIM MODE' in cfg and '[include macros-voron-standard.cfg]' in cfg, str(ref))

    real = PrinterDefinition(**dict(SEED_PRINTERS[0], mode='real'))
    cfg, ref = render_printer_cfg(real, boards)
    check('real mode with an unmeasured usb main board refuses by name (pol hwmap scan) and the unmeasured CAN toolhead too',
          not cfg and any('serial_by_id' in r and 'pol hwmap scan' in r for r in ref) and any('canbus_uuid' in r for r in ref), str(ref))
    measured = [PrinterBoard(**dict(b, serial_by_id='/dev/serial/by-id/usb-Klipper_stm32f446xx_2A0031000A50-if00' if b['connection'] == 'usb' else b['serial_by_id'],
                                    canbus_uuid='0e8a9f1c2b3d' if b['connection'] == 'canbus' else '')) for b in SEED_PRINTER_BOARDS]
    cfg, ref = render_printer_cfg(real, measured)
    check('real 2.4 with measured serial renders [mcu] serial + [mcu EBBCan] canbus_uuid + quad_gantry_level, host board omitted',
          not ref and '[mcu]\nserial: /dev/serial/by-id/usb-Klipper_stm32f446xx_2A0031000A50-if00' in cfg and '[mcu EBBCan]\ncanbus_uuid: 0e8a9f1c2b3d' in cfg
          and '[quad_gantry_level]' in cfg and '[z_tilt]' not in cfg and '[stepper_z3]' in cfg and 'step_pin: EBBCan:PD0' in cfg
          and 'enable_pin: !EBBCan:PD2' in cfg and '[mcu host]' not in cfg and 'MUST be checked' in cfg, str(ref))
    trident = PrinterDefinition(**dict(SEED_PRINTERS[0], name='trident', mode='real', model='voron-trident', bed_z_mm=250))
    cfg, ref = render_printer_cfg(trident, measured)
    check('real trident renders [z_tilt] (three Z steppers), no quad_gantry_level',
          not ref and '[z_tilt]' in cfg and '[quad_gantry_level]' not in cfg and '[stepper_z2]' in cfg and '[stepper_z3]' not in cfg, str(ref))
    _, ref = render_printer_cfg(real, [b for b in measured if b.role != 'main'])
    check('real mode with no main board refuses by name', ref and any("role 'main'" in r for r in ref), str(ref))
    _, ref = render_printer_cfg(PrinterDefinition(**dict(SEED_PRINTERS[0], model='prusa-mk4', bed_y_mm=0)), boards)
    check('unknown model + bed dim <= 0 refuse by name', len(ref) == 2 and 'unknown model' in ref[0] and 'bed dimensions' in ref[1], str(ref))

    guest = dict(SEED_VORON_HARDWARE_APPS[0], printer=printer, boards=boards)
    check('all three upstream pins are filled from PRINTER_STACK_GATE.md (2026-09-08)', provision._pins_missing() == [])
    script, ref = render_provision(guest)
    check('pinned provision renders without allow_unpinned', bool(script) and not ref, str(ref))
    script, ref = render_provision(dict(guest, allow_unpinned=True))
    check('provision renders with allow_unpinned (klipper.service, moonraker.conf, mainsail, sim host-MCU build, macros)',
          not ref and all(k in script for k in ('klipper.service', 'moonraker.conf', 'mainsail', 'klipper-mcu.service', 'CONFIG_MACH_LINUX=y',
                                                 'macros-voron-standard.cfg', 'PRINT_START', 'QUAD_GANTRY_LEVEL', 'kinematics: none'))
          and 'update_manager' in script and '#!/bin/sh' == script.split('\n')[0], str(ref))
    script, ref = render_provision(dict(guest, printer=real, boards=measured, allow_unpinned=True))
    check('real-mode provision skips the host-MCU build', not ref and 'klipper-mcu.service' not in script and 'real mode: no host-MCU build' in script, str(ref))
    _, ref = render_provision(dict(guest, printer=real, allow_unpinned=True))
    check("real-mode provision carries printer.cfg's refusals", ref and ref[0].startswith('printer.cfg:'), str(ref))
    _, ref = render_provision(dict(guest, guest_kind='openwrt', allow_unpinned=True))
    check('a non-debian guest is refused', ref and 'debian' in ref[0], str(ref))

    plan = install_plan(SEED_VORON_CATALOG[0])
    check('store plan = isle vm define/start, hardware tier', plan['ok'] and plan['requires_tier'] == 'hardware' and plan['steps'][0].startswith('isle vm define voron-printer'))
    check('the guest row names its provisioner (dotted path) and requires the hardware tier',
          SEED_VORON_HARDWARE_APPS[0]['provisioner'] == 'voron.custom.provision:render_provision' and SEED_VORON_HARDWARE_APPS[0]['requires_tier'] == 'hardware')
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
