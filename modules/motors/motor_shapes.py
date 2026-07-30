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

SEED_MOTOR_PART_SHAPES = [
    {'name': 'motor-m0-rotor-disc',
     'display_name': 'M0 rotor disc (bonded hexaferrite)',
     'family': 'primitive', 'primitive_kind': 'cylinder',
     'parameters_json': json.dumps(
         {'radius': 3.0, 'height': 0.8, 'axis': 'z',
          'center': [0.0, 0.0, 0.0]}),
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
          'center': [0.0, 0.0, 0.2]}),
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
          'center': [0.0, -5.6, 0.0]}),
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
