"""
@module vpn.objects.vpn.VpnPlacement

Row class VpnPlacement of the vpn module — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class VpnPlacement(treeObject):
    """WHERE one isle-vpn kind runs and AT WHICH LEVELS it is usable
    (vpn.custom.vpn_placement — his ask 2026-09-09).

    What it is: one row per kind (ten), seeded from PLACEMENT_INFO.
    `placement` is kvm (own guest; every kind that sees traffic and holds
    authority), openwrt-extension (on the router guest; every kind that
    carries the isle's subnet or VLAN) or container (endpoints, clients,
    peers, the blind relay). `level_isle` / `level_archipelago` /
    `level_mesh` carry the kind's ROLE at that level, '' when it has none.
    Related concepts: IsleCatalogEntry (the store row, carrying the same
    placement + guest fields), HardwareAppDefinition (the guest or
    extension for kvm / openwrt-extension kinds), VpnNetwork (the live
    mirror rows a placement produces once installed).
    How it is derived: pure data in vpn_placement.py; never typed by hand
    on a live instance — change the table, reseed.
    """

    @treeObjectInit
    def __init__(self, name: str = '', kind: str = '', provider: str = 'link',
                 title: str = '', placement: str = 'container', body: str = '',
                 extends: str = '', requires_tier: str = 'member',
                 sees_traffic: bool = False, blind: bool = False,
                 level_isle: str = '', level_archipelago: str = '',
                 level_mesh: str = '', levels_json: str = '[]',
                 install_plan_json: str = '[]', rationale: str = '',
                 notes: str = ''):
        self.name = name
        self.kind = kind
        self.provider = provider
        self.title = title
        self.placement = placement
        self.body = body
        self.extends = extends
        self.requires_tier = requires_tier
        self.sees_traffic = sees_traffic
        self.blind = blind
        self.level_isle = level_isle
        self.level_archipelago = level_archipelago
        self.level_mesh = level_mesh
        self.levels_json = levels_json
        self.install_plan_json = install_plan_json
        self.rationale = rationale
        self.notes = notes
