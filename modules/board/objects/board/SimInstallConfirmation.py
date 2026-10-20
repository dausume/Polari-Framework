"""
@module board.objects.board.SimInstallConfirmation

SimInstallConfirmation — one class per file (design §7); ins-1 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §12).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SimInstallConfirmation(treeObject):
    """What it is: A PERSON'S TICK that the simulated board does what the firmware says — the step between a Sim install and a Real
    install (ins-1). One row = one tick for one config at one exact program (`hex_sha256`): who ticked, when, from where (the installer
    page, the sim bench, the CLI), which twin session they were looking at, and the ScenarioRun names of the four Purposes as they
    stood at that moment. A Real install of the config is OFFERED only when the four Purposes passed on the twin AND a valid row for the
    build's own hex exists. A new hex VOIDS the row (`state` = voided, `voided_why` names the new hex) — the person looks again.
    Nothing here is derived from the code: it is the person's own record, and "install anyway" is recorded beside it, never instead of it.
    Related concepts: `FirmwareBuild` (the hex), `FirmwareVariant` (the config), `TwinSession` (what was looked at), `ScenarioRun`
    (the four Purposes), `InstallPlan` / `InstallRecord` (the Real install that follows, with `install_mode` and `override_reason`).
    """

    plain_words = ('A sim-install confirmation is you saying "I watched the simulated board run this exact program and it does what the firmware '
                   'says". Only then is the real board offered. A new build asks you to look again.')

    @treeObjectInit
    def __init__(self, name: str = '', config: str = '', hex_sha256: str = '', build: str = '', who: str = '', confirmed_at: str = '',
                 runs_json: str = '[]', purposes_passed: int = 0, purposes_total: int = 0, source: str = 'installer', session: str = '',
                 words: str = '', state: str = 'valid', voided_at: str = '', voided_why: str = '', manager=None):
        self.name = name  # 'simconf-<config>-<n>'
        self.config = config  # the FirmwareVariant (config) confirmed
        self.hex_sha256 = hex_sha256  # the EXACT program looked at; another hex voids this row
        self.build = build  # the FirmwareBuild name, when known
        self.who = who  # the signed-in person (Keycloak preferred_username, else the subject id); '' = no sign-in on the request
        self.confirmed_at = confirmed_at
        self.runs_json = runs_json  # [{purpose, scenario, run, status}] — the four Purposes as they stood at the tick
        self.purposes_passed = purposes_passed
        self.purposes_total = purposes_total
        self.source = source  # installer | sim-bench | cli
        self.session = session  # the TwinSession looked at (sim bench), '' from the installer's own twin
        self.words = words  # what was ticked, verbatim
        self.state = state  # valid | voided
        self.voided_at = voided_at
        self.voided_why = voided_why
