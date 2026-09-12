"""
@module climate.climate_citations_seed

NON-GOVERNMENT SOURCES, AS ROWS (Dustin 2026-08-03: "we should be
capable of citing non government sources as well... a combination
of academic journal sources and a journalistic source from someone
with a doctor credential").

Until this file existed the app could only cite a `GovSource`, and
that forced two mistakes:

1. **The cognitive thresholds had NO source link at all.** Satish
   2012 is the study the 1000 ppm decrement claim rests on, and
   because a journal is not a government agency, `source_ref` was
   left empty and the citation survived only as prose inside
   `citation_text`. A page cannot follow prose.
2. **Two sources were mis-filed as government and neither is.**
   ASHRAE is a professional society and the Global Carbon Project
   is an international research consortium. Both were seeded as
   `GovSource` rows carrying an apologetic note saying they were
   not government agencies - which is a comment doing a schema's
   job. They move here.

WHAT THIS FILE REFUSES TO DO IS AS IMPORTANT AS WHAT IT DOES. A
credentialed author writing for a magazine is a legitimate source
AND is not a peer-reviewed study, and the registry keeps those two
facts apart rather than averaging them into "expert says". The
credential, the outlet, whether an editor reviewed it, whether it
is opinion, and WHICH PRIMARY STUDIES it reports on are five
separate fields, so a reader can follow a claim to the evidence
instead of stopping at the person who repeated it.

@consumers climate.co2_thresholds_seed, climate.climate_views_seed,
climate.climate_api, polariServer
"""

import json

from moduleService.seed_upsert import upsert_seed_pairs

PROV = 'co2-C'


def _academic(name, short, title, authors, journal, year, pages,
              doi, design, n, replication, description,
              replication_refs=(), pubmed='', funding='',
              notes=''):
    return {
        'name': name, 'short_name': short, 'full_name': title,
        'official_website': doi or '', 'data_portal_url': '',
        'requires_api_key': False, 'api_key_env': '',
        'api_endpoint_names_json': '[]',
        'authors': authors, 'journal': journal, 'year': year,
        'volume_pages': pages, 'doi': doi, 'pubmed_id': pubmed,
        'peer_reviewed': True, 'study_design': design,
        'sample_size': n, 'replication_status': replication,
        'replication_refs_json': json.dumps(list(replication_refs)),
        'funding_disclosure': funding,
        'conflicts_declared': '',
        'description': description, 'notes': notes,
    }


