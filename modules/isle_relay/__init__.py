"""
@module isle_relay

isle-relay (hw-app-2/3, Dustin 2026-09-08): a hardware app — a SECOND
OpenWrt guest from the isle's own router image that EXTENDS THE ISLE: a
dedicated relay segment (its own WiFi/NIC, VLAN, DHCP) that forwards into
the isle zone, so an isle can grow past one router, and the body the
Reticulum extension app (hardware-extension-app) runs inside for
WiFi-over-Reticulum between households. Rows here; the guest is rendered
by hardwareapps and applied by `isle vm`.
"""
from isle_relay.isle_relay_basis import *  # noqa: F401,F403
