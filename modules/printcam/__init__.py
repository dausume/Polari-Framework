"""
@module printcam

Print camera (D7, Dustin 2026-09-09): a hardware-extension-app that EXTENDS
the voron-printer guest: a USB camera passed through to the guest, a
streamer (ustreamer) inside it, the Moonraker webcam entry so Mainsail
shows it, and Moonraker's timelapse component. Rows here; the extension's
provisioner renders what `isle vm extend voron-printer --with printcam`
applies; the camera's port is the hardware map's answer to the need
`usb role=camera`.
"""
from printcam.printcam_basis import *  # noqa: F401,F403
