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
Viscosity Model

Abstract viscosity property that inherits from RheologicalProperty.
This serves as the intermediate abstraction between the rheological property category
and specific viscosity measurement types.

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation properties category)
    - Level 1: Viscosity (this class - abstract viscosity concept)
    - Level 2: KrebsViscosity (derived/computed viscosity in standard units)
    - Level 3: StormerViscosity (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.rheologicalProperty import RheologicalProperty


class Viscosity(RheologicalProperty):
    """
    Abstract viscosity property inheriting from RheologicalProperty.

    This represents the concept of viscosity as a rheological material property,
    serving as the parent abstraction for specific viscosity types
    like KrebsViscosity (derived values) and StormerViscosity (raw measurements).

    The most specific form of viscosity in terms of material resolution level
    is at the Continuum-Resolution Materials (Finite Element Materials) level.

    The specific measurement forms experimentally are data-points leveraging
    devices like the Stormer Viscometers which utilize specially defined devices
    to simplify viscosity measurement in industrial contexts by standardizing
    the devices so we can use constants to convert raw measurements to derived values
    instead of requiring complex fluid dynamics calculations.

    You can choose to make a custom viscosity measurement device using fluid dynamics
    principles, but it is suggested to use established devices like the Stormer
    which are open source and well documented.

    Abstraction level: 1 (RheologicalProperty inherits MaterialProperty at 0)

    Attributes:
        materialId: ID reference to the parent Material
        abstractionLevel: Numeric level indicating specificity (1 for this class)
    """

    ABSTRACTION_LEVEL = 1

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Viscosity',
                 description='Measure of a fluid\'s resistance to flow',
                 materialId=''):
        RheologicalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                     name=name, description=description,
                                     materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"Viscosity(id='{self.id}', materialId='{self.materialId}')"
