"""
@module voron.objects.voron.PrinterBoard

PrinterBoard — one MCU of one printer (main board, toolhead board, or the
Linux-process host MCU).
"""
from objectTreeDecorators import treeObject, treeObjectInit

BOARD_ROLES = ('main', 'toolhead', 'host')
BOARD_MODELS = ('btt-octopus-1.1', 'btt-skr-3', 'btt-ebb36', 'btt-ebb42', 'linux-host')
CONNECTIONS = ('usb', 'canbus', 'linux')


class PrinterBoard(treeObject):
    """What it is: one Klipper MCU of one printer — the main board (steppers,
    bed heater, endstops), a toolhead board on CAN or USB (extruder, hotend,
    probe, fans), or the `linux-host` pseudo-board: Klipper's MCU firmware
    built with the Linux-process target and run inside the guest as
    `/tmp/klipper_host_mcu` (the only board `sim` mode uses).
    Related concepts: `PrinterDefinition` (`printer`), `DeviceLink` /
    `HardwarePort` (the measured USB device the isle passes through —
    `serial_by_id` is that device's /dev/serial/by-id path), `PrinterState`
    (`mcu_connected_json` reports each `mcu_name`).
    How it is measured: `serial_by_id`, `vendor_id`/`product_id` come from
    `pol hwmap scan` on the device (empty until measured — a real-mode USB
    board with an empty serial is a NAMED refusal, never a guessed
    /dev/ttyACM0); `canbus_uuid` from `python3 klipper/scripts/canbus_query.py
    can0` inside the guest; `firmware_flashed` is set by the person who
    flashed it. Each row becomes one `[mcu <mcu_name>]` section (the main
    board must be `mcu`, the primary section Klipper requires).
    """

    @treeObjectInit
    def __init__(self, name: str = '', printer: str = '', role: str = 'main', model: str = 'btt-octopus-1.1',
                 mcu_name: str = 'mcu', connection: str = 'usb', serial_by_id: str = '', vendor_id: str = '',
                 product_id: str = '', canbus_uuid: str = '', firmware_flashed: bool = False, notes: str = ''):
        self.name = name
        self.printer = printer
        self.role = role
        self.model = model
        self.mcu_name = mcu_name
        self.connection = connection
        self.serial_by_id = serial_by_id
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.canbus_uuid = canbus_uuid
        self.firmware_flashed = firmware_flashed
        self.notes = notes
