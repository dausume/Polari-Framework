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


from objectTreeDecorators import *
import falcon

class systemInfoAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/system-info'
        if polServer != None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        try:
            hostSys = self.manager.hostSys
            # Refresh live metrics before responding
            hostSys.refreshMetrics()

            platform = {
                "systemType": getattr(hostSys, 'systemType', ''),
                "networkName": getattr(hostSys, 'networkName', ''),
                "IPaddress": getattr(hostSys, 'IPaddress', ''),
                "domainName": getattr(hostSys, 'domainName', ''),
                "isContainerized": getattr(hostSys, 'isContainerized', False)
            }

            cpu = {
                "numPhysicalCPUs": getattr(hostSys, 'numPhysicalCPUs', 0),
                "numLogicalCPUs": getattr(hostSys, 'numLogicalCPUs', 0),
                "currentUsagePercent": getattr(hostSys, 'currentCpuPercent', 0)
            }

            # Memory values are stored as (value, timestamp) tuples
            memAvail = getattr(hostSys, 'availableMainMemoryInBytes', (0, ''))
            memUsed = getattr(hostSys, 'usedMainMemoryInBytes', (0, ''))
            memFree = getattr(hostSys, 'freeMainMemoryInBytes', (0, ''))
            memPercent = getattr(hostSys, 'percentMainMemoryUsed', (0, ''))

            memory = {
                "total": getattr(hostSys, 'totalMainMemoryInBytes', 0),
                "available": memAvail[0] if isinstance(memAvail, tuple) else memAvail,
                "used": memUsed[0] if isinstance(memUsed, tuple) else memUsed,
                "free": memFree[0] if isinstance(memFree, tuple) else memFree,
                "percentUsed": memPercent[0] if isinstance(memPercent, tuple) else memPercent
            }

            swapTotal = getattr(hostSys, 'totalSwapMemoryInBytes', 0)
            swapUsed = getattr(hostSys, 'usedSwapMemoryInBytes', (0, ''))
            swapFree = getattr(hostSys, 'freeSwapMemoryInBytes', (0, ''))

            swap = {
                "total": swapTotal,
                "used": swapUsed[0] if isinstance(swapUsed, tuple) else swapUsed,
                "free": swapFree[0] if isinstance(swapFree, tuple) else swapFree
            }

            bootProfile = {
                "isFreshBoot": getattr(self.manager, 'isFreshBoot', False),
                "baseline": getattr(self.manager, 'bootResourceBaseline', None),
                "postTree": getattr(self.manager, 'bootResourcePostTree', None),
                "postDB": getattr(self.manager, 'bootResourcePostDB', None)
            }

            systemInfo = {
                "platform": platform,
                "cpu": cpu,
                "memory": memory,
                "swap": swap,
                "bootProfile": bootProfile
            }

            jsonObj = {"system-info": systemInfo}
            response.media = [jsonObj]
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            print(f"[systemInfoAPI] Error in GET: {err}")

        response.set_header('Powered-By', 'Polari')
