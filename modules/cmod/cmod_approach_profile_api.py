"""
@module cmod.cmod_approach_profile_api

rt-0: the route of the approach pre-profiler (contract in cmod.custom.approach_profile_doors). Own class, own file - /api/missions/{name}/approach sits
beside mis-0's /api/missions/{name}/solution|resolution and pp-0's /pin-profiles (same depth, literal last segment, same {name} field).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ApproachProfileAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/missions/{name}/approach', self, suffix='mission_approach')

    def on_get_mission_approach(self, request, response, name):
        from cmod.custom import approach_profile_doors as D
        D.get_approach(self, request, response, name)
