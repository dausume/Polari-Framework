"""
@module xr.xr_settings_basis

XR settings rows (xr-1, WEBXR_PLAN.md §xr-1): the anchor objects of the
four-level mode/framing cascade plus the per-mode interface variants.

  - XrGlobalSettings   — singleton row, the GLOBAL cascade level.
  - XrTypeDefault      — one row per SimSpace CATEGORY, the TYPE level.
  - XrInterfaceVariant — per-(subject, mode) interface configuration.
                         Settings decide what is OFFERED; variants are
                         DATA and survive every settings flip. Deleting
                         one is a deliberate act on the row itself.

The multiscale and individual cascade levels live as `xr_mode` /
`xr_framing` fields on MultiScaleSimulationDefinition and
SimSpaceDefinition respectively. Resolution logic (first explicitly-set
walking individual→multiscale→type→global, with provenance) lives in
xr.custom.xr_resolution — these files stay pure data.

@consumers
  - polariServer (defClassList + seed_pairs wiring)
  - xr.custom.xr_resolution (reads the rows)
  - xr.xr_api (the /api/xr/resolve surface)
  - xr.xr_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/xr_settings/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from xr.objects.xr_settings._shared import SEED_XR_GLOBAL_SETTINGS, SEED_XR_TYPE_DEFAULTS, XR_FRAMING_VALUES, XR_GLOBAL_SETTINGS_NAME, XR_MODE_VALUES, XR_VARIANT_MODES, variant_name  # noqa: F401
from xr.objects.xr_settings.XrGlobalSettings import XrGlobalSettings  # noqa: F401
from xr.objects.xr_settings.XrTypeDefault import XrTypeDefault  # noqa: F401
from xr.objects.xr_settings.XrInterfaceVariant import XrInterfaceVariant  # noqa: F401


def xr_global_settings_row(manager) -> XrGlobalSettings:
    """The singleton global-settings row, created on first ask
    (mirrors simulationLocks.lease.lease_row)."""
    tables = getattr(manager, 'objectTables', None) or {}
    for row in (tables.get('XrGlobalSettings') or {}).values():
        if getattr(row, 'name', '') == XR_GLOBAL_SETTINGS_NAME:
            return row
    return XrGlobalSettings(manager=manager)
