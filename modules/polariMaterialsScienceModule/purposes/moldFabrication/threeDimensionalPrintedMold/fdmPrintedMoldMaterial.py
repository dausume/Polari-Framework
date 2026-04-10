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
FDMPrintedMoldMaterial Model

Defines composite suitability for creating molds via FDM printing.
FDM molds typically require post-processing to reduce layer lines.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.threeDimensionalPrintedMold.threeDimensionalPrintedMoldMaterial import ThreeDimensionalPrintedMoldMaterial


class FDMPrintedMoldMaterial(ThreeDimensionalPrintedMoldMaterial):
    """
    FDM/FFF printed mold material parameters.

    Defines composite suitability for creating molds via FDM printing.
    FDM molds typically require post-processing to reduce layer lines.

    Attributes:
        materialId: ID reference to the parent Material
        nozzleTempForMold: Optimal nozzle temperature for mold quality (C)
        bedTempForMold: Optimal bed temperature (C)
        printSpeedForMold: Optimal print speed for mold quality (mm/s)
        infillPatternForMold: Recommended infill pattern for mold strength
        infillDensityForMold: Recommended infill density (%)
        wallCountForMold: Recommended wall/perimeter count
        layerAdhesionStrength: Interlayer adhesion quality
        vapourSmoothable: Whether material can be vapour smoothed
        sandable: How well material sands for surface finishing
        coatable: Compatibility with surface coatings/sealers
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='FDM Printed Mold Material',
                 description='Composite suitable for FDM printed molds',
                 minFeatureSize=0.3,
                 surfaceFinishRa=12.0,
                 dimensionalAccuracy=0.2,
                 thermalStabilityMax=60.0,
                 layerHeightForMold=0.1,
                 nozzleTempForMold=0.0,
                 bedTempForMold=0.0,
                 printSpeedForMold=0.0,
                 infillPatternForMold='gyroid',
                 infillDensityForMold=20.0,
                 wallCountForMold=3,
                 layerAdhesionStrength='medium',
                 vapourSmoothable=False,
                 sandable='good',
                 coatable='good'):
        ThreeDimensionalPrintedMoldMaterial.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId,
            name=name, description=description,
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax,
            printingTechnology='fdm',
            layerHeightForMold=layerHeightForMold,
            layerLineVisibility='visible')
        self.nozzleTempForMold = nozzleTempForMold
        self.bedTempForMold = bedTempForMold
        self.printSpeedForMold = printSpeedForMold
        self.infillPatternForMold = infillPatternForMold
        self.infillDensityForMold = infillDensityForMold
        self.wallCountForMold = wallCountForMold
        self.layerAdhesionStrength = layerAdhesionStrength
        self.vapourSmoothable = vapourSmoothable
        self.sandable = sandable
        self.coatable = coatable

    def __repr__(self):
        return f"FDMPrintedMoldMaterial(id='{self.id}', materialId='{self.materialId}')"
