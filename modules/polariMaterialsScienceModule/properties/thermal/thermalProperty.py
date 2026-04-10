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
ThermalProperty Model

Thermal properties relate to temperature-dependent behavior of materials.
This serves as a category beneath PropertyCategory for properties like:
- Melting Point (solid to liquid transition temperature)
- Glass Transition Temperature (Tg, amorphous polymer softening)
- Smoking Point (temperature where material begins to smoke/degrade)
- Thermal Expansion (dimensional change with temperature)
- Thermal Conductivity (heat transfer capability)
- Specific Heat Capacity (energy to raise temperature)

Thermal properties are critical for:
- Polymer processing
- Metal casting and forming
- Food science and cooking
- 3D printing (FDM, SLA, SLS)
- Electronics and thermal management
- Aerospace and automotive

Standards References:
- ASTM E794: Melting and crystallization by thermal analysis
- ASTM D3418: Transition temperatures by DSC
- ASTM E1356: Glass transition temperatures by DSC
- ASTM E831: Linear thermal expansion by TMA
- ISO 11357: Plastics - Differential scanning calorimetry
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.propertyCategory import PropertyCategory


class ThermalProperty(PropertyCategory):
    """
    Thermal property category inheriting from PropertyCategory.

    Thermal properties describe temperature-dependent behavior including
    phase transitions, thermal expansion, and heat transfer characteristics.

    Child Properties:
    - meltingPoint/: MeltingPoint → MeltingPointValue → DSC/VisualMeasurement
    - glassTransition/: GlassTransition → GlassTransitionTemp → DSC/DMA measurements
    - smokingPoint/: SmokingPoint → SmokingPointValue → SmokingPointMeasurement
    - thermalExpansion/: ThermalExpansion → CTE → TMA/Dilatometer measurements

    Attributes:
        materialId: ID reference to the parent Material
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Thermal Property',
                 description='Property relating to temperature-dependent behavior of materials',
                 materialId='',
                 categoryDescription='Temperature-dependent properties including melting point, Tg, and thermal expansion'):
        PropertyCategory.__init__(self, manager=manager, branch=branch, id=id,
                                  name=name, description=description,
                                  materialId=materialId, categoryDescription=categoryDescription)

    def __repr__(self):
        return f"ThermalProperty(id='{self.id}', name='{self.name}', materialId='{self.materialId}')"
