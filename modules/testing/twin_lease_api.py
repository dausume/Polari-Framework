"""
@module testing.twin_lease_api

acct-3: TEST-BUILD-ONLY lease handle. Production has deliberately NO
HTTP endpoint to acquire/release the mutation lease — runs get it
only through the simulation gate, in-process. The twin rehearsal
drives everything over the wire from OUTSIDE the containers, so its
fixtures (which boot with POLARI_TEST_BUILD=true — they ARE test
builds) expose this thin adapter over the same
simulationLocks.lease functions the gate calls. A normal build
never registers this route (testing.custom.absence_probe pins that).

  POST /api/testing/lease  {action: acquire|release, runId, token?}
"""

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class TwinLeaseAPI(treeObject):
    """Test-build lease adapter for out-of-process orchestrators."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/testing/lease'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/testing/lease', self, suffix='lease')

    def on_post_lease(self, request, response):
        from simulationLocks.lease import acquire_lease, release_lease
        body = request.get_media() or {}
        action = body.get('action')
        run_id = body.get('runId', '')
        if action == 'acquire':
            result = acquire_lease(self.manager, run_id)
        elif action == 'release':
            result = release_lease(self.manager, run_id,
                                   int(body.get('token', 0)))
        else:
            response.status = falcon.HTTP_400
            response.media = {'ok': False,
                              'refusal': "action must be 'acquire' "
                                         "or 'release'"}
            return
        if not result.get('ok', True) and 'token' not in result:
            response.status = falcon.HTTP_409
        response.media = result
