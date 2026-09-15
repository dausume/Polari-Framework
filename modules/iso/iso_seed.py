"""
@module iso.iso_seed

Seed rows (upserted by name — never insert-by-name). ISO_SEED_PAIRS is what admission applies (manifest `seedPairs`).
The bases are Ubuntu's own Server live ISOs (subiquity): the exact file name and checksum are read from Ubuntu's
SHA256SUMS when a base is fetched, so nothing here is typed that Ubuntu publishes.
"""
from iso.iso_basis import DeviceProbe, IsoBase, IsoBuild

SEED_ISO_BASES = [
    {'name': 'ubuntu-26.04-amd64', 'release': '26.04', 'codename': 'resolute', 'arch': 'amd64', 'url': 'https://releases.ubuntu.com/26.04/', 'default': True,
     'note': 'ISO plan D1: the release the images target. Server live ISO + autoinstall; the desktop task is added by the build when the shape is desktop or detect.'},
    {'name': 'ubuntu-24.04-amd64', 'release': '24.04', 'codename': 'noble', 'arch': 'amd64', 'url': 'https://releases.ubuntu.com/24.04/', 'default': False,
     'note': 'What the home machines run today; kept so a device can be rebuilt on the same release its neighbours use.'},
]

ISO_SEED_PAIRS = [('IsoBase', IsoBase, SEED_ISO_BASES), ('DeviceProbe', DeviceProbe, []), ('IsoBuild', IsoBuild, [])]
