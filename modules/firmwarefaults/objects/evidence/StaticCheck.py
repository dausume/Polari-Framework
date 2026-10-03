"""
@module firmwarefaults.objects.evidence.StaticCheck

StaticCheck — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StaticCheck(treeObject):
    """What it is: The STATIC RULES row per firmware variant (FIRMWARE_SCENARIO_PLAN.md §4 "static rules for 8-bit", D-sc-6;
    sc-2b): cppcheck (GPL-3.0, a separate-process engine in prf-formal-engines) over the variant's generated project —
    its built-in checks (warning, style, portability, performance) on the avr8 platform plus the `threadsafety` addon. The
    MISRA addon is NOT run: its rule texts need the non-free MISRA C document. Findings are rows (StaticFinding), counted
    by severity here; a finding never fails a build.
    Related concepts: `StaticFinding`, `FirmwareVariant`, `FormalCheck`.
    """

    plain_words = ('A static check reads one firmware variant\'s source code with a rule checker, without running it, and '
                   'lists what it finds; nothing it finds stops a build.')

    @treeObjectInit
    def __init__(self, name: str = '', variant: str = '', build_name: str = '', tool: str = 'cppcheck', tool_version: str = '',
                 engine_where: str = '', checks: str = '', addons: str = '', not_run: str = '', platform: str = 'avr8', files_json: str = '[]',
                 source_sha256: str = '', findings: int = 0, counts_json: str = '{}', errors: int = 0, warnings: int = 0, style: int = 0,
                 portability: int = 0, performance: int = 0, run_info: int = 0, state: str = 'not-run', wall_s: float = 0.0,
                 peak_rss_mb: float = 0.0, repro_json: str = '{}', ran_at: str = '', notes: str = '', manager=None):
        self.name = name
        self.variant = variant
        self.build_name = build_name
        self.tool = tool
        self.tool_version = tool_version
        self.engine_where = engine_where
        self.checks = checks  # the --enable classes
        self.addons = addons  # threadsafety
        self.not_run = not_run  # misra — and why
        self.platform = platform
        self.files_json = files_json
        self.source_sha256 = source_sha256  # sha256 over the project's .c/.h, sorted
        self.findings = findings
        self.counts_json = counts_json  # {severity: n}
        self.errors = errors
        self.warnings = warnings
        self.style = style
        self.portability = portability
        self.performance = performance
        self.run_info = run_info  # information messages about the run itself (missing includes …), not findings
        self.state = state  # not-run | ran | refused: …
        self.wall_s = wall_s
        self.peak_rss_mb = peak_rss_mb
        self.repro_json = repro_json
        self.ran_at = ran_at
        self.notes = notes
