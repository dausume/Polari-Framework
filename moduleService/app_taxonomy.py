"""
@module moduleService.app_taxonomy

How apps are CATEGORISED for people (his rulings 2026-09-14): one PRIMARY category per app, any number of
sub-categories (a sub-category belongs to one category; naming one from another category cross-lists the app there
as a secondary listing), free tags, and search across everything or inside one category. The category says what an
app is FOR; the kind (polari-app / isle-app / hardware-app / …) and the tier say how it RUNS — two axes, never mixed.

The vocabulary lives here; each module's polari-app.json declares `app.category`, `app.subcategories`, `app.tags`
(manifests conform checks them against this vocabulary). DEFAULTS carries the first mapping of today's modules —
`manifests generate` writes it into a manifest that has none, after which the manifest is the truth.

@consumers
  - moduleService.manifests (validation), appstore.custom.app_forms (manifest_app), appstore.app_debs_page (the catalogue),
    appstore.apps_api (fields + filters), moduleService.selftest_app_taxonomy
"""

CATEGORIES = {
    'polari': {'title': 'Polari Apps', 'blurb': 'Ordinary web apps: pages, data and simulations that run on your isle\'s Polari.'},
    'network': {'title': 'Network Apps', 'blurb': 'Links, mesh transports, the isle\'s own network guests and the bridges to other systems.'},
    'hardware': {'title': 'Hardware Apps', 'blurb': 'Apps that own real devices: KVM guests with passthrough and the expansions that ride on them. Need the hardware tier.'},
}

#: sub-category id → (category, title, one line). Empty sub-categories are never shown.
SUBCATEGORIES = {
    'materials-devices': ('polari', 'Materials & Devices', 'Materials, transistors, chips, motors and the physics behind them.'),
    'making-mechanics': ('polari', 'Making & Mechanics', 'Shapes, parts, gears, molds, printers and computers you can build.'),
    'food-living': ('polari', 'Food & Living', 'Meals, nutrition, households and the supply chain behind them.'),
    'environment-bio': ('polari', 'Environment & Bio', 'Growing, tanks, algae, forests and the climate record.'),
    'business-work': ('polari', 'Business & Work', 'Operations, the ERP connection and collaboration sessions.'),
    'knowledge-media': ('polari', 'Knowledge & Media', 'Evidence, scoring, tech trees, terms, video and XR spaces.'),
    'platform-operations': ('polari', 'Platform & Operations', 'The store, module plans, resources, security and testing.'),
    'vpn-links': ('network', 'VPN & Links', 'WireGuard-based isle links and their placements.'),
    'mesh-radio': ('network', 'Mesh & Radio', 'Reticulum and other transports that need no internet.'),
    'isle-guests': ('network', 'Isle Network Guests', 'OpenWrt guests the isle runs: relay and guest networks.'),
    'bridges': ('network', 'Bridges & Integrations', 'MQTT, gRPC and other doors into and out of Polari.'),
    'fabrication': ('hardware', 'Fabrication & Printing', '3D printers and the cameras and tools that expand them.'),
    'network-devices': ('hardware', 'Network Devices', 'Radios, routers and access points as hardware apps.'),
    'chip-simulation': ('hardware', 'Chip Design & Simulation', 'FPGAs, SDRs and chip test rigs as hardware apps.'),
    'robotics-simulation': ('hardware', 'Robotics Simulation', 'Robots and motion rigs as hardware apps.'),
}

