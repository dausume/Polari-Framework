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
TensileTestingMachine Model

Universal testing machine for tensile, compression, and flexural testing.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.materialTestingDevices.materialTestingDevice import MaterialTestingDevice


class TensileTestingMachine(MaterialTestingDevice):
    """
    Universal testing machine for mechanical testing.

    Can perform tensile, compression, flexural, and other tests.

    Attributes:
        loadCapacity: Maximum load capacity (kN)
        loadCellsAvailable: Available load cells
        crossheadSpeedMin: Minimum crosshead speed (mm/min)
        crossheadSpeedMax: Maximum crosshead speed (mm/min)
        crossheadTravel: Crosshead travel (mm)
        frameStiffness: Frame stiffness (kN/mm)
        gripsAvailable: Available grip types
        extensometerAvailable: Whether extensometer is available
        extensometerGaugeLength: Extensometer gauge length (mm)
        testingModes: Available testing modes (tensile, compression, flexure)
        environmentalChamber: Whether environmental chamber is available
        temperatureRange: Temperature range if chamber available (C)
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Tensile Testing Machine',
                 description='',
                 manufacturer='',
                 model='',
                 standardsCompliance='ASTM D638',
                 loadCapacity=0.0,
                 loadCellsAvailable='',
                 crossheadSpeedMin=0.0,
                 crossheadSpeedMax=0.0,
                 crossheadTravel=0.0,
                 frameStiffness=0.0,
                 gripsAvailable='',
                 extensometerAvailable=False,
                 extensometerGaugeLength=0.0,
                 testingModes='tensile,compression',
                 environmentalChamber=False,
                 temperatureRange=''):
        MaterialTestingDevice.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            testingType='mechanical',
            standardsCompliance=standardsCompliance)

        self.loadCapacity = loadCapacity
        self.loadCellsAvailable = loadCellsAvailable
        self.crossheadSpeedMin = crossheadSpeedMin
        self.crossheadSpeedMax = crossheadSpeedMax
        self.crossheadTravel = crossheadTravel
        self.frameStiffness = frameStiffness
        self.gripsAvailable = gripsAvailable
        self.extensometerAvailable = extensometerAvailable
        self.extensometerGaugeLength = extensometerGaugeLength
        self.testingModes = testingModes
        self.environmentalChamber = environmentalChamber
        self.temperatureRange = temperatureRange

    def __repr__(self):
        return f"TensileTestingMachine(id='{self.id}', name='{self.name}', capacity={self.loadCapacity}kN)"
