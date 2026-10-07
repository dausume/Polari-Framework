"""
@module firmwarefaults.objects.firmwarefaults.Scenario

Scenario — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Scenario(treeObject):
    """What it is: The FORCING RECIPE for one interleaving or one trigger (FIRMWARE_SCENARIO_PLAN.md §1/§3): which
    board and variant it targets (BEFORE = the build without the technique, AFTER = with it), which fault row it
    forces and which assumption that breaks, the ordered ScenarioSteps (irq-at-pc, corrupt-word, …), the observable
    that decides the outcome, the simulated window, the seed policy. Running it BEFORE shows the failure at a named
    cycle and PC; AFTER shows it pass; the pair measures the technique's cost. `status` is `runnable` only when every
    step is forcible on its simulator today.
    Related concepts: `ScenarioStep`, `ScenarioRun`, `FirmwareFault`, `Technique`, board's `FirmwareVariant`.
    """

    plain_words = ('A scenario is a recipe that makes a bug happen on purpose in a simulated board, for example by firing '
                   'an interrupt at an exact instruction. Run it before a fix to watch the bug happen, and after the fix '
                   'to see that it no longer does.')

    #: hw priorities D-hw-2 (HARDWARE_DEV_PRIORITIES.md §4): a Scenario is 'fault' (the forcing recipes above — the
    #: ONLY kind before this) or 'acceptance' (a CapabilityDefinition's proof that a GOAL holds under NORMAL
    #: operation — no fault forced; `fault_class`/`fault`/`breaks`/`technique` stay '' on an acceptance row).
    KINDS = ('fault', 'acceptance')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', description: str = '', target_board: str = '', before_variant: str = '',
                 after_variant: str = '', fault_class: str = '', fault: str = '', breaks: str = '', technique: str = '',
                 expected_observable: str = '', observable_kind: str = '', window_cycles: int = 0, run_seconds: float = 0.0,
                 seed_policy: str = 'fixed', seed: int = 0, simulator: str = 'avr-twin', status: str = 'runnable',
                 kind: str = 'fault', capability: str = '', provenance: str = '', notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.description = description
        self.kind = kind  # fault (default, every existing row) | acceptance (hw priorities P1)
        self.capability = capability  # acceptance only: the CapabilityDefinition name this scenario proves
        self.target_board = target_board  # a BoardDefinition name
        self.before_variant = before_variant  # FirmwareVariant WITHOUT the technique
        self.after_variant = after_variant  # FirmwareVariant WITH it ('' when the technique is a refused build)
        self.fault_class = fault_class  # the kind class (TornReadFault, …)
        self.fault = fault  # the row of that class
        self.breaks = breaks  # an Assumption name
        self.technique = technique  # the Technique the AFTER build applies
        self.expected_observable = expected_observable  # in words
        self.observable_kind = observable_kind  # uptime-monotone | build-refused — the decision the runner applies
        self.window_cycles = window_cycles  # simulated cycles a forced run covers
        self.run_seconds = run_seconds  # simulated seconds (= window_cycles / 16 MHz)
        self.seed_policy = seed_policy  # fixed (deterministic; nothing drawn) | per-run (sc-2 statistics)
        self.seed = seed
        self.simulator = simulator  # avr-twin | renode | silicon
        self.status = status  # runnable | not-yet-forcible (a step's kind is not in the harness yet)
        self.provenance = provenance
        self.notes = notes
