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
MilledMoldMaterial Model

Defines composite suitability for creating molds via CNC milling.
Most common method for precision mold cavities.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.cncMachinedMold.cncMachinedMoldMaterial import CNCMachinedMoldMaterial


class MilledMoldMaterial(CNCMachinedMoldMaterial):
    """
    Milled mold material parameters.

    Defines composite suitability for creating molds via CNC milling.
    Most common method for precision mold cavities.

    Attributes:
        materialId: ID reference to the parent Material
        cuttingSpeedForMold: Optimal cutting speed for mold finish (m/min)
        feedPerToothForMold: Optimal feed for mold surface quality (mm/tooth)
        stepoverForFinish: Stepover for finish passes (% of tool diameter)
        depthOfCutFinish: Depth of cut for finish passes (mm)
        toolTypeForMold: Recommended tool type (ball, flat, bull)
        toolMaterialForMold: Recommended tool material (carbide, diamond, etc.)
        toolCoatingForMold: Recommended tool coating
        spindleSpeedForMold: Optimal spindle speed (RPM)
        climbVsConventional: Preferred milling direction
        restMachiningStrategy: Strategy for rest machining in corners
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Milled Mold Material',
                 description='Composite suitable for CNC milled molds',
                 minFeatureSize=0.1,
                 surfaceFinishRa=1.6,
                 dimensionalAccuracy=0.02,
                 thermalStabilityMax=100.0,
                 machinabilityForMold=0.0,
                 toolWearRate='medium',
                 dustGeneration='medium',
                 cuttingSpeedForMold=0.0,
                 feedPerToothForMold=0.0,
                 stepoverForFinish=10.0,
                 depthOfCutFinish=0.1,
                 toolTypeForMold='ball',
                 toolMaterialForMold='carbide',
                 toolCoatingForMold='',
                 spindleSpeedForMold=0.0,
                 climbVsConventional='climb',
                 restMachiningStrategy='pencil'):
        CNCMachinedMoldMaterial.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId,
            name=name, description=description,
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax,
            machiningOperation='milling',
            machinabilityForMold=machinabilityForMold,
            toolWearRate=toolWearRate,
            dustGeneration=dustGeneration)
        self.cuttingSpeedForMold = cuttingSpeedForMold
        self.feedPerToothForMold = feedPerToothForMold
        self.stepoverForFinish = stepoverForFinish
        self.depthOfCutFinish = depthOfCutFinish
        self.toolTypeForMold = toolTypeForMold
        self.toolMaterialForMold = toolMaterialForMold
        self.toolCoatingForMold = toolCoatingForMold
        self.spindleSpeedForMold = spindleSpeedForMold
        self.climbVsConventional = climbVsConventional
        self.restMachiningStrategy = restMachiningStrategy

    def __repr__(self):
        return f"MilledMoldMaterial(id='{self.id}', materialId='{self.materialId}')"
