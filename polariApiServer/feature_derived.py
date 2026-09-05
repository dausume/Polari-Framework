"""
@module polariApiServer.feature_derived

dyn-1 follow-up (the 2026-09-04 merge): the DERIVED seed values that
used to sit inside polariServer's guarded import blocks next to the
imports — module-level computations over imported seeds (score
subjects per device, per-device score/cell/block pages, scene rows
and part shapes, food-material seeds). The feature-import table
replays IMPORTS only, so these run right after it, per module, each
in its own try: an absent module leaves its symbols stubbed
(SEED_* -> [], callables -> None), the computation raises, the block
is skipped and says so. Statements are verbatim from the last branch
that owned them (dev + dev-lad-1). Live admission (dyn-2/4) re-runs
derive_feature_seeds(globals()) after un-stubbing.
"""


def derive_feature_seeds(g):
    """Run every derived-seed block against a namespace (polariServer
    globals). Returns {module: 'ok' | 'skipped: <why>'}."""
    report = {}
    # ---- foodstate
    g.setdefault('SEED_FOOD_MATERIALS', [])
    g.setdefault('SEED_FOOD_COMPOSITION_CLAIMS', [])
    try:
        exec(compile('SEED_FOOD_MATERIALS = build_food_material_seeds(\n    vendor_food_index())\nSEED_FOOD_COMPOSITION_CLAIMS = build_composition_claim_seeds()', 'feature_derived:%s' % 'foodstate', 'exec'), g)
        report['foodstate'] = 'ok'
    except Exception as e:  # noqa: BLE001
        report['foodstate'] = 'skipped: %s' % e
        print('[feature_derived] foodstate: derived seeds skipped (%s)' % e, flush=True)
    # ---- cntfet
    g.setdefault('SEED_FET_SCORE_SUBJECTS', [])
    g.setdefault('SEED_FET_SCORE_VALUES', [])
    g.setdefault('SEED_CELL_SCORE_SUBJECTS', [])
    g.setdefault('SEED_CNT_SCORE_PAGES', [])
    g.setdefault('SEED_CNT_DEVICE_SCENE_ROWS', [])
    g.setdefault('SEED_CNT_FV_GRAPHS', [])
    g.setdefault('SEED_CELL_CONFIGS', [])
    g.setdefault('SEED_BLOCK_CONFIGS', [])
    g.setdefault('FETRegime', [])
    g.setdefault('SEED_FET_REGIMES', [])
    g.setdefault('FETCharacteristic', [])
    g.setdefault('SEED_FET_CHARACTERISTICS', [])
    g.setdefault('ScatteringMechanism', [])
    g.setdefault('TransportRegime', [])
    g.setdefault('SEED_SCATTERING_MECHANISMS', [])
    g.setdefault('SEED_TRANSPORT_REGIMES', [])
    g.setdefault('FETFieldBand', [])
    g.setdefault('FETFieldSample', [])
    g.setdefault('SEED_FET_FIELD_BANDS', [])
    g.setdefault('SEED_FET_FIELD_MATERIALS_3D', [])
    g.setdefault('SEED_FET_PART_SHAPES_CNT', [])
    g.setdefault('SEED_FET_FIELD_BINDINGS', [])
    g.setdefault('ComplementaryPair', [])
    g.setdefault('FETOptimizationClass', [])
    g.setdefault('FETShapeType', [])
    g.setdefault('SEED_COMPLEMENTARY_PAIRS', [])
    g.setdefault('SEED_FET_OPTIMIZATION_CLASSES', [])
    g.setdefault('SEED_FET_SHAPE_TYPES', [])
    g.setdefault('SEED_SIGNAL_SCORE_CONCEPTS', [])
    g.setdefault('SEED_SIGNAL_SCORE_TERMS', [])
    g.setdefault('PowerBudget', [])
    g.setdefault('SEED_POWER_BUDGETS', [])
    g.setdefault('SEED_POWER_SCORE_TERMS', [])
    g.setdefault('DesignTarget', [])
    g.setdefault('FETTargetMapping', [])
    g.setdefault('SEED_DESIGN_TARGETS', [])
    g.setdefault('SEED_FET_TARGET_MAPPINGS', [])
    g.setdefault('SEED_TARGET_POWER_BUDGETS', [])
    g.setdefault('TechnologyIPRecord', [])
    g.setdefault('SEED_TECHNOLOGY_IP', [])
    g.setdefault('EvidenceItem', [])
    g.setdefault('SEED_EVIDENCE', [])
    g.setdefault('OpenCellLibrary', [])
    g.setdefault('SEED_OPEN_LIBRARIES', [])
    g.setdefault('SEED_OPEN_LIBRARY_PAGES', [])
    g.setdefault('FunctionalBlock', [])
    g.setdefault('SEED_FUNCTIONAL_BLOCKS', [])
    g.setdefault('SEED_BLOCK_PAGES', [])
    try:
        exec(compile("SEED_FET_SCORE_SUBJECTS, SEED_FET_SCORE_VALUES = \\\n    _fet_score_subjects([d['name'] for d in SEED_CNT_DEVICES])\nSEED_CELL_SCORE_SUBJECTS = _cell_score_subjects(\n    [c['name'] for c in SEED_CNT_CELLS])\nSEED_CNT_SCORE_PAGES = _cnt_score_pages(\n    [d['name'] for d in SEED_CNT_DEVICES])\ntry:\n    from cntfet.cnt_compare import detail_pages as _cnt_detail_pages\n    SEED_CNT_SCORE_PAGES = SEED_CNT_SCORE_PAGES + _cnt_detail_pages(\n        [d['name'] for d in SEED_CNT_DEVICES])\nexcept ImportError:\n    pass\nSEED_CNT_DEVICE_SCENE_ROWS = SEED_CNT_DEVICE_SCENES(\n    [d['name'] for d in (SEED_CNT_DEVICES or [])])\nSEED_CNT_FV_GRAPHS = _cnt_fv_graphs()\nSEED_CNT_SCORE_PAGES = SEED_CNT_SCORE_PAGES + SEED_CELL_PAGES\nSEED_CELL_CONFIGS = seed_cell_configs(\n    [d['name'] for d in SEED_CNT_DEVICES])\nSEED_CNT_SCORE_PAGES = SEED_CNT_SCORE_PAGES + SEED_BLOCK_PAGES\nSEED_BLOCK_CONFIGS = seed_block_configs(\n    [d['name'] for d in SEED_CNT_DEVICES])\ntry:\n    from cntfet.cnt_regimes import FETRegime, SEED_FET_REGIMES\nexcept ImportError:\n    FETRegime, SEED_FET_REGIMES = None, []\ntry:\n    from cntfet.cnt_characteristics import (\n        FETCharacteristic, SEED_FET_CHARACTERISTICS,\n    )\nexcept ImportError:\n    FETCharacteristic, SEED_FET_CHARACTERISTICS = None, []\ntry:\n    from cntfet.cnt_transport import (\n        ScatteringMechanism, TransportRegime,\n        SEED_SCATTERING_MECHANISMS, SEED_TRANSPORT_REGIMES,\n    )\nexcept ImportError:\n    ScatteringMechanism = TransportRegime = None\n    SEED_SCATTERING_MECHANISMS, SEED_TRANSPORT_REGIMES = [], []\ntry:\n    from cntfet.cnt_fields import (\n        FETFieldBand, FETFieldSample, SEED_FET_FIELD_BANDS,\n        SEED_FET_FIELD_MATERIALS_3D,\n    )\nexcept ImportError:\n    FETFieldBand = FETFieldSample = None\n    SEED_FET_FIELD_BANDS, SEED_FET_FIELD_MATERIALS_3D = [], []\ntry:\n    from cntfet.cnt_scene import (\n        SEED_CNT_DEVICE_SCENES, SEED_FET_FIELD_BINDINGS,\n    )\n    SEED_CNT_DEVICE_SCENE_ROWS = SEED_CNT_DEVICE_SCENES(\n        [d['name'] for d in (SEED_CNT_DEVICES or [])])\n    # fg-3: the 2-D parts view per device (fet-2d-{name}) beside\n    # the 3-D scenes — freestandingOnly region rectangles.\n    from cntfet.cnt_parts_svg import SEED_FET_2D_SCENES\n    SEED_CNT_DEVICE_SCENE_ROWS = (\n        SEED_CNT_DEVICE_SCENE_ROWS\n        + SEED_FET_2D_SCENES(\n            [d['name'] for d in (SEED_CNT_DEVICES or [])]))\n    # fg-6 (Dustin): every 3-D FET piece is a MathShapeDefinition\n    # row — the scenes reference them via mathshape: refs.\n    from cntfet.cnt_scene import part_shape_seeds as _cnt_psh\n    SEED_FET_PART_SHAPES_CNT = [\n        sh for _pn in [d['name'] for d in (SEED_CNT_DEVICES or [])]\n        for sh in _cnt_psh(_pn)]\nexcept (ImportError, TypeError):\n    SEED_CNT_DEVICE_SCENE_ROWS, SEED_FET_FIELD_BINDINGS = [], []\n    SEED_FET_PART_SHAPES_CNT = []\ntry:\n    from cntfet.cnt_device_viz import extra_graph_seeds as _cnt_fv_graphs\n    SEED_CNT_FV_GRAPHS = _cnt_fv_graphs()\nexcept ImportError:\n    SEED_CNT_FV_GRAPHS = []\ntry:\n    from cntfet.cnt_taxonomy import (\n        ComplementaryPair, FETOptimizationClass, FETShapeType,\n        SEED_COMPLEMENTARY_PAIRS, SEED_FET_OPTIMIZATION_CLASSES,\n        SEED_FET_SHAPE_TYPES, SEED_SIGNAL_SCORE_CONCEPTS,\n        SEED_SIGNAL_SCORE_TERMS,\n    )\nexcept ImportError:\n    ComplementaryPair = FETOptimizationClass = FETShapeType = None\n    SEED_COMPLEMENTARY_PAIRS = SEED_FET_OPTIMIZATION_CLASSES = []\n    SEED_FET_SHAPE_TYPES = SEED_SIGNAL_SCORE_CONCEPTS = []\n    SEED_SIGNAL_SCORE_TERMS = []\ntry:\n    from cntfet.cnt_power import (\n        PowerBudget, SEED_POWER_BUDGETS, SEED_POWER_SCORE_TERMS,\n    )\nexcept ImportError:\n    PowerBudget, SEED_POWER_BUDGETS, SEED_POWER_SCORE_TERMS = None, [], []\ntry:\n    from cntfet.cnt_targets import (\n        DesignTarget, FETTargetMapping, SEED_DESIGN_TARGETS,\n        SEED_FET_TARGET_MAPPINGS, SEED_TARGET_POWER_BUDGETS,\n    )\nexcept ImportError:\n    DesignTarget = FETTargetMapping = None\n    SEED_DESIGN_TARGETS = SEED_FET_TARGET_MAPPINGS = []\n    SEED_TARGET_POWER_BUDGETS = []\ntry:\n    from cntfet.cnt_ip import SEED_TECHNOLOGY_IP, TechnologyIPRecord\nexcept ImportError:\n    TechnologyIPRecord, SEED_TECHNOLOGY_IP = None, []\ntry:\n    from cntfet.cnt_evidence import EvidenceItem, SEED_EVIDENCE\nexcept ImportError:\n    EvidenceItem, SEED_EVIDENCE = None, []\ntry:\n    from cntfet.cnt_open_library import (\n        OpenCellLibrary, SEED_OPEN_LIBRARIES, SEED_OPEN_LIBRARY_PAGES,\n    )\nexcept ImportError:\n    OpenCellLibrary, SEED_OPEN_LIBRARIES, SEED_OPEN_LIBRARY_PAGES = None, [], []\ntry:\n    from cntfet.cnt_blocks import (\n        FunctionalBlock, SEED_FUNCTIONAL_BLOCKS, SEED_BLOCK_PAGES,\n    )\nexcept ImportError:\n    FunctionalBlock, SEED_FUNCTIONAL_BLOCKS, SEED_BLOCK_PAGES = None, [], []", 'feature_derived:%s' % 'cntfet', 'exec'), g)
        report['cntfet'] = 'ok'
    except Exception as e:  # noqa: BLE001
        report['cntfet'] = 'skipped: %s' % e
        print('[feature_derived] cntfet: derived seeds skipped (%s)' % e, flush=True)
    # ---- sifet
    g.setdefault('_si_seeds', [])
    g.setdefault('SEED_SI_DOPINGS', [])
    g.setdefault('SEED_SI_SHAPES', [])
    g.setdefault('SEED_SI_DEVICES', [])
    g.setdefault('SEED_SOLGEL_DIELECTRICS', [])
    g.setdefault('SEED_SOLGEL_PROCESSES', [])
    g.setdefault('SiliconDopingProfile', [])
    g.setdefault('SiliconFETShape', [])
    g.setdefault('SiliconMOSFET', [])
    g.setdefault('SolGelDielectric', [])
    g.setdefault('SolGelProcess', [])
    g.setdefault('RefinementRoute', [])
    g.setdefault('RefinementStep', [])
    g.setdefault('SiliconGrade', [])
    g.setdefault('SEED_REFINEMENT_ROUTES', [])
    g.setdefault('SEED_REFINEMENT_STEPS', [])
    g.setdefault('SEED_SILICON_GRADES', [])
    g.setdefault('SEED_SI_REFINEMENT_GRAPHS', [])
    g.setdefault('SiliconProcessNode', [])
    g.setdefault('SEED_SILICON_PROCESS_NODES', [])
    g.setdefault('SEED_SILICON_ANCHORS', [])
    g.setdefault('SEED_LADDER_EVIDENCE', [])
    g.setdefault('SEED_LADDER_IP', [])
    g.setdefault('SEED_SI_LADDER_GRAPHS', [])
    g.setdefault('SEED_SI_PAGE_DISPLAYS', [])
    g.setdefault('SEED_SI_SCORE_PAGES', [])
    g.setdefault('SEED_CNT_DEVICE_SCENE_ROWS', [])
    g.setdefault('SEED_FET_PART_SHAPES_SI', [])
    g.setdefault('SEED_CELL_CONFIGS', [])
    g.setdefault('SEED_BLOCK_CONFIGS', [])
    try:
        exec(compile("try:\n    from sifet.si_basis import (\n        SEED_TABLES as _SI_SEED_TABLES, SiliconDopingProfile,\n        SiliconFETShape, SiliconMOSFET, SolGelDielectric, SolGelProcess,\n    )\n    _si_seeds = dict(_SI_SEED_TABLES)\n    SEED_SI_DOPINGS = _si_seeds.get('SiliconDopingProfile', [])\n    SEED_SI_SHAPES = _si_seeds.get('SiliconFETShape', [])\n    SEED_SI_DEVICES = _si_seeds.get('SiliconMOSFET', [])\n    SEED_SOLGEL_DIELECTRICS = _si_seeds.get('SolGelDielectric', [])\n    SEED_SOLGEL_PROCESSES = _si_seeds.get('SolGelProcess', [])\nexcept ImportError:\n    SiliconDopingProfile = SiliconFETShape = SiliconMOSFET = None\n    SolGelDielectric = SolGelProcess = None\n    SEED_SI_DOPINGS = SEED_SI_SHAPES = SEED_SI_DEVICES = []\n    SEED_SOLGEL_DIELECTRICS = SEED_SOLGEL_PROCESSES = []\ntry:\n    from sifet.si_refinement import (\n        RefinementRoute, RefinementStep, SiliconGrade,\n        SEED_REFINEMENT_ROUTES, SEED_REFINEMENT_STEPS,\n        SEED_SILICON_GRADES, SEED_SI_REFINEMENT_GRAPHS,\n    )\nexcept ImportError:\n    RefinementRoute = RefinementStep = SiliconGrade = None\n    SEED_REFINEMENT_ROUTES = SEED_REFINEMENT_STEPS = []\n    SEED_SILICON_GRADES = SEED_SI_REFINEMENT_GRAPHS = []\ntry:\n    from sifet.si_ladder import (\n        SiliconProcessNode, SEED_SILICON_PROCESS_NODES,\n        SEED_SILICON_ANCHORS, SEED_LADDER_EVIDENCE, SEED_LADDER_IP,\n        SEED_SI_LADDER_GRAPHS,\n    )\nexcept ImportError:\n    SiliconProcessNode = None\n    SEED_SILICON_PROCESS_NODES = SEED_SILICON_ANCHORS = []\n    SEED_LADDER_EVIDENCE = SEED_LADDER_IP = SEED_SI_LADDER_GRAPHS = []\ntry:\n    from sifet.si_pages_seed import (\n        SEED_SI_PAGE_DISPLAYS, SEED_SI_SCORE_PAGES,\n    )\nexcept ImportError:\n    SEED_SI_PAGE_DISPLAYS, SEED_SI_SCORE_PAGES = [], []\ntry:\n    from sifet.si_pages_seed import (\n        SEED_SI_PAGE_DISPLAYS, SEED_SI_SCORE_PAGES,\n    )\n    # fg-3: a 2-D parts view (fet-2d-{name}) per silicon device too.\n    from cntfet.cnt_parts_svg import SEED_FET_2D_SCENES as _fet2d\n    from sifet.si_pages_seed import SI_DEVICE_NAMES as _si2d_names\n    SEED_CNT_DEVICE_SCENE_ROWS = (\n        (SEED_CNT_DEVICE_SCENE_ROWS or []) + _fet2d(list(_si2d_names)))\n    # fg-6: the silicon 3-D device scenes (fet-3d-{name} box stacks\n    # with the FETFieldSample binding — scrub Vg like the CNT tubes).\n    from sifet.si_scene import SEED_SI_DEVICE_SCENES as _si3d\n    SEED_CNT_DEVICE_SCENE_ROWS = (\n        SEED_CNT_DEVICE_SCENE_ROWS + _si3d(list(_si2d_names)))\n    # fg-6: the silicon pieces as MathShapeDefinition rows too.\n    from sifet.si_scene import part_shape_seeds_si as _si_psh\n    SEED_FET_PART_SHAPES_SI = [\n        sh for _pn in list(_si2d_names) for sh in _si_psh(_pn)]\n    # cell arc: the config grid covers the silicon devices too.\n    from cntfet.cnt_cell_pages import seed_cell_configs as _scc\n    SEED_CELL_CONFIGS = _scc(\n        [d['name'] for d in (SEED_CNT_DEVICES or [])]\n        + list(_si2d_names))\n    # block level: the block grid covers the silicon devices too.\n    from cntfet.cnt_block_pages import seed_block_configs as _sbc\n    SEED_BLOCK_CONFIGS = _sbc(\n        [d['name'] for d in (SEED_CNT_DEVICES or [])]\n        + list(_si2d_names))\nexcept ImportError:\n    SEED_SI_PAGE_DISPLAYS, SEED_SI_SCORE_PAGES = [], []\n    SEED_FET_PART_SHAPES_SI = []", 'feature_derived:%s' % 'sifet', 'exec'), g)
        report['sifet'] = 'ok'
    except Exception as e:  # noqa: BLE001
        report['sifet'] = 'skipped: %s' % e
        print('[feature_derived] sifet: derived seeds skipped (%s)' % e, flush=True)
    return report
