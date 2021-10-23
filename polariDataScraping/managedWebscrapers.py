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
#Requires both selenium & Chrome Driver to run
import selenium
#The path to the file \chromedriver.exe which is needed for selenium functionality.
chromeDriverPath = None

class tagObject():
    def __init__(self, tagName, tagId, tagAttributes, tagPicture):
        #The name/type of the tag (EX: span, or div)
        self.tagName = tagName
        #The id attached to the tag which may be used by javascript code.
        self.tagId = tagId
        #The attributes on the tag.
        self.tagAttributes = tagAttributes
        #A picture the tag on the web page, given the specified page conditions.
        self.tagPicture = tagPicture

class siteMap():
    def __init__(self, landingURL=None, ):
        self.landingURL = None

class webScraper():
    def __init__(self, manager=None, searchCriteria=[], desiredResourceTypes=[]):
        if(type(manager).__name__ == 'Polari'):
            #The Polari which is utilizing this webscraper to collect data from
            #the internet.
            self.manager = manager
        #The different search criteria objects which designate what types of resources
        #are acceptable to be collected for analysis.
        self.searchCriteria = searchCriteria
        #The different resource types (EX: text, jpg, png, mp4, etc..) which are allowed
        #to be returned as a part of the resources collected by the webscraper.
        self.desiredResourceTypes = desiredResourceTypes
