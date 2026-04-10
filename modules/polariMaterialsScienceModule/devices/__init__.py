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
Material Related Devices Module

Defines devices used for material processing, testing, and fabrication.
Devices are referenced by MaterialPurpose classes to determine compatibility.

Device Categories:
- threeDimensionalPrintingDevices/: 3D printers (FDM, SLA, SLS)
- cncMills/: CNC milling machines
- cncLathes/: CNC turning machines
- materialTestingDevices/: Testing equipment (viscometers, hardness testers)
"""

from polariMaterialsScienceModule.devices.deviceCategory import DeviceCategory

# 3D Printing Devices
from polariMaterialsScienceModule.devices.threeDimensionalPrintingDevices import (
    ThreeDimensionalPrintingDevice,
    FDMPrinter,
    SLAPrinter,
    SLSPrinter
)

# CNC Mills
from polariMaterialsScienceModule.devices.cncMills import (
    CNCMill,
    ThreeAxisMill,
    FiveAxisMill
)

# CNC Lathes
from polariMaterialsScienceModule.devices.cncLathes import (
    CNCLathe
)

# Material Testing Devices
from polariMaterialsScienceModule.devices.materialTestingDevices import (
    MaterialTestingDevice,
    Viscometer,
    HardnessTester,
    TensileTestingMachine,
    ThermalAnalyzer
)

__all__ = [
    # Base category
    'DeviceCategory',

    # 3D Printing Devices
    'ThreeDimensionalPrintingDevice',
    'FDMPrinter',
    'SLAPrinter',
    'SLSPrinter',

    # CNC Mills
    'CNCMill',
    'ThreeAxisMill',
    'FiveAxisMill',

    # CNC Lathes
    'CNCLathe',

    # Material Testing Devices
    'MaterialTestingDevice',
    'Viscometer',
    'HardnessTester',
    'TensileTestingMachine',
    'ThermalAnalyzer'
]
