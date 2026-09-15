"""
@module iso.iso_basis

The INDEX of iso rows (design §7): classes live one-per-file under objects/;
this file re-exports them and holds what they share.
"""
from iso.objects.iso.IsoBase import IsoBase  # noqa: F401
from iso.objects.iso.DeviceProbe import DeviceProbe  # noqa: F401
from iso.objects.iso.IsoBuild import IsoBuild  # noqa: F401

ISO_CLASSES = [IsoBase, DeviceProbe, IsoBuild]

ROLES = ('core', 'member', 'hardware', 'access', 'server')
SHAPES = ('detect', 'desktop', 'headless')
POSTURES = ('production', 'dev')
LOOKS = ('plasma-default', 'mac-like', 'microsoft-like', 'ubuntu-like')
