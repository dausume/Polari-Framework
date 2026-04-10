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
ThermalAnalyzer Model

Thermal analysis equipment: DSC, TGA, DMA, TMA, etc.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.devices.materialTestingDevices.materialTestingDevice import MaterialTestingDevice


class ThermalAnalyzer(MaterialTestingDevice):
    """
    Thermal analyzer device.

    Various types: DSC, TGA, DMA, TMA, etc.

    Attributes:
        analyzerType: Type (dsc, tga, dma, tma, dsc_tga)
        temperatureRangeMin: Minimum temperature (C)
        temperatureRangeMax: Maximum temperature (C)
        heatingRateMin: Minimum heating rate (C/min)
        heatingRateMax: Maximum heating rate (C/min)
        coolingRateMin: Minimum cooling rate (C/min)
        coolingRateMax: Maximum cooling rate (C/min)
        atmosphereControl: Atmosphere control (air, nitrogen, argon)
        samplePanType: Sample pan type
        sampleMassMax: Maximum sample mass (mg)

        # DSC specific
        heatFlowResolution: Heat flow resolution (uW)
        enthalpyAccuracy: Enthalpy accuracy (%)

        # DMA specific
        frequencyRangeMin: Frequency range min (Hz)
        frequencyRangeMax: Frequency range max (Hz)
        forceRangeMax: Maximum force (N)
        deformationModes: Available deformation modes
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Thermal Analyzer',
                 description='',
                 manufacturer='',
                 model='',
                 standardsCompliance='ASTM E1356',
                 analyzerType='dsc',
                 temperatureRangeMin=-150.0,
                 temperatureRangeMax=600.0,
                 heatingRateMin=0.1,
                 heatingRateMax=100.0,
                 coolingRateMin=0.1,
                 coolingRateMax=50.0,
                 atmosphereControl='nitrogen',
                 samplePanType='aluminum',
                 sampleMassMax=0.0,
                 # DSC specific
                 heatFlowResolution=0.0,
                 enthalpyAccuracy=0.0,
                 # DMA specific
                 frequencyRangeMin=0.0,
                 frequencyRangeMax=0.0,
                 forceRangeMax=0.0,
                 deformationModes=''):
        MaterialTestingDevice.__init__(
            self, manager=manager, branch=branch, id=id,
            name=name, description=description,
            manufacturer=manufacturer, model=model,
            testingType='thermal',
            standardsCompliance=standardsCompliance)

        self.analyzerType = analyzerType
        self.temperatureRangeMin = temperatureRangeMin
        self.temperatureRangeMax = temperatureRangeMax
        self.heatingRateMin = heatingRateMin
        self.heatingRateMax = heatingRateMax
        self.coolingRateMin = coolingRateMin
        self.coolingRateMax = coolingRateMax
        self.atmosphereControl = atmosphereControl
        self.samplePanType = samplePanType
        self.sampleMassMax = sampleMassMax

        # DSC specific
        self.heatFlowResolution = heatFlowResolution
        self.enthalpyAccuracy = enthalpyAccuracy

        # DMA specific
        self.frequencyRangeMin = frequencyRangeMin
        self.frequencyRangeMax = frequencyRangeMax
        self.forceRangeMax = forceRangeMax
        self.deformationModes = deformationModes

    def __repr__(self):
        return f"ThermalAnalyzer(id='{self.id}', name='{self.name}', type='{self.analyzerType}')"
