"""
@module materials_science.targetProfiles_basis

The targetProfiles object rows of the materials-science module, consolidated
(sap-2b, 2026-09-08) from the legacy one-class-per-file subpackage
`targetProfiles/` (propertyTarget.py, targetMaterialProfile.py) into the standard <concept>_basis.py.
"""
from objectTreeDecorators import treeObject, treeObjectInit


# ---- from targetProfiles/propertyTarget.py
class PropertyTarget(treeObject):
    """
    A single property target within a profile.

    Attributes:
        profileId: ID of the TargetMaterialProfile this belongs to
        propertyName: Name of the target property
        optimumValue: Ideal value for this property
        optimumRangeMin: Minimum of acceptable optimum range
        optimumRangeMax: Maximum of acceptable optimum range
        hardMinimum: Absolute minimum acceptable value
        hardMaximum: Absolute maximum acceptable value
        weight: Priority weight 0-1 for optimization
        unit: Unit of measurement
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 profileId='',
                 propertyName='',
                 optimumValue=0.0,
                 optimumRangeMin=0.0,
                 optimumRangeMax=0.0,
                 hardMinimum=0.0,
                 hardMaximum=0.0,
                 weight=0.0,
                 unit=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.profileId = profileId
        self.propertyName = propertyName
        self.optimumValue = optimumValue
        self.optimumRangeMin = optimumRangeMin
        self.optimumRangeMax = optimumRangeMax
        self.hardMinimum = hardMinimum
        self.hardMaximum = hardMaximum
        self.weight = weight
        self.unit = unit

    def __repr__(self):
        return f"PropertyTarget(id='{getattr(self, 'id', '?')}', property='{getattr(self, 'propertyName', '?')}', optimum={getattr(self, 'optimumValue', '?')})"


# ---- from targetProfiles/targetMaterialProfile.py
class TargetMaterialProfile(treeObject):
    """
    A named target profile for desired material properties.

    Attributes:
        name: Name of this target profile
        description: Description of the use case
        purposeId: ID of the PurposeCategory this profile targets
        referenceMaterialId: Optional ID of a baseline ReferenceMaterial
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 description='',
                 purposeId='',
                 referenceMaterialId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.description = description
        self.purposeId = purposeId
        self.referenceMaterialId = referenceMaterialId

    def __repr__(self):
        return f"TargetMaterialProfile(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}')"

