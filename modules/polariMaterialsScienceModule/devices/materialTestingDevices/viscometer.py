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
Viscometer Model

Viscosity measurement device. Various types for different applications.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.materialTestingDevices.materialTestingDevice import MaterialTestingDevice


class Viscometer(MaterialTestingDevice):
    """
    Viscometer device for measuring viscosity.

    Various types exist: rotational, capillary, falling ball, Stormer, etc.

    Attributes:
        viscometerType: Type (rotational, capillary, stormer, krebs, brookfield)
        viscosityRangeMin: Minimum measurable viscosity (cP or Pa.s)
        viscosityRangeMax: Maximum measurable viscosity (cP or Pa.s)
        shearRateRangeMin: Minimum shear rate (1/s)
        shearRateRangeMax: Maximum shear rate (1/s)
        temperatureRangeMin: Minimum temperature (C)
        temperatureRangeMax: Maximum temperature (C)
        temperatureControl: Temperature control type (bath, peltier, none)
        spindleSet: Available spindles/geometries
        sampleVolumeRequired: Sample volume required (ml)
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Viscometer',
                 description='',
                 manufacturer='',
                 model='',
                 standardsCompliance='ASTM D2196',
                 viscometerType='rotational',
                 viscosityRangeMin=0.0,
                 viscosityRangeMax=0.0,
                 shearRateRangeMin=0.0,
                 shearRateRangeMax=0.0,
                 temperatureRangeMin=0.0,
                 temperatureRangeMax=0.0,
                 temperatureControl='none',
                 spindleSet='',
                 sampleVolumeRequired=0.0):
        MaterialTestingDevice.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            testingType='rheological',
            standardsCompliance=standardsCompliance)

        self.viscometerType = viscometerType
        self.viscosityRangeMin = viscosityRangeMin
        self.viscosityRangeMax = viscosityRangeMax
        self.shearRateRangeMin = shearRateRangeMin
        self.shearRateRangeMax = shearRateRangeMax
        self.temperatureRangeMin = temperatureRangeMin
        self.temperatureRangeMax = temperatureRangeMax
        self.temperatureControl = temperatureControl
        self.spindleSet = spindleSet
        self.sampleVolumeRequired = sampleVolumeRequired

    def __repr__(self):
        return f"Viscometer(id='{self.id}', name='{self.name}', type='{self.viscometerType}')"
