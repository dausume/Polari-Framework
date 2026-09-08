"""
@module supplychain.sourcing_basis

Material/product SOURCING as data (Dustin 2026-07-28): who can supply
a thing, what they charge (dated, cited price observations), and a
DEFINABLE preference ladder over source categories.

Category flags are independent booleans precisely so sources can
OVERLAP definitions (a supplier can be local AND commercial AND
eco-friendly at once); the preference policy ranks by predicate over
those flags, first-match-wins.

A source can also be a CUSTOMER: demands_json lists what the business
behind it would buy (e.g. a hydroponics farm supplies wax-source
biomass and wants geopolymer self-watering pots + shelves) — the
mutual-supply loops the OSEB thesis is about.

@consumers polariServer seed_pairs, supplychain.custom.sourcing_analysis
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/sourcing/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from supplychain.objects.sourcing._shared import SOURCE_AVAILABILITY  # noqa: F401
from supplychain.objects.sourcing.SupplySourceProfile import SupplySourceProfile  # noqa: F401
from supplychain.objects.sourcing.PriceCitation import PriceCitation  # noqa: F401
from supplychain.objects.sourcing.ProductInputRequirement import ProductInputRequirement  # noqa: F401
from supplychain.objects.sourcing.ProductFormula import ProductFormula  # noqa: F401
from supplychain.objects.sourcing.SourcePreferencePolicy import SourcePreferencePolicy  # noqa: F401