#: The studies the CO2/health thresholds actually rest on. Every
#: one of these was already quoted in `citation_text` on a
#: threshold row; giving each a ROW is what turns a quotation into
#: a link the page can follow.
SEED_CLIMATE_ACADEMIC_SOURCES = [
    _academic(
        'satish-2012-co2-decision-making', 'Satish 2012',
        'Is CO2 an Indoor Pollutant? Direct Effects of '
        'Low-to-Moderate CO2 Concentrations on Human '
        'Decision-Making Performance',
        'Satish U, Mendell MJ, Shekhar K, Hotchi T, Sullivan D, '
        'Streufert S, Fisk WJ',
        'Environmental Health Perspectives', 2012,
        '120(12):1671-1677',
        'https://doi.org/10.1289/ehp.1104789',
        'controlled chamber exposure, within-subject, '
        'double-blinded', 22,
        'failed-to-replicate',
        'THE source behind the 1000 and 2500 ppm cognitive '
        'thresholds. Six of nine decision-making scales fell '
        '11-23 percent at 1000 ppm against a 600 ppm baseline; '
        'seven fell 44-94 percent at 2500 ppm, with five reaching '
        'levels the authors call marginal or dysfunctional.',
        replication_refs=('rodeheffer-2018-submariners',
                          'scully-2019-astronaut-like',
                          'du-2020-critical-review'),
        pubmed='23008272',
        funding='Collaborative Activities for Research and '
                'Technology Innovation (CARTI), supported by the '
                'U.S. Environmental Protection Agency',
        notes='CORRECTED 2026-08-03 after reading the paper '
              'itself: n=22, NOT the 24 this row first carried. '
              'The 24 came from a secondary summary, which is '
              'exactly the substitution this app exists to refuse '
              '- and it survived here for a day. Participants and '
              'the test administrator were BLINDED to CO2 level, '
              'and exposure order was balanced across six groups, '
              'so the design is stronger than the replication '
              'record suggests. THE AUTHORS THEMSELVES wrote that '
              'the 2500 ppm effects "almost defy credibility" and '
              'that replication was needed, and that the mechanism '
              'was unexplained. They said it first; the three '
              'replication rows are what happened when others '
              'looked.'),
    _academic(
        'rodeheffer-2018-submariners', 'Rodeheffer 2018',
        'Acute Exposure to Low-to-Moderate Carbon Dioxide Levels '
        'and Submariner Decision Making',
        'Rodeheffer CD, Chabal S, Clarke JM, Fothergill DM',
        'Aerospace Medicine and Human Performance', 2018, '',
        '', 'controlled chamber exposure, submariner crew', 36,
        'not-applicable',
        'FAILED TO REPLICATE the Satish/Allen decision-making '
        'decrements at 2500 ppm: submariner performance did not '
        'change with CO2 condition.',
        notes='A replication attempt in a population professionally '
              'habituated to elevated CO2 - which is a strength for '
              'external validity in submarines and a caveat for '
              'generalising to classrooms.'),
    _academic(
        'scully-2019-astronaut-like', 'Scully 2019',
        'Effects of acute exposures to carbon dioxide on decision '
        'making and cognition in astronaut-like subjects',
        'Scully RR, Basner M, Nasrini J, Lam C, Hermosillo E, '
        'Gur RC, Moore T, Alexander DJ, Satish U, Ryder VE',
        'npj Microgravity', 2019, '5:17',
        'https://doi.org/10.1038/s41526-019-0071-6',
        'controlled chamber exposure', 22,
        'not-applicable',
        'Did NOT reproduce the dose-dependent monotonic '
        'relationship. Performance at 1200 ppm was below the 600 '
        'ppm baseline on most measures, but at HIGHER '
        'concentrations it matched or exceeded baseline - a '
        'non-monotonic result that no simple threshold explains.',
        notes='The non-monotonicity matters: a threshold model '
              'predicts worse-with-more, and this did not show it.'),
    _academic(
        'du-2020-critical-review', 'Du 2020',
        'Indoor CO2 concentrations and cognitive function: A '
        'critical review',
        'Du B, Tandoc MC, Mack ML, Siegel JA', 'Indoor Air', 2020,
        '30(6):1067-1082', 'https://doi.org/10.1111/ina.12706',
        'systematic critical review', 37, 'not-applicable',
        'Reviewed 37 experimental studies and concluded that '
        'rigorously designed studies tend to show no or only '
        'marginally significant small effects, except on the SMS '
        'battery - and not consistently even there.',
        pubmed='32557862',
        notes='The highest-level evidence in this set, and the '
              'reason the cognitive rows are graded '
              'contested-controlled-study rather than '
              'controlled-human-study.'),
    _academic(
        'bereiter-2015-co2-composite', 'Bereiter 2015',
        'Revision of the EPICA Dome C CO2 record from 800 to 600 '
        'kyr before present',
        'Bereiter B, Eggleston S, Schmitt J, Nehrbass-Ahles C, '
        'Stocker TF, Fischer H, Kipfstuhl S, Chappellaz J',
        'Geophysical Research Letters', 2015, '42(2):542-549',
        'https://doi.org/10.1002/2014GL061957',
        'ice-core reconstruction (multi-core composite)', 1901,
        'replicated',
        'The 800,000-year Antarctic CO2 composite - the source for '
        'every statement on this page about what CO2 humans have '
        'actually lived in.',
        notes='NOAA/WDS Paleoclimatology study 17975. 1901 points; '
              'gas ages smoothed by firn diffusion, sampled '
              'centuries to millennia apart.'),
    _academic(
        'macfarling-meure-2006-law-dome', 'MacFarling Meure 2006',
        'Law Dome CO2, CH4 and N2O ice core records extended to '
        '2000 years BP',
        'MacFarling Meure C, Etheridge D, Trudinger C, Steele P, '
        'Langenfelds R, van Ommen T, Smith A, Elkins J',
        'Geophysical Research Letters', 2006, '33:L14810',
        'https://doi.org/10.1029/2006GL026152',
        'ice-core and firn-air reconstruction', 0, 'replicated',
        'The high-resolution record across the industrial '
        'transition. Its OVERLAP with the instrumental era is what '
        'makes the spliced curve a measurement rather than an '
        'assumption.',
        notes='Registered here even though its parser is '
              'deliberately unwritten: the citation is real and '
              'reachable whether or not this app reads the file.'),
    _academic(
        'friedlingstein-2025-carbon-budget', 'GCB 2025',
        'Global Carbon Budget 2025',
        'Friedlingstein P et al.',
        'Earth System Science Data', 2025, '',
        'https://doi.org/10.18160/GCP-2025',
        'annual budget synthesis (inventories and models)', 0,
        'not-applicable',
        'The source for every sink, source and differential number '
        'on this page.',
        notes='A SYNTHESIS, not a direct measurement, and it does '
              'not close exactly - the budget prints its own '
              'imbalance term and so does this app.'),
    _academic(
        'azuma-2018-low-level-co2-review', 'Azuma 2018',
        'Effects of low-level inhalation exposure to carbon '
        'dioxide in indoor environments: A short review on human '
        'health and psychomotor performance',
        'Azuma K, Kagi N, Yanagi U, Osawa H',
        'Environment International', 2018, '121(Pt 1):51-56',
        'https://doi.org/10.1016/j.envint.2018.08.059',
        'narrative review of experimental and epidemiological '
        'studies', 0, 'not-applicable',
        'The source behind the LOW thresholds: reports linear '
        'physiological changes in circulatory, cardiovascular and '
        'autonomic measures across 500-5000 ppm, cognitive effects '
        'from about 1000 ppm, and an epidemiological association '
        'with building-related symptoms from about 700 ppm.',
        notes='A REVIEW, not a trial - it summarises other '
              'people\'s experiments, so the thresholds drawn from '
              'it are graded observational rather than '
              'controlled-human-study. Recorded from its own '
              'abstract and reference metadata; the full text has '
              'NOT been read by this instance.'),
    _academic(
        'lowther-2021-co2-indicator-or-pollutant', 'Lowther 2021',
        'Low level carbon dioxide indoors - a pollution indicator '
        'or a pollutant? A health-based perspective',
        'Lowther SD, Dimitroulopoulou S, Foxall K, Shrubsole C, '
        'Cheek E, Gadeberg B, Sepai O',
        'Environments', 2021, '8(11):125',
        'https://doi.org/10.3390/environments8110125',
        'health-based review', 0, 'not-applicable',
        'Asks the question this whole page turns on: is indoor CO2 '
        'a POLLUTANT in its own right or an INDICATOR of poor '
        'ventilation? Authors are UK Health Security Agency.',
        notes='The framing matters more than any number in it: '
              'ASHRAE treats CO2 as an indicator, and whether that '
              'is right is a live scientific question rather than '
              'a settled one. Recorded from abstract and '
              'publisher metadata; full text NOT read here.'),
    _academic(
        'stumm-2023-downregulating-human-species', 'Stumm 2023',
        'Carbon dioxide\'s direct impact on down-regulating the '
        'human species',
        'Stumm RE', 'Science of the Total Environment', 2023,
        '905:167198',
        'https://doi.org/10.1016/j.scitotenv.2023.167198',
        'modelling and discussion paper (single author)', 0,
        'not-attempted',
        'Proposes a model in which hypercapnic blood pH begins to '
        'appear as atmospheric CO2 approaches about 3000 ppm, and '
        'argues a causal link to calcium balance, vascular '
        'calcification and bone demineralisation.',
        pubmed='37734619',
        notes='TREAT WITH CARE, and the reason is structural, not '
              'a matter of taste: this is a single-author MODELLING '
              'and discussion paper, not a measurement, and its '
              'central claim has no replication attempt recorded. '
              'Its own onset figure (~3000 ppm) sits ABOVE typical '
              'indoor levels and far above outdoor ones, which is '
              'worth stating whenever it is cited in support of a '
              'lower threshold. Recorded from abstract metadata; '
              'full text NOT read here.'),
]


