"""
@module household.objects.household.SleepPreference

Row class SleepPreference of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from household.objects.household._shared import DINNER_TO_SLEEP_CITATION, DINNER_TO_SLEEP_DEFAULT_MIN

class SleepPreference(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '',
                 bedtime_hhmm: str = '23:00', wake_hhmm: str = '07:00',
                 # DEFAULT 120 (his call); the citation says ~3 h.
                 dinner_to_sleep_min: int = DINNER_TO_SLEEP_DEFAULT_MIN,
                 late_snack_ok: bool = False, stated_reason: str = '',
                 citation: str = DINNER_TO_SLEEP_CITATION,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.person_name = person_name
        self.bedtime_hhmm = bedtime_hhmm
        self.wake_hhmm = wake_hhmm
        self.dinner_to_sleep_min = dinner_to_sleep_min
        self.late_snack_ok = late_snack_ok
        self.stated_reason = stated_reason
        self.citation = citation
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
