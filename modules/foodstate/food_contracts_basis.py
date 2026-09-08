"""
@module foodstate.food_contracts_basis

fsp-0 — the property-domain CONTRACTS as data (the fam-1 shell
pattern): what a fully-described FoodState must be able to answer,
per domain, with the provenance rung each quantity is expected to
arrive by (the transform honesty ladder, plan §3):

  measured > mass-balance calculation > cited mechanistic model >
  USDA retention factor > REFUSE naming the gap.

Domains follow Dustin's ratified decomposition verbatim: composition
≠ structure ≠ physical ≠ chemical ≠ physiological — "two foods could
contain essentially the same grams of starch and water while behaving
very differently because one has gelatinized starch and the other has
intact granules." The final domain is named PHYSIOLOGICAL / FUNCTIONAL
PERFORMANCE (D8, ratified) and is DOWNSTREAM of the other four —
never baked into the food definition.

These are contracts, not schemas: quantities land as pspp
PropertyClaim rows on '<material>#<state>' subjects (claims-not-
values), so no new per-quantity class exists and none should.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - foodstate.food_api (GET /api/foodstate/contracts)
  - foodstate.foodstate_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/food_contracts/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from foodstate.objects.food_contracts._shared import SEED_FOOD_DOMAIN_CONTRACTS, _PROV, _q, _row, contracts_report  # noqa: F401
from foodstate.objects.food_contracts.FoodDomainContract import FoodDomainContract  # noqa: F401
