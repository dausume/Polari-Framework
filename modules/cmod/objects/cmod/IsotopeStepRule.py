"""
@module cmod.objects.cmod.IsotopeStepRule

IsotopeStepRule - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 3 "the Catoms and isotopes decide it").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class IsotopeStepRule(treeObject):
    """What it is: THE STEP ONE ISOTOPE ASKS FOR when a node that executes it is simulated - one row per `IsotopeVariant`. `kind` says what the step is
    (a CPU cycle, one main-loop pass, one UART bit, one PWM period, one ADC conversion, a bus transaction, or a knob), `step_s` the number, `worst_s`
    how late the isotope can be (the longest loop pass, the ISR's longest run), and `basis` where the number came from: derived (measured on the twin's
    cycle record), cited (a datasheet or the build's own flags), knob (no number yet; labelled), or person (typed over, kept by the derivation).
    cmod.custom.isotope_step_rules derives the rows; the topology's step per node is the finest among its executions' rules.
    Related concepts: `IsotopeVariant`, `StructNodeExecution`, board.custom.cycle_records (the measurements), `StructNode`.
    """

    plain_words = ('A step rule says how finely the simulation must look while one way of doing a job runs - every clock tick for an interrupt, '
                   'once per loop pass for polling, once per bit for a serial link - and where that number came from.')

    @treeObjectInit
    def __init__(self, name: str = '', variant: str = '', kind: str = 'knob', step_s: float = -1.0, worst_s: float = -1.0, basis: str = 'knob',
                 source: str = '', notes: str = '', manager=None):
        self.name = name          # = the variant's name ('read-button:gpio-poll')
        self.variant = variant    # an IsotopeVariant name
        self.kind = kind          # topology_words.STEP_KINDS
        self.step_s = step_s      # the step, seconds; -1 = not known (a knob)
        self.worst_s = worst_s    # how late the isotope can react, seconds; -1 = not known
        self.basis = basis        # derived | cited | knob | person
        self.source = source      # the cycle record reference, the datasheet section, the build flag
        self.notes = notes
