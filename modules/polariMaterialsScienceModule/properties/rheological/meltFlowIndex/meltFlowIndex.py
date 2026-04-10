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
MeltFlowIndex Model

Represents the abstract concept of Melt Flow Index (MFI) - a measure of
the ease of flow of a thermoplastic polymer melt. Inherits from
RheologicalProperty at abstraction level 1.

Melt Flow Index (also called Melt Flow Rate, MFR) is inversely related
to viscosity: higher MFI = lower viscosity = easier flow.

Common uses:
- Quality control in polymer production
- Material selection for processing
- Batch-to-batch consistency verification
- Recycled material characterization

Standards References:
- ASTM D1238: Standard test method for melt flow rates of thermoplastics
- ISO 1133: Plastics - Determination of MFR and MVR
- ASTM D3364: Flow rates of thermoplastics by extrusion plastometer

Open Source References:
- RepRap community: DIY MFI testers for 3D printing filament QC
- FilamentMFI: Arduino-based melt flow tester designs
- Academic DIY designs: Various university projects for teaching

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: MeltFlowIndex (this class - abstract concept)
    - Level 2: MFIValue (derived/standard value)
    - Level 3: MFIMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.rheologicalProperty import RheologicalProperty


class MeltFlowIndex(RheologicalProperty):
    """
    Abstract Melt Flow Index property (Level 1).

    Represents the concept of melt flow - the ease with which a
    thermoplastic melt flows under specified conditions. This is
    the abstract parent for specific MFI values and measurements.

    Abstraction level: 1 (abstract concept)

    Attributes:
        materialId: ID reference to the parent Material
    """

    ABSTRACTION_LEVEL = 1

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Melt Flow Index',
                 description='Measure of thermoplastic melt flow under standard conditions',
                 materialId=''):
        RheologicalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                     name=name, description=description,
                                     materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"MeltFlowIndex(id='{self.id}', materialId='{self.materialId}')"
