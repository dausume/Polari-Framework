"""
@module voron

voron: the Voron 3D printer as a hardware app — Klipper + Moonraker +
Mainsail in a Debian KVM guest with the printer's control boards passed
through over USB/CAN (mode `real`), or Klipper's Linux-process host MCU
with NO printer (mode `sim`: the whole software stack, macros and G-code
streaming run; motion physics is not simulated). Rows here; the guest is
rendered by hardwareapps (domain XML) and this module (printer.cfg + the
provisioner) and applied by `isle vm`.
"""
from voron.voron_basis import *  # noqa: F401,F403
