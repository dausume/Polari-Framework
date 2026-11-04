"""
@module cmod.objects.cmod.TestProcedureStep

TestProcedureStep - one class per file (design section 7); msv-0b (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TestProcedureStep(treeObject):
    """What it is: ONE STEP of a TestProcedure: set up (power, flash), a power-off continuity check, a stimulus (press, hold, release, send a
    command, wait), a measurement (one MeasurementPoint) or an observation (a person's yes/no: the LED is lit). Its words and its expectation are
    derived; the left pane's picture is drawn from its plus / minus / part.
    Related concepts: `TestProcedure`, `MeasurementPoint`, `HardwareEvent`, `StructEdge`.
    """

    plain_words = ('One instruction in a test, with what you should see if the device was built right.')

    @treeObjectInit
    def __init__(self, name: str = '', procedure: str = '', order: int = 0, kind: str = 'setup', node: str = '', edge: str = '', event: str = '', point: str = '', words: str = '', expect: str = '', mode: str = '', plus_at: str = '', minus_at: str = '', part: str = '', basis: str = '', manager=None):
        self.name = name    # '<procedure>-s<n>'
        self.procedure = procedure    # a TestProcedure name
        self.order = order
        self.kind = kind    # setup | continuity | stimulus | measure | observe
        self.node = node    # the StructNode the step belongs to
        self.edge = edge    # the StructEdge a stimulus applies
        self.event = event    # its HardwareEvent
        self.point = point    # a MeasurementPoint (measure)
        self.words = words    # what to do
        self.expect = expect    # what a good build gives
        self.mode = mode    # the meter mode: V dc | I dc | continuity
        self.plus_at = plus_at    # the red probe: a net or a board pin
        self.minus_at = minus_at    # the black probe
        self.part = part    # the part to press or look at
        self.basis = basis    # where the expectation comes from
