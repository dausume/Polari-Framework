"""
Seed data for the SimSpace 3D library — stock meshes + materials + a
demo 3D SimSpace. Same idempotent-by-name pattern as simSpace2D/seed_data.
"""

SEED_MESHES_3D = [
    {
        'name': 'cube',
        'description': '1×1×1 box.',
        'source': 'builtin',
        'builtin_name': 'cube',
        'primitive_params_json': '{"width": 1, "height": 1, "depth": 1}',
        'bounding_box_json': '{"min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]}',
    },
    {
        'name': 'sphere',
        'description': 'Radius 0.5 sphere, 32 segments.',
        'source': 'builtin',
        'builtin_name': 'sphere',
        'primitive_params_json': '{"radius": 0.5, "widthSegments": 32, "heightSegments": 16}',
        'bounding_box_json': '{"min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]}',
    },
    {
        'name': 'cylinder',
        'description': 'Radius 0.5, height 1, 32 segments.',
        'source': 'builtin',
        'builtin_name': 'cylinder',
        'primitive_params_json': '{"radiusTop": 0.5, "radiusBottom": 0.5, "height": 1, "radialSegments": 32}',
        'bounding_box_json': '{"min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]}',
    },
    {
        'name': 'cone',
        'description': 'Cone, radius 0.5 base, height 1, 32 segments.',
        'source': 'builtin',
        'builtin_name': 'cone',
        'primitive_params_json': '{"radius": 0.5, "height": 1, "radialSegments": 32}',
        'bounding_box_json': '{"min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]}',
    },
    {
        'name': 'plane',
        'description': '1×1 plane, double-sided.',
        'source': 'builtin',
        'builtin_name': 'plane',
        'primitive_params_json': '{"width": 1, "height": 1}',
        'bounding_box_json': '{"min": [-0.5, 0, -0.5], "max": [0.5, 0, 0.5]}',
    },
    {
        'name': 'pyramid',
        'description': 'Square-base 4-sided pyramid. Apex up.',
        'source': 'builtin',
        'builtin_name': 'pyramid',
        'primitive_params_json': '{"radius": 0.6, "height": 1}',
        'bounding_box_json': '{"min": [-0.6, -0.5, -0.6], "max": [0.6, 0.5, 0.6]}',
    },
    {
        'name': 'octahedron',
        'description': '3D diamond (bipyramid).',
        'source': 'builtin',
        'builtin_name': 'octahedron',
        'primitive_params_json': '{"radius": 0.5}',
        'bounding_box_json': '{"min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]}',
    },
    {
        'name': 'tetrahedron',
        'description': '3D triangle (4-faced Platonic solid).',
        'source': 'builtin',
        'builtin_name': 'tetrahedron',
        'primitive_params_json': '{"radius": 0.6}',
        'bounding_box_json': '{"min": [-0.6, -0.6, -0.6], "max": [0.6, 0.6, 0.6]}',
    },
    {
        'name': 'icosahedron',
        'description': '20-face polyhedron — closest 3D analog of a star.',
        'source': 'builtin',
        'builtin_name': 'icosahedron',
        'primitive_params_json': '{"radius": 0.55}',
        'bounding_box_json': '{"min": [-0.55, -0.55, -0.55], "max": [0.55, 0.55, 0.55]}',
    },
    {
        'name': 'dodecahedron',
        'description': '12-face Platonic solid.',
        'source': 'builtin',
        'builtin_name': 'dodecahedron',
        'primitive_params_json': '{"radius": 0.55}',
        'bounding_box_json': '{"min": [-0.55, -0.55, -0.55], "max": [0.55, 0.55, 0.55]}',
    },
    {
        'name': 'torus',
        'description': 'Ring / donut.',
        'source': 'builtin',
        'builtin_name': 'torus',
        'primitive_params_json': '{"radius": 0.5, "tube": 0.15, "radialSegments": 16, "tubularSegments": 32}',
        'bounding_box_json': '{"min": [-0.65, -0.15, -0.65], "max": [0.65, 0.15, 0.65]}',
    },
]

