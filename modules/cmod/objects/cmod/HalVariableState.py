"""
@module cmod.objects.cmod.HalVariableState

HalVariableState - one class per file (design section 7). The one node kind of a HAL drawing (HARDWARE_SYSTEM_PINS_PLAN.md section 7, hsp-3c).
"""
from objectTreeDecorators import treeObject, treeObjectInit

_FIELDS = [('variable', 'Name in the firmware'), ('value', 'Value'), ('role', 'What it does'), ('scope', 'Set by'), ('verdict', 'Check'),
           ('options', 'Pins it may use'), ('why', 'Why')]


class HalVariableState(treeObject):
    """What it is: the `hal-variable` NODE KIND, category **HAL** - One named value the firmware is built with (the LED pin, the UART transmit pin,
    the clock speed). Pick its value from the pins it may use; the choice is checked against what the pin can do, what the board does with it while it
    starts up, the other values, and the firmware recipe's own rules before it is kept.
    Authored: only `value` is typed in; it is written through `cmod.custom.catom_variables.propose` into the firmware recipe's knob (or the variable's
    bench value) - the drawing is never a second copy. Everything else on the card is worked out.
    Related concepts: `CatomVariable` (the row), `FirmwareVariant` (the knob), `cmod.custom.hal_nocode` (render / validate / write_back).
    """

    plain_words = ('One named value the firmware is built with. Pick its value from the pins it may use; the choice is checked against what the pin can do, '
                   'what the board does with it while it starts up, the other values and the recipe\'s own rules before it is kept.')

    statePalette = {
        'nodeKind': 'hal-variable', 'displayName': 'HAL value', 'category': 'HAL', 'icon': 'settings_input_component', 'color': '#00695C',
        'placement': 'declarative', 'language': 'n/a (declarative, never executed)', 'overlay': '', 'description': plain_words,
        'displayFields': [f for f, _ in _FIELDS],
        'variables': [{'name': f, 'displayName': d, 'type': 'string', 'defaultValue': ''} for f, d in _FIELDS],
        'slots': {'inputs': 0, 'outputs': 0, 'outputLabels': []}, 'derived': False, 'multiple': True,
    }

    @treeObjectInit
    def __init__(self, name: str = '', variable: str = '', value: str = '', role: str = '', scope: str = '', verdict: str = '', options: str = '',
                 why: str = '', manager=None):
        self.name = name
        self.variable = variable
        self.value = value
        self.role = role
        self.scope = scope
        self.verdict = verdict
        self.options = options
        self.why = why
