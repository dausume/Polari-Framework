"""
@module xr.objects.xr_settings.XrGlobalSettings

Row class XrGlobalSettings of the xr module — one class per file (design §7), split
from xr_settings_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from xr.objects.xr_settings._shared import XR_GLOBAL_SETTINGS_NAME

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
