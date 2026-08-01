"""
@module motors.motor_shapes

mag-7b: THE M0 MOTOR AS MATH SHAPES (Dustin 2026-07-29: "make math
shapes for each of the different parts we need, and be able to
watch the full 3D simulation with the actual flip occurring from
the AC being visible").

Every physical part of the Lavet clock stepper is a
MathShapeDefinition row — the same rows the wax-mold/CAD seam
prints and casts from, so the 3D view and the buildable sample
share ONE geometry source (object coherence). Units: cm, matching
the shape module's demo convention. The rotor group (disc +
pointer bar + N-cap) rotates as one body in the viewer; the coil
ring is a CSG cylinder shell; the AC flip renders as the coil's
polarity material swap + the field vector through its bore
reversing each pulse.

Plain dicts only — importable whether or not mathshapes is enabled;
polariServer appends these to the MathShapeDefinition seed list,
which is itself gated on the mathshapes module.
"""

import json

PROV = 'mag-7b'

#: ------------------------------------------------------------
#: TWO GEOMETRIES, AND THE ROWS SAY WHICH IS WHICH.
#:
#: The set below is the SCHEMATIC M0: two separate pole shoes, a
#: coil off to one side, a disc rotor with a pointer. It reads
#: clearly and it animates the physics — but Dustin looked up
#: photographs of a real Lavet motor and it "looked nothing like
#: it", which is correct and worth stating rather than defending.
#: It is an idealised diagram of the flux path, not the machine.
#:
#: SEED_LAVET_PART_SHAPES further down is the REALISTIC one, built
#: to how the actual device is made. Both stay: the schematic is
#: better for seeing WHY it steps, the realistic one is what you
#: would recognise on a bench. Same precedent as keeping the 2D
#: card alongside the 3D.
#: ------------------------------------------------------------
SEED_MOTOR_PART_SHAPES = [
    # cap_base/cap_top: these cylinders are SOLIDS — without end caps
    # the mesher's lateral-only default made the disc read as an open
    # band in the viewer (the mag-7b gap, closed 2026-07-30).
    {'name': 'motor-m0-rotor-disc',
     'display_name': 'M0 rotor disc (bonded hexaferrite)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 3.0, 'height': 0.8, 'axis': 'z',
          'center': [0.0, 0.0, 0.0],
          'cap_base': True, 'cap_top': True}),
     'notes': 'The 6 mm-class rotor scaled to the demo scene '
              '(cm units); casts from this exact math shape.',
     'provenance_id': PROV},
    {'name': 'motor-m0-rotor-pointer',
     'display_name': 'M0 rotor orientation pointer (N bar)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [0.5, 2.6, 0.35],
          'center': [0.0, 1.4, 0.6]}),
     'notes': 'Rides the rotor group — the visible orientation '
              'body the vector overlay tracks.',
     'provenance_id': PROV},
    {'name': 'motor-m0-shaft',
     'display_name': 'M0 shaft',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 0.35, 'height': 3.0, 'axis': 'z',
          'center': [0.0, 0.0, 0.2],
          'cap_base': True, 'cap_top': True}),
     'provenance_id': PROV},
    {'name': 'motor-m0-pole-left',
     'display_name': 'M0 stator pole shoe (left)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [1.4, 4.6, 1.2], 'center': [-4.2, 0.0, 0.0]}),
     'notes': 'Cast magnetic-geopolymer pole shoe; the asymmetric '
              'notch is a casting detail below this demo scale.',
     'provenance_id': PROV},
    {'name': 'motor-m0-pole-right',
     'display_name': 'M0 stator pole shoe (right)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [1.4, 4.6, 1.2], 'center': [4.2, 0.0, 0.0]}),
     'provenance_id': PROV},
    # coil ring = CSG shell (outer minus bore), axis y so the bore
    # points at the rotor from below.
    {'name': 'motor-m0-coil-outer',
     'display_name': 'M0 coil outer (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.6, 'height': 1.4, 'axis': 'y',
          'center': [0.0, -5.6, 0.0],
          'cap_base': True, 'cap_top': True}),
     'provenance_id': PROV},
    {'name': 'motor-m0-coil-bore',
     'display_name': 'M0 coil bore (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 0.9, 'height': 1.8, 'axis': 'y',
          'center': [0.0, -5.6, 0.0]}),
     'provenance_id': PROV},
    {'name': 'motor-m0-coil-ring',
     'display_name': 'M0 coil (1500-turn winding body)',
     'family': 'csg',
     'csg_json': json.dumps(
         {'op': 'difference',
          'shapes': ['motor-m0-coil-outer', 'motor-m0-coil-bore']}),
     'bounds_json': json.dumps(
         [[-1.8, 1.8], [-6.5, -4.7], [-1.8, 1.8]]),
     'notes': 'The winding as a shell — the AC flip renders as '
              'this part\'s polarity material swap + the bore '
              'field vector reversing.',
     'provenance_id': PROV},
]

