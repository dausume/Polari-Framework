"""
@module computelod.computelod_basis

The INDEX of the computelod rows: classes live one-per-file under objects/computelod/; this file re-exports them
and holds the class list the server registers.

ONE conceptual ladder from software to materials (plan §F1): eleven rungs, each pointing at the
module that owns it (the ratified microchip ladder via design_level_ref, PSPP for fabrication, msci
for materials), KINDS as rows, downward ComputeMappings and upward CharacterizationMappings as
evidence-bearing rows, and the compute-lod tech tree for what to learn.
"""
from computelod.objects.computelod.ComputeLOD import ComputeLOD  # noqa: F401
from computelod.objects.computelod.ComputeKind import ComputeKind  # noqa: F401
from computelod.objects.computelod.ComputeMapping import ComputeMapping  # noqa: F401
from computelod.objects.computelod.CharacterizationMapping import CharacterizationMapping  # noqa: F401
from computelod.objects.computelod.CompilerArtifact import CompilerArtifact  # noqa: F401

#: every row class of the module, in registration order (the selftest asserts the count)
COMPUTELOD_CLASSES = [ComputeLOD, ComputeKind, ComputeMapping, CharacterizationMapping, CompilerArtifact]
