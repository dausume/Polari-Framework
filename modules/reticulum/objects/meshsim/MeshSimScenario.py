"""
@module reticulum.objects.meshsim.MeshSimScenario

Row class MeshSimScenario of the reticulum module — one class per file (design §7), split
from meshsim_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MeshSimScenario(treeObject):
    """One planning scenario: bearer set, devices per bearer, target
    bandwidth, app spread policies. Rows so scenarios are compared,
    not re-typed."""

    @treeObjectInit
    def __init__(self, name='', bearer_set='lora-only',
                 propagation_mode='flat-assumed',
                 device_models_json='{}', mesh_size_nodes=5,
                 area_m2=0.0, target_per_peer_bps=500,
                 app_spread_policies_json='{}', notes='',
                 manager=None):
        self.name = name
        self.bearer_set = bearer_set
        self.propagation_mode = propagation_mode
        # {'rnode-lora': 'dsd-tech-sh-l1a', ...} — KNOWN devices only.
        self.device_models_json = device_models_json
        self.mesh_size_nodes = mesh_size_nodes
        self.area_m2 = area_m2
        self.target_per_peer_bps = target_per_peer_bps
        # {app: {bearers, max_airtime_share, max_hops,
        #        max_distance_m, boundary_geojson}}
        self.app_spread_policies_json = app_spread_policies_json
        self.notes = notes
