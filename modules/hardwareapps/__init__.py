"""
@module hardwareapps

Hardware apps as rows (hw-app-1, Dustin 2026-09-08): a hardware app is a
KVM guest the isle defines and starts (the router is one, woven into the
isle and left as is); a hardware-extension-app pushes functionality INTO
a hardware app it extends (reticulum on the relay). This LIBRARY module
holds the definition/state rows and the pure renderers (libvirt domain
XML from the router's own template, the OpenWrt UCI profiles); the isle
side (`isle vm`) applies what it renders. Guest modules: isle_relay,
isle_guestnet.
"""
from hardwareapps.hardwareapps_basis import (  # noqa: F401
    HardwareAppDefinition, HardwareAppState, HARDWAREAPPS_SEED_PAIRS, HARDWAREAPPS_CLASSES,
)
