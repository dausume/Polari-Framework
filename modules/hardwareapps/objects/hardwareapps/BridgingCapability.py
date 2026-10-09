"""
@module hardwareapps.objects.hardwareapps.BridgingCapability

BridgingCapability — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit

#: FIRMWARE_EXPORT_PLAN §2b: what the proof verdict means. 'never-run' is the honest seed state — nothing proves a
#: bridge app until its own capture test (UNO_CORE_DEMO_PLAN.md §5c) actually runs.
STATUSES = ('never-run', 'passed', 'failed')


class BridgingCapability(treeObject):
    """What it is: one Hardware Bridge App's (D-ucd-2: `app.realization = bridge`, e.g. the Polari Firmware
    Installer) proven ability to hold a usb-serial port and relay a device's wire classes to Polari WITHOUT
    exposing the local host to the isle — planned in FIRMWARE_EXPORT_PLAN.md §2b, built here (ucd-2) as the row the
    readiness page's `bridge` part reads. One row per app (`app` names it — a plain string today, not a foreign key,
    since the app itself has no row class yet: ucd-4 builds the Polari Firmware Installer).

    Related concepts: `HardwareBridgeDefinition` (grpcbridge — the generated bridge this capability is ABOUT;
    `transports_json`/`bridge_versions_json` name what it generates/accepts), `ScenarioRun` / `CapabilityDefinition`
    (the same proven_by idiom cmod's Purposes use — a capability's status is DERIVED from its latest proof, never
    hand-set), `uno_core_demo.objects.uno_core_demo.DemoReadiness` (the `bridge` part's status IS this row's
    `status`, per UNO_CORE_DEMO_PLAN.md §3/§5c).

    How it is measured or derived: `status` starts 'never-run' (the seed below, for the Polari Firmware Installer)
    and only ucd-4's own capture test (§5c: the app's outbound bytes, captured against the twin, asserted to carry
    none of the host identifiers collected locally on the test machine) may ever set it to 'passed' or 'failed' —
    nothing here simulates or guesses a verdict; a status this row has not earned stays 'never-run', named honestly.
    """

    plain_words = ('A Bridge App\'s proof that it can hold a USB/serial port and relay a device to Polari without '
                   'leaking anything about the host it runs on — unproven (never-run) until its own capture test runs.')

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', transports_json: str = '["usb-serial"]',
                 bridge_versions_json: str = '[]', pkexec_verbs_json: str = '[]',
                 proven_by: str = '', proven_at: str = '', status: str = 'never-run', notes: str = '', manager=None):
        self.name = name
        self.app = app                              # the Hardware Bridge App this capability is about (a plain name — no row class yet)
        self.transports_json = transports_json      # JSON list: which transports this app may hold ('usb-serial' today)
        self.bridge_versions_json = bridge_versions_json   # JSON list: HardwareBridgeDefinition/bridge_name versions this app accepts
        self.pkexec_verbs_json = pkexec_verbs_json  # JSON list: the host-install verbs this app may invoke via pkexec (empty = none yet)
        self.proven_by = proven_by                  # a ScenarioRun / capture-test name — '' until one exists
        self.proven_at = proven_at                  # when proven_by last ran — '' until one exists
        self.status = status                        # never-run | passed | failed — DERIVED from proven_by, never hand-set past the seed
        self.notes = notes
