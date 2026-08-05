"""
@cross-cutting
@module casting.chain_basis
@tags @xc:bindings

cast-3: the nesting chain as DATA. Two treeObjects:

  MoldNestingChain        the multi-tier chain identity. Carries NO
                          parity field on purpose — whether the wax
                          master is a positive or a negative is
                          DERIVED from the stages (chain_analysis),
                          never stored, never hand-set. The handoff's
                          first correctness property.
  CastingStageDefinition  one stage: what shapes it (mold material),
                          what goes in (cast material), how it goes
                          in (fill method), what it cures/fires at,
                          whether the mold is DISPOSABLE (Dustin
                          2026-08-05: sacrificing the geopolymer
                          mold in the firing is allowed — a finding,
                          not a blocker), and how the previous form
                          leaves.

Stages link by (chain_ref, sequence) exactly like composition's
RoutingOperation rides RoutingDefinition — same spine idiom, no
parallel chain model.

@consumers polariServer.defClassList, casting.chain_analysis,
casting.chain_seed
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-3)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: 'cast' INVERTS the geometry (a mold makes a part, a part makes a
#: mold); 'conversion' transforms in place (firing clay to ceramic)
#: and does NOT flip parity.
STAGE_KINDS = ('cast', 'conversion')
#: How the cast material enters. slip-cast into geopolymer is
#: REFUSED by the gate (supplychain.mold_analysis: no proven
#: capillarity) — declared here so the refusal can name it.
FILL_METHODS = ('gravity-pour', 'inject', 'press', 'in-place')


class MoldNestingChain(treeObject):
    """A nested casting chain (wax → … → final part). Parity and
    thermal ordering are DERIVED by chain_analysis.chain_report."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # the final part this chain exists to produce.
        target_part_shape_ref: str = '',
        # the cast-1 MoldDefinition carrying the stage-1 geometry
        # (loading checks ride it).
        mold_def_ref: str = '',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.target_part_shape_ref = target_part_shape_ref
        self.mold_def_ref = mold_def_ref
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id


class CastingStageDefinition(treeObject):
    """One stage of a nesting chain, ordered by (chain_ref,
    sequence) — the RoutingOperation idiom."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        chain_ref: str = '',
        sequence: int = 1,
        # STAGE_KINDS entry — only 'cast' inverts.
        stage_kind: str = 'cast',
        # what SHAPES this stage: a MasterFeedstockDefinition name,
        # 'geopolymer' (the cured mold from a previous stage), or a
        # CeramicSample name.
        mold_material_ref: str = '',
        # what GOES IN: 'geopolymer-slurry', 'plastic-clay', …
        cast_material_ref: str = '',
        # FILL_METHODS entry.
        fill_method: str = 'gravity-pour',
        # conversion stages: the declared firing/processing temp.
        process_temp_c: float = 0.0,
        # geopolymer stages: the cure temperature (validity 40–85°C —
        # the exotherm PEAK is derived from it, never typed in).
        cure_temp_c: float = 0.0,
        # conversion stages: what the material BECOMES (a
        # CeramicSample name, e.g. 'earthenware-terracotta').
        target_material_ref: str = '',
        # Dustin 2026-08-05: a disposable mold may be sacrificed by
        # the process (fired past its ceiling, broken out) — turns
        # the thermal blocker into a named finding.
        mold_disposable: bool = False,
        # how the PREVIOUS form leaves before/after this stage.
        removal_route: str = '',
        # Dustin 2026-08-05: MEASURED linear shrink for this stage's
        # material (%). 0 = not measured yet — the chain analysis
        # falls back to the named literature prior. The two-pass
        # loop: cast uncompensated, measure the article, write the
        # number here, re-derive compensated.
        measured_shrink_pct: float = 0.0,
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.chain_ref = chain_ref
        self.sequence = sequence
        self.stage_kind = (stage_kind if stage_kind in STAGE_KINDS
                           else 'cast')
        self.mold_material_ref = mold_material_ref
        self.cast_material_ref = cast_material_ref
        self.fill_method = (fill_method if fill_method in FILL_METHODS
                            else fill_method)  # kept verbatim: the
        # gate REFUSES unknown methods loudly instead of silently
        # normalizing them (slip-cast must stay visible to refuse).
        self.process_temp_c = process_temp_c
        self.cure_temp_c = cure_temp_c
        self.target_material_ref = target_material_ref
        self.mold_disposable = mold_disposable
        self.removal_route = removal_route
        self.measured_shrink_pct = measured_shrink_pct
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
