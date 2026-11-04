"""
@module mech.objects.assembly.MechConflict

Row class MechConflict of the mech module — one class per file (design §7); mxc-2.
The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from mech.objects.assembly._shared import CONFLICT_KINDS, CONFLICT_SEVERITIES

class MechConflict(treeObject):
    """The BoardConflict analogue: one FIT-CHECK finding on an
    assembly (fit_checks + dof_solver write these). Failure MODES are
    not here — they stay composition.FailureModeDefinition (§9.1)."""

    @treeObjectInit
    def __init__(self, name='', assembly_ref='', kind='interference',
                 detail_json='{}', severity='error', notes='',
                 is_prior=True, provenance_id='', manager=None):
        self.name = name
        self.assembly_ref = assembly_ref
        #: CONFLICT_KINDS: interference | thread_engagement_short |
        #: clearance_hole_small | slide_overload | cantilever_tip |
        #: grid_mismatch | under_constrained | over_constrained |
        #: wrong_pairing.
        self.kind = kind if kind in CONFLICT_KINDS else 'interference'
        #: The numbers behind the verdict (required vs actual, the
        #: instances and joints named) — never a bare label.
        self.detail_json = detail_json
        self.severity = (severity if severity in CONFLICT_SEVERITIES
                         else 'error')
        self.notes = notes
        self.is_prior = is_prior
        self.provenance_id = provenance_id
