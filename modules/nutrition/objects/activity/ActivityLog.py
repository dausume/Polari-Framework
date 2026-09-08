"""
@module nutrition.objects.activity.ActivityLog

Row class ActivityLog of the nutrition module — one class per file (design §7), split
from activity_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ActivityLog(treeObject):
    """One logged activity session, with timing (decision 14)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('alex-2026-08-20-run').
        name: str = '',
        person_name: str = '',
        # a seeded ActivityDefinition name OR a raw Compendium code
        # (the analysis resolves either; code wins when both set).
        activity_name: str = '',
        activity_code: str = '',
        duration_min: float = 0.0,
        # nmp-5b: first-class timing — ISO date + start clock time.
        date: str = '',
        start_hhmm: str = '',
        # ties a log onto a plan day for the timeline view (0 = use
        # the date against the plan's start_date).
        day_index: int = 0,
        # the perceived-intensity knob: scales the MET +-30% (a felt
        # correction, labeled in results when != 1).
        perceived_intensity_factor: float = 1.0,
        # honest flag: was this session started without eating
        # beforehand (the fasted-exercise page uses it).
        fasted: bool = False,
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.activity_name = activity_name
        self.activity_code = activity_code
        self.duration_min = duration_min
        self.date = date
        self.start_hhmm = start_hhmm
        self.day_index = day_index
        self.perceived_intensity_factor = perceived_intensity_factor
        self.fasted = fasted
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
