"""
@module computelod.objects.computelod.CompilerArtifact

Row class CompilerArtifact of the computelod module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CompilerArtifact(treeObject):
    """AN ARTIFACT OF ONE COMPILER (plan §F5): AST, IR, assembly, object. LLVM IR is not a rung — it belongs to a compiler implementation; the canonical path stays C → Compiler → ISA."""

    plain_words = ('A compiler artifact is one file a compiler produced on the way down the ladder: the source, the assembly, '
                   'the object code. Intermediate representations are artifacts of one compiler, not rungs of the ladder.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        kind: str = 'assembly',   # source | AST | IR | assembly | object
        compiler: str = '',
        source_ref: str = '',
        content_ref: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.kind = kind  # AST | IR | assembly | object
        self.compiler = compiler  # gcc | clang | …
        self.source_ref = source_ref  # the C source row / file
        self.content_ref = content_ref  # a file or dataset holding the artifact
        self.notes = notes
