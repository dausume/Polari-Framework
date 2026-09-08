"""
@module reticulum.objects.reticulum.ReticulumInterface

Row class ReticulumInterface of the reticulum module — one class per file (design §7), split
from reticulum_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ReticulumInterface(treeObject):
    """One physical/logical link. Declared parameters and measured
    facts kept SEPARATE (fidelity); regulatory domain and rx/tx
    direction are device facts every surface must read."""

    @treeObjectInit
    def __init__(self, name='', bearer='tcp', platform='linux',
                 regulatory_domain='none', direction='both',
                 declared_params_json='{}', measured_facts_json='{}',
                 fidelity='declared', device_link_name='',
                 enabled=False, idle_policy='silent',
                 tx_legal_confirmed=False,
                 tx_legal_basis='', tx_legal_confirmed_by='',
                 tx_legal_confirmed_at='', notes='', manager=None):
        self.name = name
        self.bearer = bearer
        # 'linux' (Ubuntu default target, §5j) | 'openwrt' (the router
        # CASE, isle-core's work) — platform-specific behaviour lives
        # behind this field, never in code assumptions.
        self.platform = platform
        self.regulatory_domain = regulatory_domain
        self.direction = direction
        self.declared_params_json = declared_params_json
        self.measured_facts_json = measured_facts_json
        self.fidelity = fidelity
        # The DeviceLink row backing this interface, when hardware.
        self.device_link_name = device_link_name
        self.enabled = enabled
        # DECIDED row 19: what this interface does when idle. Radios
        # default 'silent' — not attached, guaranteed dark.
        self.idle_policy = idle_policy
        # THE TX LEGALITY GATE (Dustin 2026-08-13: "never transmit
        # anything without confirming it is legal first" — earned the
        # same day: the SH-L1A pair SHIPPED on 873.125 MHz, outside US
        # ISM). The software records the OPERATOR's confirmation with
        # its basis and refuses TX without it; it makes no legal
        # claims itself (§5f framing). RF-domain interfaces only —
        # wired links (regulatory_domain 'none') are not gated.
        self.tx_legal_confirmed = tx_legal_confirmed
        # e.g. '915.125 MHz @ 22 dBm, US 902-928 ISM' — WHAT was
        # confirmed, so a later config change visibly invalidates it.
        self.tx_legal_basis = tx_legal_basis
        self.tx_legal_confirmed_by = tx_legal_confirmed_by
        self.tx_legal_confirmed_at = tx_legal_confirmed_at
        self.notes = notes
