"""
@module materials_science.referenceMaterials_basis

The referenceMaterials object rows of the materials-science module, consolidated
(sap-2b, 2026-09-08) from the legacy one-class-per-file subpackage
`referenceMaterials/` (propertyValueSource.py, referenceMaterial.py) into the standard <concept>_basis.py.
"""
from objectTreeDecorators import treeObject, treeObjectInit


# ---- from referenceMaterials/propertyValueSource.py
class PropertyValueSource(treeObject):
    """
    A cited property value linked to provenance metadata.

    Links a property measurement to its source documentation via
    the DataProvenance system, enabling verification and comparison
    across sources.

    Attributes:
        referenceMaterialId: ID of the reference material this value belongs to
        propertyName: Name of the property (e.g., 'MeltingPoint', 'Viscosity')
        propertyClass: Class name of the property for linking

        # Value data
        value: The measured/reported value
        valueMin: Minimum value if a range
        valueMax: Maximum value if a range
        unit: Unit of measurement
        testConditions: Conditions under which value was measured

        # Quality indicators
        sampleSize: Number of samples if known
        standardUsed: Testing standard used (e.g., ASTM D638)

        # Provenance
        provenanceId: ID of the DataProvenance record for source citation
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 referenceMaterialId='',
                 propertyName='',
                 propertyClass='',
                 # Value data
                 value=0.0,
                 valueMin=0.0,
                 valueMax=0.0,
                 unit='',
                 testConditions='',
                 # Quality indicators
                 sampleSize=0,
                 standardUsed='',
                 # Provenance
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.referenceMaterialId = referenceMaterialId
        self.propertyName = propertyName
        self.propertyClass = propertyClass

        # Value data
        self.value = value
        self.valueMin = valueMin
        self.valueMax = valueMax
        self.unit = unit
        self.testConditions = testConditions

        # Quality indicators
        self.sampleSize = sampleSize
        self.standardUsed = standardUsed

        # Provenance
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"PropertyValueSource(id='{self.id}', material='{self.referenceMaterialId}', property='{self.propertyName}', value={self.value})"


# ---- from referenceMaterials/referenceMaterial.py
class ReferenceMaterial(treeObject):
    """
    Base class for reference materials with documented properties.

    Reference materials are well-characterized materials with known
    property values from literature, manufacturer data sheets, or
    community-sourced measurements.

    Attributes:
        name: Common name of the material (e.g., 'PLA', 'ABS')
        fullName: Full chemical/technical name
        description: Description of the material
        category: Material category (thermoplastic, thermoset, composite, etc.)
        chemicalFormula: Chemical formula if applicable
        casNumber: CAS registry number if applicable

        # Classification
        materialFamily: Broader family (polyester, polyamide, etc.)
        polymerType: Type of polymer (thermoplastic, thermoset, elastomer)

        # General characteristics
        biodegradable: Whether the material is biodegradable
        foodSafe: Whether the material is food-safe (general)
        uvResistant: General UV resistance
        chemicalResistance: General chemical resistance description

        # Reference data
        sourceCount: Number of sources with data for this material
        notes: Additional notes about this reference material

    Class Constants:
        MATERIAL_TYPE: Identifier for the material type
    """

    MATERIAL_TYPE = 'reference'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 fullName='',
                 description='',
                 category='thermoplastic',
                 chemicalFormula='',
                 casNumber='',
                 # Classification
                 materialFamily='',
                 polymerType='thermoplastic',
                 # General characteristics
                 biodegradable=False,
                 foodSafe=False,
                 uvResistant=False,
                 chemicalResistance='',
                 # Reference data
                 sourceCount=0,
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.fullName = fullName
        self.description = description
        self.category = category
        self.chemicalFormula = chemicalFormula
        self.casNumber = casNumber

        # Classification
        self.materialFamily = materialFamily
        self.polymerType = polymerType

        # General characteristics
        self.biodegradable = biodegradable
        self.foodSafe = foodSafe
        self.uvResistant = uvResistant
        self.chemicalResistance = chemicalResistance

        # Reference data
        self.sourceCount = sourceCount
        self.notes = notes

    def __repr__(self):
        return f"ReferenceMaterial(id='{self.id}', name='{self.name}')"

