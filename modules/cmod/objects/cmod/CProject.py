"""
@module cmod.objects.cmod.CProject

CProject — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CProject(treeObject):
    """What it is: One C PROJECT as Polari sees it (C_MODULARIZATION_PLAN.md §2, cmod-0): a NORMAL C project that builds with
    `make` alone — either a firmware template inside a module (the UNO: board/custom/firmware/uno, rendered per configuration)
    or a plain directory a person wrote. Its atoms are DERIVED by parsing (pycparser) into `polari-firmware.json`, the
    conformed manifest beside its Makefile; this row is that manifest's summary.
    Related concepts: `CModule`, `CFunctionAtom`, `CPort`, `CGraph`, board's `FirmwareVariant` (a configuration).
    """

    plain_words = 'A C project row is one ordinary firmware project — it builds with make on its own — whose functions Polari has read and listed as building blocks.'

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = '', root: str = '', board: str = '', mcu: str = '',
                     manifest_path: str = '', manifest_sha256: str = '', parser: str = '', parser_version: str = '',
                     atoms: int = 0, annotated: int = 0, isr_atoms: int = 0, pure_atoms: int = 0, not_isr_safe: int = 0,
                     modules: int = 0, configurations: str = '', cc: str = '', cc_version: str = '', cflags: str = '',
                     make_alone: str = '', conformed_at: str = '', notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.kind = kind  # template | plain
        self.root = root
        self.board = board
        self.mcu = mcu
        self.manifest_path = manifest_path
        self.manifest_sha256 = manifest_sha256
        self.parser = parser
        self.parser_version = parser_version
        self.atoms = atoms
        self.annotated = annotated
        self.isr_atoms = isr_atoms
        self.pure_atoms = pure_atoms
        self.not_isr_safe = not_isr_safe
        self.modules = modules
        self.configurations = configurations  # csv of the configuration names
        self.cc = cc
        self.cc_version = cc_version
        self.cflags = cflags
        self.make_alone = make_alone  # per configuration: ok + the .hex sha, as text
        self.conformed_at = conformed_at
        self.notes = notes
