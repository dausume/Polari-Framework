"""
@module electrodevice.photo_basis

CNT / sol-gel PHOTO devices (Dustin 2026-07-10): (A) a photo-sensor
TUNED to a target wavelength via nanoparticle shape+composition (the
acene fragment ladder — size closes the pi gap; doping shifts it) and
orientation (aligned absorbers couple to polarization); (B) a
thin-film SOLAR STACK from common/community materials, its layers as
rows with structured property records and honest gaps.

@consumers
  - electrodevice.custom.photo_derive (tuning + stack optimization)
  - electrodevice.device_api (knob surface)
  - polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/photo/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
import json as _json

from electrodevice.objects.photo._shared import SEED_PHOTO_ABSORBERS, SEED_SOLAR_LAYERS, SEED_SOLAR_STACKS  # noqa: F401
from electrodevice.objects.photo.PhotoAbsorberDefinition import PhotoAbsorberDefinition  # noqa: F401
from electrodevice.objects.photo.SolarLayerDefinition import SolarLayerDefinition  # noqa: F401
from electrodevice.objects.photo.SolarStackDefinition import SolarStackDefinition  # noqa: F401
