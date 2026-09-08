"""
@cross-cutting
@module nutrition.market_basis
@tags @xc:bindings

mpa-2 — the market layer as data (MEAL_PLANNING_APP_PLAN.md §0.1:
"account for buying at particular prices from different
geolocations" + "establishing and assigning nutritional information
and weight approximately for things that are purchased"):

  SourceLocation    one place food is bought (or grown): kind +
                    geolocation (lat/lon + free region label — no
                    geocoder dependency, A2).
  PriceObservation  one OBSERVED price: food × location × package
                    (quantity + unit) × price × date. User-entered
                    facts, never scraped (A1); normalization to $/kg
                    lives in market_analysis.
  UnitWeightPrior   'one medium onion ≈ 110 g' — the approximate-
                    weight vocabulary that turns purchases and
                    pantry entries stated in EACHES/CUPS into grams.
                    Convention priors (FDC portion conventions),
                    labeled and tunable per household — never exact.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.market_analysis, pantry_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-2
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/market/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from mealoptions.price_reference_basis import (  # noqa: F401
    CHAIN_KINDS, LOCAL_KINDS, OWNERSHIP_KINDS,
)

from nutrition.objects.market._shared import EXACT_UNIT_GRAMS, LOCATION_KINDS, SEED_PRICE_OBSERVATIONS, SEED_SOURCE_LOCATIONS, SEED_UNIT_WEIGHTS, _PROV, _UW_CITE, _po, _uw  # noqa: F401
from nutrition.objects.market.SourceLocation import SourceLocation  # noqa: F401
from nutrition.objects.market.PriceObservation import PriceObservation  # noqa: F401
from nutrition.objects.market.UnitWeightPrior import UnitWeightPrior  # noqa: F401
