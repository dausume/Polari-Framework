"""
@module cmod.cmod_page

/display/c-atoms — the C projects and their atoms as CONFIGURED tables only (no new component, no raw JSON —
C_MODULARIZATION_PLAN.md §2): the projects (parser, configurations, make-alone proof), the modules, the atoms (signature,
ports, resources, pure, ISR-safe, annotation), the ports (direction, C type, Polari type, unit), the cost per atom (text
bytes shipped / as a node, stack frame). The no-code canvas over atoms is cmod-1's (the existing canvas, a `c-atom` kind).
"""
from polariApiServer.module_pages_seed import _page, _row, _table

SEED_CMOD_PAGE_DISPLAYS = [
    _page('c-atoms', 'c-atoms',
          'C atoms — the functions of a NORMAL C firmware project (it builds with make alone) read by Polari as building blocks: '
          'their ports, the registers and globals they touch, whether they are ISR-safe, and what each costs '
          '(`pol cmod conform uno`; `pol cmod atoms uno`; `pol cmod show hal_millis`)',
          'CFunctionAtom', [
              _row(0, [_table('cmod-projects', 0, 12, 'Projects — where the C lives, how it was parsed (pycparser, in the framework process), the '
                              'configurations rendered, and the proof that each builds with make alone (the .hex sha)', 'CProject',
                              columns='name,title,kind,root,board,mcu,atoms,annotated,isr_atoms,pure_atoms,not_isr_safe,modules,configurations,'
                                      'parser,parser_version,cc_version,make_alone,manifest_sha256,conformed_at',
                              column_formats='name:ref:CProject')], min_height=160),
              _row(1, [_table('cmod-atoms', 0, 12, 'Atoms — one row per C function: its signature, ports, the resources it touches (registers by '
                              'avr-libc\'s names, globals, library resources, the ISR vector it is), pure, ISR-safe (and why not), the '
                              'POLARI_NODE annotation\'s role', 'CFunctionAtom',
                              columns='name,kind,signature,ports_summary,resources_summary,peripherals,calls,pure,isr_safe,isr_safe_why,atomic_block,'
                                      'annotated,role,configs',
                              column_formats='name:ref:CFunctionAtom,project:ref:CProject')], min_height=320),
              _row(2, [_table('cmod-ports', 0, 7, 'Ports — direction, C type and AVR width, the Polari type it carries, unit and meaning; '
                              'source = derived from the C or settled by the annotation', 'CPort',
                              columns='atom,port,direction,ctype,width_bytes,polari_type,unit,meaning,source',
                              column_formats='atom:ref:CFunctionAtom'),
                       _table('cmod-costs', 1, 5, 'Cost per atom — text bytes in the shipped build (0 when inlined or unused) and as a separate '
                              'node (-fno-inline), the stack frame from GCC\'s .su', 'CFunctionAtom',
                              columns='name,text_bytes,in_shipped_build,inlined,text_bytes_noinline,stack_bytes,stack_kind,measured_in,cost_why',
                              column_formats='name:ref:CFunctionAtom')], min_height=300),
              _row(3, [_table('cmod-modules', 0, 12, 'Modules — each .c with its .h, the files\' sha256, the atoms it defines', 'CModule',
                              columns='name,project,module,role,files,atoms,sha256', column_formats='project:ref:CProject')], min_height=160),
          ]),
]
