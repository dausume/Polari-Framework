"""
@module cmod.objects.cmod.StructFieldSamples

StructFieldSamples - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 4).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructFieldSamples(treeObject):
    """What it is: WHAT VALUES ONE STRUCT FIELD IS TESTED WITH. `kind` enumerable lists every value the field can take (a bool, an enum); `kind` samples
    says the field cannot be enumerated (an integer, an analog-derived value) and lists the declared test values ("700,750,800" millivolts). A node
    whose `exact` requirement names a value of a samples-kind field that is not declared here is blocked, in words, naming the field; a range
    requirement is not. Declared by a person; a suggestion can come from the field's cited sensor range.
    Related concepts: `StructObjectMap` (the struct), `StructNodeRequirement`, `CatomVariable` (the sensor's range).
    """

    plain_words = 'The sample values say which numbers a field that could be anything is actually tried with in the simulation.'

    @treeObjectInit
    def __init__(self, name: str = '', object_map: str = '', field: str = '', kind: str = 'samples', values: str = '', basis: str = '', notes: str = '',
                 manager=None):
        self.name = name              # '<object_map>:<field>'
        self.object_map = object_map  # a StructObjectMap name
        self.field = field
        self.kind = kind              # enumerable | samples
        self.values = values          # comma-separated
        self.basis = basis            # where the values came from (the sensor's cited range, a person)
        self.notes = notes
