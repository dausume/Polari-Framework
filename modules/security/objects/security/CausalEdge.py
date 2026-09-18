"""
@module security.objects.security.CausalEdge

Row class CausalEdge of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CausalEdge(treeObject):
    """LEDGER A — THE MAP (ct-1; design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §2).

    ONE row per (cause node, effect node, means), COUNTED and never duplicated — his rule from §17b: an
    aggregate ledger, not a log. `name` is exactly `cause|effect|means`, so the same crossing seen a thousand
    times is one row with `count` 1000.

    Nodes are strings of the form `kind:ref`:

        endpoint:PUT /api/MealEntry/{id}      a door, by METHOD + path TEMPLATE (never a real id)
        object:MealEntry:update               a class × verb
        event:trigger:daily-rollup            a trigger firing, an emitted event, or a STOMP topic
        solution:score-article                a no-code solution
        peer:kitchen-node:lease-write         another Polari instance, by the mechanism used
        external:odoo:main                    a system outside Polari, by configured name
        schedule:nightly-compost              a scheduled trigger

    `means` is HOW the edge was crossed: crude · trigger-fire · emit · solution-run · ws-publish · ws-subscribe ·
    shared-db · lease-write · bundle-export · bundle-install · send (external, with the wire in `detail`).

    CLASS-LEVEL ONLY. An instance id never appears here, so the map stays small (hundreds of rows, not millions)
    and survives a restart through the same debounced persist the observations use. The instance-level evidence
    behind an edge is the effect journal (Ledger B, `WriteJournalEntry`), which is per-trace and cleared when the
    next target is armed. The map as a whole has a ceiling (`POLARI_TRACE_MAP_MAX_ROWS`, default 5000; oldest
    `last_seen` pruned) so twenty targets over a year cannot grow it without bound.
    """

    @treeObjectInit
    def __init__(self, name: str = '', cause: str = '', effect: str = '', means: str = '', detail: str = '',
                 count: int = 0, first_seen: str = '', last_seen: str = '',
                 min_depth: int = 0, max_depth: int = 0, run_as: str = '',
                 sample_trace_id: str = '', target: str = ''):
        self.name = name                    # cause|effect|means — the dedup key
        self.cause = cause                  # kind:ref
        self.effect = effect                # kind:ref
        self.means = means                  # how the edge was crossed
        self.detail = detail                # the wire, the payload CLASSES, the trigger's note — never a payload
        self.count = count
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.min_depth = min_depth          # the shallowest chain depth this crossing was seen at
        self.max_depth = max_depth
        self.run_as = run_as                # for solution-run: the authority the solution ran with (definer/caller)
        self.sample_trace_id = sample_trace_id   # one chain to look up in the journal; ids only, never a person
        self.target = target                # the TraceTarget (class) whose arming wrote or last bumped this row
