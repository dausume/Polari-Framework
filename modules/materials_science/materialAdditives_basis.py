"""
@module materials_science.materialAdditives_basis

The materialAdditives object rows of the materials-science module, consolidated
(sap-2b, 2026-09-08) from the legacy one-class-per-file subpackage
`materialAdditives/` (additiveCompatibility.py, compatibilizer.py, materialAdditive.py, propertyEffect.py) into the standard <concept>_basis.py.
"""
from objectTreeDecorators import treeObject, treeObjectInit


# ---- from materialAdditives/additiveCompatibility.py
class AdditiveCompatibility(treeObject):
    """
    Compatibility between an additive and a base material.

    Attributes:
        additiveId: ID of the MaterialAdditive
        baseMaterialId: ID of the base RawMaterial
        compatible: Whether the combination is compatible
        requiresCompatibilizer: Whether a compatibilizer is needed
        compatibilizerId: ID of the Compatibilizer if required
        maxLoadingWithBase: Maximum loading percent with this specific base
        notes: Additional compatibility notes
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 additiveId='',
                 baseMaterialId='',
                 compatible=False,
                 requiresCompatibilizer=False,
                 compatibilizerId='',
                 maxLoadingWithBase=0.0,
                 notes='',
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.additiveId = additiveId
        self.baseMaterialId = baseMaterialId
        self.compatible = compatible
        self.requiresCompatibilizer = requiresCompatibilizer
        self.compatibilizerId = compatibilizerId
        self.maxLoadingWithBase = maxLoadingWithBase
        self.notes = notes
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"AdditiveCompatibility(id='{getattr(self, 'id', '?')}', additive='{getattr(self, 'additiveId', '?')}', base='{getattr(self, 'baseMaterialId', '?')}', compatible={getattr(self, 'compatible', '?')})"


# ---- from materialAdditives/compatibilizer.py
class Compatibilizer(treeObject):
    """
    A material enabling combination of incompatible materials.

    Attributes:
        rawMaterialId: ID of the RawMaterial this compatibilizer references
        name: Display name of the compatibilizer
        compatibilizationType: Type (emulsifier, coupling_agent, dispersant, surfactant)
        effectiveness: Effectiveness rating 0-1
        compatibleBaseTypes: Comma-separated list of compatible base material types
        compatibleAdditiveTypes: Comma-separated list of compatible additive types
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 rawMaterialId='',
                 name='',
                 compatibilizationType='',
                 effectiveness=0.0,
                 compatibleBaseTypes='',
                 compatibleAdditiveTypes='',
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.rawMaterialId = rawMaterialId
        self.name = name
        self.compatibilizationType = compatibilizationType
        self.effectiveness = effectiveness
        self.compatibleBaseTypes = compatibleBaseTypes
        self.compatibleAdditiveTypes = compatibleAdditiveTypes
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"Compatibilizer(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}', type='{getattr(self, 'compatibilizationType', '?')}')"


# ---- from materialAdditives/materialAdditive.py
class MaterialAdditive(treeObject):
    """
    A material used as a property-modifying additive.

    Attributes:
        rawMaterialId: ID of the RawMaterial this additive references
        name: Display name of the additive
        description: Description of the additive and its uses
        additiveForm: Physical form (powder, fiber, flake, liquid)
        maxLoadingPercent: Maximum loading percentage by weight
        compatibilizerRequired: Whether a compatibilizer is needed
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 rawMaterialId='',
                 name='',
                 description='',
                 additiveForm='',
                 maxLoadingPercent=0.0,
                 compatibilizerRequired=False,
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.rawMaterialId = rawMaterialId
        self.name = name
        self.description = description
        self.additiveForm = additiveForm
        self.maxLoadingPercent = maxLoadingPercent
        self.compatibilizerRequired = compatibilizerRequired
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"MaterialAdditive(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}', form='{getattr(self, 'additiveForm', '?')}')"


# ---- from materialAdditives/propertyEffect.py
class PropertyEffect(treeObject):
    """
    Describes how an additive affects a specific property.

    Attributes:
        additiveId: ID of the MaterialAdditive
        propertyName: Name of affected property (e.g. 'Hardness')
        intent: Direction of effect ('+' for increase, '-' for decrease)
        normalizedEffectStrength: Effect strength normalized 0-1
        effectPerWeightPercent: Quantitative effect per weight percent added
        effectUnit: Unit for effectPerWeightPercent
        testConditions: Conditions under which effect was measured
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 additiveId='',
                 propertyName='',
                 intent='',
                 normalizedEffectStrength=0.0,
                 effectPerWeightPercent=0.0,
                 effectUnit='',
                 testConditions='',
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.additiveId = additiveId
        self.propertyName = propertyName
        self.intent = intent
        self.normalizedEffectStrength = normalizedEffectStrength
        self.effectPerWeightPercent = effectPerWeightPercent
        self.effectUnit = effectUnit
        self.testConditions = testConditions
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"PropertyEffect(id='{getattr(self, 'id', '?')}', additive='{getattr(self, 'additiveId', '?')}', property='{getattr(self, 'propertyName', '?')}', intent='{getattr(self, 'intent', '?')}')"

