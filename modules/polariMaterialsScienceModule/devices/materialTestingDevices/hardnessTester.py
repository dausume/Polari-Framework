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
HardnessTester Model

Hardness measurement device. Various scales for different materials.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.materialTestingDevices.materialTestingDevice import MaterialTestingDevice


class HardnessTester(MaterialTestingDevice):
    """
    Hardness tester device.

    Various scales: Shore (A, D, OO), Rockwell, Brinell, Vickers, etc.

    Attributes:
        hardnessScale: Scale (shore_a, shore_d, rockwell_c, brinell, vickers)
        indenterType: Indenter type (ball, cone, pyramid, durometer)
        loadMin: Minimum test load (N or kg)
        loadMax: Maximum test load (N or kg)
        dwellTime: Dwell time for measurement (s)
        digitalReadout: Whether digital readout is available
        automaticLoadApplication: Whether load is applied automatically
        sampleThicknessMin: Minimum sample thickness (mm)
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Hardness Tester',
                 description='',
                 manufacturer='',
                 model='',
                 standardsCompliance='ASTM D2240',
                 hardnessScale='shore_a',
                 indenterType='durometer',
                 loadMin=0.0,
                 loadMax=0.0,
                 dwellTime=1.0,
                 digitalReadout=True,
                 automaticLoadApplication=False,
                 sampleThicknessMin=6.0):
        MaterialTestingDevice.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            testingType='mechanical',
            standardsCompliance=standardsCompliance)

        self.hardnessScale = hardnessScale
        self.indenterType = indenterType
        self.loadMin = loadMin
        self.loadMax = loadMax
        self.dwellTime = dwellTime
        self.digitalReadout = digitalReadout
        self.automaticLoadApplication = automaticLoadApplication
        self.sampleThicknessMin = sampleThicknessMin

    def __repr__(self):
        return f"HardnessTester(id='{self.id}', name='{self.name}', scale='{self.hardnessScale}')"
