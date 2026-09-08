"""
@module computerparts.parts_basis

ai-8 (Dustin): a DEDICATED module for computer parts — GPU cards,
CPUs, everything needed to put a computer together — so the cost
and feasibility of building devices from scratch is TRACKED DATA,
not folklore. Prices follow the ai-7 discipline: every price
carries its as-of date and source; a price without a date is a lie
waiting to happen.

A ComputerBuildDefinition is a parts LIST (by part name) plus the
build's effective specs; its total cost is DERIVED from the part
rows at read time (edit a part's price, every build using it
updates). The appstore's /ai-hosting surface reads these ROWS for
the buy-vs-rent advisory — row reads, never a Python import, so
the modules stay uncoupled.

@consumers
  - computerparts.parts_api (/api/computerparts)
  - appstore.appstore_ai_api (row reads for buy-vs-rent)
  - polariServer defClassList (tables + CRUDE)
  - computerparts.computerparts_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/parts/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from computerparts.objects.parts._shared import CONDITIONS, PART_KINDS, _field, break_even_months, build_report  # noqa: F401
from computerparts.objects.parts.ComputerPartDefinition import ComputerPartDefinition  # noqa: F401
from computerparts.objects.parts.ComputerBuildDefinition import ComputerBuildDefinition  # noqa: F401
