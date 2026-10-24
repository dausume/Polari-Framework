"""
@module board.chip_ladder_api

chp-0 (MISSION_GENERIC_PLAN.md section 13.1): the chips-and-levels doors - thin falcon handlers over board.custom.chip_ladder (the bodies
live there; this file only routes).

GET /api/board/chip-ladder?section=riscv|convenience   one row per chip: the four levels as words + basis, the emulator, what Polari holds
GET /api/board/chip-ladder/levels                       the four software levels, what each means, the open core picked for it
GET /api/board/chip-ladder/emulators                    one row per emulator: kind, licence, chips covered, pins real or stub, what is missing
A bad section is 400.
"""
import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class ChipLadderAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/chip-ladder', self, suffix='chips')
            add('/api/board/chip-ladder/levels', self, suffix='levels')
            add('/api/board/chip-ladder/emulators', self, suffix='emulators')

    def _serve(self, request, response, which):
        from board.custom import chip_ladder as CL
        status, payload = CL.door(self.manager, request.params, which)
        response.status = {200: falcon.HTTP_200, 400: falcon.HTTP_400}[status]
        response.media = payload

    def on_get_chips(self, request, response):
        """chp-0: the chips of one section (or all), one row each."""
        self._serve(request, response, 'chips')

    def on_get_levels(self, request, response):
        """chp-0: the four software levels."""
        self._serve(request, response, 'levels')

    def on_get_emulators(self, request, response):
        """chp-0: the emulators the ladder names."""
        self._serve(request, response, 'emulators')
