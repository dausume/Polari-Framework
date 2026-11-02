"""
@module cmod.custom.topology_palette

bss-5 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b): the ONE builder of the Bench Topology node kinds' `statePalette` dicts (struct-node,
hardware-event), the same idiom as cmod.custom.purpose_palette: the palette is DATA (it rides the canvas's palette door), category 'Bench Topology',
DECLARATIVE (the category validator in hwnocode.custom.cross_domain refuses every compute or runtime kind). The colour by confirmation state is here too,
so the drawing and the legend agree (the frontend maps these to theme tokens; the hex is the fallback the canvas draws today).
"""
CATEGORY = 'Bench Topology'
AUTHORED_COLOR = '#00695C'
PROPOSED_COLOR = '#9E9E9E'
EVENT_COLOR = '#5D4037'
STATE_COLORS = {'confirmed-hardware': '#1B5E20', 'confirmed-twin': '#2E7D32', 'confirmed-person': '#558B2F', 'checks-failed': '#EF6C00', 'diverged': '#C62828',
                'not-reached': '#AD1457', 'blocked': '#6A1B9A', 'voided': '#757575', 'never-tested': '#546E7A', 'proposed': PROPOSED_COLOR, 'root': '#37474F'}


def palette(kind, display_name, description, fields, inputs=1, outputs=1, icon='hub'):
    """fields: [(name, displayName)] - every one a plain string variable; the first ones are the card's displayFields."""
    return {
        'nodeKind': kind, 'displayName': display_name, 'category': CATEGORY, 'icon': icon,
        'color': EVENT_COLOR if kind == 'hardware-event' else AUTHORED_COLOR, 'placement': 'declarative', 'language': 'n/a (declarative, never executed)',
        'overlay': '', 'description': description, 'displayFields': [f for f, _ in fields],
        'variables': [{'name': f, 'displayName': d, 'type': 'string', 'defaultValue': ''} for f, d in fields],
        'slots': {'inputs': inputs, 'outputs': outputs, 'outputLabels': ['then']},
        'derived': False, 'multiple': True,
    }
