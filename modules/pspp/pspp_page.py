"""
@module pspp.pspp_page

The PSPP DisplayDefinition PAGE (msci-pages pattern: isPage +
pageRoute + hosted registered components). One published page,
module_id 'pspp', so it surfaces in the sidebar automatically; the
hosted components read live rows/endpoints themselves — the seed
carries only wiring, no data (a scientist rearranges the page in the
display editor without code).
"""

import json

SEED_PSPP_PAGE_DISPLAYS = [
    {
        'name': 'pspp',
        'description': (
            'PSPP reactive-material engine: book-proofing charts '
            'generated from digitized dataset rows, the reaction '
            'network as cited data, recipe grading against patent '
            'windows, and measured-curve cure progress.'
        ),
        'source_class': 'DigitizedDataset',
        'module_id': 'pspp',
        'isPage': True,
        'pageRoute': 'pspp',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [
            {'columns': [{'component': 'pspp-home', 'span': 12}]},
        ]}),
    },
]
