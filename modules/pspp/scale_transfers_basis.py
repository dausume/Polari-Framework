"""
@module pspp.scale_transfers_basis

Scale transfers as FIRST-CLASS rows (plan pspp-5) — the promotion of
MaterialScaleDefinition's weak derived_from/derivation_method lineage
into citable objects: WHAT moved between which scales of which
states, by which method, under which assumptions, valid where. This
is how Polari proves a material is valid at some scales and not
others (ChatGPT convergence: transfers produce CLAIMS, not values).

Wax is the retrofit proof: the live paraffin lineage (L0 measured →
L1 FEM homogenization 'wax-thermal-continuum' → L4 DFT
'paraffin-quantum-energy') re-expressed as rows WITHOUT changing wax
behavior — the rows cite the same models the msim already runs.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - future pspp transfer-execution (ENGINE_REGISTRY + simulation
    gate, like scale_execution)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/scale_transfers/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from pspp.claims_basis import canonical_subject

from pspp.objects.scale_transfers._shared import SEED_SCALE_TRANSFERS, TRANSFER_STATUSES, _PW, _WAX_PROVENANCE, _known_methods, transfers_for_state, validate_transfer  # noqa: F401
from pspp.objects.scale_transfers.ScaleTransferDefinition import ScaleTransferDefinition  # noqa: F401
