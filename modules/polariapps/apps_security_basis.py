"""
@cross-cutting
@module polariapps.apps_security_basis
@tags @xc:accessControl

ct-8 (design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6): SECURITY DECISIONS PER APP × VERSION.

His rulings 2026-09-18: *"track how many objects have any kind of security coverage and how much if any"*;
*"track security policy decisions of different types and how many have been covered per app, since security
must be worked on at a per-app basis and per each version release"*.

One row class, `SecurityDecision`: one row per SUBJECT that needs a ruling, keyed
`app|app_version|kind|subject`. The subjects are enumerated FROM THE APP, so `open` means a real gap; a
derivation may only ever suggest; a person confirms with their Keycloak `sub` and the hash of the proposal
they saw; a version bump carries rulings forward as `inherited` and marks what changed `stale`.

WHY HERE AND NOT IN security: the row is about an APP and a RELEASE — exactly the reasoning §57 wrote down for
`RoleAppBinding`/`UserAppPreference`. Everything read out of the security module (observations, owner
policies, trace targets, the causal map, the concrete step) is read through a GUARDED import, so polariapps
keeps working — and keeps counting — on an instance that carries no security module at all.

The logic is in `polariapps.custom.security_decisions` (the ledger), `polariapps.custom.security_coverage`
(the counting) and `polariapps.custom.security_confirm` (the one human confirmation); this file is the
sap-2c index that re-exports the row and its vocabulary.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - polariapps.apps_api (/api/apps/security/*)
  - polariapps.apps_page (/display/apps-security) · polariapps.apps_selftest
"""
# sap-2c INDEX (design §7): the class lives one-per-file under objects/apps_security/;
# this file re-exports it (imports keep working) and holds what it shares.

from polariapps.objects.apps_security._shared import (  # noqa: F401
    COVERAGE_LEVELS, DECISION_KINDS, DECISION_STATES, HUMAN_STATES, UNRULED_STATES, decision_name,
)
from polariapps.objects.apps_security.SecurityDecision import SecurityDecision  # noqa: F401
