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
MoldFabricationPurpose Model

Base class for mold fabrication purposes. Defines material suitability
for creating precision composite molds.

Key considerations for mold materials:
- Dimensional accuracy and stability
- Surface finish quality
- Feature resolution capability
- Thermal stability during casting/curing
- Release characteristics
- Durability for multiple uses
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.purposeCategory import PurposeCategory


class MoldFabricationPurpose(PurposeCategory):
    """
    Mold fabrication purpose category.

    Defines material suitability for creating fine-resolution molds
    from composite materials. This is the base class for specific
    mold fabrication methods (3D printing, CNC machining).

    Attributes:
        materialId: ID reference to the parent Material
        fabricationMethod: Method of mold creation (3d_printing, cnc_machining)
        minFeatureSize: Minimum achievable feature size (mm)
        surfaceFinishRa: Achievable surface roughness (Ra, μm)
        dimensionalAccuracy: Achievable dimensional accuracy (mm)
        thermalStabilityMax: Maximum temperature stability (°C)
        releaseAngleMin: Minimum draft angle for release (degrees)
        expectedMoldLife: Expected number of uses before degradation
        postProcessingRequired: Post-processing steps needed
    """

    PURPOSE_CATEGORY = 'mold_fabrication'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Mold Fabrication Purpose',
                 description='Material suitability for mold fabrication',
                 categoryDescription='Fine-resolution composite mold creation',
                 fabricationMethod='',
                 minFeatureSize=0.0,
                 surfaceFinishRa=0.0,
                 dimensionalAccuracy=0.0,
                 thermalStabilityMax=0.0,
                 releaseAngleMin=0.0,
                 expectedMoldLife=0,
                 postProcessingRequired=''):
        PurposeCategory.__init__(self, manager=manager, branch=branch, id=id,
                                 materialId=materialId,
                                 name=name, description=description,
                                 categoryDescription=categoryDescription)
        self.fabricationMethod = fabricationMethod
        self.minFeatureSize = minFeatureSize
        self.surfaceFinishRa = surfaceFinishRa
        self.dimensionalAccuracy = dimensionalAccuracy
        self.thermalStabilityMax = thermalStabilityMax
        self.releaseAngleMin = releaseAngleMin
        self.expectedMoldLife = expectedMoldLife
        self.postProcessingRequired = postProcessingRequired

    def __repr__(self):
        return f"MoldFabricationPurpose(id='{self.id}', materialId='{self.materialId}', method='{self.fabricationMethod}')"
