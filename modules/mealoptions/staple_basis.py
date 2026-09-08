"""
@module mealoptions.staple_basis

cal-4 (Dustin 2026-09-02): "periodic in bulk purchase events at 1
month, 3 month, 6 month, and yearly periods that can serve as ways
to buy stuff like rice or grains in bulk that last very long periods
without decay, and can act as a means to save money over time."

BulkStaple = one long-shelf-life food a household is willing to buy
in bulk: its CADENCE (months between bulk buys — the knob: 1, 3, 6
or 12), its shelf life (a CITED prior — a cadence longer than the
shelf life is refused by name), and the bulk offer observed (package
+ price), which the analysis compares against the best retail $/kg
to state the savings. Every number here is a labeled prior a
household overrides on its own row.

mo-1 privacy line: the class KEEPS its instance-pointer fields
(household_name, bulk_location_name, observed_date) so live rows,
the purchase analysis and the page tables stay schema-compatible,
but every SHIPPED seed leaves all three BLANK — the offer's
location, the household that saw it and the day it was seen live on
the instance, never in a published module's data. A blank
household_name means "any household" to the purchase analysis.

Shelf lives are TRANSCRIBED from the USDA FoodKeeper app (USDA FSIS /
Cornell / FMI; U.S. government work — public domain), pantry
storage, unopened, "best quality" figures; confidence 'transcribed'
means read from the table, not re-verified against the source this
session — verify before quoting.
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/staple/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mealoptions.objects.staple._shared import BULK_CADENCES, FOODKEEPER, INSTANCE_POINTER_FIELDS, SEED_BULK_STAPLES, _staple  # noqa: F401
from mealoptions.objects.staple.BulkStaple import BulkStaple  # noqa: F401
