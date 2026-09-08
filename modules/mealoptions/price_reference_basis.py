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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/price_reference/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mealoptions.objects.price_reference._shared import CHAIN_KINDS, LOCAL_KINDS, OWNERSHIP_KINDS, PRIVACY_STRIPPED_FIELDS, PROVENANCE_AGGREGATED, SEED_PRICE_REFERENCES, VARIES_BY_VENDOR_NOTE, WEIGHT_BASES, reference_name, region_slug  # noqa: F401
from mealoptions.objects.price_reference.PriceReference import PriceReference  # noqa: F401
