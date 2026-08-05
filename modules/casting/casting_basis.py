"""
@cross-cutting
@module casting.casting_basis
@tags @xc:bindings

cast-1 (WAX_MOLD_NESTING_PLAN): the mold as a first-class object — a
NEGATIVE derived from a part's math definition, never hand-built.

One treeObject (auto-CRUDE + persisted — object-coherence):

  MoldDefinition   names a part shape and the declared allowances; the
                   mold geometry itself (stock block, shrink-scaled
                   part, mold body = stock DIFFERENCE part) is DERIVED
                   by casting.mold_geometry.derive_mold as mathshapes
                   rows. The inversion is algebra the existing CSG
                   executor already evaluates: body field =
                   max(F_stock, −F_part). Hand-editing a derived row is
                   not an error state that sticks — re-derivation
                   overwrites it and REPORTS the drift (the parity
                   handoff's "compute and refuse" posture: the cavity
                   is not an opinion).

Shrink allowance is a DECLARED parameter (pattern-maker's shrink: the
cavity is oversized so the cast part lands on-size after
solidification shrink), default 0 — an honest "not yet modelled"
rather than a baked constant. Chain parity / thermal ordering live in
cast-3; sprues in cast-4.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - casting.mold_geometry (derivation), casting.casting_seed
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-1)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Where the part's geometry comes from. 'mathshape' = a
#: MathShapeDefinition (primitive/quadric/csg — has a volumetric
#: field). 'imported-cad' = an ImportedCadObject mesh — REFUSED until
#: the cast-2 voxel bridge lands (an imported mesh has no field and
#: silently evaluates as outside-everywhere; see mold_geometry).
PART_SOURCES = ('mathshape', 'imported-cad')


class MoldDefinition(treeObject):
    """A mold derived from a part definition: the part names the void;
    the stock block and the mold body are computed, not typed in."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-sphere-mold').
        name: str = '',
        display_name: str = '',
        # The part this mold casts — a MathShapeDefinition name (or an
        # ImportedCadObject name once cast-2 bridges meshes).
        part_shape_ref: str = '',
        # PART_SOURCES entry.
        part_source: str = 'mathshape',
        # Optional explicit stock shape. Empty = auto: an axis-aligned
        # box around the (shrink-scaled) part, stock_margin_cm each side.
        stock_shape_ref: str = '',
        stock_margin_cm: float = 1.0,
        # Pattern-maker's shrink: % the cavity is oversized so the cast
        # part lands on-size after solidification. 0 = not modelled
        # (named, not assumed). Applied as a uniform scale about the
        # origin — an exact quadric transform, see mold_geometry.
        shrink_allowance_pct: float = 0.0,
        # Preferred demold direction; consumed by cast-7's parting
        # sweep, carried (not interpreted) until then.
        parting_axis_hint: str = 'z',
        # What the mold is made of / coated with — bound by the cast-3
        # thermal gate and cast-8 coatings; carried as refs here.
        mold_material_ref: str = '',
        coating_ref: str = '',

        # --- DERIVED by mold_geometry.derive_mold; hand-edits are
        # --- overwritten on re-derivation, with the drift reported ---
        stock_shape_name: str = '',
        scaled_part_shape_name: str = '',
        body_shape_name: str = '',
        derivation_json: str = '',

        # seed-upsert contract: False = human customized, seeds keep off.
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.part_shape_ref = part_shape_ref
        self.part_source = (part_source if part_source in PART_SOURCES
                            else 'mathshape')
        self.stock_shape_ref = stock_shape_ref
        self.stock_margin_cm = stock_margin_cm
        self.shrink_allowance_pct = shrink_allowance_pct
        self.parting_axis_hint = parting_axis_hint
        self.mold_material_ref = mold_material_ref
        self.coating_ref = coating_ref
        self.stock_shape_name = stock_shape_name
        self.scaled_part_shape_name = scaled_part_shape_name
        self.body_shape_name = body_shape_name
        self.derivation_json = derivation_json
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
