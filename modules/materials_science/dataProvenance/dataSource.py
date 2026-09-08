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
DataSource Model

Individual citation/source record for provenance tracking.
Represents a single source of information (paper, datasheet, etc.)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class DataSource(treeObject):
    """
    An individual data source citation.

    Attributes:
        sourceType: Type of source (llm_generated, research_paper,
            manufacturer_datasheet, experimental_testing,
            community_measurement, personal_observation)
        sourceName: Name/title of the source
        sourceReference: URL, DOI, or ISBN reference
        sourceAuthor: Author(s) of the source
        sourceDate: Date of publication/measurement
        notes: Additional notes about this source
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 sourceType='',
                 sourceName='',
                 sourceReference='',
                 sourceAuthor='',
                 sourceDate='',
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.sourceType = sourceType
        self.sourceName = sourceName
        self.sourceReference = sourceReference
        self.sourceAuthor = sourceAuthor
        self.sourceDate = sourceDate
        self.notes = notes

    def __repr__(self):
        return f"DataSource(id='{getattr(self, 'id', '?')}', type='{getattr(self, 'sourceType', '?')}', name='{getattr(self, 'sourceName', '?')}')"
