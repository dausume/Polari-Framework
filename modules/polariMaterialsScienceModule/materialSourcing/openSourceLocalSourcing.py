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
OpenSourceLocalSourcing Model

Sourcing for materials that require more complex processes but can be
produced independently using open-source tools, designs, and documentation.

Key characteristic: More complex than household processes, but achievable
with readily available open-source equipment/designs you can build or acquire.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.materialSourcing.materialSourcing import MaterialSourcing


class OpenSourceLocalSourcing(MaterialSourcing):
    """
    Complex but achievable sourcing using open-source tools.

    Materials that require more sophisticated equipment or processes,
    but can be produced independently using open-source designs,
    documentation, and readily available components.

    Examples:
    - Filament extrusion with open-source extruder designs
    - Chemical synthesis with documented open-source procedures
    - Bioreactor-based production with DIY bioreactor plans

    Attributes:
        # Open source resources
        projectName: Name of the open-source project
        projectUrl: URL to the project/documentation
        projectLicense: License (GPL, MIT, CC, etc.)
        documentationQuality: Quality of docs (poor, fair, good, excellent)
        communityActive: Whether community is active
        communityUrl: URL to community (forum, Discord, etc.)

        # Equipment/tools required
        equipmentDesigns: Open-source equipment designs needed
        equipmentBuildDifficulty: Difficulty to build equipment (easy, moderate, hard)
        equipmentBuildTime: Time to build equipment (hours)
        equipmentBuildCost: Cost to build equipment
        prebuiltAvailable: Whether pre-built equipment is available to purchase
        prebuiltCost: Cost of pre-built option if available

        # Skills required
        skillsRequired: Skills needed (electronics, welding, chemistry, etc.)
        skillLevel: Overall skill level (beginner, intermediate, advanced)
        trainingResources: Available training resources

        # Process complexity
        processComplexity: Complexity level (moderate, complex, very_complex)
        processSteps: Number of major steps
        estimatedSetupTime: Time to set up and learn (hours)
        estimatedProductionTime: Time per batch once set up (hours)

        # Input materials
        inputMaterials: Input materials required
        inputMaterialsSourcing: Where to source inputs
        inputMaterialsCost: Cost of inputs per batch

        # Safety and requirements
        safetyRequirements: Safety equipment/precautions needed
        spaceRequired: Space requirements (desk, garage, workshop, etc.)
        powerRequirements: Electrical power requirements
        ventilationRequirements: Ventilation requirements
        wasteHandling: How to handle waste products

        # Quality and yield
        typicalYield: Typical yield per batch
        yieldUnit: Unit for yield
        qualityAchievable: Quality level achievable (basic, good, professional)
        qualityControlMethods: Methods to verify quality

        # Iteration and improvement
        activelyDeveloped: Whether designs are actively improved
        versionNumber: Current version of the process/design
        improvementHistory: History of improvements

        Inherits all from MaterialSourcing
    """

    SOURCING_TYPE = 'open_source_local'

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
                 renewableSource=False,
                 carbonFootprint='',
                 qualityConsistency='moderate',
                 certifications='',
                 notes='',
                 # Open source resources
                 projectName='',
                 projectUrl='',
                 projectLicense='',
                 documentationQuality='fair',
                 communityActive=False,
                 communityUrl='',
                 # Equipment/tools required
                 equipmentDesigns='',
                 equipmentBuildDifficulty='moderate',
                 equipmentBuildTime=0.0,
                 equipmentBuildCost=0.0,
                 prebuiltAvailable=False,
                 prebuiltCost=0.0,
                 # Skills required
                 skillsRequired='',
                 skillLevel='intermediate',
                 trainingResources='',
                 # Process complexity
                 processComplexity='moderate',
                 processSteps=0,
                 estimatedSetupTime=0.0,
                 estimatedProductionTime=0.0,
                 # Input materials
                 inputMaterials='',
                 inputMaterialsSourcing='',
                 inputMaterialsCost=0.0,
                 # Safety and requirements
                 safetyRequirements='',
                 spaceRequired='garage',
                 powerRequirements='',
                 ventilationRequirements='',
                 wasteHandling='',
                 # Quality and yield
                 typicalYield=0.0,
                 yieldUnit='kg',
                 qualityAchievable='good',
                 qualityControlMethods='',
                 # Iteration and improvement
                 activelyDeveloped=False,
                 versionNumber='',
                 improvementHistory=''):
        MaterialSourcing.__init__(
            self, manager=manager, branch=branch, id=id,
            rawMaterialId=rawMaterialId, sourcingType='open_source_local',
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

        # Open source resources
        self.projectName = projectName
        self.projectUrl = projectUrl
        self.projectLicense = projectLicense
        self.documentationQuality = documentationQuality
        self.communityActive = communityActive
        self.communityUrl = communityUrl

        # Equipment/tools required
        self.equipmentDesigns = equipmentDesigns
        self.equipmentBuildDifficulty = equipmentBuildDifficulty
        self.equipmentBuildTime = equipmentBuildTime
        self.equipmentBuildCost = equipmentBuildCost
        self.prebuiltAvailable = prebuiltAvailable
        self.prebuiltCost = prebuiltCost

        # Skills required
        self.skillsRequired = skillsRequired
        self.skillLevel = skillLevel
        self.trainingResources = trainingResources

        # Process complexity
        self.processComplexity = processComplexity
        self.processSteps = processSteps
        self.estimatedSetupTime = estimatedSetupTime
        self.estimatedProductionTime = estimatedProductionTime

        # Input materials
        self.inputMaterials = inputMaterials
        self.inputMaterialsSourcing = inputMaterialsSourcing
        self.inputMaterialsCost = inputMaterialsCost

        # Safety and requirements
        self.safetyRequirements = safetyRequirements
        self.spaceRequired = spaceRequired
        self.powerRequirements = powerRequirements
        self.ventilationRequirements = ventilationRequirements
        self.wasteHandling = wasteHandling

        # Quality and yield
        self.typicalYield = typicalYield
        self.yieldUnit = yieldUnit
        self.qualityAchievable = qualityAchievable
        self.qualityControlMethods = qualityControlMethods

        # Iteration and improvement
        self.activelyDeveloped = activelyDeveloped
        self.versionNumber = versionNumber
        self.improvementHistory = improvementHistory

    def __repr__(self):
        return f"OpenSourceLocalSourcing(id='{self.id}', project='{self.projectName}', skill='{self.skillLevel}')"
