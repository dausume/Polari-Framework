"""
@module cmod.cmod_page

/display/c-atoms — the C projects and their atoms as CONFIGURED tables only (no new component, no raw JSON —
C_MODULARIZATION_PLAN.md §2): the projects (parser, configurations, make-alone proof), the modules, the atoms (signature,
ports, resources, pure, ISR-safe, annotation), the ports (direction, C type, Polari type, unit), the cost per atom (text
bytes shipped / as a node, stack frame). cmod-1 adds four more configured tables: the graphs over atoms, their nodes and edges,
and the glue builds (the generated project, its sizes, the cost estimated vs measured, the twin equivalence proof).

demo-4 (DEMONSTRABLES_PLAN.md §3) adds /display/c-canvas — the ONE new component (`c-graph-canvas-panel`, justified like
firmware-installer-panel: a configured table cannot host the canvas itself, a graph picker, or render/build/prove buttons)
ABOVE described tables of the atoms available to drop, the derived TargetDefinition rows (badges on the canvas already;
the table is the same rows, described), the seeded "temperature sensor solution" CapabilityDefinition + its two
CapabilityInstance rows, and which HardwareSolutions use this graph (the reverse link — `/display/hardware-solutions`
carries the forward one). `/display/c-atoms` gets a link to the canvas plus the same "used by" table.
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _sapi, _firmware_panel


def _canvas(item_id, index, segments, title, graph, description=''):
    return {'id': item_id, 'index': index, 'type': 'component', 'rowSegmentsUsed': segments, 'gridColumnStart': None,
            'title': title, 'description': description, 'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': 'c-graph-canvas-panel', 'inputs': {'graph': graph}},
            'item': None, 'nestedRows': []}


SEED_CMOD_PAGE_DISPLAYS = [
    _page('c-atoms', 'c-atoms',
          'C atoms — the functions of a NORMAL C firmware project (it builds with make alone) read by Polari as building blocks: '
          'their ports, the registers and globals they touch, whether they are ISR-safe, and what each costs '
          '(`pol cmod conform uno`; `pol cmod atoms uno`; `pol cmod show hal_millis`). Data comes from parsing a project\'s own C '
          '(pycparser, in the framework process) — nothing here is authored by hand. The graphs built over these atoms become the '
          'board half of /display/hardware-solutions (hn-split: the glue IS a CGraph rendered here), and their build sizes feed '
          'the compat check on /display/firmware-installer.',
          'CFunctionAtom', [
              _row(0, [_table('cmod-projects', 0, 12, 'Projects — where the C lives, how it was parsed (pycparser, in the framework process), the '
                              'configurations rendered, and the proof that each builds with make alone (the .hex sha)', 'CProject',
                              description='What this is for: one row per C project Polari has read. One row = one CProject. Columns: '
                                          'atoms/annotated/isr_atoms/pure_atoms/not_isr_safe (counts from parsing), make_alone (proof it builds '
                                          'without Polari\'s own tooling), parser/parser_version/cc_version (how it was read), manifest_sha256 '
                                          '(the exact source snapshot this row describes).',
                              columns='name,title,kind,root,board,mcu,atoms,annotated,isr_atoms,pure_atoms,not_isr_safe,modules,configurations,'
                                      'parser,parser_version,cc_version,make_alone,manifest_sha256,conformed_at',
                              column_formats='name:ref:CProject')], min_height=160),
              _row(1, [_table('cmod-atoms', 0, 12, 'Atoms — one row per C function: its signature, ports, the resources it touches (registers by '
                              'avr-libc\'s names, globals, library resources, the ISR vector it is), pure, ISR-safe (and why not), the '
                              'POLARI_NODE annotation\'s role', 'CFunctionAtom',
                              description='What this is for: THE BUILDING BLOCK — one C function read as a Polari-usable unit. One row = one '
                                          'function. Columns: ports_summary (its parameters/return as typed ports), resources_summary/'
                                          'peripherals (registers and globals it touches, by avr-libc\'s own names), pure (no side effects), '
                                          'isr_safe/isr_safe_why (safe to call from an interrupt, and why not when false), annotated/role '
                                          '(the POLARI_NODE comment\'s declared role, when present).',
                              columns='name,kind,signature,ports_summary,resources_summary,peripherals,calls,pure,isr_safe,isr_safe_why,atomic_block,'
                                      'annotated,role,configs',
                              column_formats='name:ref:CFunctionAtom,project:ref:CProject')], min_height=320),
              _row(2, [_table('cmod-ports', 0, 7, 'Ports — direction, C type and AVR width, the Polari type it carries, unit and meaning; '
                              'source = derived from the C or settled by the annotation', 'CPort',
                              description='What this is for: one row per PARAMETER/RETURN of an atom, typed for wiring into a graph. One row '
                                          '= one port. Columns: direction (in | out), ctype/width_bytes (the real C type and its AVR width), '
                                          'polari_type/unit/meaning (what it means to Polari — derived from the C, or settled by an '
                                          'annotation when the C alone is ambiguous).',
                              columns='atom,port,direction,ctype,width_bytes,polari_type,unit,meaning,source',
                              column_formats='atom:ref:CFunctionAtom'),
                       _table('cmod-costs', 1, 5, 'Cost per atom — text bytes in the shipped build (0 when inlined or unused) and as a separate '
                              'node (-fno-inline), the stack frame from GCC\'s .su', 'CFunctionAtom',
                              description='What this is for: what one atom actually COSTS, measured, not estimated. One row = one atom\'s '
                                          'cost (same class as the atoms table, cost columns only). Columns: text_bytes/in_shipped_build '
                                          '(0 when GCC inlined or dropped it), text_bytes_noinline (its true size forced out, -fno-inline), '
                                          'stack_bytes/stack_kind (from GCC\'s own .su file), measured_in (which build measured it).',
                              columns='name,text_bytes,in_shipped_build,inlined,text_bytes_noinline,stack_bytes,stack_kind,measured_in,cost_why',
                              column_formats='name:ref:CFunctionAtom')], min_height=300),
              _row(3, [_table('cmod-modules', 0, 12, 'Modules — each .c with its .h, the files\' sha256, the atoms it defines', 'CModule',
                              description='What this is for: the FILE grouping above individual atoms — one .c/.h pair. One row = one '
                                          'CModule. Columns: role (hal | app | …), files/sha256 (exact fingerprints), atoms (which ones it '
                                          'defines).',
                              columns='name,project,module,role,files,atoms,sha256', column_formats='project:ref:CProject')], min_height=160),
              _row(4, [_table('cmod-graphs', 0, 12, 'Graphs over atoms (cmod-1) — a no-code graph that Polari renders into plain-C glue committed as a '
                              'real C project (`pol cmod render | build | prove | diff <graph>`); what the glue owns, the cost BEFORE building',
                              'CGraph',
                              description='What this is for: a NO-CODE composition of atoms that Polari can render back into real, compiling '
                                          'C. One row = one CGraph. Columns: base_configuration/class_name/replaces (what hand-written code '
                                          'this graph is meant to replace), node_count/edge_count/atom_count (its size), '
                                          'cost_estimate_bytes/cost_estimate_why (a prediction, checked against CGlueBuild\'s measurement below '
                                          'once built), glue_contains (what the generated project will own).',
                              columns='name,title,status,project,base_configuration,class_name,replaces,generated_project,node_count,edge_count,'
                                      'atom_count,cost_estimate_bytes,cost_estimate_why,glue_contains,graph_sha256',
                              column_formats='name:ref:CGraph')], min_height=160),
              _row(5, [_table('cmod-graph-nodes', 0, 7, 'Graph nodes — c-atom = an atom instance with its bindings (a literal or a knob); the glue '
                              'kinds: class, parser, frame, tick, rule', 'CGraphNode',
                              description='What this is for: one placed NODE inside a graph. One row = one node. Columns: kind (c-atom = an '
                                          'atom instance, or a glue kind: class | parser | frame | tick | rule), bindings/params (a literal or '
                                          'a knob wired to each port), cost_bytes/isr_safe/pure (carried over from the atom it instances).',
                              columns='name,kind,atom,stage,order,bindings,params,ports_summary,cost_bytes,isr_safe,pure,runtime,role',
                              column_formats='atom:ref:CFunctionAtom,graph:ref:CGraph'),
                       _table('cmod-graph-edges', 1, 5, 'Graph edges — data / field (values), tick / on-rx / on-command (when), calls (what an '
                              'atom calls itself, checked)', 'CGraphEdge',
                              description='What this is for: one WIRE between two graph nodes. One row = one edge. Columns: kind (data/field '
                                          '= a value flows; tick/on-rx/on-command = when it fires; calls = one atom calling another, type-'
                                          'checked), from_node/from_port -> to_node/to_port, ctype_from/ctype_to (checked compatible).',
                              columns='name,kind,from_node,from_port,to_node,to_port,order,ctype_from,ctype_to',
                              column_formats='graph:ref:CGraph')], min_height=300),
              _row(6, [_table('cmod-glue-builds', 0, 12, 'Glue builds — the generated files and their shas, make alone, avr-size of the glue vs '
                              'the hand-written app it replaces, the cost estimated vs measured, and the twin proof (same stimulus, frames '
                              'compared field by field)', 'CGlueBuild',
                              description='What this is for: the PROOF that a no-code graph is equivalent to the hand-written C it replaces. '
                                          'One row = one build-and-prove run of a graph. Columns: equivalent/proof (the verdict, in words), '
                                          'frames_compared/fields_compared/differences (the twin run that proves it: same stimulus into both '
                                          'builds, every field diffed), cost_estimate_bytes vs cost_measured_bytes (the graph\'s prediction '
                                          'checked against reality), ref_* (the hand-written build it is compared to).',
                              columns='name,graph,equivalent,proof,frames_compared,fields_compared,differences,hex_sha256,size_text,size_data,'
                                      'size_bss,ref_hex_sha256,ref_size_text,ref_size_data,ref_size_bss,cost_estimate_bytes,cost_measured_bytes,'
                                      'cost_why,stimulus,cycles,built_by,conformed,files,files_sha256,graph_sha256,proven_at',
                              column_formats='graph:ref:CGraph')], min_height=200),
              _row(7, [_sapi('cmod-used-by', 0, 12, 'Used by — the HardwareSolutions whose board half IS uno-sim-rig-graph (the reverse of '
                             '/display/hardware-solutions\' cgraph column); open it on the canvas at /display/c-canvas',
                             '/api/cmod/graphs/uno-sim-rig-graph', pick='used_by',
                             description='What this is for: the REVERSE link (demo-4 "both ways") — every HardwareSolution that places this '
                                         'graph on a board, derived from HardwareSolution.cgraph. Empty is honest (no solution uses it yet), '
                                         'not an error.')], min_height=140),
          ]),
    _page('c-canvas', 'c-canvas',
          'The no-code canvas opened on a cmod CGraph (demo-4, DEMONSTRABLES_PLAN.md §3): the EXISTING canvas, not a second editor — '
          'a graph picker, Render/Build/Prove buttons over `pol cmod render | build | prove`, and the atom/target/purpose rows the '
          'badges on the canvas come from. Linked from /display/c-atoms and /display/hardware-solutions; this page is the canvas\'s own '
          'home (D-demo-3: embedded where it belongs, not a third place).',
          'CGraph', [
              _row(0, [_canvas('c-canvas-panel', 0, 12, 'uno-sim-rig-graph on the canvas', 'uno-sim-rig-graph',
                               description='What this is for: THE DEMONSTRABLE — drag the graph picker to open any CGraph, drop a "C Atom" '
                                           'or "Temperature sensor solution" from the palette and wire it, or expand the Hardware Subgraph '
                                           'node to see its atoms, ports, wires and derived target badges. Render/Build/Prove call the same '
                                           'doors `pol cmod render|build|prove` do. demo-4b: every atom shown is a REAL node (one per '
                                           'CGraphNode), all in the c-device lane — never a single collapsed HardwareSubgraph wrapper here.')],
                   min_height=640),
              _row(1, [_table('c-canvas-runtimes', 0, 12, 'Nodes by runtime — every node this graph places, each resolved to one Runtime '
                              '(demo-4b: a CGraph is C on the device by construction, so every row here reads c-device)', 'CGraphNode',
                              description='What this is for: the SAME rows drawn as atoms on the canvas above, read as a table: which '
                                          'Runtime (hwnocode.Runtime catalog) each node resolved to. One row = one CGraphNode. Columns: '
                                          'kind (c-atom = an atom instance; class/parser/frame/tick/rule = the glue\'s own generated main/'
                                          'ISRs, read-only on the canvas), runtime (always c-device here — RULE 2, a CGraph never holds '
                                          'anything else), isr_safe/pure (carried from the atom).',
                              columns='name,kind,atom,stage,runtime,isr_safe,pure,role',
                              column_formats='atom:ref:CFunctionAtom,graph:ref:CGraph')], min_height=200),
              _row(2, [_table('c-canvas-atoms', 0, 12, 'Atoms available to drop — the graph\'s project\'s CFunctionAtom rows (drop a "C Atom" '
                              'palette node, then type one of these names into its overlay to wire it)', 'CFunctionAtom',
                              description='What this is for: which atoms a dropped "C Atom" node can be pointed at. One row = one atom of '
                                          'the project uno-sim-rig-graph is drawn over. Columns: same as /display/c-atoms\' atoms table.',
                              columns='name,kind,signature,ports_summary,resources_summary,isr_safe,role',
                              filter_field='project', filter_value='uno')], min_height=240),
              _row(3, [_table('c-canvas-targets', 0, 12, 'Target definitions — what each port or memory-field write actually controls, '
                              'derived from the atoms\' annotations/resources and matched against the board\'s BoardPin rows; unbound is '
                              'allowed and marked', 'TargetDefinition',
                              description='What this is for: the badges shown on the canvas, as a table. One row = one port (or field write) '
                                          'tied to a physical meaning. Columns: port_ref (node.port), kind (register | pin | memory-field | '
                                          'dynamic), controls (the quantity/actuator in plain words), lives_on (a BoardPin reference, or '
                                          "'unbound'), provenance (annotation = from the atom's own POLARI_NODE + resources; derived = a "
                                          'structural field edge).',
                              columns='port_ref,kind,controls,lives_on,board,direction,ctype,polari_type,unit,provenance',
                              column_formats='graph:ref:CGraph')], min_height=320),
              _row(4, [_table('c-canvas-capabilities', 0, 6, 'Purposes — a named, reusable grouping of tasks over a graph (his worked examples: '
                              '"temperature sensor solution", "data is retrieved from a temp sensor and gets sent back over USB to the OS", '
                              '"the OS turns the board\'s LED on and off on command"), with the targets it requires, the fields it exposes, '
                              'and its status DERIVED from its acceptance proof (hw priorities P1; D-ucd-12: a task may belong to several '
                              'Purposes)', 'CapabilityDefinition',
                              description='What this is for: a TEMPLATE Purpose, generalized from targets. One row = one Purpose. '
                                          'Columns: goal (the one-sentence claim, his words), status (planned | proven-on-twin | '
                                          'proven-on-hardware | failing — DERIVED from the latest ScenarioRun of acceptance_scenario, never '
                                          'hand-set), last_proof, required_targets (the port_refs it needs bound), exposes_fields (what it '
                                          'makes available once wired — temp_c), instance_count (how many instance rows use it, '
                                          'below).',
                              columns='name,title,goal,status,last_proof,required_targets,exposes_fields,instance_count',
                              column_formats='graph:ref:CGraph,acceptance_scenario:ref:Scenario'),
                       _table('c-canvas-instances', 1, 6, 'Purpose instances — one row per USE of a Purpose (two here: "define '
                              'multiple temperature sensors" proven as rows, not just a template)', 'CapabilityInstance',
                              description='What this is for: ONE use of a Purpose. One row = one instance. Columns: index (1, 2, … among '
                                          "this Purpose's instances), bindings (its targets' current lives_on, 'unbound' until a person "
                                          'ties this specific instance to a board pin — demo-5), status.',
                              columns='name,capability,index,bindings,status',
                              column_formats='capability:ref:CapabilityDefinition,graph:ref:CGraph')], min_height=200),
          ]),
    # ucd-0f (his ask 2026-10-08: "a link that shows just the UI for firmware no code and an export"): ONE lean page —
    # the canvas and the exports, nothing else; /display/firmware-solutions keeps the full set of described tables.
    _page('firmware', 'firmware',
          'Firmware — the no-code canvas for one Firmware Solution (tasks · schedule · register map on the board\'s pin map) and '
          'its EXPORT: a folder you download and build with plain CMake, no Polari needed (the rendered C, CMakeLists.txt, the '
          'avr-gcc toolchain file, a README that explains the firmware, every file\'s sha). The full tables are on '
          '/display/firmware-solutions; the hardware chain (pins → functions → peripherals → registers → bit fields) on '
          '/display/hardware-chain.', 'FirmwareSolution', [
              _row(0, [_firmware_panel('firmware-panel-lean', 0, 12, 'Firmware no-code — pick a solution, bind targets to pins, export',
                                       '/api/firmware/solutions', initial='uno-sim-rig',
                                       description='Pick a Firmware Solution. LEFT: its tasks grouped by Purpose. MIDDLE: the derived '
                                                   'schedule. RIGHT: the board\'s pin map — select a task, then a valid (outlined) pin, '
                                                   'confirm Register. EXPORT (top bar): writes the CMake project + README + manifest, '
                                                   'verifies it rebuilds on the engines image to the same hex sha, and gives the download.')],
                   min_height=640),
              _row(1, [_table('firmware-bindings-lean', 0, 12, 'Bindings — which board a solution is laid over, whether that board '
                              'meets every task requirement, and why not', 'HardwareBinding',
                              description='What this is for: ucd-0b2b (his ruling 2026-10-08) — a FirmwareSolution is hardware-'
                                          'agnostic; a HardwareBinding is the mask laying it over ONE board. One row = one binding. '
                                          'Columns: solution/board (the pair this binding is), status (valid | incomplete | invalid — '
                                          'computed from rows only: every required task requirement bound to a resource the board '
                                          'actually has), why (every unmet/conflicting/incompatible requirement, named), '
                                          'requirements_met/total, provenance (derived = the one converged default per solution; '
                                          'canvas = a person added it — kept).',
                              columns='name,solution,board,status,why,requirements_met,requirements_total,is_default,provenance',
                              column_formats='solution:ref:FirmwareSolution,board:ref:BoardDefinition')], min_height=200),
              _row(2, [_table('firmware-exports', 0, 12, 'Exports — every export made on this server: what it is, whether the CMake build '
                              'reproduced the Makefile build byte for byte (parity), the download', 'FirmwareExport',
                              description='What this is for: the record of each export. One row = one export of one solution. Columns: '
                                          'solution (link), board, target (both | board | twin), parity (identical = the exported CMake '
                                          'build produced the same firmware.hex as the proven Makefile build; differs; not-run), '
                                          'makefile_sha256 / cmake_sha256 (the two hex shas), tar_sha256, download_url (the tar.gz), '
                                          'created_at, status (created | verified | refused) and why. Exports are transient files; '
                                          'this row is the durable record.',
                              columns='name,solution,board,target,parity,makefile_sha256,cmake_sha256,tar_sha256,download_url,created_at,status,why',
                              column_formats='solution:ref:FirmwareSolution,download_url:link')]),
          ]),
    _page('firmware-solutions', 'firmware-solutions',
          'Firmware Solutions (fs-0, DEMONSTRABLES_PLAN.md §9): a `FirmwareSolution` takes a `CGraph` (its tasks = the '
          'graph\'s c-atoms) and a board (fixed or a run-time variable, validated it still exists) and derives its SCHEDULE '
          '(D-fs-1: from the atoms\' own ISR/tick/loop/init annotations, never authored) and REGISTER MAP (D-fs-2: bound/'
          'unbound/conflict against the board\'s own BoardPin rows). `uno-sim-rig` is the first one, over the existing '
          'uno-sim-rig-graph. Build/run reuse cmod-glue and the board installer/twin — nothing reimplemented here. The '
          'three-part canvas (task list · schedule lane · register map with the drag) is fs-1 — the canvas is now LIVE '
          '(the described tables below are the same rows, read-only confirmation).', 'FirmwareSolution', [
              _row(0, [_firmware_panel('firmware-solution-panel', 0, 12, 'The firmware canvas — tasks · schedule · register map (drag a target onto a pin)',
                                       '/api/firmware/solutions', initial='uno-sim-rig',
                                       description='What this is for: THE DEMONSTRABLE (fs-1) — pick a FirmwareSolution; LEFT lists its '
                                                   'tasks (name, kind, ports, resources, cost, lane), GROUPED by Purpose (hw priorities '
                                                   'P1 — the solution payload\'s purposes field names which Purpose(s) each task belongs '
                                                   'to; D-ucd-12: a task may belong to several); MIDDLE lays its schedule out in four '
                                                   'DERIVED lanes (init · isr · tick · loop, D-fs-1 — never authored), called tasks nested '
                                                   'under their caller; RIGHT draws the board\'s own pin map with bound pins coloured by '
                                                   'lane and unbound targets as chips — drag a chip onto a pin (or select it and click a '
                                                   'pin) to bind it (D-fs-2, `POST .../assign`); a drop that would conflict with another '
                                                   'task\'s pin is refused, named, never silently overwritten.')], min_height=640),
              _row(1, [_table('firmware-capabilities', 0, 12, 'Purposes — hw priorities P1: the GOAL each group of tasks across runtimes '
                              'achieves (his worked examples: "data is retrieved from a temp sensor and gets sent back over USB to the OS"; '
                              '"the OS turns the board\'s LED on and off on command"), its status DERIVED from its acceptance proof, and '
                              'which tasks per runtime realise it (D-ucd-12: a task may realise several Purposes)', 'CapabilityDefinition',
                              description='What this is for: THE THREAD that runs through the firmware/cross-domain/backend canvases — one '
                                          'row a person reads to ask "is this goal actually working" (HARDWARE_DEV_PRIORITIES.md §1). '
                                          'One row = one Purpose. Columns: goal (the one-sentence claim, his words), status '
                                          '(planned | proven-on-twin | proven-on-hardware | failing — DERIVED from the latest ScenarioRun of '
                                          'acceptance_scenario, never hand-set), last_proof (which run proved it, and when), '
                                          'tasks_by_runtime_json (c-device/java-bridge/python-backend/typescript-browser task refs), '
                                          'required_targets (the pins/registers it needs registered), acceptance_scenario (the firmwarefaults '
                                          'Scenario, kind=acceptance, that checks it).',
                              columns='name,title,goal,status,last_proof,acceptance_scenario,required_targets,exposes_fields,'
                                      'tasks_by_runtime_json,instance_count',
                              column_formats='graph:ref:CGraph,acceptance_scenario:ref:Scenario')], min_height=220),
              _row(2, [_table('firmware-solutions-table', 0, 12, 'Firmware solutions — a graph + a board in, a firmware '
                              'build out (flash or digital twin)', 'FirmwareSolution',
                              description='What this is for: one row per FirmwareSolution. Columns: graph (the CGraph whose '
                                          'c-atoms are its tasks), board_definition/board_variable (fixed or resolved at run '
                                          'time), runtime (c-device | c-digital-twin), validation/validation_why (board '
                                          'exists + usable, targets bound-or-named, no pin conflicts), task_count.',
                              columns='name,title,graph,board_definition,board_variable,board_resolved,runtime,status,'
                                      'validation,validation_why,task_count,last_build',
                              column_formats='graph:ref:CGraph,board_definition:ref:BoardDefinition')], min_height=160),
              _row(3, [_table('firmware-bindings', 0, 12, 'Bindings — which board a solution is laid over, whether that board '
                              'meets every task requirement, and why not', 'HardwareBinding',
                              description='What this is for: ucd-0b2b (his ruling 2026-10-08) — a FirmwareSolution is hardware-'
                                          'agnostic; a HardwareBinding is the mask laying it over ONE board. One row = one binding. '
                                          'Columns: solution/board (the pair this binding is), status (valid | incomplete | invalid — '
                                          'computed from rows only: every required task requirement bound to a resource the board '
                                          'actually has), why (every unmet/conflicting/incompatible requirement, named), '
                                          'requirements_met/total, provenance (derived = the one converged default per solution; '
                                          'canvas = a person added it — kept).',
                              columns='name,solution,board,status,why,requirements_met,requirements_total,is_default,provenance',
                              column_formats='solution:ref:FirmwareSolution,board:ref:BoardDefinition')], min_height=200),
              _row(4, [_table('firmware-schedule', 0, 12, 'Schedule — WHEN each task runs, DERIVED from the atoms\' own '
                              'ISR/tick/loop/init annotations (D-fs-1, his ruling: never authored by dragging)', 'ScheduleSlot',
                              description='What this is for: one row per task\'s schedule slot. One row = one ScheduleSlot. '
                                          'Columns: lane (isr | tick | loop | init | called), order (mirrors the glue\'s own '
                                          'emission order — never a second ordering scheme), trigger (the ISR vector or tick '
                                          'period macro), measured_cycles (-1 = not measured yet — cmod-0\'s cost is bytes/'
                                          'stack, not per-atom cycles).',
                              columns='solution,task,lane,order,trigger,period_ms,measured_cycles,isr_vector,provenance',
                              column_formats='solution:ref:FirmwareSolution')], min_height=280),
              _row(5, [_table('firmware-assignments', 0, 12, 'Register map — each task\'s target bound to the board\'s own '
                              'BoardPin rows, or named unbound (D-fs-2: the pin-map drag sets this; fs-0 builds the row + '
                              'the assign door)', 'RegisterAssignment',
                              description='What this is for: one row per required target. One row = one RegisterAssignment. '
                                          'Columns: target_kind (register | pin | peripheral | memory-field | bus | dynamic), '
                                          'controls (the physical quantity/actuator, in plain words), lives_on (a BoardPin '
                                          'reference or \'unbound\'), status (bound | unbound | conflict — two tasks '
                                          'claiming one pin with no cooperating relationship).',
                              columns='solution,task,port,target_kind,controls,lives_on,status,provenance,notes',
                              column_formats='solution:ref:FirmwareSolution')], min_height=280),
              _row(6, [_table('firmware-builds', 0, 12, 'Builds — the CGlueBuild rows this solution\'s graph produced '
                              '(cmod-glue, reused unchanged; `POST /api/firmware/solutions/{name}/build`)', 'CGlueBuild',
                              description='What this is for: the SAME CGlueBuild rows /display/c-atoms shows, filtered to '
                                          'this solution\'s graph. One row = one build-and-prove run.',
                              columns='name,graph,equivalent,proof,hex_sha256,size_text,size_data,size_bss,built_by',
                              column_formats='graph:ref:CGraph')], min_height=160),
              # ucd-0c (UNO_CORE_DEMO_PLAN.md §1, §5g item 5): the demo bench's circuit, as rows and as a checked
              # verdict — NOT on /display/hardware-chain (that page is the chip, Board -> SoC Pin -> ... -> RegisterField)
              # and NOT on the lean /display/firmware (canvas + export only, his ucd-0f ask) — here, beside the solution's
              # own register map, because the bench wires a BOARD pin (D6/D3/D2) onto an electrodevice circuit net.
              _row(7, [_table('board-pin-nets', 0, 6, 'Board pin nets — which board pin sits on which net of the demo '
                              'circuit, and whether it drives that net or only listens to it', 'BoardPinNet',
                              description='What this is for: one row per board-pin/circuit-net link (ucd-0c). One row = '
                                          'one BoardPinNet. Columns: board_pin/circuit_net (links), role (driver = this '
                                          'pin drives the net; input = it reads the net; ground = the board\'s own GND '
                                          'ties in here — never a BoardPin row itself, board_pin is \'\'). The demo bench '
                                          '(UNO_CORE_DEMO_PLAN.md §1): D6 drives LED_CONTROL (the LED through its 220 ohm '
                                          'resistor to GND); D3 only senses it (the jumper wire — the "sense pin"); D2 '
                                          'reads BUTTON_INPUT (the pushbutton, internal pull-up).',
                              columns='name,board_pin,circuit_net,role,provenance,notes',
                              column_formats='board_pin:ref:BoardPin,circuit_net:ref:CircuitNetDefinition'),
                       _table('circuit-check-findings', 6, 6, 'Circuit check — the electrical findings for '
                              'uno-button-clock on arduino-uno-r3 (LED current, single driver, shared ground, level '
                              'compatibility, the button\'s pull)', '',
                              description='What this is for: THE PHASE-1 ELECTRICAL CHECK (board.custom.electrical_check) '
                                          'over the demo circuit\'s rows. One row = one finding: rule (led_current | '
                                          'single_driver | shared_ground | level_compatible | pull_defined), status (ok | '
                                          'warn | refuse | undetermined — undetermined means a number was not cited, '
                                          'never guessed), subject, detail (the computed figure or the reason), cite (the '
                                          'board/datasheet/kit-part facts used). `GET /api/board/circuits/<circuit>/check'
                                          '?board=<board>`; `pol board circuit-check uno-button-clock`.',
                              columns='rule,status,subject,detail,cite',
                              data_path='/api/board/circuits/uno-button-clock/check?board=uno-button-clock@arduino-uno-r3')], min_height=260),   # the BINDING, so pull_defined reads D2's claim
          ]),
]
