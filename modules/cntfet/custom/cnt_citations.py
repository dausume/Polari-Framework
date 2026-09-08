"""
@module cntfet.custom.cnt_citations

The citation-linkage query (Dustin 2026-08-21: "proper citation
actions for linkages"): every source the module cites, with the
REVERSE map — which constants, anchor rows, and per-device
parameter rows link to it. Citation is data you can traverse, not
prose buried in docstrings.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/citations)
  - cntfet.cntfet_selftest
"""

from cntfet.custom.cnt_constants import LIT, MODEL_LABEL
from cntfet.cnt_reference_papers_seed import PAPERS

# The tag -> full-citation registry for the paper tags used across
# LIT sources and the model doc ([VS1], [FC10], ...).
TAG_CITATIONS = {
    '[VS1]': {'citation': 'Lee, Pop, Franklin, Haensch, Wong, '
              '"A Compact Virtual-Source Model for CNFETs in the '
              'Sub-10-nm Regime — Part I: Intrinsic Elements", '
              'IEEE TED 62(9):3061-3069 (2015)',
              'doi': '10.1109/TED.2015.2457453',
              'free_copy': 'arXiv:1503.04397'},
    '[VS2]': {'citation': 'ibid. Part II: Extrinsic Elements, '
              'IEEE TED 62(9):3070-3078 (2015)',
              'doi': '10.1109/TED.2015.2457424',
              'free_copy': 'arXiv:1503.04398'},
    '[KHA09]': {'citation': 'Khakifirooz, Nayfeh, Antoniadis, '
                'IEEE TED 56(8):1674-1680 (2009)',
                'doi': '10.1109/TED.2009.2024022'},
    '[FC10]': {'citation': 'Franklin & Chen, "Length scaling of '
               'carbon nanotube transistors", Nat. Nanotech. '
               '5:858-862 (2010)',
               'doi': '10.1038/nnano.2010.220',
               'free_copy': 'author PDF (franklin.pratt.duke.edu)'},
    '[RAH03]': {'citation': 'Rahman, Guo, Datta, Lundstrom, '
                '"Theory of Ballistic Nanotransistors", IEEE TED '
                '50(9):1853-1864 (2003)',
                'doi': '10.1109/TED.2003.815366',
                'free_copy': 'nanohub.org/resources/122'},
    '[LUN97]': {'citation': 'Lundstrom, IEEE EDL 18(7):361-363 '
                '(1997)', 'doi': '10.1109/55.596937'},
    '[GUO04]': {'citation': 'Guo et al., multiscale CNFET '
                'modeling', 'doi': '',
                'free_copy': 'arXiv:cond-mat/0312551'},
    '[JAV04]': {'citation': 'Javey et al., PRL 92:106804 (2004)',
                'doi': '10.1103/PhysRevLett.92.106804',
                'free_copy': 'arXiv:cond-mat/0309242'},
    '[PARK04]': {'citation': 'Park et al., Nano Lett. 4:517 '
                 '(2004)', 'doi': '10.1021/nl035258c',
                 'free_copy': 'arXiv:cond-mat/0309641'},
    '[WIL98]': {'citation': 'Wildoer et al., Nature 391:59-62 '
                '(1998)', 'doi': '10.1038/34139'},
    '[ZF92]': {'citation': 'Zone-folding 1992 trio: Hamada, '
               'Sawada, Oshiyama, PRL 68:1579 (1992) ((n-m) mod 3 '
               'rule) + Saito, Fujita, Dresselhaus, Dresselhaus, '
               'APL 60:2204 (1992)',
               'doi': '10.1103/PhysRevLett.68.1579',
               'doi_2': '10.1063/1.107080'},
    '[FIO05]': {'citation': PAPERS['FIO05']['citation'],
                'doi': PAPERS['FIO05']['doi'],
                'note': PAPERS['FIO05']['license_bucket']},
    '[HIL19]': {'citation': PAPERS['HIL19']['citation'],
                'doi': PAPERS['HIL19']['doi'],
                'note': PAPERS['HIL19']['license_bucket']},
}


def _tags_in(text):
    return [tag for tag in TAG_CITATIONS if tag in (text or '')]


def citations_report(manager):
    """source tag -> {citation, doi, linkedBy: {constants,
    anchors, parameters}}. Anchors/parameters come from the LIVE
    rows so the linkage reflects this instance, not the seeds."""
    linked = {tag: {'constants': [], 'anchors': [],
                    'parameters': []} for tag in TAG_CITATIONS}
    unlinked = {'anchors': [], 'parameters': []}
    for key, rec in LIT.items():
        for tag in _tags_in(rec.get('source', '')
                            + rec.get('notes', '')):
            linked[tag]['constants'].append(key)
    tables = getattr(manager, 'objectTables', None) or {}
    for row in (tables.get('CNTCalibrationAnchor') or {}).values():
        name = getattr(row, 'name', '')
        text = (getattr(row, 'source_reference', '')
                + getattr(row, 'figure', '')
                + getattr(row, 'doi', ''))
        tags = _tags_in(text)
        # DOI-based fallback: rows citing by DOI alone still link.
        for tag, cit in TAG_CITATIONS.items():
            if (cit.get('doi') and cit['doi'].lower()
                    in text.lower() and tag not in tags):
                tags.append(tag)
        if tags:
            for tag in tags:
                linked[tag]['anchors'].append(name)
        else:
            unlinked['anchors'].append(name)
    for row in (tables.get('CNTFETParameterRow') or {}).values():
        name = getattr(row, 'name', '')
        tags = _tags_in(getattr(row, 'source', ''))
        if tags:
            for tag in tags:
                linked[tag]['parameters'].append(name)
        elif getattr(row, 'role', '') in ('physical', 'derived',
                                          'compact-model'):
            # design choices/seeds legitimately cite no paper;
            # everything else should.
            if 'design choice' not in getattr(row, 'source', '') \
                    and 'seed' not in getattr(row, 'source', ''):
                unlinked['parameters'].append(name)
    out = []
    for tag, cit in TAG_CITATIONS.items():
        entry = dict(cit)
        entry['tag'] = tag
        entry['linkedBy'] = linked[tag]
        entry['linkCount'] = sum(len(v) for v in
                                 linked[tag].values())
        out.append(entry)
    out.sort(key=lambda e: -e['linkCount'])
    return {'ok': True, 'citations': out,
            'unlinked': unlinked,
            'modelLabel': MODEL_LABEL,
            'papersRegistry': PAPERS,
            'note': 'anchors/parameters reflect LIVE rows; '
                    'unlinked lists are the honesty surface — '
                    'they should stay empty or name design '
                    'choices only'}
