"""
@module reticulum.operator_basis

The operator + device surface (plan §5g item 1 and §5i/ret-2b).

  OperatorLicense  the operator's OWN ASSERTION that they hold a
                   licence — recorded, tied to a KC user, expiry
                   tracked and surfaced. THE ASSERTION IS THE ONLY
                   CHECK: nothing validates against an external
                   service, ever — a radio gated by an unreachable
                   server defeats an emergency tool. The software
                   holds the record, shows it, and says when it has
                   lapsed; it states NO legal conclusions.
  DeviceLink       an attached device as a row: bus ids, what we
                   think it IS, which interface it backs, which
                   VM/container owns it — measured facts separate
                   from declared. Detection degrades HONESTLY: an
                   unknown USB id is reported unknown with its ids
                   shown, never guessed into a capability.

@consumers reticulum.reticulum_api
@see modules/reticulum/reticulum_basis.py (INTERFACE_DIRECTION_VALUES —
     rx/tx is a device FACT), plan §5l (passthrough is a gated SHELL
     capability; the helper holds the privilege, never the shell)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/operator/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import datetime
from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.objects.operator._shared import DEVICE_KIND_VALUES, LICENSE_STATE_VALUES, WIFI_ASSIGNMENT_VALUES, describe_device, license_state, license_warning, offers_transmit, wifi_use_allowed  # noqa: F401
from reticulum.objects.operator.OperatorLicense import OperatorLicense  # noqa: F401
from reticulum.objects.operator.DeviceLink import DeviceLink  # noqa: F401
