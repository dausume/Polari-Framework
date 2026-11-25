"""
@module hwnocode.schematic_page

cb-1 / cb-2 PROTOTYPE PAGES (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §3, §4, §7):
  /display/schematic-components   every SchematicComponent as a card - its small schematic (red where unsolved), its parts and ports -
                                  then the port and part rows as configured tables
  /display/hardware-features      every HardwareFeature as one row of cards, one card per element (struct field, UI control, no-code
                                  piece, protocol, schematic component, chip and pins), each marked chosen / suggested / open
Both read the rows through the generated class APIs (no new routes): the two generic components `schematic-component-cards` and
`feature-cards-table` take class names, never a door.
"""
from polariApiServer.module_pages_seed import _component, _page, _row, _table

COMPONENTS_ROUTE = 'schematic-components'
FEATURES_ROUTE = 'hardware-features'

CLASSES = {'componentClass': 'SchematicComponent', 'portClass': 'SchematicComponentPort', 'partClass': 'SchematicComponentPart',
           'checkClass': 'SchematicComponentCheck'}

#: the feature table's columns: one card per element. `source_key` is the HardwareFeature column whose chosen / suggested / open state the
#: card shows (hwnocode.custom.feature_columns); kind `schematic` draws the bound SchematicComponent named by the row's `ref_field`.
FEATURE_COLUMNS = [
    {'key': 'struct', 'label': 'Struct field', 'kind': 'fields', 'source_key': 'struct_field',
     'fields': {'Instance': 'struct_instance', 'Field': 'struct_field'}},
    {'key': 'ui', 'label': 'UI control', 'kind': 'fields', 'source_key': 'ui_control',
     'fields': {'Control': 'ui_control', 'Direction': 'ui_direction'}},
    {'key': 'nocode', 'label': 'No-code piece', 'kind': 'fields', 'source_key': 'nocode_variable',
     'fields': {'Variable': 'nocode_variable', 'HAL role': 'hal_role'}},
    {'key': 'protocol', 'label': 'Protocol', 'kind': 'fields', 'source_key': 'protocol', 'fields': {'Protocol': 'protocol'}},
    {'key': 'schematic', 'label': 'Schematic component', 'kind': 'schematic', 'source_key': 'schematic_component',
     'ref_field': 'schematic_component'},
    {'key': 'pins', 'label': 'Chip and pins', 'kind': 'fields', 'source_key': 'pins', 'fields': {'Chip': 'chip', 'Pins': 'pins'}},
    {'key': 'solution', 'label': 'Solution and simulator pair', 'kind': 'fields', 'source_key': 'hardware_solution',
     'fields': {'Solution': 'hardware_solution', 'Firmware': 'firmware_variant', 'Device': 'device', 'Simulator': 'simulator'}},
]


def components_cards(item_id='schematic-components-cards', index=0, segments=12):
    return _component(item_id, index, segments, 'Schematic components - each drawn small, red where nothing has worked out its parts yet',
                      'schematic-component-cards', dict(CLASSES),
                      description='What this is for: every schematic component on one screen, as you would name it (a button, a light), '
                                  'with the small parts around it that make it behave on a real pin. One card = one component: its '
                                  'drawing (the core part in the middle, each port running out to its chip pin, the conditioning parts '
                                  'on the line they sit on, the supply below), its state, and its parts and ports. Solved means its '
                                  'conditioning parts were placed; unsolved means nothing has worked them out yet, and its lines are '
                                  'drawn red. The ones named after a hardware solution (uno-light-system:...) were cut from its real circuit '
                                  'and solved by the schematic solver (the board\'s electrical rules plus the pull, series, guard and '
                                  'filter rules); blocked means the solver wants a part it cannot place, named in its checks. The drawing\'s '
                                  'own rows are marked solved by the drawing: no solver ran on them.')


