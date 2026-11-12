"""
@module cmod.objects.cmod.VarianceRulingRework

VarianceRulingRework - one class per file (design section 7); msv-2 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class VarianceRulingRework(treeObject):
    """What it is: WHAT WAS DONE TO FIX A RULED MISTAKE - the rework between the mistake and the re-measure (reflowed D6's joint, swapped R1 for
    220 ohm). It does not close the mistake: only a later in-band reading of the same point does.
    Related concepts: `VarianceRuling`, `MeasurementReading`.
    """

    plain_words = ('What someone did to fix a building mistake, before measuring it again.')

    @treeObjectInit
    def __init__(self, name: str = '', ruling: str = '', who: str = '', words: str = '', at: str = '', manager=None):
        self.name = name    # '<ruling>#w<n>'
        self.ruling = ruling    # the mistake VarianceRuling
        self.who = who
        self.words = words    # what was done
        self.at = at
