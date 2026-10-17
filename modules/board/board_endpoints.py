"""
@module board.board_endpoints
construct_board_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
brd-fi: the firmware installer's doors (board.installer_api) are constructed beside the board API; brd-bo: the board object's
(board.board_object_api).
"""
from board.board_api import BoardAPI
from board.installer_api import BoardInstallerAPI
from board.board_object_api import BoardObjectAPI
from board.pin_view_api import PinViewAPI
from board.register_profile_api import RegisterProfileAPI


def construct_board_endpoints(polServer):
    api = BoardAPI(polServer=polServer, manager=polServer.manager)
    api.installer = BoardInstallerAPI(polServer=polServer, manager=polServer.manager)
    api.board_object = BoardObjectAPI(polServer=polServer, manager=polServer.manager)   # brd-bo: /api/board/{board}/pins|views|conflicts|render|ingest
    api.pin_view = PinViewAPI(polServer=polServer, manager=polServer.manager)   # pv-0: /api/board/{board}/pin-view[/pins|/connections|/surfaces]
    api.register_profile = RegisterProfileAPI(polServer=polServer, manager=polServer.manager)   # rp-0: /api/board/socs/{soc}/register-profile|memory-map
    return api
