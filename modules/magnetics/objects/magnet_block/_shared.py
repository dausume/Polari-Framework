"""@module magnetics.objects.magnet_block._shared — what the magnet_block row classes share (constants, seeds, helpers); split from magnet_block_basis.py (sap-2c)."""

BLOCK_SHAPE_KINDS = ('brick', 'half-brick', 'tooth', 'wedge',
                     'arc-segment', 'disk-sector', 'bearing-seat')
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
