"""
@module hwnocode.objects.hwnocode.Runtime

Runtime — one class per file (design §7). demo-4b (DEMONSTRABLES_PLAN.md §3 demo-4, his ruling 2026-10-04 quoted verbatim):
"the no-code solution seems to just be a single state, C (Hardware), along with Java/JavaFx (Native Bridge Backend and
Frontend), these should be their own runtimes."
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Runtime(treeObject):
    """What it is: the CATALOG of execution environments a no-code node can be placed into — the thing `HardwareNodePlacement.
    placement` (board/twin/bridge/backend/browser) is translated INTO for display (his ruling: C-on-hardware and Java/JavaFX
    the native bridge are their own runtimes, not just a placement string). One row = one runtime: where it runs (`kind`,
    `language`), the instance kind or device it executes on (`executes_on`), and how a person gets into it (`entered_via`:
    process | browser | firmware image | JVM). Six seeded: python-backend (the Polari engine process), typescript-browser
    (the Angular SPA tab), c-device (the flashed MCU — RULE 2: C/Verilog/SV only), c-twin (simavr standing in for the device,
    same .hex), java-bridge (the generated grpcbridge process — his "Native Bridge Backend"), javafx-native (a native-shell
    JavaFX process — his "Native Bridge Frontend"; not yet placed by any node, reserved). Every no-code node's `runtime`
    (on `HardwareNodePlacement.runtime` and the cmod graph payload) names one of these rows — derived, never typed in:
    hwnocode.custom.runtimes.runtime_for_kind is the ONE place that maps a node's kind/placement to a Runtime name.
    Related concepts: `HardwareNodePlacement`, `HardwareSolution`, cmod `CGraphNode`, `HardwareInterfaceBinding`.
    """

    plain_words = ('A runtime is one place a piece of a no-code solution can actually run — the device, its twin, the Java '
                   'bridge, the Python backend, a browser tab, or a native JavaFX bridge app — and how you get into it.')

    @treeObjectInit
    def __init__(self, name: str = '', kind: str = '', language: str = '', executes_on: str = '', entered_via: str = '',
                 description: str = '', notes: str = '', manager=None):
        self.name = name            # python-backend | typescript-browser | c-device | c-twin | java-bridge | javafx-native
        self.kind = kind            # backend-engine | browser-engine | device-firmware | device-twin | native-bridge-backend | native-bridge-frontend
        self.language = language    # Python | TypeScript | C | Java (JavaFX is Java)
        self.executes_on = executes_on  # the instance kind / device it runs on, in plain words
        self.entered_via = entered_via  # process | browser | firmware image | JVM
        self.description = description  # plain words — his ruling's own split (C hardware; Java/JavaFX native bridge back+front)
        self.notes = notes