#: the first mapping (module → primary category, sub-categories, tags); a manifest that declares its own wins
DEFAULTS = {
    'magnetics': ('polari', ['materials-devices'], ['magnets', 'motors']),
    'sifet': ('polari', ['materials-devices'], ['mosfet', 'silicon']),
    'cntfet': ('polari', ['materials-devices'], ['fet', 'nanotube']),
    'electrodevice': ('polari', ['materials-devices'], ['spice', 'circuits']),
    'microchip': ('polari', ['materials-devices', 'chip-simulation'], ['chip', 'ladder']),
    # tt-0: tensors, tensor trees, the compute ladder (plan COMPUTE_LOD_TENSOR_PLAN.md)
    'tensormath': ('polari', ['knowledge-media', 'materials-devices'], ['tensor', 'math']),
    'tensortree': ('polari', ['knowledge-media', 'materials-devices'], ['tensor', 'tree', 'visualization']),
    'computelod': ('polari', ['materials-devices', 'chip-simulation', 'knowledge-media'], ['compute', 'ladder', 'learning']),
    'hwdigital': ('polari', ['materials-devices', 'chip-simulation'], ['logic', 'ice40', 'bitstream']),
    'hwfpga': ('polari', ['materials-devices', 'chip-simulation'], ['fpga', 'verilog']),
    'motors': ('polari', ['materials-devices', 'making-mechanics'], ['motors']),
    'materials_science': ('polari', ['materials-devices'], ['materials']),
    'gears': ('polari', ['making-mechanics'], ['gears', 'ratios']),
    'mathshapes': ('polari', ['making-mechanics'], ['shapes', 'cad', 'csg']),
    'composition': ('polari', ['making-mechanics'], ['parts', 'interfaces']),
    'casting': ('polari', ['making-mechanics'], ['molds', 'casting']),
    'waxprint': ('polari', ['making-mechanics', 'fabrication'], ['wax', 'printer', 'simulation']),
    'waxsupply': ('polari', ['making-mechanics', 'environment-bio'], ['wax', 'bio']),
    'computers': ('polari', ['making-mechanics'], ['computers', 'builds']),
    'computerparts': ('polari', ['making-mechanics'], ['parts', 'prices']),
    'printing_suite': ('polari', ['making-mechanics', 'fabrication'], ['suite', 'printing']),
    'nutrition': ('polari', ['food-living'], ['nutrients', 'household']),
    'mealoptions': ('polari', ['food-living'], ['meals', 'recipes']),
    'foodstate': ('polari', ['food-living'], ['food', 'pspp']),
    'household': ('polari', ['food-living'], ['household', 'schedules']),
    'supplychain': ('polari', ['food-living', 'environment-bio'], ['supply chain', 'carbon']),
    'aquaponics': ('polari', ['environment-bio'], ['aquaponics', 'plants']),
    'tanks': ('polari', ['environment-bio'], ['tanks', 'fish']),
    'plant_morphology': ('polari', ['environment-bio'], ['plants', '3d']),
    'microalgae': ('polari', ['environment-bio'], ['algae', 'reactor']),
    'biomining': ('polari', ['environment-bio'], ['bacteria', 'extraction']),
    'agro_forestry': ('polari', ['environment-bio'], ['forestry']),
    'climate': ('polari', ['environment-bio', 'knowledge-media'], ['co2', 'climate']),
    'bizops': ('polari', ['business-work'], ['operations', 'orders']),
    'odooconnect': ('polari', ['business-work', 'bridges'], ['odoo', 'erp']),
    'dmvdata': ('polari', ['knowledge-media'], ['cost of living', 'sources']),
    'collab': ('polari', ['business-work', 'knowledge-media'], ['meetings', 'livekit']),
    'scoring': ('polari', ['knowledge-media'], ['scoring', 'epistemics']),
    'pspp': ('polari', ['materials-devices', 'knowledge-media'], ['pspp', 'materials', 'evidence', 'claims']),
    'hwmap': ('polari', ['platform-operations'], ['hardware map', 'usb', 'pci', 'iommu']),
    'techtree': ('polari', ['knowledge-media'], ['tech tree']),
    'terms': ('polari', ['knowledge-media', 'platform-operations'], ['terms', 'acceptance']),
    'video': ('polari', ['knowledge-media'], ['video', 'hls']),
    'xr': ('polari', ['knowledge-media'], ['xr', 'vr']),
    'zones': ('polari', ['knowledge-media'], ['ar', 'zones']),
    'meshassets': ('polari', ['knowledge-media', 'making-mechanics'], ['3d assets', 'licences']),
    'appstore': ('polari', ['platform-operations'], ['store', 'downloads']),
    'polariapps': ('polari', ['platform-operations'], ['module plans']),
    'resources': ('polari', ['platform-operations'], ['resources', 'admission']),
    'security': ('polari', ['platform-operations'], ['security', 'audit']),
    'testing': ('polari', ['platform-operations'], ['testing', 'accountability']),
    'cicd': ('polari', ['platform-operations'], ['cicd', 'pipeline', 'release']),
    'iso': ('polari', ['platform-operations'], ['iso', 'ubuntu', 'installer']),
    'suiteapps': ('polari', ['platform-operations'], ['suites']),
    'hardwareapps': ('polari', ['platform-operations', 'network-devices'], ['hardware apps', 'kvm']),
    'islemesh': ('polari', ['platform-operations', 'isle-guests'], ['isle', 'mesh']),
    'vpn': ('network', ['vpn-links'], ['wireguard', 'vpn']),
    'reticulum': ('network', ['mesh-radio', 'network-devices'], ['reticulum', 'lora', 'mesh']),
    'isle_relay': ('network', ['isle-guests', 'network-devices'], ['openwrt', 'relay', 'wifi']),
    'isle_guestnet': ('network', ['isle-guests', 'network-devices'], ['openwrt', 'guest wifi']),
    'mqttbridge': ('network', ['bridges'], ['mqtt']),
    'grpcbridge': ('network', ['bridges'], ['grpc', 'java']),
    'kirimoto': ('polari', ['making-mechanics', 'fabrication'], ['slicer', '3d printing']),
    'voron': ('hardware', ['fabrication'], ['voron', '3d printer', 'klipper']),
    'printcam': ('hardware', ['fabrication'], ['camera', 'printer']),
}


