"""
@module cmod.objects.cmod.ConfigOption

ConfigOption - one class per file (design section 7); cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "The words").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ConfigOption(treeObject):
    """What it is: ONE CANDIDATE for a catom - a template-level row (the System side) that says WHAT it would set, never whether it works (that is a
    `ConfigOptionGrade`, worked out per Bench Solution). `level` says how deep the change goes:
      values        a set of values for variables of one `group` (baud 115200 + U2X 1); the code stays. `isotope` names the isotope whose variables
                    these are ('' = variables every isotope of the catom shares).
      isotope       another way of doing the job (`isotope` = the IsotopeVariant to switch to); the code changes.
      part | module-board | board    used by the fix suggester (cfg-5): a part, a third-party board, another board.
    A value a person types that no option holds becomes an option of its own (source 'person'), so every value set has one home.
    Related concepts: `CatomConfiguration` / `ConfigChoice` (where an option is chosen), `ConfigOptionGrade` (whether it works), cmod.custom.config_groups.
    """

    plain_words = ('A configuration option is one candidate setting for a firmware piece - for example "115200 baud with double speed" - '
                   'with what it changes; whether it works is checked separately on each bench.')

    @treeObjectInit
    def __init__(self, name: str = '', catom: str = '', group: str = '', level: str = 'values', title: str = '', sets_json: str = '{}',
                 isotope: str = '', source: str = '', notes: str = '', manager=None):
        self.name = name            # '<catom>:<group>:<slug>'
        self.catom = catom          # the catom (AtomJob name) it is a candidate for
        self.group = group          # a variable group (cmod.custom.config_groups.GROUPS)
        self.level = level          # values | isotope | part | module-board | board
        self.title = title
        self.sets_json = sets_json  # {variable: value} for level values
        self.isotope = isotope      # values: the isotope whose variables these are ('' = shared); isotope: the one to switch to
        self.source = source        # where it comes from: a datasheet page, a firmware's own choice, 'person'
        self.notes = notes
