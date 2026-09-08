"""
@module materials_science.rawMaterials_basis

The rawMaterials object rows of the materials-science module, consolidated
(sap-2b, 2026-09-08) from the legacy one-class-per-file subpackage
`rawMaterials/` (rawMaterial.py) into the standard <concept>_basis.py.
"""
from objectTreeDecorators import treeObject, treeObjectInit


# ---- from rawMaterials/rawMaterial.py
class RawMaterial(treeObject):
    """
    A raw/base material before processing.

    Represents fundamental material inputs that can be combined,
    processed, or used directly. Linked to sourcing information.

    Attributes:
        name: Common name of the raw material
        description: Description of the material
        materialType: Type (polymer, fiber, filler, additive, etc.)

        # Chemical information
        chemicalName: IUPAC or common chemical name
        chemicalFormula: Chemical formula if applicable
        casNumber: CAS registry number

        # Physical form
        physicalForm: Form (pellets, powder, flakes, fiber, liquid, etc.)
        particleSize: Particle size if powder/granular
        aspectRatio: Aspect ratio if fiber/flake

        # Purity/grade
        purity: Purity percentage
        grade: Material grade (technical, food, medical, etc.)

        # Storage requirements
        shelfLife: Shelf life in months
        storageConditions: Required storage conditions
        moistureSensitive: Whether moisture sensitive

        # Sourcing
        sourcingIds: List of MaterialSourcing IDs for this material

        # Processing notes
        processingNotes: Notes about processing this raw material

        # Role capabilities
        canBeBase: Whether this material can serve as a primary base material
        canBeAdditive: Whether this material can serve as a property-modifying additive
        canBeCompatibilizer: Whether this material can serve as a compatibilizer/emulsifier
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 description='',
                 materialType='',
                 # Chemical information
                 chemicalName='',
                 chemicalFormula='',
                 casNumber='',
                 # Physical form
                 physicalForm='',
                 particleSize='',
                 aspectRatio='',
                 # Purity/grade
                 purity=0.0,
                 grade='technical',
                 # Storage requirements
                 shelfLife=0,
                 storageConditions='',
                 moistureSensitive=False,
                 # Sourcing
                 sourcingIds='',
                 # Processing notes
                 processingNotes='',
                 # Role capabilities
                 canBeBase=False,
                 canBeAdditive=False,
                 canBeCompatibilizer=False):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.description = description
        self.materialType = materialType

        # Chemical information
        self.chemicalName = chemicalName
        self.chemicalFormula = chemicalFormula
        self.casNumber = casNumber

        # Physical form
        self.physicalForm = physicalForm
        self.particleSize = particleSize
        self.aspectRatio = aspectRatio

        # Purity/grade
        self.purity = purity
        self.grade = grade

        # Storage requirements
        self.shelfLife = shelfLife
        self.storageConditions = storageConditions
        self.moistureSensitive = moistureSensitive

        # Sourcing
        self.sourcingIds = sourcingIds

        # Processing notes
        self.processingNotes = processingNotes

        # Role capabilities
        self.canBeBase = canBeBase
        self.canBeAdditive = canBeAdditive
        self.canBeCompatibilizer = canBeCompatibilizer

    def __repr__(self):
        return f"RawMaterial(id='{getattr(self, 'id', '?')}', name='{getattr(self, 'name', '?')}', type='{getattr(self, 'materialType', '?')}')"

