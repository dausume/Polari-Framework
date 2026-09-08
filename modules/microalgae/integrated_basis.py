"""
@cross-cutting
@module microalgae.integrated_basis
@tags @xc:bindings

algae-2 — IntegratedLoopDefinition: an ecosystem designed AROUND the
algae reactor (Dustin). A source system carries a MODEST designed
nitrogen surplus; one or more reactors are sized to consume exactly that
surplus while fixing CO2, so the composite nets to balance.

The coherent design has TWO requirements, not one:
  1. BALANCED  — composite net N ≈ 0 with the reactor running.
  2. RESILIENT — the base surplus (without the reactor) is small enough
                 that the passive regulators (macroalgae + substrate
                 denitrification + harvest) hold it if the reactor goes
                 offline. A design that only balances BECAUSE a large
                 excess is being drained by the reactor is fragile
                 ('reactor-load-bearing') — it spikes toxic if the
                 reactor hiccups, violating the self-sustaining ethos.
The reactor is a decarbonization + fine-regulation LAYER on a base that
nearly self-balances — not the load-bearing balance mechanism. The
reactors' biochar draw caps guarantee they can never over-pull the base.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - microalgae.custom.integrated_analysis (chained_balance)
@see /SALTWATER_FOOD_FOREST_SPEC.md, tanks/, [[microalgae-reactors]]
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/integrated/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from microalgae.objects.integrated._shared import DESIGN_MODES  # noqa: F401
from microalgae.objects.integrated.IntegratedLoopDefinition import IntegratedLoopDefinition  # noqa: F401
