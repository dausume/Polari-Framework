"""
@module pspp.objects.reaction_network.ReactionRule

Row class ReactionRule of the pspp module — one class per file (design §7), split
from reaction_network_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ReactionRule(treeObject):
    """One graph-rewrite template: reactants → products + topology
    change. Kinetics-free until a cited calibration exists."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # JSON lists of ChemicalSpecies names.
        reactants_json: str = '[]',
        products_json: str = '[]',
        # What happens to the network topology, as prose the rewrite
        # engine will later formalize ('break one Si-O bridge; create
        # silanol + NBO; associate charge-compensating cation').
        topology_change: str = '',
        # One of REACTION_STAGES.
        stage: str = '',
        # One of HYPOTHESIS_STATUSES + the rivals it competes with.
        hypothesis_status: str = 'mechanistic-proposal',
        competing_with_json: str = '[]',
        # One of SITE_CONSTRAINTS — where transport permits this rule
        # (Fig 8.21 two-phase selection; '' = anywhere).
        site_constraint: str = '',
        # 'Na' | 'K' | '' (both): §8.5 routes are Na, §8.6 their K
        # analogues — a rule never fires in a mix whose alkali it
        # does not name ('' rules fire in both).
        cation_family: str = '',
        # JSON list of ThresholdReactionWindow names (condition-gate
        # role) that must not grade 'failure' for this rule to fire —
        # pathway thresholds as DATA (e.g. the p.188 MR<1.20 Q0
        # gate). Enforced by pspp.custom.network_stepping.
        condition_windows_json: str = '[]',
        # 'none' until a calibration row is loaded (invariant I5).
        kinetics_status: str = 'none',
        kinetics_ref: str = '',
        material_family: str = 'general',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.reactants_json = reactants_json
        self.products_json = products_json
        self.topology_change = topology_change
        self.stage = stage
        self.hypothesis_status = hypothesis_status
        self.competing_with_json = competing_with_json
        self.site_constraint = site_constraint
        self.cation_family = cation_family
        self.condition_windows_json = condition_windows_json
        self.kinetics_status = kinetics_status
        self.kinetics_ref = kinetics_ref
        self.material_family = material_family
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes
