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
import svgwrite
from PIL import Image as PILimage
from managedFiles import *
from matplotlib import pyplot as plt
from matplotlib import image as MPLimage


picExtensions = ['svg', 'pil', 'jpg', 'png', 'pdf', 'gif']

class managedImage(managedFile):
    def __init__(self, name = None, extension = None, xPix = 100, yPix = 100):
        managedFile.__init__(self, name=name, extension=extension)
        if(picExtensions.__contains__(extension)):
            managedFile.__init__(name)
            #The number of pixels along the x-axis for the current image size, or the width.
            self.xPix = xPix
            #The number of pixels along the y-axis for the current image size, or the height.
            self.yPix = yPix
            #The Image formatted into a basic Image numPy Array
            self.imgAry = None

    def getImageArray(self):
        if(self.extension == 'png' and self.Path != None and self.isRemote == False):
            self.imgAry = MPLimage.imread(self.Path + '\\' + self.name + '.' + self.extension)
        elif(self.extension == 'png' and self.Path != None and self.isRemote == True):
            self.imgAry = MPLimage.imread(self.Path)

    def setExtension(self, fileExtension):
        if(fileExtensions.contains(fileExtension)):
            logging.warning('Entered a valid image file, but instantiated using the wrong object, should be a managedFile.')
        elif(picExtensions.contains(fileExtension)):
            self.extension = fileExtension
        elif(dataBaseExtensions.contains(fileExtension)):
            logging.warning('Entered a valid Data Base file, but instantiated using the wrong object, should be a managedDB.')
        elif(dataCommsExtensions.contains(fileExtension)):
            logging.warning('Entered a valid file extension meant for data transmissions, but instantiated using the wrong object, should be a dataComms object.')
        elif(executableExtensions.contains(fileExtension)):
            logging.warning('Entered an invalid or unhandled file Extension.')
        else:
            logging.warning('Entered an invalid or unhandled file Extension.')