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
ThreeDimensionalPrintedMoldMaterial Model

Base class for 3D printed mold materials. Defines composite material
suitability for creating molds via additive manufacturing.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.moldFabricationPurpose import MoldFabricationPurpose


class ThreeDimensionalPrintedMoldMaterial(MoldFabricationPurpose):
    """
    Base class for 3D printed mold materials.

    Defines composite material suitability for creating molds via
    additive manufacturing. Specific printing technologies inherit
    from this class.

    Attributes:
        materialId: ID reference to the parent Material
        printingTechnology: Printing technology (fdm, sla, sls)
        layerHeightForMold: Optimal layer height for mold quality (mm)
        layerLineVisibility: Visibility of layer lines on mold surface
        shrinkageCompensation: Required shrinkage compensation (%)
        warpingTendency: Tendency to warp during printing (low, medium, high)
        supportRemovalDifficulty: Difficulty removing supports without damage
        postPrintCuringRequired: Whether additional curing is needed
        releaseAgentCompatibility: Compatible release agents
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='3D Printed Mold Material',
                 description='Composite suitable for 3D printing fine-resolution molds',
                 minFeatureSize=0.0,
                 surfaceFinishRa=0.0,
                 dimensionalAccuracy=0.0,
                 thermalStabilityMax=0.0,
                 printingTechnology='',
                 layerHeightForMold=0.0,
                 layerLineVisibility='visible',
                 shrinkageCompensation=0.0,
                 warpingTendency='medium',
                 supportRemovalDifficulty='medium',
                 postPrintCuringRequired=False,
                 releaseAgentCompatibility=''):
        MoldFabricationPurpose.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId,
            name=name, description=description,
            fabricationMethod='3d_printing',
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax)
        self.printingTechnology = printingTechnology
        self.layerHeightForMold = layerHeightForMold
        self.layerLineVisibility = layerLineVisibility
        self.shrinkageCompensation = shrinkageCompensation
        self.warpingTendency = warpingTendency
        self.supportRemovalDifficulty = supportRemovalDifficulty
        self.postPrintCuringRequired = postPrintCuringRequired
        self.releaseAgentCompatibility = releaseAgentCompatibility

    def __repr__(self):
        return f"ThreeDimensionalPrintedMoldMaterial(id='{self.id}', materialId='{self.materialId}', tech='{self.printingTechnology}')"