SEED_MATERIALS_3D = [
    {
        'name': 'matte-blue',
        'description': 'Matte blue — the 3D default.',
        'material_type': 'standard',
        'color': '#1976d2',
        'metalness': 0.0,
        'roughness': 0.8,
    },
    {
        'name': 'matte-gray',
        'description': 'Neutral gray, matte finish.',
        'material_type': 'standard',
        'color': '#9e9e9e',
        'metalness': 0.0,
        'roughness': 0.9,
    },
    {
        'name': 'glossy-white',
        'description': 'Glossy white plastic.',
        'material_type': 'standard',
        'color': '#ffffff',
        'metalness': 0.0,
        'roughness': 0.15,
    },
    {
        'name': 'soil-brown',
        'description': 'Damp potting soil — matte earth tone (aquaponics-'
                       'pot-shape phase 4 soil fill).',
        'material_type': 'standard',
        'color': '#5d4037',
        'metalness': 0.0,
        'roughness': 0.95,
    },
    {
        'name': 'matte-blue-transparent',
        'description': 'Matte blue, see-through — aquaponics-pot-shape '
                       'phase 5 wall transparency toggle (see the '
                       'interior/soil/holes without hiding the vessel).',
        'material_type': 'standard',
        'color': '#1976d2',
        'metalness': 0.0,
        'roughness': 0.8,
        'opacity': 0.3,
        'transparent': True,
    },
    {
        'name': 'soil-brown-transparent',
        'description': 'Damp potting soil, see-through — aquaponics-pot-'
                       'shape phase 5 soil transparency toggle.',
        'material_type': 'standard',
        'color': '#5d4037',
        'metalness': 0.0,
        'roughness': 0.95,
        'opacity': 0.4,
        'transparent': True,
    },
    {
        'name': 'metal-steel',
        'description': 'Brushed steel — metallic finish.',
        'material_type': 'standard',
        'color': '#9e9e9e',
        'metalness': 0.9,
        'roughness': 0.4,
    },
    {
        'name': 'emissive-yellow',
        'description': 'Glowing yellow — useful for highlight markers.',
        'material_type': 'standard',
        'color': '#fdd835',
        'emissive': '#fdd835',
        'emissive_intensity': 0.6,
    },
    {
        'name': 'arrow-gravity',
        'description': 'Red — gravity force arrow (Newtonian pendulum).',
        'material_type': 'standard',
        'color': '#e53935',
        'metalness': 0.0,
        'roughness': 0.6,
    },
    {
        'name': 'arrow-net',
        'description': 'Green — net force arrow (Newtonian pendulum).',
        'material_type': 'standard',
        'color': '#43a047',
        'metalness': 0.0,
        'roughness': 0.6,
    },
    {
        'name': 'arrow-wind',
        'description': 'Cyan — wind: the sparse field cells and the sampled '
                       'drag force on the bob (wind-field coupling).',
        'material_type': 'standard',
        'color': '#29b6f6',
        'metalness': 0.0,
        'roughness': 0.6,
    },
    # --- Per-material-phase appearances (solid-materials-selection):
    # one solid + one liquid look per picker substance. Physical
    # materials map to TEXTURED SURFACES, not meshes — the solid looks
    # carry a procedural texture; liquids read as translucent color.
    {
        'name': 'wax-solid',
        'description': 'Paraffin wax, solidified — waxy off-white with a '
                       'subtle surface noise.',
        'material_type': 'standard',
        'color': '#f3ecd8',
        'metalness': 0.0,
        'roughness': 0.75,
        'map_texture_ref': 'wax-noise',
    },
    {
        'name': 'wax-liquid',
        'description': 'Paraffin wax, molten — translucent amber.',
        'material_type': 'standard',
        'color': '#e8b84a',
        'metalness': 0.0,
        'roughness': 0.25,
        'opacity': 0.55,
        'transparent': True,
    },
    {
        'name': 'ice-solid',
        'description': 'Water ice — glassy pale blue with frost noise.',
        'material_type': 'standard',
        'color': '#d7ecf7',
        'metalness': 0.0,
        'roughness': 0.2,
        'map_texture_ref': 'frost-noise',
    },
    {
        'name': 'water-liquid',
        'description': 'Liquid water — translucent blue.',
        'material_type': 'standard',
        'color': '#4fa8d8',
        'metalness': 0.0,
        'roughness': 0.1,
        'opacity': 0.5,
        'transparent': True,
    },
    {
        'name': 'lead-solid',
        'description': 'Solid lead — dull dark metal with brushed stripes.',
        'material_type': 'standard',
        'color': '#5a5f66',
        'metalness': 0.85,
        'roughness': 0.55,
        'map_texture_ref': 'brushed-stripes',
    },
    {
        'name': 'lead-liquid',
        'description': 'Molten lead — hot metallic glow.',
        'material_type': 'standard',
        'color': '#8a7f6a',
        'emissive': '#ff6d00',
        'emissive_intensity': 0.35,
        'metalness': 0.7,
        'roughness': 0.3,
    },
]

# 3D-applicable textures (procedural-first — canvas-generated, so they
# are pure config and export cleanly in module bundles; 'image' source
# via the file store is the follow-up knob).
SEED_TEXTURES_3D = [
    {
        'name': 'wax-noise',
        'description': 'Subtle warm noise — waxy surface irregularity.',
        'source': 'procedural',
        'procedural_kind': 'noise',
        'procedural_params_json': '{"colorA": "#f3ecd8", "colorB": "#e4d9bd", '
                                  '"scale": 24, "seed": 7}',
        'repeat_u': 2.0, 'repeat_v': 2.0,
    },
    {
        'name': 'frost-noise',
        'description': 'Fine cool noise — frosted ice surface.',
        'source': 'procedural',
        'procedural_kind': 'noise',
        'procedural_params_json': '{"colorA": "#e8f4fb", "colorB": "#c8e2f0", '
                                  '"scale": 40, "seed": 13}',
        'repeat_u': 3.0, 'repeat_v': 3.0,
    },
    {
        'name': 'brushed-stripes',
        'description': 'Fine directional stripes — brushed metal.',
        'source': 'procedural',
        'procedural_kind': 'stripes',
        'procedural_params_json': '{"colorA": "#6a6f76", "colorB": "#565b62", '
                                  '"stripes": 48}',
        'repeat_u': 1.0, 'repeat_v': 1.0,
    },
    {
        'name': 'checker-debug',
        'description': 'High-contrast checkerboard — UV debugging.',
        'source': 'procedural',
        'procedural_kind': 'checker',
        'procedural_params_json': '{"colorA": "#ffffff", "colorB": "#222222", '
                                  '"cells": 8}',
    },
]

