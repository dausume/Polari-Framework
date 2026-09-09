"""
@module vpn

The VPN + federation module (VPN_FEDERATION_PLAN.md, vpn-1, Polari
side). App family `isle-vpn`: Isle Link (WireGuard-based) and Isle
Bridge (OpenVPN-based), ten catalog kinds, Blind / Sees-traffic on
every row.

The authority is the ISLE side (D9): this module is the MIRROR
(rows replaced per device by the isle's push to
/api/islemesh/ingest/vpn) and the INBOX (VpnProposal rows a local
operator applies with `isle vpn apply`), plus the engine that renders
what the isle applies — never a private key, never a free-text hook.

Requires `islemesh` (the acceptor family, the netledger, the catalog
and engine idioms). Imports nothing from any other feature module.
"""

from vpn.vpn_basis import (  # noqa: F401
    VPN_CLASSES, VPN_MIRROR_CLASSES, AppVpnExposure, VpnAccessRule,
    VpnFederationLink, VpnNetwork, VpnPeer, VpnPlacement, VpnProposal,
)
from vpn.custom.vpn_placement import (  # noqa: F401
    SEED_VPN_HARDWARE_APPS, SEED_VPN_PLACEMENTS,
)
from vpn.vpn_catalog import SEED_VPN_CATALOG, vpn_install_plan  # noqa: F401
from vpn.vpn_page import SEED_VPN_PAGE_DISPLAYS  # noqa: F401

#: (class name, class, seeds) — mirror + inbox rows carry no seeds:
#: every row comes from an isle's push or an operator's proposal.
VPN_SEED_PAIRS = [
    # vpn-4: where each kind runs (kvm / openwrt-extension / container) and
    # its role at each level — pure data, seeded.
    ('VpnPlacement', VpnPlacement, SEED_VPN_PLACEMENTS),
    ('VpnNetwork', VpnNetwork, []),
    ('VpnPeer', VpnPeer, []),
    ('VpnAccessRule', VpnAccessRule, []),
    ('VpnFederationLink', VpnFederationLink, []),
    ('AppVpnExposure', AppVpnExposure, []),
    ('VpnProposal', VpnProposal, []),
]
