"""
@module cmod.cmod_basis

The INDEX of the C-modularization rows (C_MODULARIZATION_PLAN.md §2). Classes live one-per-file under objects/cmod/; this
file re-exports them and holds the class list the server registers.
"""
from cmod.objects.cmod import CProject, CModule, CFunctionAtom, CPort, CGraph  # noqa: F401

#: every row class of the module, in registration order (CGraph: the row kind only in cmod-0 — cmod-1 fills it)
CMOD_CLASSES = [CProject, CModule, CFunctionAtom, CPort, CGraph]
