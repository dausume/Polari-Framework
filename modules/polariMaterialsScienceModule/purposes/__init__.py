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
Material Purposes Module

Defines intended uses and applications for materials.

Purpose Categories:
- cncMachinable/: Base conditions for CNC machining with a device
- threeDimensionalPrintable/: Base conditions for 3D printing with a device
- moldFabrication/: Creating fine-resolution molds (3D printed, CNC machined)
- nanoparticleEmbedding/: Nanoparticle embedding purposes (planned)
"""

from polariMaterialsScienceModule.purposes.purposeCategory import PurposeCategory

# Base machinability/printability conditions
from polariMaterialsScienceModule.purposes.cncMachinable import CNCMachinable
from polariMaterialsScienceModule.purposes.threeDimensionalPrintable import ThreeDimensionalPrintable

# Mold fabrication purposes
from polariMaterialsScienceModule.purposes.moldFabrication import (
    MoldFabricationPurpose,
    # 3D Printed Molds
    ThreeDimensionalPrintedMoldMaterial,
    FDMPrintedMoldMaterial,
    SLAPrintedMoldMaterial,
    SLSPrintedMoldMaterial,
    # CNC Machined Molds
    CNCMachinedMoldMaterial,
    MilledMoldMaterial,
    TurnedMoldMaterial,
    # Geopolymer Concrete Molds
    GeopolymerConcreteMoldMaterial,
    GeopolymerThermalResistantConcreteMoldMaterial
)

__all__ = [
    # Base category
    'PurposeCategory',

    # Base conditions
    'CNCMachinable',
    'ThreeDimensionalPrintable',

    # Mold Fabrication category
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
