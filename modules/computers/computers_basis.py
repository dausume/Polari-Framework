"""
@module computers.computers_basis

cmp-c (Dustin 2026-08-25): computer ASSEMBLY + use-case PROFILES
as their OWN app, separable from microchip creation and levels.
The module GROWS FROM computerparts (ai-8) rather than beside it:
ComputerPartDefinition stays the catalog row; what is new here is

  - ComputerPartClassDefinition (cmp-c-1): the component TAXONOMY
    as rows — per part kind, which specs the kind DECLARES, which
    of them feed assembly gates, and which gaps stay honestly
    unverified until someone declares them (the ai-8 discipline:
    'unverified — <spec> not declared' is an affordance, not a
    failure).
  - ComputerAssemblyDefinition (cmp-c-2): a named assembly
    wrapping a ComputerBuildDefinition, gated by the DFA-style
    named checks in computers_gates and viewable as a composition
    tree (interfaces are all designed-separable, so composition's
    own rule derives 'assembly' — materializing real composition
    rows is the later arch-8-style splice, pending Dustin's
    decision 1 confirmation).
  - ComputerProfileDefinition (cmp-c-3): a use case as DATA — a
    declared requirements floor (the ai-6 hosting-gauge shape) an
    assembly is scored against with evidence-bearing verdicts.
    Profiles are rows, never hardcoded (knobs ethos). The
    database-binding profile is DECLARE-ONLY v1: it records the
    residence intent; real topology hooks are the
    object-ownership arc's half.

@consumers
  - computers.computers_api (/api/computers)
  - computers.custom.computers_gates / computers_fit (row reads)
  - polariServer defClassList (tables + CRUDE)
  - computers.computers_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/computers/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from computers.objects.computers._shared import field_of  # noqa: F401
from computers.objects.computers.ComputerPartClassDefinition import ComputerPartClassDefinition  # noqa: F401
from computers.objects.computers.ComputerAssemblyDefinition import ComputerAssemblyDefinition  # noqa: F401
from computers.objects.computers.ComputerProfileDefinition import ComputerProfileDefinition  # noqa: F401
