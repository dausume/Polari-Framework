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
Material Resolutions Module

This module organizes material resolution-level definitions by scale:

Resolution Categories:
- experimental/: Level 0 - Real world measurements (RawExperimental, RulesOfMixtures)
- continuum/: Level 1 - Finite Element Methods (Consistent, Stochastic, Chosen, Range)
- mesoscale/: Level 2 - Coarse-Grained Molecular Dynamics (CGMD)
- atomistic/: Level 3 - Classical Molecular Dynamics (MD)
- quantum/: Level 4 - Density Functional Theory (DFT)

Each resolution level provides a different computational view of the same material.
"""

from materials_science.custom.resolutions.resolutionCategory import ResolutionCategory

# Import resolution categories
from materials_science.custom.resolutions.experimental import ExperimentalResolution
from materials_science.custom.resolutions.continuum import ContinuumResolution
from materials_science.custom.resolutions.mesoscale import MesoscaleResolution
from materials_science.custom.resolutions.atomistic import AtomisticResolution
from materials_science.custom.resolutions.quantum import QuantumResolution

# Import specific resolution materials
from materials_science.custom.resolutions.experimental import (
    RawExperimentalMaterial,
    RulesOfMixturesExperimentalMaterial
)
from materials_science.custom.resolutions.continuum import (
    ConsistentFiniteElementMaterial,
    StochasticFiniteElementMaterial,
    ChosenMaterial,
    RangeMaterial
)
from materials_science.custom.resolutions.mesoscale import (
    CoarsegrainedMolecularDynamicsMaterial
)
from materials_science.custom.resolutions.atomistic import (
    MolecularDynamicsMaterial
)
from materials_science.custom.resolutions.quantum import (
    DensityFunctionalMaterial
)

__all__ = [
    # Base
    'ResolutionCategory',

    # Categories
    'ExperimentalResolution',
    'ContinuumResolution',
    'MesoscaleResolution',
    'AtomisticResolution',
    'QuantumResolution',

    # Experimental (Level 0)
    'RawExperimentalMaterial',
    'RulesOfMixturesExperimentalMaterial',

    # Continuum (Level 1)
    'ConsistentFiniteElementMaterial',
    'StochasticFiniteElementMaterial',
    'ChosenMaterial',
    'RangeMaterial',

    # Mesoscale (Level 2)
    'CoarsegrainedMolecularDynamicsMaterial',

    # Atomistic (Level 3)
    'MolecularDynamicsMaterial',

    # Quantum (Level 4)
    'DensityFunctionalMaterial'
]
