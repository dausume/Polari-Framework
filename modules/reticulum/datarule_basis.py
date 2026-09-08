"""
@module reticulum.datarule_basis

PER-APP DATA RULES (ret-1c, Dustin 2026-08-13): what one consumer
may SUBMIT to a mesh app, and what happens to submissions that lie.

  - per-identity size and rate caps ("only this much at one time"),
  - STRICT typing: a payload whose shape does not match the app's
    declared schema is invalid — unmatched fields are refused, not
    tolerated (tolerated garbage is how attacks start),
  - ballot-box protection: duplicate submissions per identity (per
    dedupe key) are caught,
  - and everything caught is QUARANTINED as a row, never silently
    dropped — caught garbage is EVIDENCE, and a flood of it is an
    attack signature the census can point at.

Pure functions over plain dicts; the relay daemon enforces, rows
record. Rejection never mutates anything — an mesh submission
that passes every rule still only ever becomes a PROPOSAL (ret-8).

@consumers reticulum.reticulum_api, the relay daemon (sidecar)
@see modules/reticulum/meshapp_basis.py (the tier this guards),
     plan §5n
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/datarule/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.objects.datarule._shared import QUARANTINE_REASON_VALUES, _TYPE_CHECKS, evaluate_submission, payload_matches_schema  # noqa: F401
from reticulum.objects.datarule.AppDataRule import AppDataRule  # noqa: F401
from reticulum.objects.datarule.QuarantinedSubmission import QuarantinedSubmission  # noqa: F401
