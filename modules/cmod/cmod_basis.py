"""
@module cmod.cmod_basis

The INDEX of the C-modularization rows (C_MODULARIZATION_PLAN.md §2). Classes live one-per-file under objects/cmod/; this
file re-exports them and holds the class list the server registers.
"""
from cmod.objects.cmod import CProject, CModule, CFunctionAtom, CPort, CGraph, CGraphNode, CGraphEdge, CGlueBuild  # noqa: F401

#: every row class of the module, in registration order (cmod-0: the atoms; cmod-1: graphs over them + the generated glue)
CMOD_CLASSES = [CProject, CModule, CFunctionAtom, CPort, CGraph, CGraphNode, CGraphEdge, CGlueBuild]
