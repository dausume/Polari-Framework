"""
@module security.objects.security.BrowserPolicy

Row class BrowserPolicy of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BrowserPolicy(treeObject):
    """The CSP / frame / referrer header set for one frontend host, derived from what that frontend loads (its own origin, the API origin, Keycloak when logins are on, fonts); mode observe (report-only) before enforce."""

    @treeObjectInit
    def __init__(self, name: str = '', host: str = '', env: str = '', mode: str = 'derived', csp: str = '', frame: str = 'DENY', referrer: str = 'strict-origin-when-cross-origin', report_to: str = '', violations: int = 0):
        self.name = name
        self.host = host
        self.env = env
        self.mode = mode
        self.csp = csp
        self.frame = frame
        self.referrer = referrer
        self.report_to = report_to
        self.violations = violations
