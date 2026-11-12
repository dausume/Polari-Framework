"""
@module cmod.objects.cmod.TestStepMark

TestStepMark - one class per file (design section 7); msv-0b (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TestStepMark(treeObject):
    """What it is: ONE PERSON'S MARK ON A NON-MEASURE STEP of a TestSession: a setup or stimulus done, a continuity beep or none, an observation
    yes or no, or skipped with the reason. Never edited: a later mark of the same step supersedes it. A measure step is marked by its
    MeasurementReading instead.
    Related concepts: `TestSession`, `TestProcedureStep`.
    """

    plain_words = ('A tick next to one line of a test sheet: done, yes, no, beeped, or skipped.')

    @treeObjectInit
    def __init__(self, name: str = '', session: str = '', step: str = '', outcome: str = 'done', who: str = '', at: str = '', note: str = '', manager=None):
        self.name = name    # '<session>:<step>#m<n>'
        self.session = session    # a TestSession name
        self.step = step    # a TestProcedureStep name
        self.outcome = outcome    # done | yes | no | beep | no-beep | skipped
        self.who = who
        self.at = at
        self.note = note
