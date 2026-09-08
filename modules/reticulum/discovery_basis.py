"""
@module reticulum.discovery_basis

PEER DISCOVERY + ADJUDICATION (ret-1d, plan §5o, DECIDED row 21):
every announce/broadcast HEARD becomes an observation; a HUMAN
decides what it becomes.

  PeerSighting   measured evidence that someone is out there: hashes,
                 aspects, which interface/bearer heard them, when and
                 how often. Status 'unadjudicated' until decided —
                 hearing is not admitting.

Adjudication outcomes:
  archipelago  "this is one of our own devices" → enters .arch
               (an ArchipelagoNode is created; trust GRADES stay
               separate — admission is routing and naming, never
               authority).
  mesh         a stranger we still want to see → enters .mesh:
               reachability-tracked, interactions capped at the
               mesh rung (data rules, census, proposals).
  ignored      heard, noted, not shown again (the row stays — an
               ignored peer that returns on a new bearer is a fact).

@consumers reticulum.reticulum_api (/api/reticulum/peers),
           the sidecar's announce listener (peersHeard in /status)
@see modules/reticulum/arch_basis.py (.arch), meshapp_basis.py
     (the mesh rung .mesh peers are capped at), plan §5o
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/discovery/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.objects.discovery._shared import ACTOR_MODES, ADJUDICATION_VALUES, SIGHTING_STATUS_VALUES, adjudicate, merge_heard, resolve_actor  # noqa: F401
from reticulum.objects.discovery.PeerSighting import PeerSighting  # noqa: F401
