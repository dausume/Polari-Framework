"""
@module materials_science.materialSourcing_basis

The materialSourcing object rows of the materials-science module, consolidated
(sap-2b, 2026-09-08) from the legacy one-class-per-file subpackage
`materialSourcing/` (materialSourcing.py) into the standard <concept>_basis.py.
"""
from objectTreeDecorators import treeObject, treeObjectInit


# ---- from materialSourcing/materialSourcing.py
class MaterialSourcing(treeObject):
    """
    Base class for material sourcing information.

    Tracks where materials come from, availability, cost, and
    sustainability considerations.

    Attributes:
        rawMaterialId: ID of the RawMaterial this sourcing applies to
        sourcingType: Type of sourcing (natural, open_source_local, commercial)
        name: Name/identifier for this sourcing option
        description: Description of the sourcing option

        # Availability
        availability: Availability level (abundant, common, limited, rare)
        leadTime: Typical lead time (days)
        minimumOrderQuantity: Minimum order quantity
        minimumOrderUnit: Unit for minimum order (kg, liter, piece, etc.)

        # Cost
        estimatedCostPerUnit: Estimated cost per unit
        costUnit: Unit for cost (kg, liter, etc.)
        costCurrency: Currency for cost

        # Location
        geographicRegion: Geographic region(s) available
        locallyAvailable: Whether available locally

        # Sustainability
        sustainabilityRating: Sustainability rating (poor, fair, good, excellent)
        renewableSource: Whether from renewable source
        carbonFootprint: Estimated carbon footprint notes

        # Quality
        qualityConsistency: Quality consistency (variable, moderate, consistent)
        certifications: Available certifications (ISO, food-safe, etc.)

        # Notes
        notes: Additional notes about this sourcing option

    Class Constants:
        SOURCING_TYPE: Identifier for the sourcing type
    """

    SOURCING_TYPE = 'base'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 rawMaterialId='',
                 sourcingType='',
                 name='',
                 description='',
                 # Availability
                 availability='common',
                 leadTime=0,
                 minimumOrderQuantity=0.0,
                 minimumOrderUnit='kg',
                 # Cost
                 estimatedCostPerUnit=0.0,
                 costUnit='kg',
                 costCurrency='USD',
                 # Location
                 geographicRegion='',
                 locallyAvailable=False,
                 # Sustainability
                 sustainabilityRating='fair',
                 renewableSource=False,
                 carbonFootprint='',
                 # Quality
                 qualityConsistency='moderate',
                 certifications='',
                 # Notes
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.rawMaterialId = rawMaterialId
        self.sourcingType = sourcingType
        self.name = name
        self.description = description

        # Availability
        self.availability = availability
        self.leadTime = leadTime
        self.minimumOrderQuantity = minimumOrderQuantity
        self.minimumOrderUnit = minimumOrderUnit

        # Cost
        self.estimatedCostPerUnit = estimatedCostPerUnit
        self.costUnit = costUnit
        self.costCurrency = costCurrency

        # Location
        self.geographicRegion = geographicRegion
        self.locallyAvailable = locallyAvailable

        # Sustainability
        self.sustainabilityRating = sustainabilityRating
        self.renewableSource = renewableSource
        self.carbonFootprint = carbonFootprint

        # Quality
        self.qualityConsistency = qualityConsistency
        self.certifications = certifications

        # Notes
        self.notes = notes

    def __repr__(self):
        return f"MaterialSourcing(id='{self.id}', name='{self.name}', type='{self.sourcingType}')"

