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
SLSPrintedMoldMaterial Model

Defines composite suitability for creating molds via SLS powder sintering.
SLS offers good dimensional accuracy without support structures.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.threeDimensionalPrintedMold.threeDimensionalPrintedMoldMaterial import ThreeDimensionalPrintedMoldMaterial


class SLSPrintedMoldMaterial(ThreeDimensionalPrintedMoldMaterial):
    """
    SLS printed mold material parameters.

    Defines composite suitability for creating molds via powder sintering.
    SLS offers good dimensional accuracy without support structures.

    Attributes:
        materialId: ID reference to the parent Material
        powderType: Type of powder material (nylon, tpu, glass-filled)
        laserPowerForMold: Optimal laser power for mold quality (W)
        surfacePorosityForMold: Surface porosity level
        postProcessingForMold: Required post-processing (bead blast, seal, etc.)
        infiltrationRequired: Whether surface infiltration is needed
        infiltrationMaterial: Material for surface infiltration
        mechanicalStrength: Mechanical strength rating
        thermalConductivity: Thermal conductivity for casting applications
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='SLS Printed Mold Material',
                 description='Composite suitable for SLS printed molds',
                 minFeatureSize=0.1,
                 surfaceFinishRa=8.0,
                 dimensionalAccuracy=0.1,
                 thermalStabilityMax=150.0,
                 layerHeightForMold=0.1,
                 powderType='nylon',
                 laserPowerForMold=0.0,
                 surfacePorosityForMold='medium',
                 postProcessingForMold='bead_blast',
                 infiltrationRequired=False,
                 infiltrationMaterial='',
                 mechanicalStrength='high',
                 thermalConductivity=0.0):
        ThreeDimensionalPrintedMoldMaterial.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId,
            name=name, description=description,
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax,
            printingTechnology='sls',
            layerHeightForMold=layerHeightForMold,
            layerLineVisibility='none')
        self.powderType = powderType
        self.laserPowerForMold = laserPowerForMold
        self.surfacePorosityForMold = surfacePorosityForMold
        self.postProcessingForMold = postProcessingForMold
        self.infiltrationRequired = infiltrationRequired
        self.infiltrationMaterial = infiltrationMaterial
        self.mechanicalStrength = mechanicalStrength
        self.thermalConductivity = thermalConductivity

    def __repr__(self):
        return f"SLSPrintedMoldMaterial(id='{self.id}', materialId='{self.materialId}', powderType='{self.powderType}')"
