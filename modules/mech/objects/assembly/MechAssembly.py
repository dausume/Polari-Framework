"""
@module mech.objects.assembly.MechAssembly

Row class MechAssembly of the mech module — one class per file (design §7); mxc-2.
The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from mech.objects.assembly._shared import ASSEMBLY_KINDS

class MechAssembly(treeObject):
    """One mechanical assembly — the bound SOLUTION (Systems vs
    Solutions rule, 2026-11-01: a System is the template, a Solution
    is the specific thing, bound to specific variants, simulated
    whole). The Bench analogue. Owns instances, joints, contacts and
    conflicts by back-reference (assembly_ref) and points at the
    composition node that carries its members and interfaces
    (D-mxc-8: mech EXTENDS composition, never copies it)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', kind='generic',
                 system_ref='', node_ref='', ground_instance='',
                 parameters_json='{}',
                 generator='', generator_version='', notes='',
                 provenance='', is_prior=True, provenance_id='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        #: ASSEMBLY_KINDS: desk | drawer_cassette | frame |
        #: clock_movement | printer | generic.
        self.kind = kind if kind in ASSEMBLY_KINDS else 'generic'
        #: The SYSTEM this Solution is bound from: '' = none; later a
        #: MechSystemDefinition row (kind + generator + parameter
        #: schema — the template), of which this assembly is one
        #: bound, variant-specific Solution. Not a row yet (mxc-2).
        self.system_ref = system_ref
        #: composition.CompositionNode by NAME — its members_json is
        #: the BOM (no BOM row anywhere in mech, §9.1) and it owns the
        #: InterfaceDefinition rows the joints write.
        self.node_ref = node_ref
        #: MechPartInstance name that is the fixed body (0 free DOF by
        #: definition; every other body's freedom is relative to it).
        self.ground_instance = ground_instance
        #: The generator's inputs (grid_x, grid_y, drawer_count,
        #: slide_length_mm ...) — D-mxc-3: parameters, not solids.
        self.parameters_json = parameters_json
        #: '' = hand-built; else the generator key ('gridfinity_desk')
        #: and its version, so a regenerated assembly is diffable.
        self.generator = generator
        self.generator_version = generator_version
        self.notes = notes
        #: Where the design came from (a plan section, a fixture id,
        #: a FreeCAD ingest sha) — free text beside provenance_id.
        self.provenance = provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
