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
WebSocket Status API Endpoint

Provides runtime status of the STOMP-over-WebSocket notification server
and a summary of per-class WebSocket notification configuration.

GET /wsStatus - Returns STOMP server status and per-class WS config
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariApiServer.stompWebSocketServer import get_stomp_server
import falcon


class WsStatusAPI(treeObject):
    """
    API endpoint for inspecting STOMP WebSocket server status and
    per-class notification configuration.
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/wsStatus'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        """
        Returns the STOMP server runtime status and per-class WS configuration.

        Response:
        {
            "server": { "running": true, "port": 3001, "topics": [...], "subscribers": N },
            "classes": {
                "MyClass": {
                    "polariTreeWs": true,
                    "flatJsonWs": false,
                    "d3ColumnWs": false,
                    "geoJsonWs": false,
                    "activeTopics": ["/topic/MyClass"]
                },
                ...
            }
        }
        """
        try:
            # Get STOMP server runtime status (module-level singleton)
            stompServer = get_stomp_server()
            if stompServer is not None:
                serverStatus = stompServer.get_status()
            else:
                serverStatus = {
                    "running": False,
                    "port": None,
                    "topics": [],
                    "subscribers": 0
                }

            # Gather per-class WS configuration from ApiFormatConfig instances
            classConfigs = {}
            if hasattr(self.manager, 'objectTypingDict'):
                for className, typingObj in self.manager.objectTypingDict.items():
                    formatConfig = getattr(typingObj, 'apiFormatConfig', None)
                    if formatConfig is None:
                        continue
                    # Only include classes that have at least one WS flag enabled
                    hasAnyWs = (formatConfig.polariTreeWsEnabled or
                                formatConfig.flatJsonWsEnabled or
                                formatConfig.d3ColumnWsEnabled or
                                formatConfig.geoJsonWsEnabled)
                    if hasAnyWs:
                        classConfigs[className] = {
                            "polariTreeWs": formatConfig.polariTreeWsEnabled,
                            "flatJsonWs": formatConfig.flatJsonWsEnabled,
                            "d3ColumnWs": formatConfig.d3ColumnWsEnabled,
                            "geoJsonWs": formatConfig.geoJsonWsEnabled,
                            "activeTopics": formatConfig.getActiveWsTopics()
                        }

            response.status = falcon.HTTP_200
            response.media = {
                "server": serverStatus,
                "classes": classConfigs
            }

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"error": str(err)}
            print(f"[WsStatusAPI] Error: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')
