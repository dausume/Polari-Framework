"""
@module materials_science.formulation_basis

The formulation object rows of the materials-science module, consolidated
(sap-2b, 2026-09-08) from the legacy one-class-per-file subpackage
`formulation/` (formulation.py, formulationComponent.py, formulationIntent.py) into the standard <concept>_basis.py.
"""
from objectTreeDecorators import treeObject, treeObjectInit


# ---- from formulation/formulation.py
class Formulation(treeObject):
    """
    A composite material recipe.

    Attributes:
        name: Name of this formulation
        description: Description of the formulation
        targetProfileId: ID of the TargetMaterialProfile this aims to achieve
        baseMaterialId: ID of the primary base RawMaterial
        totalAdditiveLoadPercent: Total additive loading as weight percent
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 description='',
                 targetProfileId='',
                 baseMaterialId='',
                 totalAdditiveLoadPercent=0.0,
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.description = description
        self.targetProfileId = targetProfileId
        self.baseMaterialId = baseMaterialId
        self.totalAdditiveLoadPercent = totalAdditiveLoadPercent
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"Formulation(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}')"


# ---- from formulation/formulationComponent.py
class FormulationComponent(treeObject):
    """
    A component in a formulation recipe with explicit role declaration.

    Attributes:
        formulationId: ID of the parent Formulation
        materialId: ID of the RawMaterial used
        role: Role in the formulation (base, additive, compatibilizer)
        roleJustification: Explanation of why this role was assigned
        weightPercent: Weight percentage in the formulation
        orderOfAddition: Order in which this component is added
        mixingInstructions: Instructions for mixing this component
        expectedPropertyEffects: Comma-separated list of properties this component targets
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 formulationId='',
                 materialId='',
                 role='',
                 roleJustification='',
                 weightPercent=0.0,
                 orderOfAddition=0,
                 mixingInstructions='',
                 expectedPropertyEffects=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.formulationId = formulationId
        self.materialId = materialId
        self.role = role
        self.roleJustification = roleJustification
        self.weightPercent = weightPercent
        self.orderOfAddition = orderOfAddition
        self.mixingInstructions = mixingInstructions
        self.expectedPropertyEffects = expectedPropertyEffects

    def __repr__(self):
        return f"FormulationComponent(id='{getattr(self, 'id', '?')}', material='{getattr(self, 'materialId', '?')}', role='{getattr(self, 'role', '?')}', weight={getattr(self, 'weightPercent', '?')}%)"


# ---- from formulation/formulationIntent.py
class FormulationIntent(treeObject):
    """
    A desired property direction for a formulation.

    Attributes:
        formulationId: ID of the parent Formulation
        propertyName: Name of the target property
        direction: Desired direction (increase, decrease, maintain)
        priority: Priority level (critical, important, nice_to_have)
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 formulationId='',
                 propertyName='',
                 direction='',
                 priority=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.formulationId = formulationId
        self.propertyName = propertyName
        self.direction = direction
        self.priority = priority

    def __repr__(self):
        return f"FormulationIntent(id='{getattr(self, 'id', '?')}', property='{getattr(self, 'propertyName', '?')}', direction='{getattr(self, 'direction', '?')}')"