#: Standards bodies and research consortia: real, citable, and NOT
#: government. Filed as nonprofits because that is what they are.
SEED_CLIMATE_NONPROFIT_SOURCES = [
    {'name': 'ashrae-society', 'short_name': 'ASHRAE',
     'full_name': 'American Society of Heating, Refrigerating and '
                  'Air-Conditioning Engineers',
     'official_website': 'https://www.ashrae.org',
     'data_portal_url': '', 'requires_api_key': False,
     'api_key_env': '', 'api_endpoint_names_json': '[]',
     'ein': '', 'irs_subsection': '', 'state_registered': '',
     'irs_lookup_url': 'https://apps.irs.gov/app/eos/',
     'funding_transparency_url': '',
     'description': 'The professional society that publishes '
                    'Standard 62.1, the ventilation criterion '
                    'behind the indoor CO2 numbers everyone '
                    'quotes.',
     'notes': 'MOVED HERE from the government registry, where it '
              'was originally mis-filed with a note apologising '
              'that it was not a government agency. A comment '
              'cannot do a schema\'s job. ASHRAE is also explicit '
              'that its IAQ standards do NOT use indoor CO2 to '
              'determine acceptable air quality, which is why its '
              'thresholds are graded standard-or-guideline and '
              'drawn in an indicator colour rather than a severity '
              'one.'},
    {'name': 'global-carbon-project-org', 'short_name': 'GCP',
     'full_name': 'Global Carbon Project',
     'official_website': 'https://www.globalcarbonproject.org',
     'data_portal_url': 'https://globalcarbonbudget.org/carbonbudget/',
     'requires_api_key': False, 'api_key_env': '',
     'api_endpoint_names_json': '["gcb-global-carbon-budget"]',
     'ein': '', 'irs_subsection': '', 'state_registered': '',
     'irs_lookup_url': '', 'funding_transparency_url': '',
     'description': 'The international research consortium behind '
                    'the annual Global Carbon Budget.',
     'notes': 'MOVED HERE from the government registry for the '
              'same reason as ASHRAE. Not a US entity and not a '
              'government body; the IRS lookup fields do not apply '
              'and are left empty rather than filled with '
              'something plausible.'},
]


