"""
@cross-cutting
@module nutrition.weight_basis
@tags @xc:bindings

nmp-6 — WeightObservation: one measured weight for a person. The
trajectory engine (weight_trajectory) projects; observations are
what actually happened — drift between the two is shown, and the
model's priors are tunable knobs, never silently recalibrated.

Q4 (Dustin default): trajectories are OWN-PROFILE ONLY by default —
household members see each other's only via explicit sharing (a
frontend/permission concern; the API serves per-person data and
says so).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.weight_trajectory
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-6
"""

from objectTreeDecorators import treeObject, treeObjectInit


class WeightObservation(treeObject):
    """One measured weight (a fact, never a projection)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('alex-2026-08-20').
        name: str = '',
        person_name: str = '',
        # ISO date of the measurement.
        date: str = '',
        # days since the projection start (drift math uses this when
        # set; 0 = align by date order).
        day_index: int = 0,
        weight_kg: float = 0.0,
        # measurement context knob ('morning-fasted' etc. — scale
        # noise is real; context travels with the number).
        context: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.date = date
        self.day_index = day_index
        self.weight_kg = weight_kg
        self.context = context
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


#: mpa-5: demo observations so the trends chart renders before real
#: measurements land (is_prior=True marks them as replaceable demo
#: rows — a real scale beats these).
SEED_WEIGHT_OBSERVATIONS = [
    {'name': f'demo-alex-{d}', 'person_name': 'demo-alex',
     'date': d, 'day_index': i, 'weight_kg': w,
     'context': 'morning', 'is_prior': True,
     'provenance_id': 'mpa-5',
     'notes': 'demo observation — replace with real measurements'}
    for i, (d, w) in enumerate((
        ('2026-08-25', 80.4), ('2026-08-28', 80.1),
        ('2026-08-31', 79.8), ('2026-09-01', 79.9)))
]
