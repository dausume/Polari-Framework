"""
@module nutrition.objects.market.SourceLocation

Row class SourceLocation of the nutrition module — one class per file (design §7), split
from market_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SourceLocation(treeObject):
    """One buying/growing location with its geolocation.

    mo-2 source typing (MEAL_OPTIONS_MODULE_PLAN.md §2): `ownership_kind`
    (OWNERSHIP_KINDS — chain / franchise / online-chain /
    warehouse-chain / independent / farmers-market / coop / direct-farm
    / other) says WHO sets the price; `chain_name` is the brand slug
    ('kroger') and stays BLANK unless ownership_kind is a CHAIN_KINDS
    entry. `kind` (LOCATION_KINDS) keeps saying what the place IS.

    Schema-addition gotcha: live rows created before mo-2 lack both new
    fields (they read as the defaults 'other' / '' until written).
    The demo rows converge through moduleService.seed_upsert on boot
    (is_prior=True rows are diffed field-by-field); a household's OWN
    rows (is_prior=False) are never touched by seeds — type them from
    the Food Supply page (Places table → ownership_kind, chain_name)
    or the price export files them under 'other'.
    """

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('eastside-grocery').
        name: str = '',
        display_name: str = '',
        # LOCATION_KINDS entry.
        kind: str = 'grocery',
        # OWNERSHIP_KINDS entry (mo-2): who sets the price here.
        ownership_kind: str = 'other',
        # brand slug for CHAIN_KINDS ('kroger'); '' for everything else.
        chain_name: str = '',
        latitude: float = 0.0,
        longitude: float = 0.0,
        # free-text region ('' = unstated; NO geocoding, A2).
        region_label: str = '',
        address: str = '',
        # household that uses this location ('' = shared/global).
        household_name: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.ownership_kind = ownership_kind
        self.chain_name = chain_name
        self.latitude = latitude
        self.longitude = longitude
        self.region_label = region_label
        self.address = address
        self.household_name = household_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
