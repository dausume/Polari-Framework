"""
@module cmod.objects.cmod.CatomConfiguration

CatomConfiguration - one class per file (design section 7); cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "The words").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CatomConfiguration(treeObject):
    """What it is: HOW ONE CATOM IS SET UP IN ONE FIRMWARE SOLUTION (the Solution side): which isotope it uses, and who picked it. The values live
    one level down, in one `ConfigChoice` per variable group (each names the `ConfigOption` whose values are used), so this row never copies a value.
    Isotope = how the catom does its job (changing it changes the code); configuration = the values it runs with (changing them keeps the code).
    Edited on the catom's page, per Firmware Solution.
    Related concepts: cmod `FirmwareSolution`, `IsotopeVariant` (the isotope), `ConfigChoice` (the values per group), `ConfigOption`.
    """

    plain_words = ('A catom configuration says how one firmware piece is set up in one firmware: which way it does its job, and (in its '
                   'choices) the values it runs with.')

    @treeObjectInit
    def __init__(self, name: str = '', firmware_solution: str = '', catom: str = '', isotope: str = '', isotope_chosen_by: str = 'auto',
                 notes: str = '', manager=None):
        self.name = name                            # '<firmware_solution>:<catom>'
        self.firmware_solution = firmware_solution  # a FirmwareSolution name
        self.catom = catom                          # the catom (AtomJob name)
        self.isotope = isotope                      # an IsotopeVariant name ('' = the catom has one way only)
        self.isotope_chosen_by = isotope_chosen_by  # auto | person
        self.notes = notes
