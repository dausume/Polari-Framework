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
NaturalSourcing Model

Sourcing for materials that can be obtained from natural sources
(plants, minerals, etc.) and refined using simple household processes.

Key characteristic: Accessible to anyone with basic household equipment
and simple, safe steps to follow.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.materialSourcing.materialSourcing import MaterialSourcing


class NaturalSourcing(MaterialSourcing):
    """
    Simple, household-level sourcing from natural sources.

    Materials that can be extracted/refined from plants, minerals,
    or other natural sources using easy household processes with
    simple, safe steps anyone can follow.

    Examples:
    - Extracting oils from seeds with a press
    - Refining plant fibers with household chemicals
    - Drying and processing natural resins

    Attributes:
        # Natural source
        sourceType: Type of source (plant, mineral, animal, fungal, bacterial)
        sourceName: Name of source organism/mineral
        sourcePart: Part used (seed, bark, leaf, root, etc.)
        sourceAvailability: How easy to find/grow (common, regional, cultivatable)

        # Household process
        processDescription: Step-by-step description of the process
        processSteps: Number of steps in the process
        processDifficulty: Difficulty level (very_easy, easy, moderate)
        estimatedTime: Estimated time to complete (hours)

        # Equipment needed (household level)
        equipmentNeeded: List of equipment (should be household items)
        specialEquipmentNeeded: Any non-standard equipment needed
        equipmentCost: Estimated cost for any equipment needed

        # Consumables/inputs
        inputMaterials: Other materials needed (household chemicals, etc.)
        inputMaterialsSafe: Whether inputs are safe/non-toxic
        inputMaterialsAvailability: Where to get inputs (grocery, hardware, etc.)

        # Safety
        safetyLevel: Safety level (safe, caution_needed, protective_gear_needed)
        safetyNotes: Safety precautions to follow
        childSafe: Whether process is safe with children present
        indoorSafe: Whether process can be done indoors
        ventilationRequired: Whether ventilation is needed

        # Yield
        typicalYield: Typical yield from process
        yieldUnit: Unit for yield
        yieldVariability: How much yield varies (low, moderate, high)

        # Seasonality
        seasonal: Whether source is seasonal
        bestSeason: Best season to harvest/collect
        storageOfSource: How to store raw source material

        Inherits all from MaterialSourcing
    """

    SOURCING_TYPE = 'natural'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 rawMaterialId='',
                 name='',
                 description='',
                 availability='common',
                 leadTime=0,
                 minimumOrderQuantity=0.0,
                 minimumOrderUnit='kg',
                 estimatedCostPerUnit=0.0,
                 costUnit='kg',
                 costCurrency='USD',
                 geographicRegion='',
                 locallyAvailable=True,
                 sustainabilityRating='good',
                 renewableSource=True,
                 carbonFootprint='',
                 qualityConsistency='variable',
                 certifications='',
                 notes='',
                 # Natural source
                 sourceType='plant',
                 sourceName='',
                 sourcePart='',
                 sourceAvailability='common',
                 # Household process
                 processDescription='',
                 processSteps=0,
                 processDifficulty='easy',
                 estimatedTime=0.0,
                 # Equipment needed
                 equipmentNeeded='',
                 specialEquipmentNeeded='',
                 equipmentCost=0.0,
                 # Consumables/inputs
                 inputMaterials='',
                 inputMaterialsSafe=True,
                 inputMaterialsAvailability='grocery store',
                 # Safety
                 safetyLevel='safe',
                 safetyNotes='',
                 childSafe=True,
                 indoorSafe=True,
                 ventilationRequired=False,
                 # Yield
                 typicalYield=0.0,
                 yieldUnit='g',
                 yieldVariability='moderate',
                 # Seasonality
                 seasonal=False,
                 bestSeason='',
                 storageOfSource=''):
        MaterialSourcing.__init__(
            self, manager=manager, branch=branch, id=id,
            rawMaterialId=rawMaterialId, sourcingType='natural',
            name=name, description=description,
            availability=availability, leadTime=leadTime,
            minimumOrderQuantity=minimumOrderQuantity,
            minimumOrderUnit=minimumOrderUnit,
            estimatedCostPerUnit=estimatedCostPerUnit,
            costUnit=costUnit, costCurrency=costCurrency,
            geographicRegion=geographicRegion,
            locallyAvailable=locallyAvailable,
            sustainabilityRating=sustainabilityRating,
            renewableSource=renewableSource,
            carbonFootprint=carbonFootprint,
            qualityConsistency=qualityConsistency,
            certifications=certifications, notes=notes)

        # Natural source
        self.sourceType = sourceType
        self.sourceName = sourceName
        self.sourcePart = sourcePart
        self.sourceAvailability = sourceAvailability

        # Household process
        self.processDescription = processDescription
        self.processSteps = processSteps
        self.processDifficulty = processDifficulty
        self.estimatedTime = estimatedTime

        # Equipment needed
        self.equipmentNeeded = equipmentNeeded
        self.specialEquipmentNeeded = specialEquipmentNeeded
        self.equipmentCost = equipmentCost

        # Consumables/inputs
        self.inputMaterials = inputMaterials
        self.inputMaterialsSafe = inputMaterialsSafe
        self.inputMaterialsAvailability = inputMaterialsAvailability

        # Safety
        self.safetyLevel = safetyLevel
        self.safetyNotes = safetyNotes
        self.childSafe = childSafe
        self.indoorSafe = indoorSafe
        self.ventilationRequired = ventilationRequired

        # Yield
        self.typicalYield = typicalYield
        self.yieldUnit = yieldUnit
        self.yieldVariability = yieldVariability

        # Seasonality
        self.seasonal = seasonal
        self.bestSeason = bestSeason
        self.storageOfSource = storageOfSource

    def __repr__(self):
        return f"NaturalSourcing(id='{self.id}', source='{self.sourceName}', difficulty='{self.processDifficulty}')"
