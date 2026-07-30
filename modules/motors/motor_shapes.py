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