def classify(module, app=None):
    """{category, subcategories, tags, secondary} for one app: the manifest's own declaration, else DEFAULTS, else
    the kind decides (hardware kinds → hardware; everything else → polari)."""
    app = app or {}
    cat = app.get('category') or ''
    subs = list(app.get('subcategories') or [])
    tags = list(app.get('tags') or [])
    if not cat:
        d = DEFAULTS.get(module)
        if d:
            cat, subs, tags = d[0], (subs or list(d[1])), (tags or list(d[2]))
        else:
            cat = 'hardware' if app.get('kind') in ('hardware-app', 'hardware-extension-app') else 'polari'
    subs = [s for s in subs if s in SUBCATEGORIES]
    secondary = sorted({SUBCATEGORIES[s][0] for s in subs} - {cat})
    return {'category': cat if cat in CATEGORIES else 'polari', 'subcategories': subs, 'tags': tags, 'secondary': secondary}


def problems(app):
    """Vocabulary problems in a manifest's app block (for conform); [] when fine or undeclared."""
    out = []
    cat = app.get('category')
    if cat and cat not in CATEGORIES:
        out.append('app.category must be one of %s' % (tuple(CATEGORIES),))
    for s in app.get('subcategories') or []:
        if s not in SUBCATEGORIES:
            out.append('app.subcategories: unknown "%s" (see moduleService/app_taxonomy.py)' % s)
    if not isinstance(app.get('tags', []), list):
        out.append('app.tags must be a list')
    return out


def matches(query, module, app, cls):
    """Search by name or properties: the id, the title, the description, the tags, the kind, the sub-category titles."""
    q = (query or '').strip().lower()
    if not q:
        return True
    hay = ' '.join([module, app.get('title', ''), app.get('description', ''), app.get('kind', ''), app.get('extends', ''),
                    ' '.join(cls['tags']), ' '.join(SUBCATEGORIES[s][1] for s in cls['subcategories']), CATEGORIES[cls['category']]['title']]).lower()
    return all(term in hay for term in q.split())
