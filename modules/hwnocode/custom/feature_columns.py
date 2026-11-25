"""
@module hwnocode.custom.feature_columns

cb-2 ROUGH MODEL (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §4): HOW EACH COLUMN OF A `HardwareFeature` PLUGS IN - what existing row it
points at, which other columns a choice in it narrows and why, and whether it is needed before the feature is complete (provisional:
the user confirms the required set, plan §9). Pure data plus three readers; nothing here solves anything yet (cb-3).

  COLUMNS                      the columns in order (complete also needs the device AND its simulator pair: the user, 2026-11-24): {key, label, refers_to, narrows: {column: why}, required}
  column(key)                  one column, or None
  state(feature, components)   per column: open | chosen | suggested, plus the feature's completeness in words
  schematic_state(feature, components)   the bound component's solve state ('none' when no component is bound)
"""

COLUMNS = [
    {'key': 'struct_field', 'label': 'Struct field', 'refers_to': 'grpcbridge StructObjectMap (a struct instance and its field)',
     'narrows': {'ui_control': 'a field\'s type decides which controls can show or drive it (a bool: a toggle or a light)',
                 'schematic_component': 'a bool field admits a button, a switch or a light; a number admits an analogue part'},
     'required': True},
    {'key': 'ui_control', 'label': 'UI control', 'refers_to': 'a bridge input or output on the screen',
     'narrows': {'struct_field': 'a control drives or shows one field of a matching type'},
     'required': False},
    {'key': 'nocode_variable', 'label': 'No-code piece', 'refers_to': 'cmod HalVariableState (a catom / HAL variable)',
     'narrows': {'pins': 'the HAL and the firmware variant both check the pin (cmod_catom_hal_nocode)',
                 'hal_role': 'a variable has one HAL role'},
     'required': True},
    {'key': 'hal_role', 'label': 'HAL role', 'refers_to': 'hal soc rules (the roles a chip offers)',
     'narrows': {'pins': 'only pins that offer the role', 'protocol': 'the role decides input or output'},
     'required': True},
    {'key': 'protocol', 'label': 'Protocol', 'refers_to': 'how the signal behaves: active level, debounce, interrupt or polled',
     'narrows': {'pins': 'an interrupt protocol admits only pins with an interrupt route',
                 'schematic_component': 'the protocol decides the conditioning parts (a pull, a filter capacitor)'},
     'required': True},
    {'key': 'schematic_component', 'label': 'Schematic component', 'refers_to': 'SchematicComponent (with its ports and parts)',
     'narrows': {'struct_field': 'a button or light carries a bool', 'protocol': 'the protocols its core part supports'},
     'required': True},
    {'key': 'pins', 'label': 'Chip and pins', 'refers_to': 'board SocPin / BoardPin (suggested by the pin solver, cmod_solve, when open)',
     'narrows': {'hal_role': 'a pin offers only some roles', 'protocol': 'a pin without an interrupt route admits only polling'},
     'required': True},
    {'key': 'hardware_solution', 'label': 'Hardware solution', 'refers_to': 'board HardwareSolution (the specific assembly it belongs to)',
     'narrows': {'pins': 'only the pins of the solution\'s board', 'schematic_component': 'only components on the solution\'s circuit'},
     'required': True},
    {'key': 'device', 'label': 'Device', 'refers_to': 'board BoardDefinition (the real board it is solved for)',
     'narrows': {'simulator': 'the twin kind of that board', 'pins': 'that board\'s pins'},
     'required': True},
    {'key': 'simulator', 'label': 'Simulator pair', 'refers_to': 'board.custom.twin_kinds (the engine that stands in for the device)',
     'narrows': {'device': 'a twin stands in for one board'},
     'required': True},
]

_BY_KEY = {c['key']: c for c in COLUMNS}


def column(key):
    return _BY_KEY.get(key)


def _value(feature, key):
    if key == 'pins':
        return (feature.get('pins') or '').strip()
    return (feature.get(key) or '').strip()


def schematic_state(feature, components):
    """The bound component's solve state, or 'none' (no component bound) / 'missing' (it names a component that does not exist)."""
    name = (feature.get('schematic_component') or '').strip()
    if not name:
        return 'none'
    comp = next((c for c in components if c.get('name') == name), None)
    return comp.get('solve_state') or 'unsolved' if comp else 'missing'


def state(feature, components):
    """-> {'columns': [{key, label, value, source}], 'missing': [labels], 'schematic': state, 'complete': bool, 'words': str}.
    source = chosen (in the feature's `chosen` csv) | suggested (filled, not chosen) | open (empty)."""
    chosen = {c.strip() for c in (feature.get('chosen') or '').split(',') if c.strip()}
    cols, missing = [], []
    for c in COLUMNS:
        v = _value(feature, c['key'])
        source = 'open' if not v else ('chosen' if c['key'] in chosen else 'suggested')
        cols.append({'key': c['key'], 'label': c['label'], 'value': v, 'source': source})
        if c['required'] and not v:
            missing.append(c['label'])
    sch = schematic_state(feature, components)
    complete = not missing and sch == 'solved'
    if complete:
        words = 'complete: every required column is filled, its schematic component is solved and its device has a simulator pair'
    else:
        parts = []
        if missing:
            parts.append('open: ' + ', '.join(missing))
        if sch not in ('solved', 'none'):
            parts.append('its schematic component is %s' % sch)
        words = 'not complete - ' + '; '.join(parts)
    return {'columns': cols, 'missing': missing, 'schematic': sch, 'complete': complete, 'words': words}
