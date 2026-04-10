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
Material Testing Devices Module

Defines material testing equipment and their capabilities.
These devices measure material properties.
"""

from polariMaterialsScienceModule.devices.materialTestingDevices.materialTestingDevice import MaterialTestingDevice
from polariMaterialsScienceModule.devices.materialTestingDevices.viscometer import Viscometer
from polariMaterialsScienceModule.devices.materialTestingDevices.hardnessTester import HardnessTester
from polariMaterialsScienceModule.devices.materialTestingDevices.tensileTestingMachine import TensileTestingMachine
from polariMaterialsScienceModule.devices.materialTestingDevices.thermalAnalyzer import ThermalAnalyzer

__all__ = [
    'MaterialTestingDevice',
    'Viscometer',
    'HardnessTester',
    'TensileTestingMachine',
    'ThermalAnalyzer'
]
