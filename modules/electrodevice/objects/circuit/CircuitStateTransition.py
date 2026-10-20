"""
@module electrodevice.objects.circuit.CircuitStateTransition

CircuitStateTransition — one class per file (design §7); cst-0 (PROTOTYPING_VIEWS_PLAN.md §2, §8).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CircuitStateTransition(treeObject):
    """What it is: ONE MOVE of a bench circuit from one CircuitState to another, and what makes it: an EXTERNAL event (the button pressed or
    released), a FIRMWARE event (the atom that writes the pin — `led_toggle` → `led_follow_state` on a press, `apply_command` → `led_follow_state` on
    SET_LED), or a LIFECYCLE phase (power on / reset → every pin high-Z; init → the HAL's pin modes). `timing` carries the measured latency when a
    twin record has one (the press record: press → the light pin's rise), else says the transition was read from the source. DERIVED, never typed.
    Related concepts: `CircuitState`, `CAtom` (the firmware event), `ScenarioRun` / the press record (the evidence).
    """

    plain_words = 'A transition says what moves the circuit from one state to the next - a finger, a line of firmware, or the power - and how fast.'

    @treeObjectInit
    def __init__(self, name: str = '', config: str = '', circuit: str = '', from_state: str = '', to_state: str = '', kind: str = '', trigger: str = '',
                 atoms: str = '', timing: str = '', timing_ms: float = -1.0, evidence: str = '', words: str = '', manager=None):
        self.name = name  # '<config>:<from>-><to>#<kind>'
        self.config = config
        self.circuit = circuit
        self.from_state = from_state
        self.to_state = to_state
        self.kind = kind  # external | firmware | lifecycle
        self.trigger = trigger  # 'press on SW1 (D2)', 'SET_LED led_on=1', 'power on / reset', 'init (hal_led_init, hal_button_init)'
        self.atoms = atoms  # the firmware atoms on the way, csv
        self.timing = timing  # 'measured on the twin: 0.013..0.024 ms (press record)' | 'read from the source: no twin record of this step'
        self.timing_ms = timing_ms  # the worst measured latency, -1 when none
        self.evidence = evidence
        self.words = words
