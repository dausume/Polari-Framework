"""
@module cmod.objects.cmod.VarianceRuling

VarianceRuling - one class per file (design section 7); msv-2 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class VarianceRuling(treeObject):
    """What it is: A PERSON'S RULING ON ONE READING the simulation does not explain. It is one of:
    accepted-variance (the build is right and this is how it reads; scoped to this unit, this design or this part lot - D-msv-3, the unit by default),
    mistake (the build is wrong, with a cause; it stays OPEN until a later reading of the same point on the same unit is in band - derived, never
    typed), or measurement-error (the reading is wrong, not the board: measure again). The fault ranking's first suggestion at the moment of ruling is
    kept beside it as evidence, never as the ruling. The user (2026-11-04): "acceptable variance vs mistakes, recorded".
    Related concepts: `MeasurementReading`, `BuiltUnit`, `VarianceRulingRework`.
    """

    plain_words = ('A person\'s decision about one measurement that did not match: fine as it is, a building mistake (and what kind), or a bad measurement to take again.')

    @treeObjectInit
    def __init__(self, name: str = '', reading: str = '', unit: str = '', point: str = '', ruling: str = '', cause: str = '', scope: str = 'unit', part_lot: str = '', value: float = 0.0, hex_sha256: str = '', who: str = '', words: str = '', evidence_sha256: str = '', suggested: str = '', at: str = '', manager=None):
        self.name = name    # '<reading>-rule<n>' (the newest of a reading is the one in force)
        self.reading = reading    # the MeasurementReading ruled
        self.unit = unit    # its BuiltUnit
        self.point = point    # its MeasurementPoint
        self.ruling = ruling    # accepted-variance | mistake | measurement-error
        self.cause = cause    # a mistake's: cold-joint | bridge | open | wrong-part-value | reversed-polarity | wrong-pin | damaged-part | other
        self.scope = scope    # an accepted variance's: unit | design | lot
        self.part_lot = part_lot    # the lot, when scope = lot
        self.value = value    # the value ruled on (SI), so a later reading near it is covered
        self.hex_sha256 = hex_sha256    # the build it was read on (a ruling does not cross a rebuild)
        self.who = who    # who ruled
        self.words = words    # why, in the person's words
        self.evidence_sha256 = evidence_sha256    # a photo / file of what was found
        self.suggested = suggested    # the fault ranking's first suggestion when ruled (evidence beside the ruling, never the ruling)
        self.at = at
