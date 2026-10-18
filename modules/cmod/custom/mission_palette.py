"""
@module cmod.custom.mission_palette

The ONE builder of the Mission node kinds' `statePalette` dicts, so the six `Mission*State` classes (one per file) stay a few
lines each and read alike. The palette is DATA (it rides GET /stateSpaceClasses), the same idiom as `purpose_palette`; category is
always 'Mission'. These kinds are DECLARATIVE: the engine never executes them (the `mission` category validator,
hwnocode.custom.cross_domain, refuses every compute or runtime kind).
"""
CATEGORY = 'Mission'
AUTHORED_COLOR = '#AD1457'
DERIVED_COLOR = '#9E9E9E'


def palette(kind, display_name, description, fields, derived=False, icon='rocket_launch', multiple=False):
    """fields: [(name, displayName)] - every one a plain string variable; the first ones are the card's displayFields."""
    return {
        'nodeKind': kind, 'displayName': display_name, 'category': CATEGORY, 'icon': icon,
        'color': DERIVED_COLOR if derived else AUTHORED_COLOR, 'placement': 'declarative', 'language': 'n/a (declarative, never executed)',
        'overlay': '', 'description': description, 'displayFields': [f for f, _ in fields],
        'variables': [{'name': f, 'displayName': d, 'type': 'string', 'defaultValue': ''} for f, d in fields],
        'slots': {'inputs': 0 if kind == 'mission-goal' else 1, 'outputs': 1, 'outputLabels': ['then']},
        'derived': bool(derived), 'multiple': bool(multiple),
    }
