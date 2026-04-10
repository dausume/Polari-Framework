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
RawExperimentalMaterial Model

Represents raw experimental measurement data for a material.
This is the most basic form of material data - direct lab measurements
without any derived or computed values.

Raw experimental data serves as the foundation for:
- Quality control and batch verification
- Material property database entries
- Input for rules-of-mixtures calculations
- Validation of simulation results
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.experimental.experimentalResolution import ExperimentalResolution


class RawExperimentalMaterial(ExperimentalResolution):
    """
    Raw experimental measurement data for a material.

    Contains direct measurement results from laboratory testing
    without any computational processing or modeling.

    Attributes:
        materialId: ID reference to the parent Material
        batchId: Batch or lot identifier for traceability
        testDate: Date when measurements were taken
        testLab: Laboratory where testing was performed
        testStandard: Test standard used (ASTM, ISO, etc.)
        rawDataReference: Reference to raw data files
        notes: Additional notes about the measurements
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='Raw Experimental Material',
                 description='Direct experimental measurement data',
                 batchId='',
                 testDate='',
                 testLab='',
                 testStandard='',
                 rawDataReference='',
                 notes=''):
        ExperimentalResolution.__init__(self, manager=manager, branch=branch, id=id,
                                        materialId=materialId,
                                        name=name, description=description)
        self.batchId = batchId
        self.testDate = testDate
        self.testLab = testLab
        self.testStandard = testStandard
        self.rawDataReference = rawDataReference
        self.notes = notes

    def __repr__(self):
        return f"RawExperimentalMaterial(id='{self.id}', materialId='{self.materialId}', batch='{self.batchId}')"
