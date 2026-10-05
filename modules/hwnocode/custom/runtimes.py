"""
@module hwnocode.custom.runtimes

THE RUNTIME CATALOG + the ONE mapping from a node's kind/placement to a `Runtime` name (demo-4b, his ruling 2026-10-04:
"the no-code solution seems to just be a single state, C (Hardware), along with Java/JavaFx (Native Bridge Backend and
Frontend), these should be their own runtimes."). `runtime_for_kind` is read by `hwnocode.custom.placement.place()` (every
HardwareNodePlacement row) and by cmod's graph payload (every CGraphNode is device-kind, so always `c-device` there — cmod
has no solution/board context to resolve twin vs board).
"""

#: six seeded rows — name, kind, language, where it executes, how it is entered, plain-words description
RUNTIME_ROWS = [
    {'name': 'python-backend', 'kind': 'backend-engine', 'language': 'Python', 'executes_on': 'the Polari backend instance (host process)',
     'entered_via': 'process',
     'description': 'The Python engine that runs every no-code state not placed on a device or in a browser — AnalysisCall, '
                    'ConditionalChain, StateChangeCommit and the rest of the existing no-code node kinds.'},
    {'name': 'typescript-browser', 'kind': 'browser-engine', 'language': 'TypeScript', 'executes_on': 'the Angular SPA, in a browser tab',
     'entered_via': 'browser',
     'description': 'The TS engine inside the Angular app: display/chart states, form subscriptions, reactive transforms — '
                    'anything that runs client-side on the page a person has open.'},
    {'name': 'c-device', 'kind': 'device-firmware', 'language': 'C', 'executes_on': 'the flashed microcontroller (a BoardInstance)',
     'entered_via': 'firmware image',
     'description': 'His "C (Hardware)" state: a c-atom or the glue-generated main/ISRs, compiled by cmod-glue and flashed as '
                    'one firmware image. RULE 2 — only C, Verilog or SystemVerilog ever runs here.'},
    {'name': 'c-twin', 'kind': 'device-twin', 'language': 'C', 'executes_on': 'simavr on the host, standing in for the device',
     'entered_via': 'firmware image',
     'description': 'The SAME firmware image as c-device, run under simavr when no BoardInstance is attached — hn-0\'s twin '
                    'proof: byte-identical to what a real board would be flashed with.'},
    {'name': 'java-bridge', 'kind': 'native-bridge-backend', 'language': 'Java', 'executes_on': 'the generated grpcbridge process on the host',
     'entered_via': 'JVM',
     'description': 'His "Native Bridge Backend": the generated Java process that decodes device frames UP into Polari rows '
                    'and routes Commands DOWN — the ONE split point between the device and the backend/browser.'},
    {'name': 'javafx-native', 'kind': 'native-bridge-frontend', 'language': 'Java (JavaFX)', 'executes_on': 'a native-shell JavaFX process on the host',
     'entered_via': 'JVM',
     'description': 'His "Native Bridge Frontend": a native desktop UI process (JavaFX) beside the Java bridge — reserved; no '
                    'no-code node places into it yet (today\'s solutions are browser-first).'},
]

#: node kinds that are C-on-the-device (mirrors hwnocode.custom.placement.DEVICE_KINDS + cmod's CMOD_KINDS)
_DEVICE_KINDS = {'HardwareSubgraph', 'CAtom', 'c-atom', 'hardware-subgraph', 'class', 'parser', 'frame', 'tick', 'rule'}
#: the split point (mirrors hwnocode.custom.placement.SPLIT_KINDS)
_BRIDGE_KINDS = {'HardwareInterface', 'hw-interface'}
#: client-side state classes (mirrors hwnocode.custom.placement.BROWSER_KINDS) + the display layer
_BROWSER_KINDS = {'EmitFrontendEvent', 'FormSubscription', 'ReactiveTransform', 'display'}


def runtime_for_kind(kind, placement='', refused=False):
    """One Runtime name for a node's kind — never typed in, the one place this mapping lives (demo-4b's rule, exactly:
    c-atom/glue/subgraph kinds -> c-device; hw-interface -> java-bridge; a browser-kind/display state -> typescript-browser;
    otherwise -> python-backend, the solution's default). board vs twin (`placement`) does not split the RUNTIME — both run
    the same C on the same simavr-or-silicon target (lane item 4: "board/twin -> c-device"); `c-twin` stays a seeded,
    described Runtime row for the twin PROCESS itself (hn-0's simavr host process), not a per-node assignment, same as
    `javafx-native` is seeded and described with no node placed into it yet. A refused node (Python drawn where C must run)
    names no runtime: it cannot run where it was drawn."""
    if refused or placement == 'refused':
        return ''
    if kind in _BRIDGE_KINDS:
        return 'java-bridge'
    if kind in _DEVICE_KINDS:
        return 'c-device'
    if kind in _BROWSER_KINDS:
        return 'typescript-browser'
    return 'python-backend'
