"""
@module xr.objects.xr_settings.XrTypeDefault

Row class XrTypeDefault of the xr module — one class per file (design §7), split
from xr_settings_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
