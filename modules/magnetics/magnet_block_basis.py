"""
@module magnetics.magnet_block_basis

mag-4: SLOT-MATRIX ASSEMBLY AS DATA (Dustin: "configure block sizes
(sometimes varying block sizes in one design) and then 'slot' them
into place to make a matrix that is solidified by a thin sol-gel
mortar which we selectively make to be magnetic or not").

- BlockSizeVariant = the block-geometry vocabulary (MIXED sizes in
  one layout are first-class, like masonry bonds).
- BlockLayoutDefinition + BlockPlacement = the slot grid: each
  placement names its slot (integer x/y/z), its variant, its
  MATERIAL (a Section-A catalog row — theoretical materials ride
  their watermark/gates), optional coil winding, and interlocks.
- JointMortarAssignment = SELECTIVE MORTAR PER JOINT: magnetic
  mortar (flux passes) or plain (flux fence). Field routing is the
  LAYOUT; containment is a boundary course of plain joints.

The reluctance network GENERATES from these rows (magnet_layout) —
mag-3 hand-authored circuits stay possible, the matrix is the
primary authoring surface.

@consumers magnetics.magnet_layout, magnetics.magnet_api,
polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Shape kinds with v1 volume math (magnet_layout refuses others
#: honestly). 'tooth' and 'bearing-seat' compute as bricks.
BLOCK_SHAPE_KINDS = ('brick', 'half-brick', 'tooth', 'wedge',
                     'arc-segment', 'disk-sector', 'bearing-seat')


class BlockSizeVariant(treeObject):
    """One block geometry in the vocabulary. dims_json per shape:
    brick/half-brick/tooth/bearing-seat {x_m, y_m, z_m};
    wedge {x_m, y_m, z_m} (half-brick volume, triangular section);
    arc-segment/disk-sector {r_in_m, r_out_m, angle_deg, thick_m}."""

    @treeObjectInit
    def __init__(self, name='', display_name='', shape_kind='brick',
                 dims_json='{}', interlock_json='[]',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.shape_kind = (shape_kind
                           if shape_kind in BLOCK_SHAPE_KINDS
                           else 'brick')
        self.dims_json = dims_json
        #: JSON list of interlock features ('tongue-x', 'groove-x',
        #: 'dowel-pocket', ...) — dry-fit rigidity BEFORE mortar.
        self.interlock_json = interlock_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class BlockLayoutDefinition(treeObject):
    """One slotted matrix design (2D layers stacked to 3D)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 grid_json='{}', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        #: {'cols': N, 'rows': N, 'layers': N} — documentation of
        #: the intended envelope; placements carry the actual slots.
        self.grid_json = grid_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class BlockPlacement(treeObject):
    """One block slotted into the matrix. slot_json = {'x','y','z'}
    integers; adjacency = unit distance on one axis."""

    @treeObjectInit
    def __init__(self, name='', layout_name='', slot_json='{}',
                 variant_ref='', material_ref='', coil_json='{}',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.layout_name = layout_name
        self.slot_json = slot_json
        #: BlockSizeVariant.name.
        self.variant_ref = variant_ref
        #: MagneticMaterialOption.name — gates/watermarks ride the
        #: catalog row (a theoretical material simulates, refuses
        #: costing).
        self.material_ref = material_ref
        #: Optional winding on THIS block: {'turns': N, 'amps': I}.
        #: v1 rule: a wound block must have exactly TWO magnetic
        #: joints (a limb) — winding a junction block is ambiguous
        #: and refuses honestly.
        self.coil_json = coil_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class JointMortarAssignment(treeObject):
    """The mortar grade of ONE joint (adjacent slot pair) — the
    selective-mortar design knob the solver prices. thickness
    priors ride the §2c tolerance ladder (T0 ~0.5-1 mm cast-as-is,
    T1 ~0.1-0.3 mm lapped) and are ESTIMATES until measured joints
    (calipers, QA dimensional check) replace them."""

    @treeObjectInit
    def __init__(self, name='', layout_name='', from_placement='',
                 to_placement='', mortar_ref='',
                 thickness_m=0.001, contact_area_m2=0.0,
                 thickness_is_estimate=True,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.layout_name = layout_name
        self.from_placement = from_placement
        self.to_placement = to_placement
        #: MagneticMaterialOption.name of the MORTAR (e.g.
        #: opt-solgel-ferrite = flux passes, opt-plain-solgel-mortar
        #: = flux fence).
        self.mortar_ref = mortar_ref
        self.thickness_m = thickness_m
        #: Face contact area; 0.0 = derive from the smaller block
        #: face along the adjacency axis (v1 brick math).
        self.contact_area_m2 = contact_area_m2
        self.thickness_is_estimate = thickness_is_estimate
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ------------------------------------------------------------------ #
# Seeds: one hand-checkable ring — FOUR magnetic-geopolymer bricks
# in a square loop, THREE flux-continuity joints + ONE plain joint
# (the deliberate gap), a 200-turn coil on one limb, and a
# structural bearing-seat block hung off the ring by plain mortar
# (containment in the same masonry). The selftest pins the loop
# flux by hand.
# ------------------------------------------------------------------ #

SEED_BLOCK_VARIANTS = [
    {
        'name': 'brick-40x20x20',
        'display_name': 'Brick 40x20x20 mm',
        'shape_kind': 'brick',
        'dims_json': '{"x_m": 0.04, "y_m": 0.02, "z_m": 0.02}',
        'interlock_json': '["tongue-x", "groove-x"]',
        'is_prior': True, 'provenance_id': 'mag-4',
        'notes': 'The workhorse course brick; tongue/groove along '
                 'x so courses slot rigidly before mortar.',
    },
    {
        'name': 'half-brick-20x20x20',
        'display_name': 'Half brick 20x20x20 mm',
        'shape_kind': 'half-brick',
        'dims_json': '{"x_m": 0.02, "y_m": 0.02, "z_m": 0.02}',
        'interlock_json': '["tongue-x", "groove-x"]',
        'is_prior': True, 'provenance_id': 'mag-4',
        'notes': 'Bond-staggering unit (masonry bonds need halves).',
    },
    {
        'name': 'arc-segment-30deg',
        'display_name': 'Arc segment 30 deg (r 30-50 mm x 20)',
        'shape_kind': 'arc-segment',
        'dims_json': '{"r_in_m": 0.03, "r_out_m": 0.05, '
                     '"angle_deg": 30, "thick_m": 0.02}',
        'interlock_json': '["dowel-pocket"]',
        'is_prior': True, 'provenance_id': 'mag-4',
        'notes': '12 segments close a stator ring — the axial-flux '
                 'tooth course of §2d.',
    },
    {
        'name': 'bearing-seat-20',
        'display_name': 'Bearing seat block (608 pocket)',
        'shape_kind': 'bearing-seat',
        'dims_json': '{"x_m": 0.03, "y_m": 0.03, "z_m": 0.01}',
        'interlock_json': '["dowel-pocket"]',
        'is_prior': True, 'provenance_id': 'mag-4',
        'notes': 'STRUCTURAL variant: holds a 608 bearing (mag-1 '
                 'cited) — positioning rigidity from the same '
                 'masonry that routes flux; pocket bore rides the '
                 '§2c tolerance ladder.',
    },
]

SEED_BLOCK_LAYOUTS = [
    {
        'name': 'ring-core-demo',
        'display_name': 'Four-brick ring core (selective mortar '
                        'demo)',
        'description': 'Four magnetic-geopolymer bricks in a '
                       'square loop: three sol-gel-ferrite joints '
                       '(flux passes) + ONE plain sol-gel joint '
                       '(the deliberate gap) + a coil on one limb '
                       '+ a structural bearing-seat hung off the '
                       'ring by plain mortar. Field routing BY '
                       'CONSTRUCTION, hand-checkable.',
        'grid_json': '{"cols": 2, "rows": 2, "layers": 1}',
        'is_prior': True, 'provenance_id': 'mag-4',
        'notes': 'mag-4 seed; expected loop flux pinned in '
                 'selftest_magnet_layout.',
    },
]

SEED_BLOCK_PLACEMENTS = [
    {'name': 'ring-blk-00', 'layout_name': 'ring-core-demo',
     'slot_json': '{"x": 0, "y": 0, "z": 0}',
     'variant_ref': 'brick-40x20x20',
     'material_ref': 'opt-geopolymer-ferrite',
     'coil_json': '{"turns": 200, "amps": 1.0}',
     'is_prior': True, 'provenance_id': 'mag-4',
     'notes': 'the wound limb (exactly two magnetic joints)'},
    {'name': 'ring-blk-10', 'layout_name': 'ring-core-demo',
     'slot_json': '{"x": 1, "y": 0, "z": 0}',
     'variant_ref': 'brick-40x20x20',
     'material_ref': 'opt-geopolymer-ferrite',
     'coil_json': '{}',
     'is_prior': True, 'provenance_id': 'mag-4', 'notes': ''},
    {'name': 'ring-blk-11', 'layout_name': 'ring-core-demo',
     'slot_json': '{"x": 1, "y": 1, "z": 0}',
     'variant_ref': 'brick-40x20x20',
     'material_ref': 'opt-geopolymer-ferrite',
     'coil_json': '{}',
     'is_prior': True, 'provenance_id': 'mag-4', 'notes': ''},
    {'name': 'ring-blk-01', 'layout_name': 'ring-core-demo',
     'slot_json': '{"x": 0, "y": 1, "z": 0}',
     'variant_ref': 'brick-40x20x20',
     'material_ref': 'opt-geopolymer-ferrite',
     'coil_json': '{}',
     'is_prior': True, 'provenance_id': 'mag-4', 'notes': ''},
    {'name': 'ring-seat', 'layout_name': 'ring-core-demo',
     'slot_json': '{"x": 2, "y": 0, "z": 0}',
     'variant_ref': 'bearing-seat-20',
     'material_ref': 'opt-plain-geopolymer',
     'coil_json': '{}',
     'is_prior': True, 'provenance_id': 'mag-4',
     'notes': 'structural containment IN the masonry — plain '
              'block, plain joint, no flux role'},
]

SEED_JOINT_MORTARS = [
    {'name': 'ring-joint-00-10', 'layout_name': 'ring-core-demo',
     'from_placement': 'ring-blk-00', 'to_placement': 'ring-blk-10',
     'mortar_ref': 'opt-solgel-ferrite', 'thickness_m': 0.001,
     'contact_area_m2': 0.0, 'thickness_is_estimate': True,
     'is_prior': True, 'provenance_id': 'mag-4',
     'notes': 'flux-continuity joint (T0 1 mm prior)'},
    {'name': 'ring-joint-10-11', 'layout_name': 'ring-core-demo',
     'from_placement': 'ring-blk-10', 'to_placement': 'ring-blk-11',
     'mortar_ref': 'opt-solgel-ferrite', 'thickness_m': 0.001,
     'contact_area_m2': 0.0, 'thickness_is_estimate': True,
     'is_prior': True, 'provenance_id': 'mag-4', 'notes': ''},
    {'name': 'ring-joint-11-01', 'layout_name': 'ring-core-demo',
     'from_placement': 'ring-blk-11', 'to_placement': 'ring-blk-01',
     'mortar_ref': 'opt-solgel-ferrite', 'thickness_m': 0.001,
     'contact_area_m2': 0.0, 'thickness_is_estimate': True,
     'is_prior': True, 'provenance_id': 'mag-4', 'notes': ''},
    {'name': 'ring-joint-01-00', 'layout_name': 'ring-core-demo',
     'from_placement': 'ring-blk-01', 'to_placement': 'ring-blk-00',
     'mortar_ref': 'opt-plain-solgel-mortar', 'thickness_m': 0.001,
     'contact_area_m2': 0.0, 'thickness_is_estimate': True,
     'is_prior': True, 'provenance_id': 'mag-4',
     'notes': 'THE DELIBERATE GAP: plain mortar = flux fence — '
              'selective mortar is the design language'},
    {'name': 'ring-joint-seat', 'layout_name': 'ring-core-demo',
     'from_placement': 'ring-blk-10', 'to_placement': 'ring-seat',
     'mortar_ref': 'opt-plain-solgel-mortar', 'thickness_m': 0.001,
     'contact_area_m2': 0.0, 'thickness_is_estimate': True,
     'is_prior': True, 'provenance_id': 'mag-4',
     'notes': 'structural attachment, magnetically a fence'},
]
