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
SurfaceProperty Model

Surface properties relate to interfacial phenomena between materials
and their environment. This serves as a category beneath PropertyCategory
for properties like:
- Solid Surface Energy (energy required to create new surface area on solids)
- Liquid Surface Tension (cohesive forces at liquid-gas interface)
- Contact Angle (wettability measurement)
- Adhesion (bonding between dissimilar materials)

Surface properties are critical for:
- Coatings and paints (adhesion, wetting)
- Adhesives and bonding
- Microfluidics
- Emulsions and foams
- Printing and inkjet technology
- Biomedical surfaces

Standards References:
- ASTM D5946: Corona-treated polymer films, contact angle
- ASTM D1331: Surface and interfacial tension of solutions
- ISO 19403: Wettability - Determination of contact angle
- ASTM D2578: Wetting tension of polyethylene and polypropylene films
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.propertyCategory import PropertyCategory


class SurfaceProperty(PropertyCategory):
    """
    Surface property category inheriting from PropertyCategory.

    Surface properties describe interfacial phenomena including surface energy,
    surface tension, and wettability characteristics.

    Child Properties:
    - solidSurfaceEnergy/: SolidSurfaceEnergy → CriticalSurfaceTension → ContactAngleMeasurement
    - liquidSurfaceTension/: LiquidSurfaceTension → SurfaceTensionValue → Wilhelmy/DuNouy/Pendant measurements

    Attributes:
        materialId: ID reference to the parent Material
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Surface Property',
                 description='Property relating to interfacial phenomena between materials',
                 materialId='',
                 categoryDescription='Interfacial properties including surface energy and surface tension'):
        PropertyCategory.__init__(self, manager=manager, branch=branch, id=id,
                                  name=name, description=description,
                                  materialId=materialId, categoryDescription=categoryDescription)

    def __repr__(self):
        return f"SurfaceProperty(id='{self.id}', name='{self.name}', materialId='{self.materialId}')"
