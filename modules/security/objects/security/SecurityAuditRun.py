"""
@module security.objects.security.SecurityAuditRun

Row class SecurityAuditRun of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SecurityAuditRun(treeObject):
    """One run of os-security/audit.sh --json posted from a machine (pol security os audit --post / pol deploy audit <node> --post): host, scenario, verdict, counts, the controls, and the per-container facts when included. The latest run per scenario is what 'today' means for the views."""

    @treeObjectInit
    def __init__(self, name: str = '', host: str = '', scenario: str = '', ran_at: str = '', verdict: str = '', pass_count: int = 0, fail_count: int = 0, skip_count: int = 0, controls_json: str = '', containers_json: str = '', source: str = ''):
        self.name = name
        self.host = host
        self.scenario = scenario
        self.ran_at = ran_at
        self.verdict = verdict
        self.pass_count = pass_count
        self.fail_count = fail_count
        self.skip_count = skip_count
        self.controls_json = controls_json
        self.containers_json = containers_json
        self.source = source
