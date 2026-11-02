"""
@module cmod.objects.cmod.StructNodeExecution

StructNodeExecution - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNodeExecution(treeObject):
    """What it is: ONE CATOM EXECUTION expected at a `StructNode` - the atom that runs to bring the structs to the node's requirements, with the isotope
    the Firmware Solution's configuration selected for it ('' = the atom's only way), in order. The isotope's `IsotopeStepRule` is what decides how
    finely the simulation steps at this node (the user: "the Catoms and isotopes selected for a node determine what stepping we do"). `assertion` names
    the CatomAssertion this execution is predicted from, when it was derived.
    Related concepts: `StructNode` (the parent), `CFunctionAtom`, `IsotopeVariant`, `IsotopeStepRule`, `CatomAssertion`.
    """

    plain_words = 'One execution says which piece of code is expected to run at this node, and which way of doing it was chosen.'

    @treeObjectInit
    def __init__(self, name: str = '', node: str = '', order: int = 1, atom: str = '', isotope: str = '', assertion: str = '', notes: str = '',
                 manager=None):
        self.name = name            # '<node>:<order>'
        self.node = node            # a StructNode name
        self.order = order
        self.atom = atom            # the atom's manifest name ('apps/light.led_follow_state')
        self.isotope = isotope      # an IsotopeVariant name ('drive-led:gpio-out'), or ''
        self.assertion = assertion  # the CatomAssertion name it was predicted from, or ''
        self.notes = notes
