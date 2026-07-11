"""
@module xr.xr_settings

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
xr.xr_resolution — these files stay pure data.

@consumers
  - polariServer (defClassList + seed_pairs wiring)
  - xr.xr_resolution (reads the rows)
  - xr.xr_api (the /api/xr/resolve surface)
  - xr.selftest_xr
"""

from objectTreeDecorators import treeObject, treeObjectInit

# Cascade values. 'unset' means "inherit upward"; the builtin fallback
# when the WHOLE ladder is unset is mode='none' (XR is opt-in at some
# level, never ambient) and framing='exhibit' (museum mode is the
# comfort-safe default entry).
XR_MODE_VALUES = ('unset', 'none', 'vr', 'ar', 'both')
XR_FRAMING_VALUES = ('unset', 'inside', 'exhibit')
XR_VARIANT_MODES = ('flat', 'vr', 'ar')

XR_GLOBAL_SETTINGS_NAME = 'xr-global-settings'


class XrGlobalSettings(treeObject):
    """Singleton row — the global level of the XR cascade."""

    @treeObjectInit
    def __init__(
        self,
        name: str = XR_GLOBAL_SETTINGS_NAME,
        # 'unset' | 'none' | 'vr' | 'ar' | 'both'
        xr_mode: str = 'unset',
        # 'unset' | 'inside' | 'exhibit'
        xr_framing: str = 'unset',
        manager=None,
    ):
        self.name = name
        self.xr_mode = xr_mode
        self.xr_framing = xr_framing


class XrTypeDefault(treeObject):
    """Type-level cascade row, keyed by SimSpace category.

    Categories are the Q1b vocabulary: an explicit `category` field on
    SimSpaceDefinition, defaulting to the definition's owning module
    when unset (see xr_resolution.effective_category). Seed rows are
    suggestions made durable — editable like any row.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The SimSpace category this default applies to.
        category: str = '',
        xr_mode: str = 'unset',
        xr_framing: str = 'unset',
        description: str = '',
        manager=None,
    ):
        self.name = name
        self.category = category
        self.xr_mode = xr_mode
        self.xr_framing = xr_framing
        self.description = description


class XrInterfaceVariant(treeObject):
    """Per-mode interface configuration for one subject.

    A space's interface can be configured DIFFERENTLY per presentation
    (flat / vr / ar): panel placements, control layout, entry scale,
    viewpoint bookmarks — all inside config_json. The cascade only
    decides which variants are OFFERED right now; flipping any setting
    (even global 'none') leaves every variant row intact and dormant.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # 'sim-space' | 'multiscale' — what subject_name refers to.
        subject_kind: str = 'sim-space',
        subject_name: str = '',
        # 'flat' | 'vr' | 'ar'
        mode: str = 'flat',
        # Opaque per-mode interface configuration blob.
        config_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_kind = subject_kind
        self.subject_name = subject_name
        self.mode = mode
        self.config_json = config_json
        self.notes = notes


def variant_name(subject_kind: str, subject_name: str, mode: str) -> str:
    """Canonical identity for a variant row (idempotent seeding/lookup)."""
    return f'xr-variant:{subject_kind}:{subject_name}:{mode}'


def xr_global_settings_row(manager) -> XrGlobalSettings:
    """The singleton global-settings row, created on first ask
    (mirrors simulationLocks.lease.lease_row)."""
    tables = getattr(manager, 'objectTables', None) or {}
    for row in (tables.get('XrGlobalSettings') or {}).values():
        if getattr(row, 'name', '') == XR_GLOBAL_SETTINGS_NAME:
            return row
    return XrGlobalSettings(manager=manager)


# One-row idempotent seed for the singleton (skipped by name when the
# row already exists — the boot seed flow in polariServer).
SEED_XR_GLOBAL_SETTINGS = [
    {
        'name': XR_GLOBAL_SETTINGS_NAME,
        'xr_mode': 'unset',
        'xr_framing': 'unset',
    },
]

# Q9 (Dustin confirmed 2026-07-12): room-like categories seed 'inside',
# object-like categories seed 'exhibit'; hydroponics layouts are AR
# spaces, abstract simulation worlds are VR spaces. Editable rows.
SEED_XR_TYPE_DEFAULTS = [
    {
        'name': 'xr-type-hydroponics-layout',
        'category': 'hydroponics-layout',
        'xr_mode': 'ar',
        'xr_framing': 'inside',
        'description': 'Room-layout planning spaces present in AR, '
                       'entered at person scale.',
    },
    {
        'name': 'xr-type-msim-world',
        'category': 'msim-world',
        'xr_mode': 'vr',
        'xr_framing': 'exhibit',
        'description': 'Abstract multi-scale simulation worlds present '
                       'in VR as orbitable exhibits.',
    },
    {
        'name': 'xr-type-wind-volume',
        'category': 'wind-volume',
        'xr_mode': 'vr',
        'xr_framing': 'inside',
        'description': 'Volumetric field spaces are rooms — entered at '
                       'person scale in VR.',
    },
]