# Per-substance phase→appearance rows (the object-level home of "what
# does this material look like per phase"; scene bindings compose their
# inline styleRef maps FROM these via binding_style_map()).
SEED_MATERIAL_PHASE_APPEARANCES = [
    {
        'name': 'wax-phases',
        'description': 'Paraffin wax: solid → wax-solid, molten → wax-liquid.',
        'substance_ref': 'paraffin-wax',
        'phase_field': 'phase_solid',
        'appearance_map_json': '{"1": "wax-solid", "0": "wax-liquid"}',
        'default_material_ref': 'wax-liquid',
    },
    {
        'name': 'ice-phases',
        'description': 'Water ice: frozen → ice-solid, melted → water-liquid.',
        'substance_ref': 'water-ice',
        'phase_field': 'phase_solid',
        'appearance_map_json': '{"1": "ice-solid", "0": "water-liquid"}',
        'default_material_ref': 'water-liquid',
    },
    {
        'name': 'lead-phases',
        'description': 'Lead: solid → lead-solid, molten → lead-liquid.',
        'substance_ref': 'lead',
        'phase_field': 'phase_solid',
        'appearance_map_json': '{"1": "lead-solid", "0": "lead-liquid"}',
        'default_material_ref': 'lead-liquid',
    },
]

SEED_SIM_SPACES_3D = [
    {
        'name': 'demo-3d',
        'description': 'Demo SimSpace3D — one of each builtin primitive arranged in a 3×3 grid. Showcases the full mesh library + each material so users can see what every shape/style looks like.',
        'dimensionality': '3d',
        'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': '{"center": [0, 0, 0], "extent": [6, 4, 6]}',
        'bound_classes_json': '[]',
        # Freestanding placements — every builtin mesh, spread on a grid
        # so the user can spin the camera and inspect each one.
        # freestandingOnly (2026-07-14 fix): this is a curated shelf, not
        # a data view — without it, compile_3d falls through past the
        # (only-checked-when-freestandingOnly) early return and pours in
        # EVERY defaultVisible-bound class in the whole system (wind
        # field grid cells, every pendulum run's bob/rod/string history,
        # material condensation states — thousands of unrelated objects
        # crowding what should be nine static primitives). Same pattern
        # already used correctly by solid-material-selector / periodic-
        # table-selector / the aquaponics pot-viz scenes.
        'definition': (
            '{"freestandingOnly": true, "freestanding": ['
            # Row z=-2: 3D analogs of 2D shapes
            '{"id":"demo-cube","position":[-4,0,-2],"shapeRef":"cube","styleRef":"matte-blue","label":"Cube"},'
            '{"id":"demo-pyramid","position":[-2,0,-2],"shapeRef":"pyramid","styleRef":"emissive-yellow","label":"Pyramid"},'
            '{"id":"demo-tetra","position":[0,0,-2],"shapeRef":"tetrahedron","styleRef":"matte-gray","label":"Tetrahedron"},'
            '{"id":"demo-octa","position":[2,0,-2],"shapeRef":"octahedron","styleRef":"glossy-white","label":"Octahedron"},'
            '{"id":"demo-icos","position":[4,0,-2],"shapeRef":"icosahedron","styleRef":"metal-steel","label":"Icosahedron"},'
            # Row z=0: core round / curved shapes
            '{"id":"demo-sphere","position":[-4,0,0],"shapeRef":"sphere","styleRef":"glossy-white","label":"Sphere"},'
            '{"id":"demo-cylinder","position":[-2,0,0],"shapeRef":"cylinder","styleRef":"metal-steel","label":"Cylinder"},'
            '{"id":"demo-cone","position":[0,0,0],"shapeRef":"cone","styleRef":"matte-gray","label":"Cone"},'
            '{"id":"demo-torus","position":[2,0,0],"shapeRef":"torus","styleRef":"matte-blue","label":"Torus"},'
            '{"id":"demo-dodeca","position":[4,0,0],"shapeRef":"dodecahedron","styleRef":"emissive-yellow","label":"Dodecahedron"},'
            # Row z=2: flat / floor reference
            '{"id":"demo-plane","position":[0,-1,2],"shapeRef":"plane","styleRef":"matte-gray","label":"Plane (floor)"}'
            ']}'
        ),
    },
]
