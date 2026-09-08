"""
@cross-cutting
@module resources.profile_basis
@tags @xc:bindings

Module/engine resource profiles (res-2): what a subject NEEDS (the
floor — min RAM/disk/threads), what it BENEFITS from (scalability —
a strictly single-threaded engine gains nothing from a big-compute
server), what it IS (compute / data / balanced), and — for data
subjects — which storage tier it belongs in (redis / sqlite /
mariadb, the InstanceDefinition.db_backend vocabulary).

Every number carries its label: fidelity='declared' (a knob or a
seed) until res-3 measurement flips it to 'measured' — labels travel
with numbers, honest absence otherwise.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - resources.custom.profile_analysis / resources.profile_api
  - resources.custom.admission_advisor (res-4)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/profile/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from resources.objects.profile.ModuleResourceProfile import ModuleResourceProfile  # noqa: F401
