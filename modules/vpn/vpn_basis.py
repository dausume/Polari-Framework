"""
@module vpn.vpn_basis

Object model for the VPN + federation arc (vpn-1, Polari side).

Authority split (VPN_FEDERATION_PLAN §7.3, D9): the isle-side
`isle-vpn` app is the control plane. These rows are its SHADOW (fed by
the isle's push to /api/islemesh/ingest/vpn — replace-per-device, the
islemesh acceptor rule) and its INBOX (VpnProposal rows a local
operator applies with `isle vpn apply`). Nothing reached remotely or
through a tunnel can alter a VPN; nothing here renders a private key.

Every row carries `provider` (link|bridge), `kind` (the guide's ten
ids) and the derived Blind / Sees-traffic `label`, plus `is_mock` (the
islemesh mock discipline: real pushes never set it).

@consumers
  - vpn.vpn_api (ingest + read + proposals)
  - polariServer defClassList (tables + CRUDE)
  - vpn.vpn_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/vpn/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from vpn.objects.vpn._shared import VPN_MIRROR_CLASSES  # noqa: F401
from vpn.objects.vpn.VpnNetwork import VpnNetwork  # noqa: F401
from vpn.objects.vpn.VpnPeer import VpnPeer  # noqa: F401
from vpn.objects.vpn.VpnAccessRule import VpnAccessRule  # noqa: F401
from vpn.objects.vpn.VpnFederationLink import VpnFederationLink  # noqa: F401
from vpn.objects.vpn.AppVpnExposure import AppVpnExposure  # noqa: F401
from vpn.objects.vpn.VpnProposal import VpnProposal  # noqa: F401
from vpn.objects.vpn.VpnPlacement import VpnPlacement  # noqa: F401


VPN_CLASSES = [VpnPlacement, VpnNetwork, VpnPeer, VpnAccessRule, VpnFederationLink,
               AppVpnExposure, VpnProposal]
