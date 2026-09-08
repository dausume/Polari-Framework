"""
@module composition.routing_basis

arch-4: PROCESS HISTORY as data, and PROMOTION as a recorded,
audited OPERATION — never a relabelling.

The routing (practice: the traveler) is the ordered operation list
that builds a construction variant. Step COUNT derives from it.
Every operation declares the CAPABILITY RUNG it assumes (techtree
ladder, the mag-22 lesson: an optimisation that hides its rung is
inadmissible) and WHAT ITS SPEC IS FOR (rate/yield/tolerance/
physics — handover §3.8: industrial requirements are re-derived
against our volume, not inherited).

A PROMOTE operation is the schema's answer to handover §1.1: it
consumes the source assembly's separable interfaces, names the
interface set it fuses, emits a NEW identity with genealogy, and
records modes deleted / modes introduced / repairability spent. The
audit enforces the Boothroyd-Dewhurst gate (practice map §2): an
interface whose members must move relative to each other, or must
separate for service, may NOT be fused — and the seeds carry the
mag-26 snap interface as exactly such a refusal case.

Nothing here EXECUTES a promotion on live rows: rows are seeded or
human-made, the engine audits and reports (knobs-and-suggestions —
mag-12's suggestion-over-evidence discipline).

@consumers polariServer seed passes, composition.composition_seed,
composition.composition_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/routing/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import named, resolve_named, rows
from composition.node_basis import owned_interfaces

from composition.objects.routing._shared import OPERATION_KINDS, PURPOSE_CLASSES, _loads, audit_promotion, routing_operations, routing_report, variant_step_counts  # noqa: F401
from composition.objects.routing.RoutingDefinition import RoutingDefinition  # noqa: F401
from composition.objects.routing.RoutingOperation import RoutingOperation  # noqa: F401
