"""
@module nutrition.purchase_basis

cal-4 — long-shelf-life staples bought in bulk on a cadence. mo-1
(MEAL_OPTIONS_MODULE_PLAN.md) MOVED BulkStaple, BULK_CADENCES,
FOODKEEPER and SEED_BULK_STAPLES to mealoptions.staple_basis with
names unchanged (the shipped seeds lose their household / location /
date pointers there); this module now RE-EXPORTS them so every
`from nutrition.purchase_basis import X` keeps working. The purchase
analysis (purchase_analysis) stays here — it names households.

@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""

from mealoptions.staple_basis import (  # noqa: F401
    BULK_CADENCES, FOODKEEPER, INSTANCE_POINTER_FIELDS, BulkStaple,
    SEED_BULK_STAPLES,
)
