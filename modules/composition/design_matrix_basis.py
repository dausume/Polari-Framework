"""
@module composition.design_matrix_basis

arch-5: CANCELLATION AS DATA — the Axiomatic Design half of the
archetype (practice map §3). The design matrix maps knobs (design
parameters) to outcomes (functional requirements), and its DERIVED
classification is the well-formedness check of a characteristic
equation set (handover §2.5):

  uncoupled  every knob moves one outcome — tune in any order
  decoupled  triangular — a valid TUNING ORDER exists, and it is
             part of the design (the M0: gauge, then window, then
             turns)
  coupled    no order works — optimising one objective moves
             another, and that is exactly where requirements move
             silently (mag-22). Coupled is a LOUD FINDING, not an
             error.

Entries also carry the §3.1 ratio trap: coupling='both' means one
parameter feeds BOTH terms of a ratio (remanence: the magnet that
makes the torque makes the detent), so 'more is better' is exactly
wrong — any structure storing it as monotone gets this class of
case wrong, so the matrix reports it as a finding whatever the
classification.

@consumers composition.archetype_basis, polariServer seed passes,
composition.composition_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/design_matrix/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import resolve_named

from composition.objects.design_matrix._shared import COUPLINGS, classify, matrix_report  # noqa: F401
from composition.objects.design_matrix.DesignMatrixDefinition import DesignMatrixDefinition  # noqa: F401
