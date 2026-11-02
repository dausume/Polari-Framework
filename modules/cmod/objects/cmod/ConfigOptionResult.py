"""
@module cmod.objects.cmod.ConfigOptionResult

ConfigOptionResult - one class per file (design section 7); cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "Three verdicts and the default").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ConfigOptionResult(treeObject):
    """What it is: WHAT ONE CHECK FOUND for one `ConfigOptionGrade` - the evidence under a grade. Checks run cheapest first by `layer`
    (1 closed form, 2 derived ranges, 3 simulation); once one says invalid, the later ones are recorded as skipped. `margin` is the share of the
    limit left (0.12 = 12 %; negative = past it); `gives_up` says what a compromise costs, as a number in words; `evidence` names where the numbers
    came from (a datasheet page, a run id).
    Related concepts: `ConfigOptionGrade` (the parent), cmod.custom.config_checks (the registered checks).
    """

    plain_words = ('An option result is what one test said about one candidate setting: passed, passed with a cost, failed, or skipped, '
                   'with the numbers behind it.')

    @treeObjectInit
    def __init__(self, name: str = '', grade: str = '', check: str = '', layer: int = 1, outcome: str = '', margin: float = 0.0,
                 gives_up: str = '', why: str = '', evidence: str = '', manager=None):
        self.name = name          # '<grade>#<check>'
        self.grade = grade        # the parent ConfigOptionGrade's name
        self.check = check        # the registered check's name
        self.layer = layer        # 1 closed form | 2 derived range | 3 simulation
        self.outcome = outcome    # invalid | compromise | ideal | skipped
        self.margin = margin
        self.gives_up = gives_up
        self.why = why
        self.evidence = evidence