#: Press and trade articles. Seeded EMPTY on purpose - see the
#: module docstring. A journalistic row is only worth having when
#: someone has actually read the piece and can fill in the outlet,
#: the author's stated credentials and the primary studies it
#: reports on. Inventing a plausible-looking article row would be
#: the exact failure this registry exists to prevent, and an
#: article nobody has read cannot have its primary sources named.
SEED_CLIMATE_JOURNALISTIC_SOURCES = [
    {
        'name': 'airgradient-2025-hidden-health-risks',
        'short_name': 'AirGradient 2025',
        'full_name': 'The Hidden Health Risks of CO2: Rethinking '
                     'Acceptable Exposure Limits',
        'official_website': 'https://www.airgradient.com',
        'data_portal_url': '', 'requires_api_key': False,
        'api_key_env': '', 'api_endpoint_names_json': '[]',
        'outlet': 'AirGradient (company blog)',
        'author_name': 'Dr. Safiya Cummings',
        #: EXACTLY what the byline states. The article says "Dr."
        #: and does not say which doctorate, so neither does this
        #: row: writing "MD" here would be inventing a credential
        #: to make a citation look stronger.
        'author_credentials': 'Dr. (degree type not stated in the '
                              'byline)',
        'author_affiliation': '(none stated)',
        'published_date': '2025-04-21',
        'article_url':
            'https://www.airgradient.com/blog/'
            'hidden-health-risks-of-co2/',
        'editorially_reviewed': False,
        'is_opinion': True,
        'primary_sources_json': json.dumps([
            'azuma-2018-low-level-co2-review',
            'lowther-2021-co2-indicator-or-pollutant',
            'stumm-2023-downregulating-human-species',
            'satish-2012-co2-decision-making']),
        'unsourced_claims_noted': True,
        'commercial_interest':
            'AirGradient Co. Ltd. SELLS CO2 and air-quality '
            'monitors. An argument that CO2 is a hidden health '
            'risk at the levels its products measure is an '
            'argument that increases demand for those products. '
            'That does not make the article wrong - its four '
            'citations are real papers and were checked - but a '
            'citation that omits the interest is hiding something '
            'a reader would want to weigh.',
        'publisher_sells': 'indoor, outdoor and portable CO2 / '
                           'air-quality monitors (open-source '
                           'hardware), Chiang Mai, Thailand',
        'description': 'An advocacy piece arguing that accepted '
                       'CO2 exposure limits are too high, with a '
                       'ladder of thresholds from 500 ppm to '
                       '80000 ppm. It is the reason several '
                       'low-level thresholds exist on this page '
                       'at all.',
        'notes': 'ALL FOUR of its citations were verified to be '
                 'real, correctly attributed papers (Azuma 2018, '
                 'Lowther 2021, Stumm 2023, Satish 2012) - better '
                 'sourcing than most writing in this genre. '
                 'unsourced_claims_noted is True because the '
                 'article does not attribute each individual '
                 'threshold in its ladder to a specific one of '
                 'those four, so the mapping from a given ppm '
                 'figure to the study behind it cannot be '
                 'reconstructed from the piece. That is why every '
                 'threshold sourced to this row is graded '
                 'secondary-reporting and points at the article '
                 'rather than at a study it may or may not rest '
                 'on.',
    },
]


