"""
@module voron.objects.voron.PrinterDefinition

PrinterDefinition — one Voron-class CoreXY printer as data.
"""
from objectTreeDecorators import treeObject, treeObjectInit

MODELS = ('voron-2.4', 'voron-trident', 'voron-0', 'equivalent-corexy')
MODES = ('real', 'sim')
PROBES = ('tap', 'klicky', 'none')


class PrinterDefinition(treeObject):
    """What it is: one Voron 2.4 / Trident / 0 (or an equivalent CoreXY) 3D
    printer: its model, bed envelope, toolhead/extruder/probe choice and
    motion limits — everything Klipper's printer.cfg is rendered FROM. Two
    modes: `real` (the printer's control boards are passed through into the
    guest over USB/CAN) and `sim` (NO printer: Klipper's Linux-process host
    MCU runs inside the guest, so the whole software stack — Klipper,
    Moonraker, Mainsail, the macros, G-code streaming — runs with no
    hardware; motion physics is NOT simulated, nothing moves or heats).
    Related concepts: `PrinterBoard` (the MCUs, `printer` names this row),
    `PrinterState` (the twin), `HardwareAppDefinition` (`hardware_app` names
    the Debian KVM guest the stack runs in), `DeviceLink` / `HardwarePort`
    (the measured USB boards elsewhere; here they are named by
    `serial_by_id`).
    How it is realised: `voron.custom.printer_cfg.render_printer_cfg` turns
    this row + its boards into printer.cfg (Voron reference pin mapping,
    leveling section per model, sim-mode `kinematics: none`);
    `voron.custom.provision.render_provision` turns the guest row + this
    row into the guest's provisioner. Both refuse by name instead of
    guessing (unmeasured serial, unknown model, missing main board).
    """

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', model: str = 'voron-2.4', kinematics: str = 'corexy',
                 bed_x_mm: int = 350, bed_y_mm: int = 350, bed_z_mm: int = 340, mode: str = 'sim',
                 hardware_app: str = 'voron-printer', toolhead: str = 'stealthburner', extruder: str = 'clockwork2',
                 probe: str = 'tap', max_velocity: int = 300, max_accel: int = 3000,
                 macros_profile: str = 'voron-standard', is_prior: bool = True, notes: str = ''):
        self.name = name
        self.title = title
        self.model = model
        self.kinematics = kinematics
        self.bed_x_mm = bed_x_mm
        self.bed_y_mm = bed_y_mm
        self.bed_z_mm = bed_z_mm
        self.mode = mode
        self.hardware_app = hardware_app
        self.toolhead = toolhead
        self.extruder = extruder
        self.probe = probe
        self.max_velocity = max_velocity
        self.max_accel = max_accel
        self.macros_profile = macros_profile
        self.is_prior = is_prior
        self.notes = notes
