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
CNCMachinedMoldMaterial Model

Base class for CNC machined mold materials. Defines composite material
suitability for creating molds via subtractive manufacturing.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.moldFabricationPurpose import MoldFabricationPurpose


class CNCMachinedMoldMaterial(MoldFabricationPurpose):
    """
    Base class for CNC machined mold materials.

    Defines composite material suitability for creating molds via
    subtractive manufacturing. Specific machining operations inherit
    from this class.

    Attributes:
        materialId: ID reference to the parent Material
        machiningOperation: Type of operation (milling, turning)
        machinabilityForMold: Machinability rating for mold quality
        toolWearRate: Tool wear rate with this material (low, medium, high)
        chipFormation: Chip type formed during machining
        dustGeneration: Dust generation level (requires extraction)
        coolantCompatibility: Compatible coolants for this material
        workHoldingMethod: Recommended work holding method
        internalStressRelief: Whether stress relief is needed
        finishPassStrategy: Recommended finish pass strategy
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='CNC Machined Mold Material',
                 description='Composite suitable for CNC machined molds',
                 minFeatureSize=0.0,
                 surfaceFinishRa=0.0,
                 dimensionalAccuracy=0.0,
                 thermalStabilityMax=0.0,
                 machiningOperation='',
                 machinabilityForMold=0.0,
                 toolWearRate='medium',
                 chipFormation='',
                 dustGeneration='medium',
                 coolantCompatibility='',
                 workHoldingMethod='',
                 internalStressRelief=False,
                 finishPassStrategy=''):
        MoldFabricationPurpose.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId,
            name=name, description=description,
            fabricationMethod='cnc_machining',
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax)
        self.machiningOperation = machiningOperation
        self.machinabilityForMold = machinabilityForMold
        self.toolWearRate = toolWearRate
        self.chipFormation = chipFormation
        self.dustGeneration = dustGeneration
        self.coolantCompatibility = coolantCompatibility
        self.workHoldingMethod = workHoldingMethod
        self.internalStressRelief = internalStressRelief
        self.finishPassStrategy = finishPassStrategy

    def __repr__(self):
        return f"CNCMachinedMoldMaterial(id='{self.id}', materialId='{self.materialId}', op='{self.machiningOperation}')"