#: mag-7 remainder (2026-07-30): the assembled M0 motor as a PROPER
#: SimSpaceDefinition row — scene = data, not a blob hard-coded in
#: the Angular component. freestandingOnly (curated shelf, the
#: demo-3d lesson: without it every defaultVisible binding pours in).
#: The motor page fetches this row's snapshot, then drives the rotor
#: entries' transforms from the clock-sim replay — layout from the
#: row, motion from the solver. The coil entry references the CSG
#: RING (triangulated via the coaxial-tube mesher this same pass),
#: not the solid outer stand-in.
SEED_MOTOR_SIM_SPACES = [
    {'name': 'motor-m0-viz',
     'description': 'M0 Lavet clock stepper, assembled: every part '
                    'a MathShapeDefinition row (the same geometry '
                    'the wax-mold seam casts). The motor page '
                    'replays the solver history through this '
                    'scene — rotor rotation + coil polarity are '
                    'runtime transforms, never baked in.',
     'dimensionality': '3d',
     'coordinate_system': 'math',
     'unit_scale': 1.0,
     'viewport_json': json.dumps(
         {'center': [0, -1.5, 0], 'extent': [7, 8, 5]}),
     'bound_classes_json': '[]',
     'definition': json.dumps({
         'freestandingOnly': True,
         'freestanding': [
             {'id': 'pole-left',
              'shapeRef': 'mathshape:motor-m0-pole-left',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'pole-right',
              'shapeRef': 'mathshape:motor-m0-pole-right',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'coil',
              'shapeRef': 'mathshape:motor-m0-coil-ring',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'shaft',
              'shapeRef': 'mathshape:motor-m0-shaft',
              'styleRef': 'motor-shaft-steel',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-disc',
              'shapeRef': 'mathshape:motor-m0-rotor-disc',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-pointer',
              'shapeRef': 'mathshape:motor-m0-rotor-pointer',
              'styleRef': 'motor-pointer-red',
              'position': [0.0, 0.0, 0.0]},
         ]}),
     'axis_labels_json': '{}',
     'camera_json': '',
     'category': 'motors',
     'owning_module': 'motors'},
]

SEED_MOTOR_MATERIALS_3D = [
    {'name': 'motor-part-gray',
     'description': 'Stator pole shoes (cast magnetic geopolymer).',
     'material_type': 'standard', 'color': '#8a8f98',
     'metalness': 0.1, 'roughness': 0.85},
    {'name': 'motor-rotor-dark',
     'description': 'Rotor disc (bonded hexaferrite).',
     'material_type': 'standard', 'color': '#3a3f4a',
     'metalness': 0.2, 'roughness': 0.7},
    {'name': 'motor-pointer-red',
     'description': 'Rotor orientation pointer.',
     'material_type': 'standard', 'color': '#d33340',
     'metalness': 0.0, 'roughness': 0.6},
    {'name': 'motor-shaft-steel',
     'description': 'Shaft (8 mm rod, mag-1 cited).',
     'material_type': 'standard', 'color': '#c8cdd4',
     'metalness': 0.8, 'roughness': 0.35},
    {'name': 'motor-coil-idle',
     'description': 'Coil at rest (enameled copper).',
     'material_type': 'standard', 'color': '#b0722d',
     'metalness': 0.5, 'roughness': 0.5},
    {'name': 'motor-coil-pos',
     'description': 'Coil during a +polarity pulse.',
     'material_type': 'standard', 'color': '#2fa84a',
     'metalness': 0.5, 'roughness': 0.5},
    {'name': 'motor-coil-neg',
     'description': 'Coil during a −polarity pulse.',
     'material_type': 'standard', 'color': '#d69422',
     'metalness': 0.5, 'roughness': 0.5},
]

#: ------------------------------------------------------------
#: THE REALISTIC LAVET-TYPE STEPPING MOTOR (mag-10)
#:
#: What a quartz-clock motor actually is, and why the schematic
#: above misleads:
#:   - ONE flat stamped soft-iron stator plate, not two floating
#:     pole shoes;
#:   - a circular BORE through that plate holding the rotor;
#:   - two NOTCHES in the bore wall, offset from the coil axis —
#:     these create the detent positions, and their asymmetry is
#:     what makes the rotor always step the SAME WAY rather than
#:     rocking. This is the whole trick of the design;
#:   - two narrow SATURABLE NECKS in the plate that shape the flux
#:     path around the bore;
#:   - a coil on a bobbin around a core leg joined to the plate;
#:   - a rotor that is a tiny DIAMETRICALLY-MAGNETISED CYLINDER
#:     (~1.5-2 mm across), not a disc with a pointer;
#:   - a PINION on the rotor shaft that drives the gear train —
#:     which is exactly the clock-train-m0 reduction in the gears
#:     module (8t pinion -> 240t seconds wheel = 30:1).
#:
#: Units: 1 unit = 1 mm, matching the schematic set. Real device
#: dimensions, so the pinion and the seconds wheel are at their
#: TRUE relative size — the wheel really is ~30x the pinion, and
#: seeing that is half of understanding why clocks are mostly gear.
#: ------------------------------------------------------------
SEED_LAVET_PART_SHAPES = [
    {'name': 'motor-m0r-stator-blank',
     'display_name': 'Lavet stator plate (blank, CSG component)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [22.0, 13.0, 1.2], 'center': [0.0, 0.0, 0.0]}),
     'notes': 'Flat stamped soft-iron plate — ONE piece. The bore '
              'and notches are cut from it below.',
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-bore',
     'display_name': 'Lavet stator bore (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.35, 'height': 2.0, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-stator',
     'display_name': 'Lavet stator plate (bored)',
     'family': 'csg',
     'csg_json': json.dumps(
         {'op': 'difference',
          'shapes': ['motor-m0r-stator-blank', 'motor-m0r-bore']}),
     'bounds_json': json.dumps(
         [[-11.5, 11.5], [-7.0, 7.0], [-1.0, 1.0]]),
     'notes': 'Plate minus bore. Renders through the voxel-face '
              'mesher (blocky, and the method string says so) — '
              'the notches and saturable necks are stamped detail '
              'below this mesh resolution and are documented on '
              'the design row rather than faked in geometry.',
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-rotor',
     'display_name': 'Lavet rotor (diametrically-magnetised '
                     'cylinder, 2.0 mm)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.0, 'height': 2.2, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'notes': 'THE correction to the schematic: a real Lavet rotor '
              'is this small, and it is magnetised ACROSS its '
              'diameter (N one side, S the other) — not a disc '
              'with a pointer.',
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-rotor-north',
     'display_name': 'Lavet rotor N half (orientation marker)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [0.9, 1.8, 2.3], 'center': [0.45, 0.0, 0.0]}),
     'notes': 'Viz only: marks which side of the diametric magnet '
              'is north so the step is visible. Not a part.',
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-shaft',
     'display_name': 'Lavet rotor shaft',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 0.25, 'height': 8.0, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-pinion',
     'display_name': 'Rotor pinion (8 teeth, module 0.3 -> 2.4 mm '
                     'pitch dia)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.2, 'height': 1.0, 'axis': 'z',
          'center': [0.0, 0.0, 2.6], 'cap_base': True,
          'cap_top': True}),
     'notes': 'Pitch CYLINDER, teeth not rendered — gear tooth '
              'geometry is generated by gears gr-3, and drawing '
              'fake teeth here would be the exact "close enough '
              'gear" mistake the mesh catalog refuses. Its 8 teeth '
              'at module 0.3 are the clock-train-m0 input.',
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-core-leg',
     'display_name': 'Coil core leg (joins the plate)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 0.8, 'height': 9.0, 'axis': 'x',
          'center': [-14.5, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-coil-outer',
     'display_name': 'Lavet coil outer (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 2.6, 'height': 7.0, 'axis': 'x',
          'center': [-14.5, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-coil-bore',
     'display_name': 'Lavet coil bore (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 0.85, 'height': 7.4, 'axis': 'x',
          'center': [-14.5, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-coil',
     'display_name': 'Lavet coil (1500 turns of 44 AWG, mag-9)',
     'family': 'csg',
     'csg_json': json.dumps(
         {'op': 'difference',
          'shapes': ['motor-m0r-coil-outer',
                     'motor-m0r-coil-bore']}),
     'bounds_json': json.dumps(
         [[-18.2, -10.8], [-2.8, 2.8], [-2.8, 2.8]]),
     'notes': 'Coaxial-cylinder difference => the EXACT parametric '
              'tube mesh. Its bobbin window is the 12 mm2 the mag-9 '
              'winding check judges, so this body and that report '
              'describe the same object.',
     'provenance_id': 'mag-10'},
    {'name': 'motor-m0r-seconds-wheel',
     'display_name': 'Seconds wheel (240 teeth, 72 mm pitch dia) — '
                     'TRUE relative size',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 36.0, 'height': 0.6, 'axis': 'z',
          'center': [37.2, 0.0, 2.6], 'cap_base': True,
          'cap_top': True}),
     'notes': 'Placed at the true centre distance (1.2 + 36 = 37.2 '
              'mm) so the 30:1 stage is shown at REAL scale. This '
              'is why clocks are mostly gear: one 30:1 stage in a '
              'single step is enormous, which is exactly why real '
              'movements split it across several small ones — the '
              'honest lesson the picture teaches.',
     'provenance_id': 'mag-10'},
]

