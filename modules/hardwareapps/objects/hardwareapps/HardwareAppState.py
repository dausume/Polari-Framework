"""
@module hardwareapps.objects.hardwareapps.HardwareAppState

HardwareAppState — the twin: what the isle reports about a guest.
"""
from objectTreeDecorators import treeObject, treeObjectInit

VM_STATES = ('undefined', 'defined', 'running', 'shut off', 'paused', 'crashed', 'unknown')


class HardwareAppState(treeObject):
    """What it is: the last reported state of one hardware app on one
    device (name = '<app>@<device>'), pushed by the isle's `isle vm status`
    through the islemesh ingest — never typed here.
    Related concepts: `HardwareAppDefinition` (what it should be),
    `IsleDevice` (where it runs; `hosts_router`/`router_running` are the
    router's own fields of the same idea).
    How it is measured: `virsh domstate`, the guest's DHCP lease/IP from the
    router, uptime and the SSH/guest-agent probe — facts, with `observed_at`.
    """

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', device_name: str = '',
                 vm_state: str = 'unknown', ip: str = '', uptime_s: int = 0,
                 probe_ok: bool = False, observed_at: str = '', is_mock: bool = False,
                 notes: str = ''):
        self.name = name
        self.app = app
        self.device_name = device_name
        self.vm_state = vm_state
        self.ip = ip
        self.uptime_s = uptime_s
        self.probe_ok = probe_ok
        self.observed_at = observed_at
        self.is_mock = is_mock
        self.notes = notes
