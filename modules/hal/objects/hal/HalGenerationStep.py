"""
@module hal.objects.hal.HalGenerationStep

HalGenerationStep — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HalGenerationStep(treeObject):
    """One step of generating a HalCodeUnit — what went in, the rule applied, what came out, and where the data came from (hal-0).

    What it is: the debugging record the user asked for (2026-11-11: "pages that can fully review the exact steps for
    generating finalized code ... and where they pulled data from in steps"). `inputs` and `output` are plain text,
    `rule` the judgement made (or "lookup" when nothing was judged), `source` the module the data was read from and
    `cite` the datasheet / manual place behind it.
    Related concepts: HalCodeUnit (its trace), HalBinding, HalAccessMechanism.
    How it is derived: written by hal.custom.generate as it runs; same inputs, same steps.
    """

    @treeObjectInit
    def __init__(self, name: str = '', unit: str = '', index: int = 0, step: str = '', title: str = '', inputs: str = '', rule: str = '', output: str = '', source: str = '', cite: str = '', notes: str = '', manager=None):
        self.name = name
        self.unit = unit
        self.index = index
        self.step = step
        self.title = title
        self.inputs = inputs
        self.rule = rule
        self.output = output
        self.source = source
        self.cite = cite
        self.notes = notes
