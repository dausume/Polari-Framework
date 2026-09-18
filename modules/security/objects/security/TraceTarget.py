"""
@module security.objects.security.TraceTarget

Row class TraceTarget of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TraceTarget(treeObject):
    """THE ONE ARMED CLASS (ct-1; design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §2).

    His rule (2026-09-18): *"we should always only be doing tracing for one kind of object at a time and be able
    to put limits on how many tracing objects we generate at a time, or we could easily overwhelm ourselves in
    terms of data."* So causal recording is OFF unless exactly one row of this class is `active`, and that row
    names ONE class. A second arm while one is active is REFUSED naming the active one.

    DEV POSTURE ONLY (his ruling 2026-09-18, design §2/§10): a target cannot be armed outside dev posture, and
    neither ledger is written there. What reaches production are the finalized rows DERIVED from a dev trace.

    THE BUDGET RULE (design §2): every write checks the counters first. The FIRST budget hit disarms the target,
    stamps `stopped_because`, and raises one `SecurityEvent` — the stop is stated, never silent. `dropped` then
    counts every write the ledgers declined inside the window, so a map read as "complete" can be checked
    against it.

    THE PII BOUNDARY (his rule D18-1): `started_by` holds the arming person's opaque Keycloak `sub` and nothing
    else — never a username, an e-mail or a display name.

    One row per class ever traced: the row is KEPT after the target stops, because the set of rows IS the
    `coverage` block (design §2, "coverage, not silence") — a closure over a class that has never been a target
    answers *not traced*, never *nothing reaches it*.
    """

    #: why a target stopped (design §2)
    STOP_REASONS = ('manual', 'window', 'restart', 'budget-traces', 'budget-edges', 'budget-journal')

    @treeObjectInit
    def __init__(self, name: str = '', class_name: str = '', verbs_json: str = '[]',
                 max_traces: int = 200, max_edges: int = 500, max_journal_rows: int = 5000,
                 max_depth: int = 8, window_seconds: int = 3600,
                 started_by: str = '', started_at: str = '', stopped_at: str = '', stopped_because: str = '',
                 traces_opened: int = 0, edges_written: int = 0, journal_written: int = 0, dropped: int = 0,
                 active: bool = False):
        self.name = name                        # the row id — the class name (one row per class ever traced)
        self.class_name = class_name            # the ONE class this target traces
        self.verbs_json = verbs_json            # which verbs on that class OPEN a trace; [] = all five
        self.max_traces = max_traces            # distinct trace ids this target may open
        self.max_edges = max_edges              # CausalEdge rows this target may write OR bump
        self.max_journal_rows = max_journal_rows    # instance-level journal rows this target may write
        self.max_depth = max_depth              # how far down a chain recording follows (the trigger default)
        self.window_seconds = window_seconds    # the target disarms itself after this long
        self.started_by = started_by            # the arming person's Keycloak `sub` (D18-1) — never a name
        self.started_at = started_at
        self.stopped_at = stopped_at
        self.stopped_because = stopped_because  # one of STOP_REASONS
        self.traces_opened = traces_opened
        self.edges_written = edges_written
        self.journal_written = journal_written
        self.dropped = dropped                  # writes declined after the stop, inside the window
        self.active = active                    # exactly one row of this class may be True at a time
