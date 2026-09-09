"""
@module hwmap

Hardware map (hwm-1, Dustin 2026-09-08): "an app for mapping out hardware,
ports, and slots, for devices where we are choosing to enable hardware
apps … the capability to query 'what can be mapped to a potential KVM'."
A scanner runs ON the device (usb, pci + iommu groups, serial by-id, nics,
the kvm/libvirt facts) and pushes a snapshot; Polari keeps the ports and
slots as rows and answers, per port, whether and how it can be handed to a
guest: usb hostdev, pci vfio (needs an IOMMU group of its own), macvtap
NIC, or not at all — with the reason. Hardware apps name what they need;
the map says what the device has.
"""
from hwmap.hwmap_basis import *  # noqa: F401,F403
