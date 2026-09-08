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

from objectTreeDecorators import treeObject, treeObjectInit

#: The increasing-scales ladder (B3): one person doing everything →
#: a business that fits a full unit economy and sustains itself.
BUSINESS_SCALES = ('one-person', 'small-team', 'unit-economy')
POLICY_EFFECTS = ('increase', 'decrease')


class RealArtifact(treeObject):
    """One finalized physical design filling a REAL segment."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Where the geometry lives: a mathshapes/CAD-import ref.
        cad_ref: str = '',
        # Electronics/mechanical design data beyond the geometry.
        hardware_design_ref: str = '',
        # Proven to WORK — physical evidence, not simulation.
        proven: bool = False,
        # JSON evidence for `proven` (build logs, test reports).
        evidence_json: str = '[]',
        # JSON: how to BUY it (vendors, parts, price points).
        commercial_route_json: str = '{}',
        # JSON: how to MAKE it open-source (guide, tooling, BOM).
        self_manufacture_route_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.cad_ref = cad_ref
        self.hardware_design_ref = hardware_design_ref
        self.proven = proven
        self.evidence_json = evidence_json
        self.commercial_route_json = commercial_route_json
        self.self_manufacture_route_json = self_manufacture_route_json
        self.notes = notes


class BusinessModelDefinition(treeObject):
    """One business model at an explicit scale on the ladder."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # BUSINESS_SCALES entry.
        scale: str = 'one-person',
        # JSON list of business-logic policies the model runs on.
        policies_json: str = '[]',
        # JSON unit economics (costs, revenue, break-even).
        unit_economics_json: str = '{}',
        # Evidenced self-sustaining (the done-test gate).
        self_sustaining: bool = False,
        # JSON evidence — typically BusinessOutcome names.
        evidence_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.scale = scale
        self.policies_json = policies_json
        self.unit_economics_json = unit_economics_json
        self.self_sustaining = self_sustaining
        self.evidence_json = evidence_json
        self.notes = notes


class BusinessOutcome(treeObject):
    """How one business model actually worked out — evidence."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # BusinessModelDefinition.name this outcome evidences.
        business_model: str = '',
        summary: str = '',
        # 'succeeded' | 'failed' | 'mixed' — honesty over polish.
        outcome: str = 'mixed',
        evidence_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.business_model = business_model
        self.summary = summary
        self.outcome = outcome
        self.evidence_json = evidence_json
        self.notes = notes


class PolicyDefinition(treeObject):
    """Policy that moves a business model's odds of success."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The policy itself, stated plainly.
        policy: str = '',
        # POLICY_EFFECTS entry — which way it moves the odds.
        effect: str = 'increase',
        # BusinessModelDefinition.name it targets ('' = general).
        target_business_model: str = '',
        # JSON evidence of the effect (examples, outcomes).
        evidence_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.policy = policy
        self.effect = effect
        self.target_business_model = target_business_model
        self.evidence_json = evidence_json
        self.notes = notes
