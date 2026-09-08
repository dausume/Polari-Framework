"""
@cross-cutting
@module reticulum.reticulum_basis
@tags @xc:bindings

Reticulum transport core (ret-1, RETICULUM_TRANSPORT_PLAN §4): the
object model for mesh transport over Reticulum — the third module born
manifest-first on the dyn-1 machinery (scanning, collab walked first).

The one hard architectural line (plan ret-8, inherited VERBATIM from
LiveKit §2), stated here because this module is where it would be
easiest to violate:

    NOTHING ARRIVING FROM ANOTHER ISLE OVER RETICULUM MAY MUTATE
    POLARI STATE. Inbound app data becomes a PROPOSAL through the
    ordinary ai_actions path; applying stays a confirmed act.

Licence: the RNS stack is pinned to the last MIT releases
(rns==0.9.4 + lxmf==0.6.3, RETICULUM_LICENCE_GATE.md) — pins are
LICENCE pins, never `>=`. This module itself never imports RNS: the
stack lives in the pol-reticulum sidecar (plan §5k); rows here are
facts ABOUT the mesh.

Six treeObjects (auto-CRUDE + persisted — object-coherence):

  ReticulumIdentity     an identity we hold or trust. Keycloak stays
                        the authority for PEOPLE (mtg-2 lesson);
                        this row BINDS a KC subject / an instance to
                        an RNS identity. PRIVATE KEYS NEVER LAND IN
                        A ROW — only the hash and where the key lives.
  ReticulumDestination  name ⇄ destination hash, aspects, scope,
                        direction, destination type (single|plain|…).
  ReticulumInterface    one physical/logical link and its DECLARED
                        parameters, with MEASURED facts kept separate
                        (fidelity — the resources-module idiom). Also
                        carries the regulatory domain and rx/tx
                        direction as DEVICE FACTS (§5g/§5i).
  TransportBinding      "this app endpoint reaches that destination"
                        + the admission POLICY (encoding, size, rate,
                        FEC, snapshot mode) — ret-3's detection as
                        data rather than code.
  LinkMeasurement       measured facts PER PATH, not per interface
                        (§5e: latency is a property of the path);
                        every fact carries a timestamp — stale
                        measurements are not measurements.
  AirtimeBudget         duty-cycle accounting per interface: the
                        netledger analogue for spectrum. Airtime is
                        ledgered, never assumed.

@consumers
  - polariApiServer.polariServer.defClassList (auto-CRUDE + persistence)
  - reticulum.reticulum_api (capability, arch listing, inbound seam)
@see modules/reticulum/rns_remote.py (the resolution ladder),
     modules/collab/collab_basis.py (the pattern this walks),
     RETICULUM_TRANSPORT_PLAN.md (decisions ledger — do not relitigate)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/reticulum/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import re
from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.objects.reticulum._shared import BEARER_VALUES, DESTINATION_SCOPE_VALUES, DESTINATION_TYPE_VALUES, DIRECTION_VALUES, ENCODING_VALUES, FEC_MODE_VALUES, FIDELITY_VALUES, IDENTITY_KIND_VALUES, IDLE_POLICY_VALUES, INTERFACE_DIRECTION_VALUES, REGULATORY_DOMAIN_VALUES, SEED_RNS_INTERFACES, SNAPSHOT_MODE_VALUES, _SAFE_NAME_RE, admit_binding, airtime_ms, budget_admits, capability_for_path, derive_timeout_ms, interface_may_attach, may_announce, may_route, measurement_fresh, safe_mesh_name, tx_permitted  # noqa: F401
from reticulum.objects.reticulum.ReticulumIdentity import ReticulumIdentity  # noqa: F401
from reticulum.objects.reticulum.ReticulumDestination import ReticulumDestination  # noqa: F401
from reticulum.objects.reticulum.ReticulumInterface import ReticulumInterface  # noqa: F401
from reticulum.objects.reticulum.TransportBinding import TransportBinding  # noqa: F401
from reticulum.objects.reticulum.LinkMeasurement import LinkMeasurement  # noqa: F401
from reticulum.objects.reticulum.AirtimeBudget import AirtimeBudget  # noqa: F401
