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

SEED_MSCI_PAGE_DISPLAYS = [
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
