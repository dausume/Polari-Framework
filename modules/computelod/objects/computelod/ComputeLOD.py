"""
@module computelod.objects.computelod.ComputeLOD

Row class ComputeLOD of the computelod module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ComputeLOD(treeObject):
    """ONE RUNG of the conceptual compute ladder (plan §F1). Software (C, compiler, ISA), architecture (microarchitecture, RTL), digital (logic, standard cells, devices), physical (layout, fabrication, materials). The rung REFERENCES its authoritative objects: `design_level_ref` into the microchip ladder, `owner_module` for the rest. die/package are not rungs."""

    plain_words = ('A level of detail is one rung of the ladder from a program written in C all the way down to the atoms of '
                   'a chip: source code, machine instructions, logic gates, transistors, layout, manufacturing process, '
                   'material. Each rung names the module that owns it.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        rank: int = 0,
        group: str = '',
        title: str = '',
        design_level_ref: str = '',
        owner_module: str = '',
        artifact_classes_json: str = '[]',
        languages_json: str = '[]',
        tools_json: str = '[]',
        concept_node: str = '',
        status: str = 'planned',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.rank = rank  # 1..11
        self.group = group  # software | architecture | digital | physical
        self.title = title
        self.design_level_ref = design_level_ref  # microchip DesignLevelDefinition.name when the rung IS a ladder rung
        self.owner_module = owner_module  # the module whose rows are the artifacts here
        self.artifact_classes_json = artifact_classes_json  # JSON [{module, class}]
        self.languages_json = languages_json
        self.tools_json = tools_json
        self.concept_node = concept_node  # TechNode.name in the compute-lod tree
        self.status = status  # planned | partial | live
        self.notes = notes
