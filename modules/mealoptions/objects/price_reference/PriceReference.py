"""
@module mealoptions.objects.price_reference.PriceReference

Row class PriceReference of the mealoptions module — one class per file (design §7), split
from price_reference_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from mealoptions.objects.price_reference._shared import PROVENANCE_AGGREGATED

class PriceReference(treeObject):
    """One food × month × source type (× chain) × region price
    reference — median / min / max $/kg over `sample_count`
    observations, every person / place / day field stripped."""

    @treeObjectInit
    def __init__(
        self,
        # reference_name(...) — see above.
        name: str = '',
        # FoodMaterial/FoodItem slug ('chicken-breast-raw').
        food_name: str = '',
        # 'YYYY-MM' — month granularity, NO day (D1).
        month: str = '',
        # OWNERSHIP_KINDS entry.
        source_type: str = 'other',
        # brand slug for CHAIN_KINDS ('kroger'); '' for everything else.
        chain_name: str = '',
        # the SourceLocation's region_label AS TYPED; 'unstated' if blank.
        region_label: str = 'unstated',
        currency: str = 'USD',
        price_per_kg_median: float = 0.0,
        price_per_kg_min: float = 0.0,
        price_per_kg_max: float = 0.0,
        sample_count: int = 0,
        # 'exact' = every sample converted by an exact mass unit;
        # 'prior-mixed' = at least one rode a UnitWeightPrior.
        weight_basis: str = 'exact',
        # True for LOCAL_KINDS: many owners, prices differ by vendor.
        varies_by_vendor: bool = False,
        provenance_id: str = PROVENANCE_AGGREGATED,
        # True so a re-publish CONVERGES the row (seed_upsert never
        # touches is_prior=False rows); a derived aggregate is a prior
        # over next month's price, never a measurement of it.
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.food_name = food_name
        self.month = month
        self.source_type = source_type
        self.chain_name = chain_name
        self.region_label = region_label
        self.currency = currency
        self.price_per_kg_median = price_per_kg_median
        self.price_per_kg_min = price_per_kg_min
        self.price_per_kg_max = price_per_kg_max
        self.sample_count = sample_count
        self.weight_basis = weight_basis
        self.varies_by_vendor = varies_by_vendor
        self.provenance_id = provenance_id
        self.is_prior = is_prior
        self.notes = notes
