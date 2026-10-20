"""
@module electrodevice.objects.circuit.CircuitState

CircuitState — one class per file (design §7); cst-0 (PROTOTYPING_VIEWS_PLAN.md §2, §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CircuitState(treeObject):
    """What it is: ONE ELECTRONIC STATE of a bench circuit under one firmware config — one assignment of every component's electrical mode (the
    pushbutton open | closed, the LED forward-biased | off, each board pin driven-high | driven-low | input-pullup | input-hiz | high-z). Two states
    differ exactly when the SPICE netlist that solves them differs (D-ptv-2). DERIVED, never typed: the candidate space is the product of the parts'
    modes, PRUNED to what the firmware can reach — the pin modes its HAL init writes (read from the source), the levels its pin-writer atom can drive
    (read from the parsed atoms), the external events a person can make (a press), and the power/reset lifecycle. `spice_verdict` / `currents_json`
    come from the state's own `.op` run (a CircuitRunResult named `<config>:<state>:op`) when an ngspice binary is present; otherwise they say so.
    Related concepts: `CircuitStateTransition` (what moves the circuit between states), `CircuitDefinition` (the bench circuit), `FirmwareVariant`
    (the config), `CircuitRunResult` (the SPICE run), `ElectricalCharacteristic` / `PinGroupBudget` (the limits the currents are judged against).
    """

    plain_words = ('A circuit state is one way the parts can be set: button up or down, light on or off, each pin driving or listening. '
                   'The firmware moves the circuit between these states; SPICE says what current flows in each.')

    @treeObjectInit
    def __init__(self, name: str = '', config: str = '', circuit: str = '', state: str = '', lifecycle: str = 'running', modes_json: str = '{}',
                 led: str = '', words: str = '', reachable_by: str = '', evidence: str = '', spice_verdict: str = '', spice_words: str = '',
                 currents_json: str = '{}', findings_json: str = '[]', run: str = '', manager=None):
        self.name = name  # '<config>:<state>' e.g. 'uno-light:led-on-button-held'
        self.config = config
        self.circuit = circuit  # the CircuitDefinition
        self.state = state  # idle-led-off | button-held-led-off | led-on | led-on-button-held | reset-high-z | reset-button-held
        self.lifecycle = lifecycle  # running | reset
        self.modes_json = modes_json  # {component or pin: mode}
        self.led = led  # forward | off (derived from the driver pin's mode)
        self.words = words
        self.reachable_by = reachable_by  # the transitions that lead here, in words
        self.evidence = evidence  # where each mode was read from
        self.spice_verdict = spice_verdict  # ok | warn | refuse | undetermined | not-simulated
        self.spice_words = spice_words
        self.currents_json = currents_json  # {probe: mA} from the .op
        self.findings_json = findings_json
        self.run = run  # the CircuitRunResult name
