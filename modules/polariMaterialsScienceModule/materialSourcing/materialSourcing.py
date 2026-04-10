#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
MaterialSourcing Model

Base class for material sourcing information.
Defines where and how materials can be obtained.

Sourcing Types (by production method complexity):
- NaturalSourcing: Simple household-level extraction from natural sources
  (e.g., pressing oils from seeds, extracting plant fibers)
- OpenSourceLocalSourcing: More complex but achievable with open-source tools
  (e.g., filament extrusion with DIY extruder, chemical synthesis with documented procedures)
- CommercialSourcing: Purchasing from vendors
  (NOT exclusive - vendors may use natural or open-source methods)
"""

from objectTreeDecorators import treeObject, treeObjectInit


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
