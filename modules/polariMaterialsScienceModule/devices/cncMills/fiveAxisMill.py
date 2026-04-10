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
FiveAxisMill Model

5-axis CNC milling machine. For complex geometries and mold making.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.cncMills.cncMill import CNCMill


class FiveAxisMill(CNCMill):
    """
    5-axis CNC milling machine.

    Milling machine with X, Y, Z linear axes plus two rotary axes.
    Essential for complex mold geometries.

    Attributes:
        rotaryAxisA: A-axis rotation range (degrees) or 'continuous'
        rotaryAxisB: B-axis rotation range (degrees) or 'continuous'
        rotaryAxisC: C-axis rotation range if present
        simultaneousAxes: Number of simultaneous axes (3+2 or full 5)
        tiltingHead: Whether head tilts vs table tilts
        trunnionType: Trunnion configuration if table tilts
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='5-Axis CNC Mill',
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
                 toolChangerType='atc',
                 toolCapacity=0,
                 hasCoolantSystem=True,
                 coolantType='flood',
                 controllerBrand='',
                 controllerModel='',
                 # 5-axis specific
                 rotaryAxisA='',
                 rotaryAxisB='',
                 rotaryAxisC='',
                 simultaneousAxes=5,
                 tiltingHead=False,
                 trunnionType=''):
        CNCMill.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            axisCount=5,
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

        # 5-axis specific
        self.rotaryAxisA = rotaryAxisA
        self.rotaryAxisB = rotaryAxisB
        self.rotaryAxisC = rotaryAxisC
        self.simultaneousAxes = simultaneousAxes
        self.tiltingHead = tiltingHead
        self.trunnionType = trunnionType

    def __repr__(self):
        return f"FiveAxisMill(id='{self.id}', name='{self.name}', simultaneous={self.simultaneousAxes})"