SCHEMATIC_PAGES = [
    _page(COMPONENTS_ROUTE, COMPONENTS_ROUTE,
          'Schematic components (a prototype): the pieces a device is built from - a button, a light - each with the parts that make it '
          'safe and reliable on a chip pin: a pull resistor, a series resistor, a guard diode that stops current flowing back into a pin, '
          'a filter capacitor as close to the pin as possible. A component whose parts were never worked out is drawn red. The cards come '
          'first; the tables below hold the same ports and parts as rows.',
          'SchematicComponent', [
              _row(0, [components_cards()], min_height=420),
              _row(1, [_table('schematic-component-ports', 0, 6, 'Ports - where each component connects', 'SchematicComponentPort',
                              description='One row = one port of one component. kind is signal, supply or ground; chip and pin say where a '
                                          'signal port lands (empty = left open for the pin solver); pin_source says whether a person '
                                          'chose the pin (held) or a solver suggested it.',
                              columns='component,port,kind,chip,pin,pin_source'),
                       _table('schematic-component-parts', 6, 6, 'Parts - the core part and its conditioning parts', 'SchematicComponentPart',
                              description='One row = one part of one component. role is core, pull, series, guard, filter or supply; port is '
                                          'the port the part sits on; value is empty until it is worked out; placed_by and rule say who or '
                                          'what placed it and why.',
                              columns='component,ref,role,part_kind,value,port,placed_by,rule')], min_height=260),
              _row(2, [_table('schematic-component-checks', 0, 12, 'What the solver decided - one rule per row', 'SchematicComponentCheck',
                              description='One row = one decision of the schematic solver about one component (component empty = about the '
                                          'whole solution). rule is pull, series, guard or filter (the conditioning rules) or one of the '
                                          'board\'s electrical rules; status is placed, not-needed or needed for a conditioning rule, and ok, '
                                          'warn, refuse or undetermined for an electrical one (undetermined = a number is not cited, never '
                                          'guessed); detail says why, with the numbers.',
                              columns='component,rule,status,subject,detail,hardware_solution')], min_height=260),
          ], title='Schematic components'),
    _page(FEATURES_ROUTE, FEATURES_ROUTE,
          'Hardware features (a rough model): one row per thing a device does - the button, the light - with one card per element that '
          'makes it work: the struct field that carries it, the screen control, the no-code piece and its HAL role, the protocol, the '
          'schematic component and the chip pins. Each card says whether a person chose it (held), a solver suggested it, or it is still '
          'open. Any element can be chosen first; the rest are narrowed to what fits (the narrowing and the solvers are the next slices). '
          'The design is solved for the real device and tried first on its simulator pair.',
          'HardwareFeature', [
              _row(0, [_component('hardware-features-table', 0, 12, 'Hardware features - one row each, one card per element',
                                  'feature-cards-table', dict({k: v for k, v in CLASSES.items() if k != 'checkClass'}, featureClass='HardwareFeature',
                                                                       columns=FEATURE_COLUMNS),
                                  description='What this is for: seeing everything a feature is made of at once, and what is still open. '
                                              'One row = one HardwareFeature. Each card is one element; its corner says chosen (a person '
                                              'picked it and it is held), suggested (a solver filled it) or open. The schematic card is '
                                              'the component\'s own drawing, red where it is unsolved. The last cell says whether the '
                                              'feature is complete and, if not, what is open.')], min_height=360),
              _row(1, [_table('hardware-features-rows', 0, 12, 'The same features as plain rows', 'HardwareFeature',
                              description='One row = one HardwareFeature with every column; chosen lists the columns a person picked.',
                              columns='name,hardware_solution,struct_instance,struct_field,ui_control,nocode_variable,hal_role,protocol,schematic_component,'
                                      'chip,pins,device,simulator,chosen')],
                   min_height=200),
          ], title='Hardware features'),
]


def _required():
    """Each card column's `required` comes from the ONE column model (hwnocode.custom.feature_columns), never typed twice."""
    from hwnocode.custom import feature_columns as FC
    for c in FEATURE_COLUMNS:
        col = FC.column(c['source_key'])
        c['required'] = bool(col and col['required'])


_required()
