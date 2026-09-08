"""
@module xr.objects.xr_settings.XrInterfaceVariant

Row class XrInterfaceVariant of the xr module — one class per file (design §7), split
from xr_settings_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
