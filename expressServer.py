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
import http.server as srv
import ssl

#Creates a basic server with a ssl certificate that allows for a secure website to operate.
pyServer = srv.HTTPServer(('localhost',4443), srv.SimpleHTTPRequestHandler)
pyServer.socket = ssl.wrap_socket(pyServer.socket,certfile='./server.pem', server_side=True)
#If you want to open this permanently for actual website hosting - uncomment below.
#pyServer.serve_forever()

class expressServer:
    def __init__(self, name=None, displayName=None, manager=None):
        self.name
        self.displayName
        self.manager
        #The exact system that is the primary host of this server.
        self.hostSystem
        #The systems that maintain a secure local connection to this system/server and are used
        #for data processing by it, but do not have their own servers.
        self.siblingSystems = []
        #Other servers which maintain a connection with the internet, which this server may
        #maintain APIs to for exclusive access to that server.
        self.siblingServers = []
        self.certFile='./server.pem'
        self.sockets = []
        self.localChannel = None
        self.apiPages = []
    
#The api endpoints that are used to allow users to access files or data remotely through a
#specific URI Ex: http://www.polariai.com/login would send a user the static login html page
#for the polari website.
class apiEndPoint:
    def __init__(self, domainName, route, sourceFile):
        self.domainName 
        self.route
        self.sourceFile