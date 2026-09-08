"""
@module mealoptions.price_reference_basis

mo-2 (MEAL_OPTIONS_MODULE_PLAN.md §1, §2, D1–D4; Dustin 2026-09-03):
"Data about purchase prices without information about who did the
purchase and if they are stripped down to only the month data, can
be put up to the module for persistence and reference."

PriceReference = one food × one month × one SOURCE TYPE (× the chain
name ONLY when the source is a chain) × one coarse region, carrying
the median / min / max price per kg and the sample count. It is the
published, person-free shadow of nutrition's PriceObservation rows:
the purchaser, the place (name, address, lat/lon, household) and the
DAY are stripped before a row is built — see PRIVACY_STRIPPED_FIELDS,
which the export and its selftest pin.

Source typing (§2): OWNERSHIP_KINDS is the ONE vocabulary — nutrition's
SourceLocation imports it from here (mealoptions imports nothing from
nutrition). A Kroger price is a Kroger price in any region, so chain
references carry the brand slug; an independent / farmers market /
coop / direct farm is one of many differently-owned vendors, so those
references carry only the type + region and say so
(varies_by_vendor=True, VARIES_BY_VENDOR_NOTE) — no vendor name leaves
the instance.

SEED_PRICE_REFERENCES is EMPTY by design: references come from
`nutrition.custom.market_analysis.export_price_references` (aggregation of
live observations) and, from mo-3 on, the module's initialData —
never from hand-written seeds.
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: The one source-ownership vocabulary (plan §2). nutrition imports it.
OWNERSHIP_KINDS = ('chain', 'franchise', 'online-chain', 'warehouse-chain',
                   'independent', 'farmers-market', 'coop', 'direct-farm',
                   'other')
#: Kinds whose price is set by ONE owner across every branch — the
#: reference keeps the brand (chain_name).
CHAIN_KINDS = ('chain', 'franchise', 'online-chain', 'warehouse-chain')
#: Kinds where every vendor is independently owned — the reference
#: keeps only the type + region and says prices differ by vendor.
LOCAL_KINDS = ('independent', 'farmers-market', 'coop', 'direct-farm')

VARIES_BY_VENDOR_NOTE = ('each is independently owned; prices differ by '
                         'vendor and week')
PROVENANCE_AGGREGATED = ('aggregated from PriceObservation rows; purchaser, '
                         'place and day stripped')

#: Observation / location fields that must NEVER reach a PriceReference
#: row (a person, a household, a place or a day). The aggregation
#: selftest proves no output row carries any of them.
PRIVACY_STRIPPED_FIELDS = ('location_name', 'latitude', 'longitude',
                           'address', 'household_name', 'observed_date',
                           'purchaser', 'person_name')

WEIGHT_BASES = ('exact', 'prior-mixed')


def region_slug(region_label):
    """Coarse region label as typed → a name-safe slug ('unstated'
    when blank; D2 — no geocoding)."""
    label = (region_label or '').strip().lower()
    if not label:
        return 'unstated'
    out = ''.join(ch if ch.isalnum() else '-' for ch in label)
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-') or 'unstated'


def reference_name(food_name, month, source_type, chain_name, region_label):
    """`<food>-<YYYY-MM>-<source_type>[-<chain_name>]-<region_slug>` —
    the unique key one reference row lives under."""
    parts = [food_name, month, source_type]
    if chain_name:
        parts.append(chain_name)
    parts.append(region_slug(region_label))
    return '-'.join(parts)


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


#: References are EXPORTED (aggregated from observations), never
#: hand-seeded — the registration triple ships an empty list.
SEED_PRICE_REFERENCES = []
