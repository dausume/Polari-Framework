"""
@module hwnocode.custom.schematic_seed

cb-1 / cb-2 PROTOTYPE ROWS (AI-Notes/plans/COMPONENT_BINDING_PLAN.md): the user's drawing of 2026-11-24, as rows.
  - "LightComp" (solved): a light; a noise-prevention capacitor at GPIO2; a guard diode at GPIO1; a battery.
  - "BtnSchematicComponent" (solved): a button; a capacitor at chip 2's GPIO4; a diode at chip 1's GPIO3; a battery.
  - two unsolved components: a light between GPIO8 and GPIO7, a button between GPIO6 and GPIO5 - bare wiring, nothing placed.
  - "Struct Instance 1": ButtonOn bound to the button component, LightOn bound to the light component, the UI's btnToggle a bridge input.
The drawing gives no part values, so every value is '' (shown as unverified). "Solved" here is the drawing's own mark: no solver has
run on any of them (cb-3 is not built), and `solved_by` says so. The chips are named as the drawing names them (chip1, chip2).
"""

DRAWING = "the user's drawing (2026-11-24); no solver has run yet"

COMPONENTS = [
    {'name': 'light-comp', 'title': 'LightComp', 'intent': 'light', 'core_part': 'led', 'protocol': '', 'solve_state': 'solved',
     'solved_by': DRAWING, 'description': 'A light with a noise-prevention capacitor on one pin and a guard diode on the other.'},
    {'name': 'btn-comp', 'title': 'BtnSchematicComponent', 'intent': 'button', 'core_part': 'pushbutton', 'protocol': '',
     'solve_state': 'solved', 'solved_by': DRAWING,
     'description': 'A button across two chips, with a capacitor on chip 2\'s pin and a diode on chip 1\'s pin.'},
    {'name': 'light-unsolved', 'title': 'Light (unsolved)', 'intent': 'light', 'core_part': 'led', 'protocol': '', 'solve_state': 'unsolved',
     'solved_by': '', 'description': 'A light wired straight to two pins: nothing has worked out its conditioning parts.'},
    {'name': 'button-unsolved', 'title': 'Button (unsolved)', 'intent': 'button', 'core_part': 'pushbutton', 'protocol': '',
     'solve_state': 'unsolved', 'solved_by': '', 'description': 'A button wired straight to two pins: nothing has worked out its conditioning parts.'},
]


def _port(component, port, kind, chip='', pin='', order=0):
    return {'name': '%s/%s' % (component, port), 'component': component, 'port': port, 'kind': kind, 'chip': chip, 'pin': pin,
            'pin_source': 'chosen' if pin else '', 'order': order}


def _part(component, ref, role, kind, port='', order=0, placed_by='drawing', rule=''):
    return {'name': '%s/%s' % (component, ref), 'component': component, 'ref': ref, 'role': role, 'part_kind': kind, 'value': '',
            'port': port, 'placed_by': placed_by, 'rule': rule, 'order': order}


PORTS = [
    _port('light-comp', 'a', 'signal', 'chip1', 'GPIO2', 0), _port('light-comp', 'b', 'signal', 'chip1', 'GPIO1', 1),
    _port('light-comp', 'supply', 'supply', order=2),
    _port('btn-comp', 'a', 'signal', 'chip2', 'GPIO4', 0), _port('btn-comp', 'b', 'signal', 'chip1', 'GPIO3', 1),
    _port('btn-comp', 'supply', 'supply', order=2),
    _port('light-unsolved', 'a', 'signal', 'chip1', 'GPIO8', 0), _port('light-unsolved', 'b', 'signal', 'chip1', 'GPIO7', 1),
    _port('button-unsolved', 'a', 'signal', 'chip1', 'GPIO6', 0), _port('button-unsolved', 'b', 'signal', 'chip1', 'GPIO5', 1),
]

PARTS = [
    _part('light-comp', 'LED1', 'core', 'led', order=0),
    _part('light-comp', 'C1', 'filter', 'capacitor', 'a', 1, rule='the drawing: a noise-prevention capacitor at the pin'),
    _part('light-comp', 'D1', 'guard', 'diode', 'b', 2, rule='the drawing: a guard diode at the pin'),
    _part('light-comp', 'BT1', 'supply', 'battery', 'supply', 3, rule='the drawing: the battery'),
    _part('btn-comp', 'SW1', 'core', 'pushbutton', order=0),
    _part('btn-comp', 'C1', 'filter', 'capacitor', 'a', 1, rule='the drawing: a capacitor at the pin'),
    _part('btn-comp', 'D1', 'guard', 'diode', 'b', 2, rule='the drawing: a diode at the pin'),
    _part('btn-comp', 'BT1', 'supply', 'battery', 'supply', 3, rule='the drawing: the battery'),
    _part('light-unsolved', 'LED1', 'core', 'led', order=0),
    _part('button-unsolved', 'SW1', 'core', 'pushbutton', order=0),
]

FEATURES = [
    {'name': 'button-on', 'title': 'The button', 'struct_instance': 'struct-instance-1', 'struct_field': 'ButtonOn', 'ui_control': 'btnToggle',
     'ui_direction': 'bridge input', 'nocode_variable': '', 'hal_role': '', 'protocol': '', 'schematic_component': 'btn-comp',
     'chip': 'chip1, chip2', 'pins': 'GPIO3, GPIO4', 'chosen': 'struct_field,ui_control,schematic_component,pins',
     'notes': 'From the drawing: ButtonOn bound to BtnSchematicComponent; the UI btnToggle is a bridge input.'},
    {'name': 'light-on', 'title': 'The light', 'struct_instance': 'struct-instance-1', 'struct_field': 'LightOn', 'ui_control': '',
     'ui_direction': '', 'nocode_variable': '', 'hal_role': '', 'protocol': '', 'schematic_component': 'light-comp',
     'chip': 'chip1', 'pins': 'GPIO1, GPIO2', 'chosen': 'struct_field,schematic_component,pins',
     'notes': 'From the drawing: LightOn bound to LightComp.'},
]
