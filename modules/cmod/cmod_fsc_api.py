"""
@module cmod.cmod_fsc_api

fsc-2 doors (contract in cmod.custom.fsc_doors): GET /api/firmware-scores, /api/firmware-scores/top, /api/firmware-scores/breakdown, POST /api/firmware-scores/values,
GET|POST /api/firmware-score-profiles, GET /api/firmware-score-profiles/{name}/terms (the editor's term table). Own class, own file - registered beside the Mission / solve doors.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FscAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/firmware-scores', self, suffix='scores')
            add('/api/firmware-scores/top', self, suffix='top')
            add('/api/firmware-scores/breakdown', self, suffix='breakdown')
            add('/api/firmware-scores/values', self, suffix='values')
            add('/api/firmware-score-profiles', self, suffix='profiles')
            add('/api/firmware-score-profiles/{name}/terms', self, suffix='profile_terms')

    def on_get_scores(self, request, response):
        from cmod.custom import fsc_doors as D
        D.get_scores(self, request, response)

    def on_get_top(self, request, response):
        from cmod.custom import fsc_doors as D
        D.get_top(self, request, response)

    def on_get_breakdown(self, request, response):
        from cmod.custom import fsc_doors as D
        D.get_breakdown(self, request, response)

    def on_post_values(self, request, response):
        from cmod.custom import fsc_doors as D
        D.post_values(self, request, response)

    def on_get_profiles(self, request, response):
        from cmod.custom import fsc_doors as D
        D.get_profiles(self, request, response)

    def on_post_profiles(self, request, response):
        from cmod.custom import fsc_doors as D
        D.post_profile(self, request, response)

    def on_get_profile_terms(self, request, response, name):
        from cmod.custom import fsc_doors as D
        D.get_profile_terms(self, request, response, name)
