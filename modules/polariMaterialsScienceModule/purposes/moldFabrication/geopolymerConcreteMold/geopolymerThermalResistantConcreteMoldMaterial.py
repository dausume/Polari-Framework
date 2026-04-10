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
GeopolymerThermalResistantConcreteMoldMaterial Model

Geopolymer concrete mold formulated for high-temperature applications.
Uses refractory aggregates and optimized binder chemistry to withstand
elevated temperatures and thermal cycling.

Applications:
- Metal casting molds (low-melting alloys)
- High-temperature composite curing molds
- Molds for thermoset resins with high exotherm
- Furnace components and thermal tooling
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.purposes.moldFabrication.geopolymerConcreteMold.geopolymerConcreteMoldMaterial import GeopolymerConcreteMoldMaterial


class GeopolymerThermalResistantConcreteMoldMaterial(GeopolymerConcreteMoldMaterial):
    """
    Thermally resistant geopolymer concrete mold material.

    Extends the base geopolymer concrete mold with thermal resistance
    properties for high-temperature applications. Uses refractory
    aggregates and optimized formulations.

    Attributes:
        # Thermal resistance
        maxServiceTemperature: Maximum continuous service temperature (C)
        peakTemperatureTolerance: Maximum peak/short-term temperature (C)
        thermalCycleResistance: Number of thermal cycles before degradation
        thermalShockResistance: Resistance to rapid temperature changes (poor, moderate, good, excellent)
        thermalConductivity: Thermal conductivity (W/m*K)
        thermalExpansionCoefficient: CTE (um/m*C)

        # Refractory aggregate
        refractoryAggregateType: Type of refractory aggregate (chamotte, vermiculite, perlite, alumina, etc.)
        refractoryAggregateFraction: Fraction of refractory aggregate by weight
        refractoryAggregateSource: Where to source refractory aggregate

        # High-temp formulation
        highTempBinderAdditive: Additives for thermal performance
        fiberReinforcement: Fiber type for thermal crack resistance (none, steel, basalt, ceramic)
        fiberFraction: Fiber content by weight (%)

        # Post-curing for thermal use
        thermalConditioningRequired: Whether thermal conditioning/ramping needed
        conditioningSchedule: Temperature ramp schedule before first high-temp use
        conditioningMaxTemp: Maximum conditioning temperature (C)

        # Performance at temperature
        hotCompressiveStrength: Compressive strength at max service temp (MPa)
        creepResistance: Creep resistance at temperature (poor, moderate, good)
        residualStrengthAfterCycling: Retained strength after thermal cycling (%)

        # Safety at temperature
        offgassingRisk: Risk of offgassing at temperature (none, low, moderate)
        safetyNotes: Safety notes for high-temperature use

        Inherits all from GeopolymerConcreteMoldMaterial
    """

    PURPOSE_CATEGORY = 'geopolymer_thermal_resistant_mold'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Geopolymer Thermal Resistant Concrete Mold',
                 description='Thermally resistant geopolymer concrete mold for high-temperature applications',
                 # MoldFabricationPurpose params (higher thermal defaults)
                 minFeatureSize=2.0,
                 surfaceFinishRa=10.0,
                 dimensionalAccuracy=1.0,
                 thermalStabilityMax=800.0,
                 releaseAngleMin=5.0,
                 expectedMoldLife=20,
                 postProcessingRequired='Thermal conditioning ramp, surface sealing',
                 # GeopolymerConcreteMoldMaterial params
                 binderType='metakaolin',
                 activatorType='sodium_silicate',
                 activatorToBinderRatio=0.45,
                 waterToSolidsRatio=0.25,
                 silicateToHydroxideRatio=2.0,
                 aggregateType='refractory',
                 aggregateSize=3.0,
                 aggregateToBinderRatio=2.5,
                 aggregateSource='',
                 mixingMethod='mechanical_mixer',
                 potLife=20.0,
                 pouringViscosity='thick',
                 vibrationRequired=True,
                 moldReleaseAgent='',
                 curingMethod='heat',
                 curingTemperature=60.0,
                 curingTime=24.0,
                 fullCureTime=14,
                 curingHumidity='sealed',
                 compressiveStrength=50.0,
                 flexuralStrength=6.0,
                 shrinkageDuringCure=0.3,
                 porosity='low',
                 chemicalResistance='Excellent at elevated temperatures',
                 phResistance='3-14',
                 waterAbsorption=3.0,
                 formType='',
                 formReusable=True,
                 surfaceSealerRequired=True,
                 surfaceSealer='',
                 # Thermal resistance
                 maxServiceTemperature=800.0,
                 peakTemperatureTolerance=1000.0,
                 thermalCycleResistance=50,
                 thermalShockResistance='moderate',
                 thermalConductivity=0.8,
                 thermalExpansionCoefficient=10.0,
                 # Refractory aggregate
                 refractoryAggregateType='chamotte',
                 refractoryAggregateFraction=0.5,
                 refractoryAggregateSource='',
                 # High-temp formulation
                 highTempBinderAdditive='',
                 fiberReinforcement='none',
                 fiberFraction=0.0,
                 # Post-curing for thermal use
                 thermalConditioningRequired=True,
                 conditioningSchedule='Ramp 50C/hr to 300C, hold 2hr, ramp to 600C, hold 2hr',
                 conditioningMaxTemp=600.0,
                 # Performance at temperature
                 hotCompressiveStrength=30.0,
                 creepResistance='moderate',
                 residualStrengthAfterCycling=80.0,
                 # Safety at temperature
                 offgassingRisk='low',
                 safetyNotes='Ensure full thermal conditioning before first high-temp use'):
        GeopolymerConcreteMoldMaterial.__init__(
            self, manager=manager, branch=branch, id=id,
            materialId=materialId, name=name, description=description,
            minFeatureSize=minFeatureSize,
            surfaceFinishRa=surfaceFinishRa,
            dimensionalAccuracy=dimensionalAccuracy,
            thermalStabilityMax=thermalStabilityMax,
            releaseAngleMin=releaseAngleMin,
            expectedMoldLife=expectedMoldLife,
            postProcessingRequired=postProcessingRequired,
            binderType=binderType,
            activatorType=activatorType,
            activatorToBinderRatio=activatorToBinderRatio,
            waterToSolidsRatio=waterToSolidsRatio,
            silicateToHydroxideRatio=silicateToHydroxideRatio,
            aggregateType=aggregateType,
            aggregateSize=aggregateSize,
            aggregateToBinderRatio=aggregateToBinderRatio,
            aggregateSource=aggregateSource,
            mixingMethod=mixingMethod,
            potLife=potLife,
            pouringViscosity=pouringViscosity,
            vibrationRequired=vibrationRequired,
            moldReleaseAgent=moldReleaseAgent,
            curingMethod=curingMethod,
            curingTemperature=curingTemperature,
            curingTime=curingTime,
            fullCureTime=fullCureTime,
            curingHumidity=curingHumidity,
            compressiveStrength=compressiveStrength,
            flexuralStrength=flexuralStrength,
            shrinkageDuringCure=shrinkageDuringCure,
            porosity=porosity,
            chemicalResistance=chemicalResistance,
            phResistance=phResistance,
            waterAbsorption=waterAbsorption,
            formType=formType,
            formReusable=formReusable,
            surfaceSealerRequired=surfaceSealerRequired,
            surfaceSealer=surfaceSealer)

        # Thermal resistance
        self.maxServiceTemperature = maxServiceTemperature
        self.peakTemperatureTolerance = peakTemperatureTolerance
        self.thermalCycleResistance = thermalCycleResistance
        self.thermalShockResistance = thermalShockResistance
        self.thermalConductivity = thermalConductivity
        self.thermalExpansionCoefficient = thermalExpansionCoefficient

        # Refractory aggregate
        self.refractoryAggregateType = refractoryAggregateType
        self.refractoryAggregateFraction = refractoryAggregateFraction
        self.refractoryAggregateSource = refractoryAggregateSource

        # High-temp formulation
        self.highTempBinderAdditive = highTempBinderAdditive
        self.fiberReinforcement = fiberReinforcement
        self.fiberFraction = fiberFraction

        # Post-curing for thermal use
        self.thermalConditioningRequired = thermalConditioningRequired
        self.conditioningSchedule = conditioningSchedule
        self.conditioningMaxTemp = conditioningMaxTemp

        # Performance at temperature
        self.hotCompressiveStrength = hotCompressiveStrength
        self.creepResistance = creepResistance
        self.residualStrengthAfterCycling = residualStrengthAfterCycling

        # Safety at temperature
        self.offgassingRisk = offgassingRisk
        self.safetyNotes = safetyNotes

    def __repr__(self):
        return f"GeopolymerThermalResistantConcreteMoldMaterial(id='{self.id}', materialId='{self.materialId}', maxTemp={self.maxServiceTemperature}C)"
