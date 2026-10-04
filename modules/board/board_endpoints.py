"""
@module board.board_endpoints
construct_board_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
brd-fi: the firmware installer's doors (board.installer_api) are constructed beside the board API; brd-bo: the board object's
(board.board_object_api).
"""
from board.board_api import BoardAPI
from board.installer_api import BoardInstallerAPI
from board.board_object_api import BoardObjectAPI


def construct_board_endpoints(polServer):
    api = BoardAPI(polServer=polServer, manager=polServer.manager)
    api.installer = BoardInstallerAPI(polServer=polServer, manager=polServer.manager)
    api.board_object = BoardObjectAPI(polServer=polServer, manager=polServer.manager)   # brd-bo: /api/board/{board}/pins|views|conflicts|render|ingest
    return api
