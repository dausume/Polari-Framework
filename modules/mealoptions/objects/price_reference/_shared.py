"""@module mealoptions.objects.price_reference._shared — what the price_reference row classes share (constants, seeds, helpers); split from price_reference_basis.py (sap-2c)."""

OWNERSHIP_KINDS = ('chain', 'franchise', 'online-chain', 'warehouse-chain',
                   'independent', 'farmers-market', 'coop', 'direct-farm',
                   'other')
CHAIN_KINDS = ('chain', 'franchise', 'online-chain', 'warehouse-chain')
LOCAL_KINDS = ('independent', 'farmers-market', 'coop', 'direct-farm')
VARIES_BY_VENDOR_NOTE = ('each is independently owned; prices differ by '
                         'vendor and week')
PROVENANCE_AGGREGATED = ('aggregated from PriceObservation rows; purchaser, '
                         'place and day stripped')
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
SEED_PRICE_REFERENCES = []
