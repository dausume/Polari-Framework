"""
@cross-cutting
@module techtree.techtree_content_basis
@tags @xc:bindings

Segment-content objects (tt-6, TECH_TREE_TOPOLOGY_PLAN B3) — what
the real / business / politics segments reference:

  RealArtifact             — proven CAD/hardware + BOTH routes
                             (commercial AND open-source
                             self-manufacture); real completion =
                             proven AND both routes documented.
  BusinessModelDefinition  — business-logic policies at an explicit
                             SCALE on the one-person → unit-economy
                             ladder; done = self-sustaining with
                             evidence.
  BusinessOutcome          — one example of how a business model
                             actually worked out (the evidence rows
                             business/politics point at).
  PolicyDefinition         — policy raising/lowering the odds of
                             success of a business model; done =
                             policy stated with evidence.

The done-tests live in techtree_analysis (_ASSIGNMENT_TESTS) and
read these rows duck-typed — a missing row is an honest gap naming
what to create.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - techtree.custom.techtree_analysis (real/business/politics done-tests)
  - techtree.techtree_api (row-level upserts)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/techtree_content/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from techtree.objects.techtree_content._shared import BUSINESS_SCALES, POLICY_EFFECTS  # noqa: F401
from techtree.objects.techtree_content.RealArtifact import RealArtifact  # noqa: F401
from techtree.objects.techtree_content.BusinessModelDefinition import BusinessModelDefinition  # noqa: F401
from techtree.objects.techtree_content.BusinessOutcome import BusinessOutcome  # noqa: F401
from techtree.objects.techtree_content.PolicyDefinition import PolicyDefinition  # noqa: F401
