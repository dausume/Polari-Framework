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
        'definition': (
            '{"freestanding": ['
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
