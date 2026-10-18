"""
@module cmod.objects.cmod.AtomJob

AtomJob - one class per file (design section 7). MISSION_PROFILE_SOLVER_PLAN.md section 8.3 / 8.5 (iso-0).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class AtomJob(treeObject):
    """What it is: one JOB a C atom does, said without any hardware - "read the button", "drive the LED", "read the temperature". The job is the
    question; its `IsotopeVariant` rows are every way of answering it on some hardware. The row holds what is declared (the words, which Purposes
    need the job, the atoms that do it today); which existing atoms really do it is checked against the atom rows when asked
    (`cmod.custom.isotope_variants`), so a renamed or missing atom shows up instead of staying quietly listed.
    Related concepts: `IsotopeVariant`, `CFunctionAtom`, `CIsotope` (one isotope per atom and binding - a different axis), `CapabilityDefinition` (a Purpose).
    """

    plain_words = ('An atom job is one thing a piece of firmware has to do - read a button, drive a light, read a temperature - said without '
                   'naming any hardware. The ways of doing it are its variants.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', plain: str = '', direction: str = '', purposes_json: str = '[]',
                 atoms_json: str = '[]', uses_macro: str = '', notes: str = '', manager=None):
        self.name = name                    # read-button | drive-led | sense-led-line | read-temperature | report-state | receive-command
        self.title = title
        self.plain = plain                  # the job in plain words
        self.direction = direction          # in (the world to the firmware) | out (the firmware to the world) | transport
        self.purposes_json = purposes_json  # [CapabilityDefinition names that need this job]
        self.atoms_json = atoms_json        # [CFunctionAtom names the seed lists as doing the job today] - checked against the atom rows when asked
        self.uses_macro = uses_macro        # the POLARI_NODE uses() pin macro that marks atoms of this job (BUTTON_PIN, LED_PIN, SENSE_PIN) - atoms are also DERIVED by it
        self.notes = notes
