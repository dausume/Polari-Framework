"""
@module reticulum.device_catalog_basis

The DEVICE CATALOG (Dustin 2026-08-13): what a KIND of device IS —
who makes it, who REALLY makes it (rebadges are the norm), how open
its firmware and protocol are, what it refuses to talk to, and the
restrictions an operator must know before keying it up. Prompted by
the SH-L1A bring-up, where every one of those facts was invisible
from the USB descriptor and material to legality and interop.

The idiom is the mesh-asset licence gate's: facts are STATED or the
row refuses to vouch — an unstated openness field is not "probably
fine", it is unstated. Every fact carries evidence (links, manual
sections, measurements) in evidence_json, and fidelity says whether
a number was declared by a vendor or measured by us.

One treeObject:

  DeviceModel   a product/kind row. DeviceLink (operator_basis)
                instances point at it via device_model_name — the
                catalog answers "what is this thing", the link row
                answers "which one is plugged in where".

@consumers reticulum.reticulum_api, DeviceLink rows
@see modules/reticulum/operator_basis.py (DeviceLink),
     modules/meshassets (the licence-gated catalog precedent)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/device_catalog/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.objects.device_catalog._shared import DEVICE_CLASS_VALUES, FIRMWARE_OPENNESS_VALUES, INTEROP_VALUES, MODEL_STATUS_VALUES, PROTOCOL_OPENNESS_VALUES, SEED_DEVICE_MODELS, _REFERENCE_NOTE, interop_possible, model_vouches  # noqa: F401
from reticulum.objects.device_catalog.DeviceModel import DeviceModel  # noqa: F401
