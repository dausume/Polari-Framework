"""
Seed data for the SimSpace2D library — stock shapes + styles users get
out of the box on a fresh deploy. Loaded once on first boot, idempotent
on subsequent boots (existing rows skipped by name).

Mirrors how SEED_EQUATIONS + SEED_SOLUTIONS bootstrap their tables.
"""

SEED_SHAPES_2D = [
    {
        'name': 'circle',
        'description': 'Filled circle — the SimSpace default shape.',
        'source': 'builtin',
        'builtin_name': 'circle',
        'default_width': 16.0,
        'default_height': 16.0,
        'anchor': 'center',
        'category': 'general',
    },
    {
        'name': 'rectangle',
        'description': 'Axis-aligned rectangle.',
        'source': 'builtin',
        'builtin_name': 'rectangle',
        'default_width': 24.0,
        'default_height': 16.0,
        'anchor': 'center',
        'category': 'general',
    },
    {
        'name': 'diamond',
        'description': 'Rotated square — useful for decision-style nodes.',
        'source': 'builtin',
        'builtin_name': 'diamond',
        'default_width': 20.0,
        'default_height': 20.0,
        'anchor': 'center',
        'category': 'general',
    },
    {
        'name': 'triangle',
        'description': 'Equilateral triangle, point-up.',
        'source': 'builtin',
        'builtin_name': 'triangle',
        'default_width': 20.0,
        'default_height': 20.0,
        'anchor': 'center',
        'category': 'general',
    },
    {
        'name': 'star',
        'description': '5-point star.',
        'source': 'builtin',
        'builtin_name': 'star',
        'default_width': 20.0,
        'default_height': 20.0,
        'anchor': 'center',
        'category': 'general',
    },
    {
        'name': 'pin',
        'description': 'Map-style teardrop pin (anchor at point).',
        'source': 'builtin',
        'builtin_name': 'pin',
        'default_width': 18.0,
        'default_height': 28.0,
        'anchor': 'bottom',
        'category': 'marker',
    },
]

SEED_STYLES_2D = [
    {
        'name': 'default',
        'description': 'Neutral blue fill, slightly darker stroke.',
        'width': 40.0, 'height': 40.0,
        'fill_color': '#1976d2',
        'stroke_color': '#0d47a1',
        'stroke_width': 2.0,
        'opacity': 1.0,
        'anchor': 'center',
    },
    {
        'name': 'success',
        'description': 'Green — typically used for active / passing instances.',
        'width': 40.0, 'height': 40.0,
        'fill_color': '#2e7d32',
        'stroke_color': '#1b5e20',
        'stroke_width': 2.0,
        'opacity': 1.0,
        'anchor': 'center',
    },
    {
        'name': 'warning',
        'description': 'Orange — typically used for caution / pending states.',
        'width': 40.0, 'height': 40.0,
        'fill_color': '#ed6c02',
        'stroke_color': '#b53d00',
        'stroke_width': 2.0,
        'opacity': 1.0,
        'anchor': 'center',
    },
    {
        'name': 'danger',
        'description': 'Red — typically used for errors / failing instances.',
        'width': 40.0, 'height': 40.0,
        'fill_color': '#c62828',
        'stroke_color': '#7f0000',
        'stroke_width': 2.0,
        'opacity': 1.0,
        'anchor': 'center',
    },
    {
        'name': 'muted',
        'description': 'Gray — for read-only / archived instances.',
        'width': 40.0, 'height': 40.0,
        'fill_color': '#9e9e9e',
        'stroke_color': '#616161',
        'stroke_width': 2.0,
        'opacity': 0.85,
        'anchor': 'center',
    },
]


SEED_SIM_SPACES_2D = [
    {
        'name': 'demo-2d',
        'description': 'Demo SimSpace2D — a few freestanding shapes to confirm the '
                       'renderer wires up: origin reference, diamond, star, '
                       'triangle, rectangle.',
        'dimensionality': '2d',
        'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': '{"center": [0, 0], "extent": [10, 10]}',
        'bound_classes_json': '[]',
        # Freestanding shapes baked into the scene — independent of class
        # bindings. Each entry is a SimSpaceObject placement record.
        # freestandingOnly (2026-07-14 fix, same bug as demo-3d): this is
        # a curated shelf, not a data view — the OLD description's claim
        # that "class bindings can be configured to populate it further"
        # was itself the bug's symptom, not a real design intent (Dustin
        # confirmed) — without this flag compile_2d pours in every
        # defaultVisible-bound class in the whole system.
        'definition': (
            '{"freestandingOnly": true, "freestanding": ['
            '{"id":"demo-1","position":[-5,3],"shapeRef":"circle","styleRef":"default","label":"Origin reference"},'
            '{"id":"demo-2","position":[5,3],"shapeRef":"diamond","styleRef":"success","label":"Diamond"},'
            '{"id":"demo-3","position":[0,-3],"shapeRef":"star","styleRef":"warning","label":"Star"},'
            '{"id":"demo-4","position":[-3,-5],"shapeRef":"triangle","styleRef":"danger","label":"Triangle"},'
            '{"id":"demo-5","position":[3,-5],"shapeRef":"rectangle","styleRef":"muted","label":"Rectangle"}'
            ']}'
        ),
    },
]