def seed_climate_citations(manager):
    from dmvdata.legal_sources_basis import (
        AcademicSource, JournalisticSource, NonProfitSource,
    )
    return upsert_seed_pairs(manager, [
        ('AcademicSource', AcademicSource,
         SEED_CLIMATE_ACADEMIC_SOURCES),
        ('NonProfitSource', NonProfitSource,
         SEED_CLIMATE_NONPROFIT_SOURCES),
        ('JournalisticSource', JournalisticSource,
         SEED_CLIMATE_JOURNALISTIC_SOURCES),
    ], tag='ClimateCitationSeed')


def resolve_citation(manager, source_ref):
    """One source_ref -> its row, its KIND and a formatted line,
    across every registry (government, nonprofit, academic,
    journalistic, ...).

    This is the function that makes `source_ref` mean "a source"
    rather than "a government source".
    """
    if not source_ref:
        return {'ok': False,
                'refusal': ('this row names no source; its '
                            'authority is whatever its '
                            'citation_text says and nothing can '
                            'follow it')}
    from dmvdata.gov_sources_basis import find_source
    row, kind = find_source(manager, source_ref)
    if row is None:
        return {'ok': False, 'sourceRef': source_ref,
                'refusal': (f'no source row named {source_ref!r} in '
                            f'any registry - seed it, or the '
                            f'citation is unreachable')}
    out = {'ok': True, 'sourceRef': source_ref, 'kind': kind,
           'displayName': (getattr(row, 'short_name', '')
                           or getattr(row, 'acronym', '')
                           or source_ref),
           'fullName': getattr(row, 'full_name', ''),
           'url': (getattr(row, 'doi', '')
                   or getattr(row, 'article_url', '')
                   or getattr(row, 'official_website', '')),
           'notes': getattr(row, 'notes', '')}
    if kind == 'academic':
        out.update(
            authors=getattr(row, 'authors', ''),
            journal=getattr(row, 'journal', ''),
            year=getattr(row, 'year', 0),
            studyDesign=getattr(row, 'study_design', ''),
            sampleSize=getattr(row, 'sample_size', 0),
            peerReviewed=bool(getattr(row, 'peer_reviewed', True)),
            replicationStatus=getattr(row, 'replication_status',
                                      ''),
            replicationRefs=json.loads(
                getattr(row, 'replication_refs_json', '') or '[]'),
            citationLine=(
                f'{getattr(row, "authors", "")}. '
                f'{getattr(row, "full_name", "")}. '
                f'{getattr(row, "journal", "")} '
                f'{getattr(row, "year", "")}'
                f'{"; " + getattr(row, "volume_pages", "") if getattr(row, "volume_pages", "") else ""}.'
            ).strip())
    elif kind == 'journalistic':
        credentials = getattr(row, 'author_credentials', '')
        out.update(
            outlet=getattr(row, 'outlet', ''),
            author=getattr(row, 'author_name', ''),
            authorCredentials=credentials,
            editoriallyReviewed=bool(
                getattr(row, 'editorially_reviewed', False)),
            isOpinion=bool(getattr(row, 'is_opinion', False)),
            primarySources=json.loads(
                getattr(row, 'primary_sources_json', '') or '[]'),
            unsourcedClaimsNoted=bool(
                getattr(row, 'unsourced_claims_noted', False)),
            credentialCaveat=(
                'the author\'s credentials are real AND this is '
                'not peer-reviewed: expertise and review are '
                'different guarantees, and a citation has to carry '
                'both or a reader cannot weigh it'
                if credentials else
                'no author credential is recorded for this piece'),
            citationLine=(
                f'{getattr(row, "author_name", "")}'
                f'{" (" + credentials + ")" if credentials else ""}. '
                f'{getattr(row, "full_name", "")}. '
                f'{getattr(row, "outlet", "")}, '
                f'{getattr(row, "published_date", "")}.').strip())
    else:
        out['citationLine'] = (
            f'{getattr(row, "full_name", "") or source_ref}'
            f'{" (" + out["displayName"] + ")" if out["displayName"] else ""}.')
    return out


