"""
@module polariNoCode.event_triggers

cal-1 (rows) / cal-2 (runtime) — "when X happens, run solution Y":
the no-code hook that makes event logic authorable as data.

EventTrigger.source_kind ∈
  object   {class, operations: [create|update|delete], fieldFilter}
           fired from the CRUDE lifecycle hook (publish_crude_change)
  event    {eventName, channel}    an EmitEvent from any completed run
  schedule {schedule: <ScheduleDefinition JSON>}   a time arrives (tick)
  window   {eventDefinition | calendar, relation: starts|ends,
            withinMinutes}         an event's start/end enters the window

Every firing is a TriggerFiring ROW (object-coherence, never
silent): what fired, from what, the execution id, the outcome or the
plain error. Firings are idempotent by occurrence_key (schedule and
window sources) and rate-limited by cooldown_s; event chaining is
bounded by max_depth (the SolutionInvocation depth idiom).

The dispatcher itself lives in polariNoCode.event_dispatcher (cal-2).
"""

from objectTreeDecorators import treeObject, treeObjectInit

SOURCE_KINDS = ('object', 'event', 'schedule', 'window')
FIRING_STATUSES = ('fired', 'skipped', 'failed', 'refused')


class EventTrigger(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        enabled: bool = True,
        # SOURCE_KINDS entry.
        source_kind: str = 'object',
        # the source's own configuration (shape per kind, above).
        source_json: str = '{}',
        # SolutionDefinition.name to run; the trigger payload is the
        # run's input context (contract inputs).
        solution_name: str = '',
        # extra literal inputs merged under the payload.
        inputs_json: str = '{}',
        # seconds between firings of THIS trigger (0 = none).
        cooldown_s: float = 0.0,
        # chained-event depth guard.
        max_depth: int = 8,
        # D11: backend-trusted as DEFINER until P6 auth nodes land —
        # stated on every firing row.
        run_as: str = 'definer',
        last_fired: str = '',
        fire_count: int = 0,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.enabled = enabled
        self.source_kind = source_kind
        self.source_json = source_json
        self.solution_name = solution_name
        self.inputs_json = inputs_json
        self.cooldown_s = cooldown_s
        self.max_depth = max_depth
        self.run_as = run_as
        self.last_fired = last_fired
        self.fire_count = fire_count
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class TriggerFiring(treeObject):
    """One firing of one trigger — the audit row."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        trigger_name: str = '',
        fired_at: str = '',
        source_kind: str = '',
        # what fired it: 'MealEntry:demo-alex-week-d1-dinner', an event
        # name, or an occurrence timestamp.
        source_ref: str = '',
        # idempotency key for schedule/window sources.
        occurrence_key: str = '',
        execution_id: str = '',
        # FIRING_STATUSES entry.
        status: str = 'fired',
        run_as: str = 'definer',
        depth: int = 0,
        # the run's final return value / emitted events summary.
        outcome_json: str = '{}',
        error: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.trigger_name = trigger_name
        self.fired_at = fired_at
        self.source_kind = source_kind
        self.source_ref = source_ref
        self.occurrence_key = occurrence_key
        self.execution_id = execution_id
        self.status = status
        self.run_as = run_as
        self.depth = depth
        self.outcome_json = outcome_json
        self.error = error
        self.notes = notes
