"""
@module security.objects.security.AppSecurityRecord

Row class AppSecurityRecord of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class AppSecurityRecord(treeObject):
    """ONE row per app (module id or fixed piece): which automation steps it has been through and with what result — stanza declared/conforms, MAC rendered/loaded/enforced, DAC rendered, surface applied, proxy snippets, channels, content policy, browser policy, hardware trial, the audit verdict of its scenario, steps complete/total and the first blocking step. Refreshed from the live state, never typed."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', kind: str = 'polari-app', scenario: str = '', stanza_declared: bool = False, stanza_hash: str = '', stanza_conforms: str = '', mac_rendered: bool = False, mac_mode: str = 'absent', mac_enforced: bool = False, dac_rendered: bool = False, surface_applied: bool = False, proxy_snippets: str = '0/0', channels_declared: int = 0, content_policy: str = 'none', browser_policy: str = 'n/a', hardware_trial: str = 'n/a', audit_verdict: str = '', steps_complete: int = 0, steps_total: int = 0, blocking: str = '', last_refresh: str = ''):
        self.name = name
        self.app = app
        self.kind = kind
        self.scenario = scenario
        self.stanza_declared = stanza_declared
        self.stanza_hash = stanza_hash
        self.stanza_conforms = stanza_conforms
        self.mac_rendered = mac_rendered
        self.mac_mode = mac_mode
        self.mac_enforced = mac_enforced
        self.dac_rendered = dac_rendered
        self.surface_applied = surface_applied
        self.proxy_snippets = proxy_snippets
        self.channels_declared = channels_declared
        self.content_policy = content_policy
        self.browser_policy = browser_policy
        self.hardware_trial = hardware_trial
        self.audit_verdict = audit_verdict
        self.steps_complete = steps_complete
        self.steps_total = steps_total
        self.blocking = blocking
        self.last_refresh = last_refresh
