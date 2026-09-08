"""
@module isle_guestnet

isle-guestnet (hw-app-2, Dustin 2026-09-08): a hardware app — an OpenWrt
guest from the isle's router image serving a GUEST-ONLY WiFi/VLAN:
isolated from the isle (forward=REJECT), client isolation on, internet
through the WAN zone only, and an explicit allow-list of isle hosts a
guest may reach — every exposure a row. Rows here; rendered by
hardwareapps; applied by `isle vm`.
"""
from isle_guestnet.isle_guestnet_basis import *  # noqa: F401,F403
