"""
@module cmod.objects.cmod.CModule

CModule — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CModule(treeObject):
    """What it is: One MODULE of a C project — a .c file with its .h (hal.c + hal.h), an app (apps/sim_rig.c), or a header on its
    own (board_config.h) — with the sha256 of each file and how many atoms it defines (C_MODULARIZATION_PLAN.md §2).
    Related concepts: `CProject`, `CFunctionAtom`.
    """

    plain_words = 'A C module row is one source file (and its header) of a firmware project, with how many building blocks it holds.'

    @treeObjectInit
    def __init__(self, name: str = '', project: str = '', module: str = '', role: str = '',
                     files: str = '', sha256: str = '', atoms: int = 0, notes: str = '', manager=None):
        self.name = name
        self.project = project
        self.module = module
        self.role = role  # hal | app | config | source | header
        self.files = files
        self.sha256 = sha256
        self.atoms = atoms
        self.notes = notes