#: The realistic assembly as a scene row, alongside (not instead
#: of) the schematic motor-m0-viz.
SEED_LAVET_SIM_SPACES = [
    {'name': 'motor-m0-lavet-viz',
     'description': 'The M0 rung as a REAL Lavet-type stepping '
                    'motor: one bored stator plate, a 2 mm '
                    'diametric rotor, the coil on its core leg, '
                    'and the rotor pinion meshing its 240-tooth '
                    'seconds wheel at TRUE relative scale. The '
                    'schematic scene (motor-m0-viz) shows why it '
                    'steps; this one shows what it is.',
     'dimensionality': '3d', 'coordinate_system': 'math',
     'unit_scale': 1.0,
     'viewport_json': json.dumps(
         {'center': [12.0, 0.0, 0.0], 'extent': [90.0, 80.0, 20.0]}),
     'bound_classes_json': '[]',
     'definition': json.dumps({
         'freestandingOnly': True,
         'freestanding': [
             {'id': 'stator',
              'shapeRef': 'mathshape:motor-m0r-stator',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'core-leg',
              'shapeRef': 'mathshape:motor-m0r-core-leg',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'coil',
              'shapeRef': 'mathshape:motor-m0r-coil',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'shaft',
              'shapeRef': 'mathshape:motor-m0r-shaft',
              'styleRef': 'motor-shaft-steel',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor',
              'shapeRef': 'mathshape:motor-m0r-rotor',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-north',
              'shapeRef': 'mathshape:motor-m0r-rotor-north',
              'styleRef': 'motor-pointer-red',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'pinion',
              'shapeRef': 'mathshape:motor-m0r-pinion',
              'styleRef': 'motor-shaft-steel',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'seconds-wheel',
              'shapeRef': 'mathshape:motor-m0r-seconds-wheel',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
         ]}),
     'axis_labels_json': '{}', 'camera_json': '',
     'category': 'motors', 'owning_module': 'motors'},
]

#: ------------------------------------------------------------
#: LAVET v2 (mag-10b) — built from Dustin's reference photographs
#: (Prof MAD, "Lavet type stepper motor in clock").
#:
#: v1 was still wrong in four specific ways, each visible in the
#: reference and each fixed here:
#:   1. STATOR SHAPE. v1 was a plain slab with a centred hole. The
#:      real part is a squared-C BRACKET: a plate with a large
#:      rectangular window cut out of it, and the rotor bore at
#:      ONE END, joined to that window by a narrow neck. The
#:      window and neck are not decoration — they are what forces
#:      the flux around the rotor instead of straight across.
#:   2. COIL SIZE AND FORM. v1 had a small ring on a leg. The real
#:      coil is a BIG flanged bobbin — a thread-spool — lying
#:      alongside the stator, comparable in length to the plate
#:      itself, with two lead wires off the top.
#:   3. ROTOR. v1 was a bare cylinder. The real rotor is a stepped
#:      part: the magnet cylinder below, an integrated PINION
#:      above, and an index mark on top.
#:   4. LAYOUT. v1 centred everything. The real device puts the
#:      rotor at one END and the coil at the other, both on the
#:      same flat plate.
#:
#: Teeth are still NOT drawn on the pinion. The reference clearly
#: shows them, and it is still the right call: gear geometry is
#: GENERATED (gears gr-3), and modelling decorative teeth that
#: mesh with nothing is exactly the "close enough gear" mistake
#: the mesh-asset catalog refuses. The pitch cylinder is honest
#: about being a pitch cylinder.
#:
#: Units: 1 unit = 1 mm.
#: ------------------------------------------------------------
SEED_LAVET_V2_PART_SHAPES = [
    {'name': 'motor-m0v2-plate-blank',
     'display_name': 'v2 stator plate blank (CSG component)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [26.0, 14.0, 1.2], 'center': [0.0, 0.0, 0.0]}),
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-plate-window',
     'display_name': 'v2 stator window (CSG component)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [17.0, 6.0, 3.0], 'center': [2.5, 0.0, 0.0]}),
     'notes': 'The big rectangular cut-out that makes the plate a '
              'squared C — clearly visible in the reference.',
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-plate-bore',
     'display_name': 'v2 rotor bore (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 2.6, 'height': 3.0, 'axis': 'z',
          'center': [-9.5, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'notes': 'At the LEFT END of the plate, as in the reference — '
              'not centred.',
     'provenance_id': 'mag-10b'},
    # ws-2 (Dustin): the real Lavet has an AIR GAP opening the bore
    # to the LEFT of the rotor — the asymmetry that offsets the
    # detent position so the pulsed field always flips the rotor the
    # same way. The old model only bored a hole; a symmetric bore
    # would leave the rotor with no preferred flip direction.
    {'name': 'motor-m0v2-gap-slot',
     'display_name': 'v2 stator air-gap slot (CSG component)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [2.6, 1.4, 3.0], 'center': [-12.3, 0.0, 0.0]}),
     'notes': 'Cuts from the rotor bore through the left plate '
              'edge — the working asymmetry of the Lavet stator.',
     'provenance_id': 'ws-2'},
    {'name': 'motor-m0v2-stator',
     'display_name': 'Lavet v2 stator (C-bracket plate, bored, '
                     'gapped)',
     'family': 'csg',
     'csg_json': json.dumps(
         {'op': 'difference',
          'shapes': ['motor-m0v2-plate-blank',
                     'motor-m0v2-plate-window',
                     'motor-m0v2-plate-bore',
                     'motor-m0v2-gap-slot']}),
     'bounds_json': json.dumps(
         [[-13.5, 13.5], [-7.5, 7.5], [-1.0, 1.0]]),
     'notes': 'Plate MINUS window MINUS bore MINUS the left air-gap '
              'slot — the gap is the Lavet asymmetry that makes the '
              'flip directional, not a drawing choice. Renders '
              'through the voxel-face mesher, blocky and labelled '
              'so.',
     'provenance_id': 'mag-10b'},
    # --- the big flanged bobbin, the reference\'s most obvious
    # --- correction to v1
    {'name': 'motor-m0v2-coil-outer',
     'display_name': 'v2 coil winding outer (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 3.4, 'height': 13.0, 'axis': 'x',
          'center': [4.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-coil-bore',
     'display_name': 'v2 coil bore (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.1, 'height': 13.6, 'axis': 'x',
          'center': [4.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-coil',
     'display_name': 'Lavet v2 coil winding (the spool body)',
     'family': 'csg',
     'csg_json': json.dumps(
         {'op': 'difference',
          'shapes': ['motor-m0v2-coil-outer',
                     'motor-m0v2-coil-bore']}),
     'bounds_json': json.dumps(
         [[-3.0, 11.0], [-3.6, 3.6], [-3.6, 3.6]]),
     'notes': 'Coaxial difference => the EXACT tube mesh. Big, '
              'like the reference: 13 mm long against a 26 mm '
              'plate, not the small ring v1 had.',
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-bobbin-flange-a',
     'display_name': 'v2 bobbin flange (rotor side)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 4.0, 'height': 0.7, 'axis': 'x',
          'center': [-2.7, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-bobbin-flange-b',
     'display_name': 'v2 bobbin flange (far side)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 4.0, 'height': 0.7, 'axis': 'x',
          'center': [10.7, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-lead-a',
     'display_name': 'v2 coil lead wire A',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 0.22, 'height': 7.0, 'axis': 'z',
          'center': [-1.5, 0.0, 6.5], 'cap_base': True,
          'cap_top': True}),
     'notes': 'The two leads rising off the bobbin — small, but '
              'they are the first thing you see in the reference '
              'and they say which end is electrical.',
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-lead-b',
     'display_name': 'v2 coil lead wire B',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 0.22, 'height': 7.0, 'axis': 'z',
          'center': [9.5, 0.0, 6.5], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-10b'},
    # --- the stepped rotor: magnet below, pinion above ---
    {'name': 'motor-m0v2-rotor-magnet',
     'display_name': 'v2 rotor magnet (diametric cylinder)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 2.1, 'height': 2.4, 'axis': 'z',
          'center': [-9.5, 0.0, -0.2], 'cap_base': True,
          'cap_top': True}),
     'notes': 'Sits IN the bore. Magnetised across its diameter — '
              'the A/B reference frames show exactly this flipping '
              'with the alternating pulse.',
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-rotor-pinion',
     'display_name': 'v2 rotor pinion (pitch cylinder, 8t @ m0.3)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 1.2, 'height': 1.6, 'axis': 'z',
          'center': [-9.5, 0.0, 1.8], 'cap_base': True,
          'cap_top': True}),
     'notes': 'Integrated above the magnet, as the reference '
              'shows. PITCH cylinder only — the involute teeth '
              'come from gears gr-3; decorative teeth that mesh '
              'with nothing would be the mistake the mesh-asset '
              'catalog exists to refuse.',
     'provenance_id': 'mag-10b'},
    {'name': 'motor-m0v2-rotor-index',
     'display_name': 'v2 rotor index mark (N side)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [1.9, 0.45, 0.3], 'center': [-8.6, 0.0, 2.7]}),
     'notes': 'The little scribe on the rotor top in the '
              'reference — viz only, and it is what makes the '
              '180 deg step legible.',
     'provenance_id': 'mag-10b'},
    # ws-2: the ACTUAL winding — a math object (mathshapes family
    # 'winding'), not a solid. Tunables are the coil's real
    # as-built numbers: 1500 turns of 44 AWG (bare 0.0503 mm +
    # 0.025 enamel build, motor_winding's own constants) on the
    # 1.1 mm bore over the 13 mm window, leads exiting downward.
    # render_wire_scale is DISPLAY-ONLY and says so in the payload.
    {'name': 'motor-m0v2-winding',
     'display_name': 'v2 coil winding (the wire itself)',
     'family': 'winding',
     'parameters_json': json.dumps(
         {'center': [4.0, 0.0, 0.0], 'axis': [1.0, 0.0, 0.0],
          'exit_dir': [0.0, -1.0, 0.0],
          'bore_radius': 1.1,
          'wire_diameter': 0.0753,
          'turns': 1500, 'window_length': 13.0,
          'render_wire_scale': 6.0,
          'samples_per_turn': 16, 'n_ring': 5}),
     'notes': 'The observable winding: world points from the ws-1 '
              'matrix equation; decimation and wire-scale are '
              'display knobs whose values ride the method string. '
              'The equation is never decimated.',
     'provenance_id': 'ws-2'},
    # ws-4: the COUPLED family — nothing below states a size the
    # winding already implies. Modulate the winding (turns,
    # fineness) and the spool flanges + the follower gear rescale
    # on the next read: the engine-scale cascade as data.
    {'name': 'motor-m0v2-spool',
     'display_name': 'v2 spool (barrel + flanges, follows the '
                     'winding)',
     'family': 'spool',
     'parameters_json': json.dumps(
         {'winding_ref': 'motor-m0v2-winding',
          'barrel_wall': 0.35,
          'flange_thickness': 0.7,
          'flange_clearance': 2.22}),
     'notes': 'Barrel bore = the winding bore; window = the '
              'winding window; flange radius = wound OUTER radius '
              '+ clearance. A winding that overflows the flange '
              'REFUSES. turnCapacity/utilization are derived '
              'facts, not assertions.',
     'provenance_id': 'ws-4'},
    {'name': 'motor-m0v2-pinion-coupled',
     'display_name': 'v2 pinion envelope (follows the spool scale)',
     'family': 'derived-cylinder',
     'parameters_json': json.dumps(
         {'ref': 'motor-m0v2-spool',
          'radius_from': 'flangeRadius', 'radius_ratio': 0.3,
          'height': 1.6, 'axis': 'z',
          'center': [-9.5, 0.0, 1.8]}),
     'notes': 'The toothless ENVELOPE follower (kept as the '
              'generic cascade demo); the real toothed pinion is '
              'motor-m0v2-pinion-gear.',
     'provenance_id': 'ws-4'},
    # gr-3 (Dustin 2026-08-01): the gear with REAL, TUNABLE teeth.
    # The rotor is TWO materials doing opposite jobs: the magnetic
    # BACK (lavet-v2-rotor-magnet, torque-magnet-active) and this
    # gear, which must be field-inert and wear-optimized (the
    # colliding role — hardness, mag-16/17). They join at the
    # ifm0-rotor-shaft interface: press-fit on the arbor (separable,
    # as seeded) or a sol-gel bond (the promotion op, which trades
    # the joint's fretting for bulk brittleness). WELDING is the
    # option that does NOT work here: hard ferrite is a ceramic and
    # heat near the join degrades magnetization — magnetize AFTER
    # any hot process (the mag-22 route already orders it so).
    {'name': 'motor-m0v2-pinion-gear',
     'display_name': 'v2 pinion gear (8 involute teeth, follows '
                     'the spool)',
     'family': 'gear',
     'parameters_json': json.dumps(
         {'ref': 'motor-m0v2-spool',
          'radius_from': 'flangeRadius', 'radius_ratio': 0.3,
          'teeth': 8, 'pressure_angle_deg': 20.0,
          'profile_shift': 0.55, 'addendum_coeff': 0.6,
          'dedendum_coeff': 1.25,
          'face_width': 1.6, 'bore_radius': 0.25,
          'center': [-9.5, 0.0, 1.8], 'axis': 'z'}),
     'notes': 'Pitch radius follows the cascade (flangeRadius x '
              '0.3 -> module derives); 8 teeth need profile shift '
              '0.55 against undercut and a shortened addendum '
              'against tip sharpening — both coherence-checked. '
              'Cycloidal (the horological low-count profile) '
              'remains a named seam.',
     'provenance_id': 'gr-3'},
]


def seed_v2_shapes(manager):
    """ws-2: the v2 shape rows ride the UPSERT path — the stator
    csg change (air-gap slot) and any tuning of the winding row
    must REACH live rows, not strike the seed-field gotcha an
    11th time."""
    from composition.seed_upsert import upsert_seed_pairs
    from mathshapes.shape_basis import MathShapeDefinition
    return upsert_seed_pairs(
        manager,
        [('MathShapeDefinition', MathShapeDefinition,
          SEED_LAVET_V2_PART_SHAPES)],
        tag='V2ShapeSeed')


SEED_LAVET_V2_SIM_SPACES = [
    {'name': 'motor-m0-lavet-v2-viz',
     'description': 'Lavet-type stepping motor, v2 — modelled from '
                    'reference photographs: a squared-C stator '
                    'plate with the rotor bore at one end, the big '
                    'flanged coil bobbin alongside with its two '
                    'leads, and the stepped rotor (diametric '
                    'magnet + integrated pinion + index mark). The '
                    'rotor group turns from the clock-sim replay.',
     'dimensionality': '3d', 'coordinate_system': 'math',
     'unit_scale': 1.0,
     'viewport_json': json.dumps(
         {'center': [0.0, 0.0, 1.0], 'extent': [34.0, 22.0, 16.0]}),
     'bound_classes_json': '[]',
     'definition': json.dumps({
         'freestandingOnly': True,
         'freestanding': [
             {'id': 'stator',
              'shapeRef': 'mathshape:motor-m0v2-stator',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'bobbin-flange-a',
              'shapeRef': 'mathshape:motor-m0v2-bobbin-flange-a',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'bobbin-flange-b',
              'shapeRef': 'mathshape:motor-m0v2-bobbin-flange-b',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'coil',
              'shapeRef': 'mathshape:motor-m0v2-coil',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'lead-a',
              'shapeRef': 'mathshape:motor-m0v2-lead-a',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'lead-b',
              'shapeRef': 'mathshape:motor-m0v2-lead-b',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-magnet',
              'shapeRef': 'mathshape:motor-m0v2-rotor-magnet',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-pinion',
              'shapeRef': 'mathshape:motor-m0v2-rotor-pinion',
              'styleRef': 'motor-shaft-steel',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-index',
              'shapeRef': 'mathshape:motor-m0v2-rotor-index',
              'styleRef': 'motor-pointer-red',
              'position': [0.0, 0.0, 0.0]},
         ]}),
     'axis_labels_json': '{}', 'camera_json': '',
     'category': 'motors', 'owning_module': 'motors'},
]

#: ------------------------------------------------------------
#: M1 — 6-SLOT / 4-POLE RADIAL RELUCTANCE (mag-12)
#:
#: The no-permanent-magnet rung: torque comes from SALIENCY alone.
#: The rotor has 4 lumps and 4 gaps, so the magnetic circuit's
#: reluctance depends on rotor angle; energising a stator tooth
#: pulls the nearest rotor pole toward alignment. There is nothing
#: magnetised anywhere in this machine — which is exactly why every
#: material in it is costed TODAY, and why it is the honest first
#: rung after the clock.
#:
#: Geometry from the seeded design's own params_json:
#:   6 slots, 4 poles, gap 0.6 mm, tooth face 4e-5 m2 = 40 mm2
#:   (here 6.0 mm tangential x 6.7 mm axial = 40.2 mm2), 300 turns.
#:
#: ONE tooth row placed SIX times by scene rotation, one pole row
#: placed FOUR times — the array is in the scene, not in 14 nearly
#: identical shape rows. Rotation is about the world origin, which
#: is why every arrayed part is authored on the +X axis.
#:
#: UNITS: 1 unit = 1 mm, as with the Lavet sets. mathshapes'
#: shape_properties reports volumeCm3 (it assumes cm), so any part
#: row pointing here MUST carry shape_units='mm' or a 40 mm2 tooth
#: silently becomes a 40 cm2 one.
#: ------------------------------------------------------------
SEED_M1_PART_SHAPES = [
    {'name': 'motor-m1-shaft',
     'display_name': 'M1 shaft (8 mm, mag-1 cited stock)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 4.0, 'height': 34.0, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'notes': 'Matches the 8 mm rod cited in mag-1, so the bill '
              'and the shopping list describe one object.',
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-rotor-core',
     'display_name': 'M1 rotor core (the hub the poles stand on)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 6.0, 'height': 6.7, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-rotor-pole',
     'display_name': 'M1 rotor salient pole (x4 by rotation)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [6.0, 6.0, 6.7], 'center': [9.0, 0.0, 0.0]}),
     'notes': 'Spans radius 6.0 to 12.0 mm. FOUR of these, 90 deg '
              'apart, are the whole torque mechanism: the lumps '
              'want to line up with an energised tooth, and the '
              'gaps between them are what makes lining up mean '
              'something.',
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-stator-tooth',
     'display_name': 'M1 stator tooth (x6 by rotation)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [7.4, 6.0, 6.7], 'center': [16.3, 0.0, 0.0]}),
     'notes': 'Face sits at radius 12.6 mm — 0.6 mm clear of the '
              'rotor pole tip, which IS the gap_base_m the solver '
              'uses. Face area 6.0 x 6.7 = 40.2 mm2, the design\'s '
              'tooth_area_m2 of 4e-5.',
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-yoke-outer',
     'display_name': 'M1 stator yoke outer (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 24.0, 'height': 6.7, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-yoke-bore',
     'display_name': 'M1 stator yoke bore (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 20.0, 'height': 7.2, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-yoke',
     'display_name': 'M1 stator yoke (back-iron ring)',
     'family': 'csg',
     'csg_json': json.dumps(
         {'op': 'difference',
          'shapes': ['motor-m1-yoke-outer', 'motor-m1-yoke-bore']}),
     'bounds_json': json.dumps(
         [[-24.5, 24.5], [-24.5, 24.5], [-3.8, 3.8]]),
     'notes': 'Coaxial-cylinder difference, so it gets the EXACT '
              'parametric tube mesh rather than the blocky voxel '
              'fallback. Its job is the return path: flux leaving '
              'one tooth has to get back to another, and this ring '
              'is that road.',
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-coil-outer',
     'display_name': 'M1 phase coil outer (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 6.5, 'height': 6.0, 'axis': 'x',
          'center': [16.3, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-coil-bore',
     'display_name': 'M1 phase coil bore (CSG component)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 5.0, 'height': 6.4, 'axis': 'x',
          'center': [16.3, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-12'},
    {'name': 'motor-m1-coil',
     'display_name': 'M1 phase coil (300 t, 26 AWG) (x6 by '
                     'rotation)',
     'family': 'csg',
     'csg_json': json.dumps(
         {'op': 'difference',
          'shapes': ['motor-m1-coil-outer', 'motor-m1-coil-bore']}),
     'bounds_json': json.dumps(
         [[13.0, 19.6], [-6.9, 6.9], [-6.9, 6.9]]),
     'notes': 'Wraps its tooth (bore 5.0 mm clears the tooth\'s '
              '4.5 mm half-diagonal). Six of them, wired A-B-C-A-'
              'B-C, are the three phases; the mag-9 winding check '
              'judges 300 turns of 26 AWG in the design\'s stated '
              '72 mm2 window.',
     'provenance_id': 'mag-12'},
]

SEED_M1_SIM_SPACES = [
    {'name': 'motor-m1-viz',
     'description': 'M1 6-slot/4-pole radial reluctance motor: a '
                    'salient 4-pole rotor inside 6 wound stator '
                    'teeth on a ring yoke. No magnets anywhere — '
                    'the torque is saliency, the rotor lumps '
                    'wanting to line up with whichever tooth is '
                    'energised. Teeth and poles are ONE shape row '
                    'each, arrayed by scene rotation.',
     'dimensionality': '3d', 'coordinate_system': 'math',
     'unit_scale': 1.0,
     'viewport_json': json.dumps(
         {'center': [0.0, 0.0, 0.0], 'extent': [60.0, 60.0, 40.0]}),
     'bound_classes_json': '[]',
     'definition': json.dumps({
         'freestandingOnly': True,
         'freestanding': [
             {'id': 'shaft',
              'shapeRef': 'mathshape:motor-m1-shaft',
              'styleRef': 'motor-shaft-steel',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-core',
              'shapeRef': 'mathshape:motor-m1-rotor-core',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-pole-0',
              'shapeRef': 'mathshape:motor-m1-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.0]},
             {'id': 'rotor-pole-1',
              'shapeRef': 'mathshape:motor-m1-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 1.570796]},
             {'id': 'rotor-pole-2',
              'shapeRef': 'mathshape:motor-m1-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.141593]},
             {'id': 'rotor-pole-3',
              'shapeRef': 'mathshape:motor-m1-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 4.712389]},
             {'id': 'yoke',
              'shapeRef': 'mathshape:motor-m1-yoke',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'stator-tooth-0',
              'shapeRef': 'mathshape:motor-m1-stator-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.0]},
             {'id': 'stator-tooth-1',
              'shapeRef': 'mathshape:motor-m1-stator-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 1.047198]},
             {'id': 'stator-tooth-2',
              'shapeRef': 'mathshape:motor-m1-stator-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 2.094395]},
             {'id': 'stator-tooth-3',
              'shapeRef': 'mathshape:motor-m1-stator-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.141593]},
             {'id': 'stator-tooth-4',
              'shapeRef': 'mathshape:motor-m1-stator-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 4.18879]},
             {'id': 'stator-tooth-5',
              'shapeRef': 'mathshape:motor-m1-stator-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 5.235988]},
             {'id': 'coil-A0',
              'shapeRef': 'mathshape:motor-m1-coil',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.0]},
             {'id': 'coil-B0',
              'shapeRef': 'mathshape:motor-m1-coil',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 1.047198]},
             {'id': 'coil-C0',
              'shapeRef': 'mathshape:motor-m1-coil',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 2.094395]},
             {'id': 'coil-A1',
              'shapeRef': 'mathshape:motor-m1-coil',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.141593]},
             {'id': 'coil-B1',
              'shapeRef': 'mathshape:motor-m1-coil',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 4.18879]},
             {'id': 'coil-C1',
              'shapeRef': 'mathshape:motor-m1-coil',
              'styleRef': 'motor-coil-idle',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 5.235988]}
         ]}),
     'axis_labels_json': '{}', 'camera_json': '',
     'category': 'motors', 'owning_module': 'motors'},
]

#: ------------------------------------------------------------
#: M3 — DUAL-STATOR AXIAL FLUX (mag-12), the SS2d flagship
#:
#: Two stator disks sandwich one rotor disk, so the machine has
#: TWO working air gaps instead of one. That is the entire thesis:
#: force scales with gap AREA, and a second gap doubles the area
#: inside the same envelope — which is how a ferrite machine
#: reaches for parity with a rare-earth one. torque_curve()
#: computes that doubling rather than asserting it.
#:
#: Geometry from the design's params_json: 12 teeth per stator,
#: 8 rotor poles, gap 0.8 mm, tooth face 2.5e-4 m2 = 250 mm2
#: (here 23 x 11 = 253 mm2), rotor magnet length 6 mm.
#:
#: NAMED GAP — no coils are drawn. An axial-flux coil is a
#: trapezoidal wedge that fills the space between two teeth, and a
#: round tube is simply the wrong primitive for it: at 12 teeth on
#: a 33 mm pitch circle the tube OD needed to clear a 23 mm-long
#: tooth is wider than the tooth pitch, so tubes would intersect
#: each other and lie about the winding. Drawing the wrong shape
#: would be worse than drawing none. The mag-9 winding report
#: still judges the real 100 t / 20 AWG winding.
#: ------------------------------------------------------------
SEED_M3_PART_SHAPES = [
    {'name': 'motor-m3-shaft',
     'display_name': 'M3 shaft',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 5.0, 'height': 46.0, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-12'},
    {'name': 'motor-m3-rotor-disk',
     'display_name': 'M3 rotor disk (the carrier)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 42.0, 'height': 6.0, 'axis': 'z',
          'center': [0.0, 0.0, 0.0], 'cap_base': True,
          'cap_top': True}),
     'notes': '6 mm thick = the design\'s magnet_length_m. It sits '
              'BETWEEN the two stators, which is what gives the '
              'machine two gaps.',
     'provenance_id': 'mag-12'},
    {'name': 'motor-m3-rotor-pole',
     'display_name': 'M3 rotor magnet pole (x8 by rotation)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [23.0, 14.0, 6.2], 'center': [30.0, 0.0, 0.0]}),
     'notes': 'Eight sintered-hexaferrite sectors, alternating N/S '
              'around the disk. These face BOTH stators at once — '
              'one magnet, two gaps, which is where the doubling '
              'comes from.',
     'provenance_id': 'mag-12'},
    {'name': 'motor-m3-stator-a-yoke',
     'display_name': 'M3 stator A yoke (upper back-iron disk)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 45.0, 'height': 5.0, 'axis': 'z',
          'center': [0.0, 0.0, 10.3], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-12'},
    {'name': 'motor-m3-stator-a-tooth',
     'display_name': 'M3 stator A tooth (x12 by rotation)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [23.0, 11.0, 4.0], 'center': [30.0, 0.0, 5.8]}),
     'notes': 'Face at z = +3.8 mm, i.e. 0.8 mm above the rotor '
              'face — the design\'s gap_base_m. Face 23 x 11 = 253 '
              'mm2 against the stated 2.5e-4 m2.',
     'provenance_id': 'mag-12'},
    {'name': 'motor-m3-stator-b-yoke',
     'display_name': 'M3 stator B yoke (lower back-iron disk)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 45.0, 'height': 5.0, 'axis': 'z',
          'center': [0.0, 0.0, -10.3], 'cap_base': True,
          'cap_top': True}),
     'provenance_id': 'mag-12'},
    {'name': 'motor-m3-stator-b-tooth',
     'display_name': 'M3 stator B tooth (x12 by rotation)',
     'family': 'primitive', 'primitive_kind': 'box',
     'parameters_json': json.dumps(
         {'size': [23.0, 11.0, 4.0], 'center': [30.0, 0.0, -5.8]}),
     'notes': 'The mirror of stator A. Its existence is the point '
              'of the whole rung: the SECOND gap.',
     'provenance_id': 'mag-12'},
]

SEED_M3_SIM_SPACES = [
    {'name': 'motor-m3-viz',
     'description': 'M3 dual-stator axial flux — the SS2d end goal. '
                    'Two 12-tooth stator disks sandwich one '
                    '8-pole rotor, giving TWO working air gaps in '
                    'one envelope; that doubled area is how a '
                    'ferrite machine reaches toward rare-earth '
                    'torque. Windings are deliberately NOT drawn: '
                    'an axial-flux coil is a trapezoidal wedge and '
                    'a round tube would intersect its neighbours '
                    'and lie about the winding.',
     'dimensionality': '3d', 'coordinate_system': 'math',
     'unit_scale': 1.0,
     'viewport_json': json.dumps(
         {'center': [0.0, 0.0, 0.0],
          'extent': [110.0, 110.0, 60.0]}),
     'bound_classes_json': '[]',
     'definition': json.dumps({
         'freestandingOnly': True,
         'freestanding': [
             {'id': 'shaft',
              'shapeRef': 'mathshape:motor-m3-shaft',
              'styleRef': 'motor-shaft-steel',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-disk',
              'shapeRef': 'mathshape:motor-m3-rotor-disk',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'rotor-pole-0',
              'shapeRef': 'mathshape:motor-m3-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.0]},
             {'id': 'rotor-pole-1',
              'shapeRef': 'mathshape:motor-m3-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.785398]},
             {'id': 'rotor-pole-2',
              'shapeRef': 'mathshape:motor-m3-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 1.570796]},
             {'id': 'rotor-pole-3',
              'shapeRef': 'mathshape:motor-m3-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 2.356194]},
             {'id': 'rotor-pole-4',
              'shapeRef': 'mathshape:motor-m3-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.141593]},
             {'id': 'rotor-pole-5',
              'shapeRef': 'mathshape:motor-m3-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.926991]},
             {'id': 'rotor-pole-6',
              'shapeRef': 'mathshape:motor-m3-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 4.712389]},
             {'id': 'rotor-pole-7',
              'shapeRef': 'mathshape:motor-m3-rotor-pole',
              'styleRef': 'motor-rotor-dark',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 5.497787]},
             {'id': 'stator-a-yoke',
              'shapeRef': 'mathshape:motor-m3-stator-a-yoke',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'stator-a-tooth-0',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.0]},
             {'id': 'stator-a-tooth-1',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.523599]},
             {'id': 'stator-a-tooth-2',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 1.047198]},
             {'id': 'stator-a-tooth-3',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 1.570796]},
             {'id': 'stator-a-tooth-4',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 2.094395]},
             {'id': 'stator-a-tooth-5',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 2.617994]},
             {'id': 'stator-a-tooth-6',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.141593]},
             {'id': 'stator-a-tooth-7',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.665191]},
             {'id': 'stator-a-tooth-8',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 4.18879]},
             {'id': 'stator-a-tooth-9',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 4.712389]},
             {'id': 'stator-a-tooth-10',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 5.235988]},
             {'id': 'stator-a-tooth-11',
              'shapeRef': 'mathshape:motor-m3-stator-a-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 5.759587]},
             {'id': 'stator-b-yoke',
              'shapeRef': 'mathshape:motor-m3-stator-b-yoke',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0]},
             {'id': 'stator-b-tooth-0',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.0]},
             {'id': 'stator-b-tooth-1',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 0.523599]},
             {'id': 'stator-b-tooth-2',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 1.047198]},
             {'id': 'stator-b-tooth-3',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 1.570796]},
             {'id': 'stator-b-tooth-4',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 2.094395]},
             {'id': 'stator-b-tooth-5',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 2.617994]},
             {'id': 'stator-b-tooth-6',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.141593]},
             {'id': 'stator-b-tooth-7',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 3.665191]},
             {'id': 'stator-b-tooth-8',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 4.18879]},
             {'id': 'stator-b-tooth-9',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 4.712389]},
             {'id': 'stator-b-tooth-10',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 5.235988]},
             {'id': 'stator-b-tooth-11',
              'shapeRef': 'mathshape:motor-m3-stator-b-tooth',
              'styleRef': 'motor-part-gray',
              'position': [0.0, 0.0, 0.0],
              'rotation': [0.0, 0.0, 5.759587]}
         ]}),
     'axis_labels_json': '{}', 'camera_json': '',
     'category': 'motors', 'owning_module': 'motors'},
]

