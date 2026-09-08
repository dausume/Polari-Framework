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
                   by casting.custom.mold_geometry.derive_mold as mathshapes
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
  - casting.custom.mold_geometry (derivation), casting.casting_seed
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-1)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Where the part's geometry comes from. 'mathshape' = a
#: MathShapeDefinition (primitive/quadric/csg — has a volumetric
#: field). 'imported-cad' = an ImportedCadObject mesh — derived on
#: the cast-2 GRID path (an imported mesh has no field and silently
#: evaluates as outside-everywhere; see mold_geometry).
PART_SOURCES = ('mathshape', 'imported-cad')

#: What the sacrificial master is made of (Dustin 2026-08-05: the
#: NATURAL LOCALLY-PRODUCIBLE wax is the core focus; commercial
#: machinable wax, FDM wax filament on a standard Voron, and PLA are
#: supported alternates that meet the general 3D-printable criteria).
MASTER_MATERIAL_KINDS = ('natural-wax', 'machinable-wax',
                         'wax-filament', 'pla')
#: How a master gets made from this feedstock. auger-pellet-print =
#: the waxprint two-zone extruder; fdm-voron = a standard cartesian
#: FDM machine; cnc = subtractive on a block.
MAKE_ROUTES = ('auger-pellet-print', 'fdm-voron', 'cnc')
#: How the master LEAVES the mold (the sacrificial exit — the cast-3
#: thermal gate checks it against the mold's damage threshold).
REMOVAL_ROUTES = ('melt-out', 'burn-out', 'mechanical')
#: 'core' = the locally-producible focus; 'supported' = works, bought.
FEEDSTOCK_PRIORITIES = ('core', 'supported')


class CastingMaterialThermalProfile(treeObject):
    """cast-3b: the thermal data NO other table carries — melt/pour
    temperatures for castable metals (the survey found none anywhere
    in the framework). Literature-approximate with claim status, the
    CeramicSample pattern; a measured row replaces a prior."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # the MaterialsScienceMaterial (or common name) this covers.
        material_ref: str = '',
        solidus_c: float = 0.0,
        liquidus_c: float = 0.0,
        recommended_pour_c: float = 0.0,
        solidification_shrink_pct: float = 0.0,
        claim_status: str = 'literature-approximate',
        source_note: str = '',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.material_ref = material_ref
        self.solidus_c = solidus_c
        self.liquidus_c = liquidus_c
        self.recommended_pour_c = recommended_pour_c
        self.solidification_shrink_pct = solidification_shrink_pct
        self.claim_status = claim_status
        self.source_note = source_note
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id


class MasterFeedstockDefinition(treeObject):
    """A material the sacrificial master can be made from, with its
    make route(s), mechanical/thermal data (claim status attached),
    and how it leaves the mold. Natural wax rows link back to their
    waxsupply source; commercial rows carry their own numbers."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # MASTER_MATERIAL_KINDS entry.
        material_kind: str = 'natural-wax',
        # FEEDSTOCK_PRIORITIES entry — 'core' is the local focus.
        priority: str = 'supported',
        # solgel_sourcing ACCESSIBILITY_TIERS vocabulary.
        accessibility_tier: str = 'common-industrial',
        renewable: bool = False,
        # natural waxes: the waxsupply WaxSourceDefinition this rides.
        wax_source_ref: str = '',
        # JSON list of MAKE_ROUTES entries this feedstock supports.
        make_routes_json: str = '[]',
        # --- mechanical/thermal (claim status travels with them) ---
        density_kg_m3: float = 0.0,
        compressive_strength_mpa: float = 0.0,
        # loses structural credibility here (wax: near melt; PLA: Tg).
        soften_temp_c: float = 0.0,
        melt_temp_c: float = 0.0,
        claim_status: str = 'literature-approximate',
        # --- print params for the FDM/auger routes ---
        print_temp_c: float = 0.0,
        nozzle_diameter_mm: float = 0.4,
        layer_height_mm: float = 0.2,
        print_speed_mm_s: float = 30.0,
        # --- the sacrificial exit ---
        removal_route: str = 'melt-out',
        removal_temp_c: float = 0.0,
        removal_notes: str = '',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.material_kind = (material_kind
                              if material_kind in MASTER_MATERIAL_KINDS
                              else 'natural-wax')
        self.priority = (priority if priority in FEEDSTOCK_PRIORITIES
                         else 'supported')
        self.accessibility_tier = accessibility_tier
        self.renewable = renewable
        self.wax_source_ref = wax_source_ref
        self.make_routes_json = make_routes_json
        self.density_kg_m3 = density_kg_m3
        self.compressive_strength_mpa = compressive_strength_mpa
        self.soften_temp_c = soften_temp_c
        self.melt_temp_c = melt_temp_c
        self.claim_status = claim_status
        self.print_temp_c = print_temp_c
        self.nozzle_diameter_mm = nozzle_diameter_mm
        self.layer_height_mm = layer_height_mm
        self.print_speed_mm_s = print_speed_mm_s
        self.removal_route = (removal_route
                              if removal_route in REMOVAL_ROUTES
                              else 'melt-out')
        self.removal_temp_c = removal_temp_c
        self.removal_notes = removal_notes
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id


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
