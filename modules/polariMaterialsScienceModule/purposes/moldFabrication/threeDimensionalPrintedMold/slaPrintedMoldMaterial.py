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
SLAPrintedMoldMaterial Model

Defines composite suitability for creating molds via SLA/DLP printing.
SLA typically achieves better surface finish than FDM.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.threeDimensionalPrintedMold.threeDimensionalPrintedMoldMaterial import ThreeDimensionalPrintedMoldMaterial


class SLAPrintedMoldMaterial(ThreeDimensionalPrintedMoldMaterial):
    """
    SLA/DLP printed mold material parameters.

    Defines composite suitability for creating molds via resin printing.
    SLA typically achieves better surface finish than FDM.

    Attributes:
        materialId: ID reference to the parent Material
        exposureTimeForMold: Optimal exposure time for mold detail (s)
        layerHeightForMold: Layer height for mold quality (mm)
        resinType: Type of resin (standard, tough, high-temp, castable)
        uvStability: Stability under UV exposure over time
        heatDeflectionTemp: Heat deflection temperature (C)
        chemicalResistance: Resistance to casting resins/chemicals
        postCureTimeForMold: Post-cure time for optimal properties (min)
        brittleness: Material brittleness (low, medium, high)
        detailRetention: How well fine details hold up
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='SLA Printed Mold Material',
                 description='Composite suitable for SLA/DLP printed molds',
                 minFeatureSize=0.05,
                 surfaceFinishRa=2.0,
                 dimensionalAccuracy=0.05,
                 thermalStabilityMax=80.0,
                 layerHeightForMold=0.05,
                 exposureTimeForMold=0.0,
                 resinType='standard',
                 uvStability='medium',
                 heatDeflectionTemp=0.0,
                 chemicalResistance='medium',
                 postCureTimeForMold=0.0,
                 brittleness='medium',
                 detailRetention='excellent'):
        ThreeDimensionalPrintedMoldMaterial.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId,
            name=name, description=description,
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax,
            printingTechnology='sla',
            layerHeightForMold=layerHeightForMold,
            layerLineVisibility='minimal',
            postPrintCuringRequired=True)
        self.exposureTimeForMold = exposureTimeForMold
        self.resinType = resinType
        self.uvStability = uvStability
        self.heatDeflectionTemp = heatDeflectionTemp
        self.chemicalResistance = chemicalResistance
        self.postCureTimeForMold = postCureTimeForMold
        self.brittleness = brittleness
        self.detailRetention = detailRetention

    def __repr__(self):
        return f"SLAPrintedMoldMaterial(id='{self.id}', materialId='{self.materialId}', resinType='{self.resinType}')"
