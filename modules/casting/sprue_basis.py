"""
@cross-cutting
@module casting.sprue_basis
@tags @xc:bindings

cast-4: sprues and gating as OBJECTS — a reusable strategy, and the
strategy APPLIED to one mold with the generated geometry + the
removability verdict recorded.

  SprueStrategyDefinition   HOW to gate (style, vents, taper, neck
                            ratio, removal mode) — reusable across
                            molds; the neck ratio is THE removability
                            knob (Dustin's "easy to remove", made
                            numeric: neck cross-section as a fraction
                            of the LOCAL part section, thresholds
                            0.25 brittle / 0.40 ductile — named
                            priors, confirmable).
  SprueSetInstance          the strategy applied to one mold: which
                            -eq rows were generated, where and WHY
                            (placements carry evidence), and the
                            worst-wins removability score.

Parity note: the same generated solids serve both parities — they
are SUBTRACTED from the mold body (channels in a negative) and
UNIONED onto the master (attached sprues on a positive); cast-3's
derived parity decides which artifact gets printed.

@consumers polariServer.defClassList, casting.sprue_geometry
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-4)
"""

from objectTreeDecorators import treeObject, treeObjectInit

GATE_STYLES = ('top-gate', 'bottom-gate-riser', 'side-gate')
VENT_PLACEMENTS = ('high-points', 'manual')
REMOVAL_MODES = ('snap', 'cut', 'melt-with-master')
#: Neck-ratio ceilings by part material class — the plan §4 proposal,
#: carried as NAMED priors until Dustin adjusts them.
NECK_RATIO_LIMITS = {'brittle': 0.25, 'ductile': 0.40}


class SprueStrategyDefinition(treeObject):
    """A reusable gating strategy — the knobs, not the geometry."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # GATE_STYLES entry.
        gate_style: str = 'top-gate',
        n_vents: int = 2,
        # VENT_PLACEMENTS entry — high-points uses the cast-2 grid
        # connectivity to find cavity ceilings air must escape from.
        vent_placement: str = 'high-points',
        sprue_taper_deg: float = 2.0,
        # neck cross-section ÷ LOCAL part section at the attachment —
        # the removability knob. Checked against NECK_RATIO_LIMITS.
        neck_area_ratio: float = 0.2,
        # REMOVAL_MODES entry: snap needs a brittle part + small
        # neck; cut tolerates more; melt-with-master only when the
        # sprue material IS the sacrificial master.
        removal_mode: str = 'snap',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.gate_style = (gate_style if gate_style in GATE_STYLES
                           else 'top-gate')
        self.n_vents = n_vents
        self.vent_placement = (vent_placement
                               if vent_placement in VENT_PLACEMENTS
                               else 'high-points')
        self.sprue_taper_deg = sprue_taper_deg
        self.neck_area_ratio = neck_area_ratio
        self.removal_mode = (removal_mode
                             if removal_mode in REMOVAL_MODES
                             else 'snap')
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id


class SprueSetInstance(treeObject):
    """One strategy applied to one mold — generated rows + verdict.
    All geometry fields are DERIVED by sprue_geometry; re-application
    reconverges them (the derived-row rule from cast-1)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        mold_ref: str = '',
        strategy_ref: str = '',
        sprue_shape_names_json: str = '[]',
        vent_shape_names_json: str = '[]',
        # per-feature placement + WHY (evidence) — never bare
        # coordinates.
        placements_json: str = '[]',
        removability_score: float = 0.0,
        removability_json: str = '{}',
        # the two parity artifacts (see module header).
        sprued_body_shape_name: str = '',
        sprued_master_shape_name: str = '',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.mold_ref = mold_ref
        self.strategy_ref = strategy_ref
        self.sprue_shape_names_json = sprue_shape_names_json
        self.vent_shape_names_json = vent_shape_names_json
        self.placements_json = placements_json
        self.removability_score = removability_score
        self.removability_json = removability_json
        self.sprued_body_shape_name = sprued_body_shape_name
        self.sprued_master_shape_name = sprued_master_shape_name
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
