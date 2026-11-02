"""
@module cmod.objects.cmod.ConfigChoice

ConfigChoice - one class per file (design section 7); cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "Three verdicts and the default").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ConfigChoice(treeObject):
    """What it is: ONE CHOSEN OPTION for one variable group of a `CatomConfiguration` - which `ConfigOption` supplies the values, and whether it was
    chosen automatically (the best valid option) or by a person, with why. The group is the option's own; the values are the option's own. A person's
    choice keeps `why` = what it gives up against the automatic one. Whether a choice has turned invalid on some bench is worked out on read from the
    verdicts, never stored here.
    Related concepts: `CatomConfiguration` (the parent), `ConfigOption` (the values), `ConfigVerdict` (whether it works, per Bench Solution).
    """

    plain_words = ('A configuration choice records which candidate setting is used for one group of values, and whether Polari picked it '
                   'or a person did.')

    @treeObjectInit
    def __init__(self, name: str = '', configuration: str = '', option: str = '', chosen_by: str = 'auto', why: str = '', manager=None):
        self.name = name                    # '<configuration>:<group>'
        self.configuration = configuration  # a CatomConfiguration name
        self.option = option                # a ConfigOption name
        self.chosen_by = chosen_by          # auto | person
        self.why = why
