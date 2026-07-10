"""
@module materialsScience.msci_pages_seed

Seeds: the two materials-science DisplayDefinition PAGES (the
periodic-table page pattern — isPage + pageRoute + hosted registered
components), fixing the "no page for the wax derivation" gap:

  /display/materials-basis     — the materials × scale-levels 0-4 grid
                                 (status/lineage/results per cell,
                                 thermal windows, engine capability).
  /display/formulation-search  — the derivation workbench: every
                                 FormulationSearchDefinition knob
                                 editable, run/continue controls,
                                 refinement trajectory, winners table
                                 with fidelity badges + the explicit
                                 promote-to-L1 knob.

Both components read live rows/endpooints themselves — the seeds carry
only the wiring, no data.
"""

import json

from materialsScience.materials_basis import SCALE_LEVEL_DETAILS

SEED_MSCI_PAGE_DISPLAYS = [
    {
        'name': 'materials',
        'description': (
            'The Materials home: every material identity x every scale '
            'level (experimental -> quantum) as an accountability '
            'matrix — where each material IS defined, where it is '
            'partial, and where it is honestly missing — with per-level '
            'pages and the materials-science tools one click away.'
        ),
        'source_class': 'MaterialsScienceMaterial',
        'isPage': True,
        'pageRoute': 'materials',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': 'materials-home-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'Materials — definition levels 0-4',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'materials-home',
                    'inputs': {},
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    },
    {
        'name': 'materials-basis',
        'description': (
            'The materials basis browser: every material x scale level '
            '(experimental -> quantum) with its definition status, '
            'derivation lineage, stored engine results, thermal '
            'processing windows, and the live FEM/DFT engine '
            'capability. Gaps are shown honestly — absence of a level '
            'is data, not an error.'
        ),
        'source_class': 'MaterialScaleDefinition',
        'isPage': True,
        'pageRoute': 'materials-basis',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': 'materials-basis-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'Materials basis — scale levels 0-4',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'materials-basis-browser',
                    'inputs': {},
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    },
    {
        'name': 'fem-models',
        'description': (
            'The FEM simulation interface: configure finite-element '
            'problems the way FEM tools structure them — physics, '
            'domain and geometry, per-region materials (bindable to '
            'live object rows), boundary conditions, mesh, solver, '
            'results. Unsupported choices stay visible and say why.'
        ),
        'source_class': 'FEMModelDefinition',
        'isPage': True,
        'pageRoute': 'fem-models',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': 'fem-models-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'FEM models — configure and solve',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'fem-model-config',
                    'inputs': {'defaultModelRef':
                               'wax-thermal-continuum'},
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    },
    {
        'name': 'dft-models',
        'description': (
            'The DFT simulation interface: configure electronic-'
            'structure calculations the way DFT tools structure their '
            'inputs — calculation type, structure (molecule or bulk), '
            'method (basis, XC functional, charge/spin), accuracy '
            '(cutoff, k-points), results. Capability-gated honestly.'
        ),
        'source_class': 'DFTModelDefinition',
        'isPage': True,
        'pageRoute': 'dft-models',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': 'dft-models-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'DFT models — configure and compute',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'dft-model-config',
                    'inputs': {'defaultModelRef':
                               'paraffin-quantum-energy'},
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    },
    {
        'name': 'md-models',
        'description': (
            'The MD simulation interface: configure molecular-dynamics '
            'runs the way MD tools structure their decks — system '
            '(LJ fluid or bead-spring chains, reduced units with an '
            'optional bindable real-material mapping), interactions '
            '(force-field MD shown as the named gap), ensemble and '
            'thermostat, integration with the O(N^2) cost estimate '
            'before running, results with measured-vs-target honesty '
            'badges.'
        ),
        'source_class': 'MDModelDefinition',
        'isPage': True,
        'pageRoute': 'md-models',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': 'md-models-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'MD models — configure and simulate',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'md-model-config',
                    'inputs': {'defaultModelRef':
                               'lj-reference-fluid'},
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    },
    {
        'name': 'meso-models',
        'description': (
            'The mesoscale simulation interface: rod-network '
            'percolation (Monte-Carlo bisection sampling) and dipolar '
            'chaining (Brownian dynamics with the lambda-from-physics '
            'helper and the kinetics-limited warning). Verdicts show '
            'the derived vf_c against the Balberg slender-rod limit, '
            'and the explicit use-as-percolationThreshold knob binds '
            'the derived result into a chosen L1 model — never '
            'automatically.'
        ),
        'source_class': 'MesoModelDefinition',
        'isPage': True,
        'pageRoute': 'meso-models',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': 'meso-models-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'Mesoscale models — configure and study',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'meso-model-config',
                    'inputs': {'defaultModelRef':
                               'cnt-percolation-threshold'},
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    },
    {
        'name': 'formulation-search',
        'description': (
            'The formulation-search workbench: configure a '
            'FormulationSearchDefinition (targets, base, sourcing '
            'policy, staged-fidelity ladder — every knob explicit), '
            'run or continue the search, watch the refinement '
            'trajectory, and inspect winners with their fidelity '
            'badges. Promoting a winner to a level-1 scale definition '
            'is an explicit button, never automatic.'
        ),
        'source_class': 'FormulationSearchDefinition',
        'isPage': True,
        'pageRoute': 'formulation-search',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': 'formulation-search-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': 'Wax formulation search',
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'formulation-search-workbench',
                    'inputs': {
                        'defaultSearchRef': 'wax-derivation-screening',
                    },
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    },
]

# One page per scale level (msci-24) — generated from the SAME
# SCALE_LEVEL_DETAILS the presence API reads, so the pages and the
# taxonomy cannot drift apart. Each page hosts material-level-page
# with the level as its only input; the component fetches the level's
# defined/partial/missing accountability itself.
for _level, _detail in sorted(SCALE_LEVEL_DETAILS.items()):
    SEED_MSCI_PAGE_DISPLAYS.append({
        'name': f'materials-level-{_level}',
        'description': (
            f"Scale level {_level} — {_detail['name']} "
            f"({_detail['lengthRange']}; {_detail['methods']}). Which "
            f"materials are defined at this level, which are partial, "
            f"and which are missing — every absence carries what "
            f"earning the level takes."
        ),
        'source_class': 'MaterialScaleDefinition',
        'isPage': True,
        'pageRoute': f'materials-level-{_level}',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [{
            'index': 0, 'rowSegments': 12, 'minRowHeight': 480,
            'maxRowHeight': 0, 'autoHeight': True, 'cssClass': '',
            'items': [{
                'id': f'materials-level-{_level}-item', 'index': 0,
                'type': 'component', 'rowSegmentsUsed': 12,
                'gridColumnStart': None,
                'title': (f"Level {_level} — {_detail['name']} "
                          f"({_detail['lengthRange']})"),
                'visible': True, 'collapsed': False, 'cssClass': '',
                'componentProps': {
                    'componentName': 'material-level-page',
                    'inputs': {'level': _level},
                },
                'item': None, 'nestedRows': [],
            }],
        }]}),
    })
