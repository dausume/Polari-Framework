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

#Defines all of the python modules that should be installed prior to running this as an Application
from setuptools import setup

setup(
    name='polari-framework-node',
    version='0.1',
    author='Dustin Etts',
    author_email='dustinetts@gmail.com',
    url='https://www.polariai.com',
    install_requires=[
        'psutil',
        'falcon',
        'jwt',
        'svgwrite',
    ],
    packages=[
        'POLARI-FRAMEWORK',
    ],
)
