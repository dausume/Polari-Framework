"""
@module pspp.reaction_network_basis

The reaction network as DATA (Ch.8.2-8.6 review, Findings 3/5/7):
Polari is not a "geopolymer simulator" — it is a generic
reactive-material engine, and the geopolymer chemistry is one LIBRARY
of species and graph-rewrite rules within it. Swapping the library,
not redesigning the simulator, is how sol-gels / cement hydration /
oxidation arrive later.

- ChemicalSpecies rows — the inventory reaction rules consume and
  produce (Q-species are DYNAMIC RESOURCES here, not static labels).
- ReactionRule rows — graph-rewrite templates (reactants → products +
  topology change), each carrying its hypothesis status: Ch.7's
  lesson is that mechanisms are COMPETING HYPOTHESES (seven-step
  mechanism vs Loewenstein-conflicting Al-O-Al condensation), so
  rules register their standing and rivals instead of being hardcoded
  truth. NO rule carries kinetics until a cited calibration is loaded
  (invariant I5) — rate queries refuse.
- REACTION_STAGES — the reusable common pipeline (Finding 7):
  activation → dissolution → ortho-sialate generation → branch
  selection → framework growth. Na and K systems share the stages;
  only branching condensation and framework selection differ, which
  is exactly why rules are per-family DATA.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - future pspp-8 reaction-progress engines (rules feed the network)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/reaction_network/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.reaction_network._shared import HYPOTHESIS_STATUSES, REACTION_STAGES, SEED_CHEMICAL_SPECIES, SEED_REACTION_RULES, SITE_CONSTRAINTS, _NET_PROVENANCE, _RULE_CATION_FAMILIES, _row, _species_names, rule_rate, validate_rule  # noqa: F401
from pspp.objects.reaction_network.ChemicalSpecies import ChemicalSpecies  # noqa: F401
from pspp.objects.reaction_network.ReactionRule import ReactionRule  # noqa: F401
