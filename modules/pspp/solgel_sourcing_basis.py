"""
@module pspp.solgel_sourcing_basis

mtt-2 sg-community: PRECURSOR SOURCING as first-class data — the layer
that turns a sol-gel chemistry route into a question a community can
answer: "can we make this from common materials, and if not, what is
the common-material analog?"

Per Dustin (2026-07-26): model EVERY route, common or not — the
industrial/lab routes are reference points whose precursors we map to
common-material SUBSTITUTES. Accessibility is therefore a recorded
PROPERTY of each precursor and route, never a gate that hides a route.

- PrecursorSource — one way to obtain a ChemicalSpecies, with its
  accessibility tier, the common inputs it is derivable from, the lab
  reagent it substitutes for, and a citation. This is the object the
  substitution map is built from.
- COMMUNITY_ROUTES — named sol-gel routes (water-glass+citric-acid,
  citrus-catalyzed TEOS, rice-husk bio-silica, Stoeber lab reference…)
  each declaring its precursors; route accessibility = the LEAST
  accessible precursor (a route is only as community-ready as its
  hardest input).
- route_report — runs the chemistry through the existing engine to a
  gel AND attaches the sourcing/accessibility/substitution picture,
  with honest caveats (numbers refuse; the water-glass morphology
  fork is unvalidated vs the alkoxide picture until digitized).

Honesty: accessibility tiers + derivations are QUALITATIVE cited
claims (textbook-level: water glass from sand + alkali, silica from
rice-husk ash). Numeric performance (gel time, yield, morphology) is
NOT asserted — the reference datasets in solgel_process refuse until
the photographed figures are digitized.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.pspp_api (/api/pspp/solgel/sources, /solgel/community-routes)
  - pspp.solgel_sourcing_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/solgel_sourcing/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.solgel_sourcing._shared import ACCESSIBILITY_TIERS, CLAIM_STATUSES, COMMUNITY_ROUTES, SEED_PRECURSOR_SOURCES, _SRC_PROVENANCE, _TIER_RANK, _loads, _row, _run_waterglass, _source_index, _tier_rank, route_accessibility, route_report, substitution_map  # noqa: F401
from pspp.objects.solgel_sourcing.PrecursorSource import PrecursorSource  # noqa: F401
