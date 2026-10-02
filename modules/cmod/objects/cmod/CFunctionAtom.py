"""
@module cmod.objects.cmod.CFunctionAtom

CFunctionAtom — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CFunctionAtom(treeObject):
    """What it is: One ATOM — a C function of a project, with declared PORTS (parameters and return mapped to Polari types),
    the RESOURCES it touches (registers by avr-libc's names and their peripheral, file-scope globals, library resources, the
    ISR vector it is), whether it is pure, whether it is ISR-safe, and its measured COST (text bytes in the shipped build and
    as a separate node, the stack frame from GCC's .su) — all derived by parsing, never typed in (C_MODULARIZATION_PLAN.md
    §2, §4, §9). A POLARI_NODE annotation (an empty macro) adds units and meanings without changing a byte of the .hex.
    Related concepts: `CProject`, `CModule`, `CPort`, `CGraph` (cmod-1: a no-code graph over atoms).
    """

    plain_words = 'An atom is one C function of a firmware project, described as a building block: what goes in, what comes out, which hardware it touches, and how much memory it costs.'

    @treeObjectInit
    def __init__(self, name: str = '', project: str = '', module: str = '', function: str = '', kind: str = '',
                     signature: str = '', line: int = 0, is_static: bool = False, isr_vector: str = '',
                     port_count: int = 0, ports_summary: str = '', resources_summary: str = '', registers: str = '',
                     peripherals: str = '', globals_touched: str = '', calls: str = '', pure: bool = False, pure_why: str = '',
                     isr_safe: str = '', isr_safe_why: str = '', atomic_block: bool = False, annotated: bool = False,
                     annotation_form: str = '', role: str = '', configs: str = '', text_bytes: int = 0,
                     in_shipped_build: bool = False, inlined: bool = False, text_bytes_noinline: int = 0,
                     stack_bytes: int = -1, stack_kind: str = '', measured_in: str = '', cost_why: str = '',
                     title: str = '', notes: str = '', manager=None):
        self.name = name
        self.project = project
        self.module = module
        self.function = function
        self.kind = kind  # function | isr | entry
        self.signature = signature
        self.line = line
        self.is_static = is_static
        self.isr_vector = isr_vector
        self.port_count = port_count
        self.ports_summary = ports_summary
        self.resources_summary = resources_summary
        self.registers = registers
        self.peripherals = peripherals
        self.globals_touched = globals_touched
        self.calls = calls
        self.pure = pure
        self.pure_why = pure_why
        self.isr_safe = isr_safe  # yes | no | undetermined | isr
        self.isr_safe_why = isr_safe_why
        self.atomic_block = atomic_block
        self.annotated = annotated
        self.annotation_form = annotation_form
        self.role = role
        self.configs = configs
        self.text_bytes = text_bytes
        self.in_shipped_build = in_shipped_build
        self.inlined = inlined
        self.text_bytes_noinline = text_bytes_noinline
        self.stack_bytes = stack_bytes  # -1 = no .su frame (naked)
        self.stack_kind = stack_kind
        self.measured_in = measured_in
        self.cost_why = cost_why
        self.title = title
        self.notes = notes
