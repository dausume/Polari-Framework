"""
@module uno_core_demo.objects.uno_core_demo.DemoReadiness

DemoReadiness — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit

#: UNO_CORE_DEMO_PLAN.md §3: the six composed parts the manifest's `parts` block names, plus the composition itself
#: (the synthetic row whose `status` is the weakest of the six).
PARTS = ('firmware', 'bridge', 'polari_app', 'cross_domain', 'circuit', 'purpose', 'composition')


class DemoReadiness(treeObject):
    """What it is: ONE row per composed part of the UNO core demo (UNO_CORE_DEMO_PLAN.md §3) — whether the row(s)
    that part names actually exist on this instance, and that part's OWN status, read from its own class (never a
    hand-set claim). A seventh row, `composition`, carries the weakest of the other six: the demo is only as ready
    as its least-ready part.

    Related concepts: `cmod.objects.cmod.FirmwareSolution` (the `firmware` part), `grpcbridge.objects.java_bridge.
    HardwareBridgeDefinition` + `hardwareapps.objects.hardwareapps.BridgingCapability` (the `bridge` part — its
    STATUS is the capability's, not the bridge row's own fields), `polariApiServer.solutionDefinition.
    SolutionDefinition` + `DisplayDefinition` (the `polari_app` part: a solution AND a display, so it has no single
    `ref_class`), the Cross-Domain `SolutionDefinition` (`cross_domain`, validated by `hwnocode.custom.cross_domain.
    validate`), `electrodevice.objects.circuit.CircuitDefinition` (`circuit`, checked by `board.custom.
    electrical_check.check`), `cmod.objects.cmod.CapabilityDefinition` (`purpose` — the Purpose `button-clock-to-os`,
    D-ucd-12: a Purpose is a CapabilityDefinition in person-facing words).

    How it is measured or derived: materialized ONLY by `uno_core_demo.custom.readiness.readiness()` on a GET of
    `/api/uno-core-demo/readiness` (a door, never boot) — a pure read of each part's own live/seed rows, upserted by
    name; nothing here is ever hand-seeded with a claim (modules/README.md §5's refusal rule: an absent part is
    `exists=False, status='missing'`, named, never a crash and never a guess)."""

    plain_words = ('One row per part of the UNO core demo (firmware, bridge, the Polari app, the cross-domain '
                   'canvas, the circuit, the Purpose) plus one row for the whole composition — read fresh from '
                   'each part\'s own rows, never typed in by hand.')

    @treeObjectInit
    def __init__(self, name: str = '', part: str = '', ref_class: str = '', ref_name: str = '', refs: str = '',
                 exists: bool = False, status: str = '', why: str = '', checked_at: str = '', manager=None):
        self.name = name
        self.part = part               # firmware | bridge | polari_app | cross_domain | circuit | purpose | composition
        self.ref_class = ref_class     # the row class this part names (empty for `polari_app`, which names two)
        self.ref_name = ref_name       # the row name this part names (or 'solution + display' for polari_app)
        self.refs = refs               # 'Class:name[, Class:name]' — the configured table's `refs` column
        self.exists = exists           # the named row(s) are actually present, live or seeded
        self.status = status           # the part's OWN status word (its class's field, or 'missing')
        self.why = why                 # plain words — always, not only on a break
        self.checked_at = checked_at
