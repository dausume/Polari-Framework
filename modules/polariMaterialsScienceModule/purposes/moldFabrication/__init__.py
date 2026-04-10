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
Mold Fabrication Purposes Module

Defines material suitability for creating fine-resolution composite molds.

This is NOT general-purpose 3D printing or CNC machining - these purposes
specifically relate to fabricating precision molds from composite materials.

Sections:
- threeDimensionalPrintedMold/: 3D printed mold materials (FDM, SLA, SLS)
- cncMachinedMold/: CNC machined mold materials (milling, turning)
- geopolymerConcreteMold/: Cast geopolymer concrete molds (standard, thermal resistant)
"""

from polariMaterialsScienceModule.purposes.moldFabrication.moldFabricationPurpose import MoldFabricationPurpose

# 3D Printed Molds
from polariMaterialsScienceModule.purposes.moldFabrication.threeDimensionalPrintedMold import (
    ThreeDimensionalPrintedMoldMaterial,
    FDMPrintedMoldMaterial,
    SLAPrintedMoldMaterial,
    SLSPrintedMoldMaterial
)

# CNC Machined Molds
from polariMaterialsScienceModule.purposes.moldFabrication.cncMachinedMold import (
    CNCMachinedMoldMaterial,
    MilledMoldMaterial,
    TurnedMoldMaterial
)

# Geopolymer Concrete Molds
from polariMaterialsScienceModule.purposes.moldFabrication.geopolymerConcreteMold import (
    GeopolymerConcreteMoldMaterial,
    GeopolymerThermalResistantConcreteMoldMaterial
)

__all__ = [
    'MoldFabricationPurpose',

    # 3D Printed Molds
    'ThreeDimensionalPrintedMoldMaterial',
    'FDMPrintedMoldMaterial',
    'SLAPrintedMoldMaterial',
    'SLSPrintedMoldMaterial',

    # CNC Machined Molds
    'CNCMachinedMoldMaterial',
    'MilledMoldMaterial',
    'TurnedMoldMaterial',

    # Geopolymer Concrete Molds
    'GeopolymerConcreteMoldMaterial',
    'GeopolymerThermalResistantConcreteMoldMaterial'
]
