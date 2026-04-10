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
TurnedMoldMaterial Model

Defines composite suitability for creating molds via CNC turning.
Used for axially symmetric mold components.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.cncMachinedMold.cncMachinedMoldMaterial import CNCMachinedMoldMaterial


class TurnedMoldMaterial(CNCMachinedMoldMaterial):
    """
    Turned mold material parameters.

    Defines composite suitability for creating molds via CNC turning.
    Used for axially symmetric mold components.

    Attributes:
        materialId: ID reference to the parent Material
        cuttingSpeedForMold: Optimal cutting speed for mold finish (m/min)
        feedRateForMold: Optimal feed rate for surface quality (mm/rev)
        depthOfCutFinish: Depth of cut for finish passes (mm)
        insertGeometryForMold: Recommended insert geometry
        noseRadiusForMold: Recommended insert nose radius (mm)
        approachAngleForMold: Recommended approach angle (degrees)
        coolantDelivery: Coolant delivery method
        chuckPressure: Recommended chuck pressure considerations
        concentricityAchievable: Achievable concentricity (mm)
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Turned Mold Material',
                 description='Composite suitable for CNC turned molds',
                 minFeatureSize=0.05,
                 surfaceFinishRa=0.8,
                 dimensionalAccuracy=0.01,
                 thermalStabilityMax=100.0,
                 machinabilityForMold=0.0,
                 toolWearRate='medium',
                 dustGeneration='low',
                 cuttingSpeedForMold=0.0,
                 feedRateForMold=0.0,
                 depthOfCutFinish=0.05,
                 insertGeometryForMold='',
                 noseRadiusForMold=0.4,
                 approachAngleForMold=90.0,
                 coolantDelivery='flood',
                 chuckPressure='standard',
                 concentricityAchievable=0.01):
        CNCMachinedMoldMaterial.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId,
            name=name, description=description,
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax,
            machiningOperation='turning',
            machinabilityForMold=machinabilityForMold,
            toolWearRate=toolWearRate,
            dustGeneration=dustGeneration)
        self.cuttingSpeedForMold = cuttingSpeedForMold
        self.feedRateForMold = feedRateForMold
        self.depthOfCutFinish = depthOfCutFinish
        self.insertGeometryForMold = insertGeometryForMold
        self.noseRadiusForMold = noseRadiusForMold
        self.approachAngleForMold = approachAngleForMold
        self.coolantDelivery = coolantDelivery
        self.chuckPressure = chuckPressure
        self.concentricityAchievable = concentricityAchievable

    def __repr__(self):
        return f"TurnedMoldMaterial(id='{self.id}', materialId='{self.materialId}')"
