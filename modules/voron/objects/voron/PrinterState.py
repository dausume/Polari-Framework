"""
@module voron.objects.voron.PrinterState

PrinterState — what the printer's guest reports about the running stack.
"""
from objectTreeDecorators import treeObject, treeObjectInit

KLIPPER_STATES = ('unknown', 'ready', 'startup', 'shutdown', 'error')


class PrinterState(treeObject):
    """What it is: the twin of one printer: Klipper's state, whether
    Moonraker answers, where Mainsail is served, which MCUs are connected,
    the temperatures, the current job and its progress — pushed by the
    guest (or an observer polling Moonraker).
    Related concepts: `PrinterDefinition` (`printer`), `PrinterBoard`
    (the keys of `mcu_connected_json` are their `mcu_name`s),
    `HardwareAppState` (the guest's own twin).
    How it is measured: Moonraker's `/printer/info` (klipper_state),
    `/printer/objects/query?mcu&extruder&heater_bed&print_stats&
    virtual_sdcard` (mcus, temps, job, progress) on port 7125; every row
    carries `observed_at`. In `sim` mode the temperatures are whatever the
    Linux host MCU reports (there is no heater) and `is_mock` says so.
    """

    @treeObjectInit
    def __init__(self, name: str = '', printer: str = '', klipper_state: str = 'unknown', moonraker_ok: bool = False,
                 mainsail_url: str = '', mcu_connected_json: str = '{}', temps_json: str = '{}', print_job: str = '',
                 progress_pct: float = 0.0, observed_at: str = '', is_mock: bool = False):
        self.name = name
        self.printer = printer
        self.klipper_state = klipper_state
        self.moonraker_ok = moonraker_ok
        self.mainsail_url = mainsail_url
        self.mcu_connected_json = mcu_connected_json
        self.temps_json = temps_json
        self.print_job = print_job
        self.progress_pct = progress_pct
        self.observed_at = observed_at
        self.is_mock = is_mock
