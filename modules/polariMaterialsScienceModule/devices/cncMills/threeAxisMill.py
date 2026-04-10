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
ThreeAxisMill Model

3-axis CNC milling machine. Most common type for general machining.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.cncMills.cncMill import CNCMill


class ThreeAxisMill(CNCMill):
    """
    3-axis CNC milling machine.

    Standard milling machine with X, Y, Z linear axes.
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='3-Axis CNC Mill',
                 description='',
                 manufacturer='',
                 model='',
                 workEnvelopeX=0.0,
                 workEnvelopeY=0.0,
                 workEnvelopeZ=0.0,
                 spindlePower=0.0,
                 spindleSpeedMin=0,
                 spindleSpeedMax=0,
                 spindleTaper='',
                 positioningAccuracy=0.0,
                 repeatability=0.0,
                 toolChangerType='manual',
                 toolCapacity=0,
                 hasCoolantSystem=True,
                 coolantType='flood',
                 controllerBrand='',
                 controllerModel=''):
        CNCMill.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            axisCount=3,
            workEnvelopeX=workEnvelopeX,
            workEnvelopeY=workEnvelopeY,
            workEnvelopeZ=workEnvelopeZ,
            spindlePower=spindlePower,
            spindleSpeedMin=spindleSpeedMin,
            spindleSpeedMax=spindleSpeedMax,
            spindleTaper=spindleTaper,
            positioningAccuracy=positioningAccuracy,
            repeatability=repeatability,
            toolChangerType=toolChangerType,
            toolCapacity=toolCapacity,
            hasCoolantSystem=hasCoolantSystem,
            coolantType=coolantType,
            controllerBrand=controllerBrand,
            controllerModel=controllerModel)

    def __repr__(self):
        return f"ThreeAxisMill(id='{self.id}', name='{self.name}')"
