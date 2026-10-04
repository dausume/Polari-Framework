"""
@module cmod.cmod_page

/display/c-atoms — the C projects and their atoms as CONFIGURED tables only (no new component, no raw JSON —
C_MODULARIZATION_PLAN.md §2): the projects (parser, configurations, make-alone proof), the modules, the atoms (signature,
ports, resources, pure, ISR-safe, annotation), the ports (direction, C type, Polari type, unit), the cost per atom (text
bytes shipped / as a node, stack frame). cmod-1 adds four more configured tables: the graphs over atoms, their nodes and edges,
and the glue builds (the generated project, its sizes, the cost estimated vs measured, the twin equivalence proof). The canvas
overlay for a `c-atom` node is cmod-3's — still no new component here.
"""
from polariApiServer.module_pages_seed import _page, _row, _table

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
                              columns='name,kind,atom,stage,order,bindings,params,ports_summary,cost_bytes,isr_safe,pure,role',
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
          ]),
]
