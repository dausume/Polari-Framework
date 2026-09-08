"""
@cross-cutting
@module polariapps.apps_basis
@tags @xc:bindings

Polari-Apps (tt-12, Dustin 2026-07-18): an APP is a CONFIGURATION
OF MODULES for a particular capability or use-case — a local wax
3D-printing company trying wax simulations and auger-shape variants,
a lean judicial app, a DMV policy-analysis build. Apps ride the
existing module + topology machinery: deploying an app is PLANNED
first (never on-the-spot), the plan is EXPORTABLE as a
credential-free JSON package the pol CLI can point at
(`pol apps deploy <file.json>`), and applying only ever writes
ModuleAssignment rows — the actual container deploy stays the
human's pol command (knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - polariapps.custom.apps_analysis / polariapps.apps_api
  - polari-cli scripts/apps.sh · polari-platform-angular /apps page
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/apps/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from polariapps.objects.apps._shared import PLAN_STATUSES  # noqa: F401
from polariapps.objects.apps.PolariAppDefinition import PolariAppDefinition  # noqa: F401
from polariapps.objects.apps.AppDeploymentPlan import AppDeploymentPlan  # noqa: F401
