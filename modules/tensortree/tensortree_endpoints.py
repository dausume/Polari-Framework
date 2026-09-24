"""
@module tensortree.tensortree_endpoints
construct_tensortree_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from tensortree.tensortree_api import TensorTreeAPI


def construct_tensortree_endpoints(polServer):
    return TensorTreeAPI(polServer=polServer, manager=polServer.manager)
