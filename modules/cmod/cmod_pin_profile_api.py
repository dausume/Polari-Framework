"""
@module cmod.cmod_pin_profile_api

pp-0: the routes of the pin-profile doors (contracts in cmod.custom.pin_profile_doors). Own class, own file - the Mission route
/api/missions/{name}/pin-profiles sits beside mis-0's /api/missions/{name}/solution|resolution (same depth, literal last segment, same {name} field).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PinProfileAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/capabilities/{name}/pin-profiles', self, suffix='purpose_pin_profiles')
            add('/api/missions/{name}/pin-profiles', self, suffix='mission_pin_profiles')
            add('/api/pin-profiles', self, suffix='pin_profiles_table')

    def on_get_purpose_pin_profiles(self, request, response, name):
        from cmod.custom import pin_profile_doors as D
        D.get_purpose(self, request, response, name)

    def on_get_mission_pin_profiles(self, request, response, name):
        from cmod.custom import pin_profile_doors as D
        D.get_mission(self, request, response, name)

    def on_get_pin_profiles_table(self, request, response):
        from cmod.custom import pin_profile_doors as D
        D.get_table(self, request, response)