def threshold_citations(manager):
    """Every CO2 health threshold with its source RESOLVED - the
    section a reader checks before believing any line on the page.

    Grouped by source kind so the shape of the evidence is visible
    at a glance: which lines come from a peer-reviewed study, which
    from a standards body that says it is not making a health
    claim, and which from a credentialed writer reporting on
    someone else's work.
    """
    from composition.custom.data_refs import rows
    out, unresolved = [], []
    for row in rows(manager, 'CO2HealthThreshold'):
        ref = getattr(row, 'source_ref', '')
        cite = resolve_citation(manager, ref)
        entry = {
            'threshold': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'ppm': getattr(row, 'ppm', 0.0),
            'isDifferential': bool(
                getattr(row, 'is_differential', False)),
            'evidenceGrade': getattr(row, 'evidence_grade', ''),
            'sourceRef': ref,
            'citationText': getattr(row, 'citation_text', ''),
            'contestedBy': getattr(row, 'contested_by', ''),
            'resolved': cite.get('ok', False),
            'sourceKind': cite.get('kind', ''),
            'citationLine': cite.get('citationLine', ''),
            'url': cite.get('url', ''),
        }
        for key in ('studyDesign', 'sampleSize', 'peerReviewed',
                    'replicationStatus', 'replicationRefs',
                    'authorCredentials', 'isOpinion',
                    'primarySources', 'credentialCaveat'):
            if key in cite:
                entry[key] = cite[key]
        if not cite.get('ok'):
            entry['refusal'] = cite.get('refusal', '')
            unresolved.append(entry['threshold'])
        out.append(entry)
    out.sort(key=lambda e: e['ppm'])
    by_kind = {}
    for entry in out:
        by_kind.setdefault(entry['sourceKind'] or 'unresolved',
                           []).append(entry['threshold'])
    return {
        'ok': True, 'thresholds': out, 'count': len(out),
        'bySourceKind': by_kind, 'unresolved': unresolved,
        'note': ('a source is not the same thing as a government '
                 'source. These lines come from peer-reviewed '
                 'studies, a professional standards body and '
                 'federal occupational limits, and each is '
                 'labelled with which - because a ventilation '
                 'standard that explicitly disclaims being a '
                 'health threshold should never sit on a page '
                 'looking like a trial result.'),
        'journalismRule': (
            'a credentialed author writing outside peer review is '
            'citable here, graded secondary-reporting, and carries '
            'the primary studies it reports on so a claim can be '
            'followed to the evidence rather than stopping at the '
            'person who repeated it.'),
    }
