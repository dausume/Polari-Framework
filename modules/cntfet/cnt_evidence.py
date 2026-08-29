"""
@module cntfet.cnt_evidence

EVIDENCE + PROOF-OF-FREEDOM tracking for every FET / cell / route the
cntfet + sifet modules model (Dustin 2026-08-29: "tie in citations
and patents or public domain proof into all of these FETs and cells
… first class information … clickable … establish proof of which
ones are fully free to use").

Evidence is FIRST-CLASS ROWS (EvidenceItem, cnt_states row style):
one row per patent, publication, textbook, standard, licence or
prior-art item, each saying what it PROVES (expired / active /
prior-art-before / public-domain-textbook / open-licence /
proprietary-licence / model-source), whether it was VERIFIED (and
via what), and which records / devices / cells it supports. The
TechnologyIPRecord.evidence_json column (cnt_ip) is a JOIN onto
these names — the proof chain is a lookup, never a re-derivation.

The proof rules are DATA (PROOF_RULES, EXPIRY_RULES, SATISFIES):
    proven-free      every governing record green AND each cites
                     >=1 VERIFIED expired patent, or >=1 VERIFIED
                     dated public-domain / textbook / prior-art item
                     >= 20 years old, or (open-licence records) a
                     VERIFIED open licence; no active-claim item
    free-unverified  green records but evidence unverified or
                     < 20 y old; or an amber record with NO known
                     active claim (unsearched, not encumbered)
    encumbered       any amber/red record with an active-claim item
    unknown          a governing record has no evidence at all

JURISDICTION (Dustin 2026-08-29): UNITED STATES. Every item is US
unless a foreign patent is deliberately cited; 'proven-free' means
proven free in the US; non-US families are out of scope and are
NOT listed as gaps — every payload carries SCOPE_LINE.

DISCLAIMER on every payload: engineering FTO evidence — NOT LEGAL
ADVICE — verify with counsel before commercial use.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/evidence, /evidence/{name},
    /device/{name}/proof, /cell/{cell}/proof, /proof)
  - cntfet.cnt_device_viz (CURVE_BUILDERS 'proof-status';
    SEED_CNT_EVIDENCE_GRAPHS)
  - cntfet.selftest_evidence
  - polariServer (EvidenceItem registration + SEED_EVIDENCE)
"""

import datetime as _dt
import json

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet import cnt_ip as ip
from cntfet.cnt_citations import TAG_CITATIONS
from cntfet.cnt_power import POWER_CITATIONS
from cntfet.cnt_reference_papers import PAPERS
from cntfet.cnt_taxonomy import TAXONOMY_CITATIONS

try:
    from sifet.si_model import SI_CITATIONS
except ImportError:  # sifet optional at import time
    SI_CITATIONS = {}
try:
    from sifet.si_refinement import CITATIONS as SI_REFINEMENT_CITATIONS
except ImportError:
    SI_REFINEMENT_CITATIONS = {}

REVIEWED_AT = '2026-08-29'
JURISDICTION = 'US'
SCOPE_LINE = 'scope: United States; foreign families not assessed'
DISCLAIMER = ('ENGINEERING FTO EVIDENCE — NOT LEGAL ADVICE — verify '
              'with counsel before commercial use. Proof status is a '
              'rule applied to recorded evidence (US only; 20-year '
              'expiry estimate, no PTA / terminal-disclaimer / claim '
              'construction); "verified" means the number, title, '
              'dates and status were fetched from the named source '
              'on verified_at, nothing more.')

#: Age an item must have to count as "old enough" prior art / textbook
#: (mirrors the US 20-year utility-patent term).
PRIOR_ART_YEARS = 20

KINDS = ('patent', 'publication', 'textbook', 'standard', 'licence',
         'prior-art')
PROVES = ('expired', 'active', 'prior-art-before',
          'public-domain-textbook', 'open-licence',
          'proprietary-licence', 'model-source')
STATUSES = ('proven-free', 'free-unverified', 'encumbered', 'unknown')
STATUS_INDEX = {s: i for i, s in enumerate(STATUSES)}

PROOF_RULES = {
    'proven-free': 'every governing record is green AND each green '
                   'record cites >=1 VERIFIED expired patent or >=1 '
                   'VERIFIED dated public-domain/textbook/prior-art '
                   f'item >= {PRIOR_ART_YEARS} years old (or, for an '
                   'open-licence record, a VERIFIED open licence), AND '
                   'no active-claim item is attached — proven free in '
                   'the United States',
    'free-unverified': 'green records but the evidence is unverified '
                       f'or younger than {PRIOR_ART_YEARS} y; or a '
                       'governing record is amber (unsearched) with NO '
                       'active-claim item attached',
    'encumbered': 'any governing record amber/red with an active-claim '
                  'item',
    'unknown': 'a governing record has no evidence at all',
    'precedence': ['encumbered', 'unknown', 'free-unverified',
                   'proven-free'],
    'jurisdiction': JURISDICTION,
    'scope': SCOPE_LINE,
}

#: US utility-patent expiry as data (Dustin 2026-08-29).
EXPIRY_RULES = {
    'jurisdiction': 'US',
    'cutover': '1995-06-08',
    'on_or_after_cutover': '20 years from the earliest effective '
                           '(non-provisional / priority) filing date; '
                           'PTA ignored unless the item records it',
    'before_cutover': 'the LONGER of 17 years from grant and 20 years '
                      'from filing',
    'fee_lapse': "maintenance-fee lapse ('Expired - Fee Related' / "
                 "'ceased') counts as expired for US only if the "
                 "source says so — proves 'expired', proves_detail "
                 "'lapsed for non-payment (US)'",
    'foreign': 'non-US families are OUT OF SCOPE of the proof status',
}

#: Which (proves, verified, age) combinations SATISFY a green record.
SATISFIES = {
    'expired': 'verified',
    'prior-art-before': f'verified AND dated >= {PRIOR_ART_YEARS} y',
    'public-domain-textbook': f'verified AND dated >= {PRIOR_ART_YEARS} y',
    'model-source': f'verified AND dated >= {PRIOR_ART_YEARS} y',
    'open-licence': 'verified (a licence grants freedom by its text; '
                    'age irrelevant)',
    'active': 'NEVER — attaches an active claim',
    'proprietary-licence': 'NEVER — but only blocks if the record '
                           'depends on it (ours never do; recorded so '
                           'the not-read discipline is visible)',
}


# ── the row ────────────────────────────────────────────────────────

class EvidenceItem(treeObject):
    """One piece of evidence (patent / publication / textbook /
    standard / licence / prior-art) with what it PROVES, whether it
    was verified, and which subjects it supports."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        kind: str = 'publication',
        title: str = '',
        parties: str = '',
        ref: str = '',            # patent number / DOI / ISBN / SPDX
        date: str = '',           # ISO (filing / publication / release)
        url: str = '',
        proves: str = 'prior-art-before',
        proves_detail: str = '',
        expiry: str = '',
        jurisdiction: str = JURISDICTION,
        verified: bool = False,
        verified_via: str = '',
        verified_at: str = '',
        licence_bucket: str = '',
        subjects_json: str = '[]',
        citation_key: str = '',   # '[VS1]' etc. — reverse lookup
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.kind = kind
        self.title = title
        self.parties = parties
        self.ref = ref
        self.date = date
        self.url = url
        self.proves = proves
        self.proves_detail = proves_detail
        self.expiry = expiry
        self.jurisdiction = jurisdiction
        self.verified = verified
        self.verified_via = verified_via
        self.verified_at = verified_at
        self.licence_bucket = licence_bucket
        self.subjects_json = subjects_json
        self.citation_key = citation_key
        self.notes = notes
        self.is_prior = is_prior


# ── expiry computation (data-driven) ───────────────────────────────

def _iso(d):
    return d.isoformat()


def _parse(s):
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def _add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + n, day=28)


def expiry_estimate(filed, granted='', priority=''):
    """US utility-patent nominal expiry per EXPIRY_RULES; '' if the
    dates are missing. `priority` = earliest effective filing date."""
    eff = _parse(priority) or _parse(filed)
    f = _parse(filed)
    g = _parse(granted)
    if eff is None:
        return ''
    if eff >= _parse(EXPIRY_RULES['cutover']):
        return _iso(_add_years(eff, 20))
    cands = [_add_years(f or eff, 20)]
    if g is not None:
        cands.append(_add_years(g, 17))
    return _iso(max(cands))


def age_years(date, today=None):
    d = _parse(date)
    if d is None:
        return None
    today = today or _dt.date.today()
    return (today - d).days / 365.25


# ── seed helpers ───────────────────────────────────────────────────

def _item(name, kind, title, parties, ref, date, proves, proves_detail,
          subjects, url='', expiry='', verified=False, verified_via='',
          licence_bucket='', citation_key='', notes='',
          jurisdiction=JURISDICTION):
    assert kind in KINDS, kind
    assert proves in PROVES, proves
    return {
        'name': name, 'kind': kind, 'title': title, 'parties': parties,
        'ref': ref, 'date': date, 'url': url, 'proves': proves,
        'proves_detail': proves_detail, 'expiry': expiry,
        'jurisdiction': jurisdiction, 'verified': bool(verified),
        'verified_via': verified_via,
        'verified_at': REVIEWED_AT if verified else '',
        'licence_bucket': licence_bucket,
        'subjects_json': json.dumps(list(subjects)),
        'citation_key': citation_key, 'notes': notes, 'is_prior': True,
    }


def _gp(number):
    return f'https://patents.google.com/patent/US{number}/en'


def _patent(number, title, assignee, filed, granted, status, subjects,
            priority='', verified=False, status_note='', notes='',
            expiry_seen='', lapsed=''):
    """status: expired | fee-lapsed | active | active-unverified.
    `lapsed` = the fee-lapse date when the source states it."""
    exp = expiry_seen or expiry_estimate(filed, granted, priority)
    if status == 'expired':
        proves, detail = 'expired', (
            f'filed {filed} → expired {exp} '
            f'({"20 y from filing" if (_parse(priority) or _parse(filed)) >= _parse(EXPIRY_RULES["cutover"]) else "pre-1995 rule: max(17 y from grant, 20 y from filing)"})'
            + (f'; {status_note}' if status_note else ''))
    elif status == 'fee-lapsed':
        # enforceable end = the lapse date; when the source shows no
        # lapse date the observation date (REVIEWED_AT) is used —
        # the nominal term is kept in the detail text
        nominal = exp
        exp = lapsed or REVIEWED_AT
        proves, detail = 'expired', (
            f'lapsed for non-payment (US)'
            + (f' on {lapsed}' if lapsed else
               f' — lapse date not shown by source, observed '
               f'{REVIEWED_AT}')
            + f'; nominal term to {nominal}'
            + (f'; {status_note}' if status_note else ''))
    else:
        proves, detail = 'active', (
            f'filed {filed} → active to {exp}'
            + (f'; {status_note}' if status_note else ''))
    return _item(f'pat-us-{number}', 'patent', title, assignee,
                 f'US {number}', filed, proves, detail, subjects,
                 url=_gp(number), expiry=exp, verified=verified,
                 verified_via=_gp(number) if verified else '',
                 notes=notes)


_XREF = 'https://api.crossref.org/works/'


def _pub(key, title, parties, doi, date, subjects, proves='model-source',
         detail='', verified=False, via='', bucket='', notes='',
         kind='publication', url=''):
    return _item(f'pub-{key}', kind, title, parties,
                 f'doi:{doi}' if doi else '', date, proves,
                 detail or f'published {date}; cited as [{key}]',
                 subjects,
                 url=url or (f'https://doi.org/{doi}' if doi else ''),
                 verified=verified,
                 verified_via=via or (f'{_XREF}{doi}' if verified else ''),
                 licence_bucket=bucket or (
                     'cite+link+values (publisher copyright; not CC)'
                     if doi else 'open-literature prior'),
                 citation_key=f'[{key}]', notes=notes)


def _book(name, title, parties, isbn, date, subjects, detail='',
          verified=False, citation_key='', notes=''):
    return _item(name, 'textbook', title, parties, f'ISBN {isbn}', date,
                 'public-domain-textbook',
                 detail or f'textbook, published {date} — the circuit/'
                           f'physics it teaches is public knowledge',
                 subjects, url=f'https://openlibrary.org/isbn/'
                               f'{isbn.replace("-", "")}',
                 verified=verified,
                 verified_via=('https://openlibrary.org/api/books?'
                               f'bibkeys=ISBN:{isbn.replace("-", "")}'
                               if verified else ''),
                 licence_bucket='cite only (copyrighted text; the '
                                'knowledge is free)',
                 citation_key=citation_key, notes=notes)


def _lic(spdx, title, parties, date, proves, detail, subjects, url,
         verified=False, via='', notes=''):
    return _item(f'lic-{spdx.lower()}', 'licence', title, parties, spdx,
                 date, proves, detail, subjects, url=url,
                 verified=verified, verified_via=via if verified else '',
                 licence_bucket=('GPLv3-compatible' if proves ==
                                 'open-licence' else 'NOT in tree'),
                 notes=notes)


def _std(name, title, parties, ref, date, subjects, url, detail='',
         verified=False, via='', citation_key='', notes=''):
    return _item(name, 'standard', title, parties, ref, date,
                 'open-licence', detail or 'open standard — using the '
                 'language/format creates no licence obligation',
                 subjects, url=url, verified=verified,
                 verified_via=via if verified else '',
                 licence_bucket='open standard', citation_key=citation_key,
                 notes=notes)


V_GP = True   # fetched from Google Patents 2026-08-29
V_XR = True   # fetched from Crossref 2026-08-29


# ── SEED_EVIDENCE ──────────────────────────────────────────────────

SEED_EVIDENCE = [
    # ---- patents: one per entry in cnt_ip key_patents_json ---------
    _patent('3102230', 'Electric field controlled semiconductor device',
            'Kahng / Bell Telephone Laboratories', '1960-05-31',
            '1963-08-27', 'expired', ['mosfet-generic'],
            verified=V_GP, expiry_seen='1980-08-27',
            status_note='Google Patents: Expired - Lifetime'),
    _patent('3356858', 'Low stand-by power complementary field effect '
            'circuitry', 'Wanlass / Fairchild Camera and Instrument',
            '1963-06-18', '1967-12-05', 'expired',
            ['cmos', 'standard-cells'], verified=V_GP,
            expiry_seen='1984-12-05',
            status_note='Google Patents: Expired - Lifetime; discloses '
                        'the complementary inverter every static cell '
                        'is built from'),
    _patent('3025589', 'Method of manufacturing semiconductor devices',
            'Hoerni / Fairchild Semiconductor', '1959-05-01',
            '1962-03-20', 'expired', ['planar-process'], verified=V_GP,
            expiry_seen='1979-03-20',
            status_note='Google Patents: Expired - Lifetime'),
    _patent('5374564', 'Process for the production of thin '
            'semiconductor material films (Smart Cut)', 'Bruel / CEA',
            '1992-09-15', '1994-12-20', 'fee-lapsed', ['soi'],
            verified=V_GP, expiry_seen='2012-09-15', lapsed='2012-09-15',
            status_note='Google Patents: Ceased; nominal expiry '
                        '2012-09-15 passed anyway'),
    _patent('6413802', 'FinFET transistor structures having a double '
            'gate channel extending vertically from a substrate and '
            'methods of manufacture', 'Hu, Bokor, King et al. / Regents '
            'of the University of California', '2000-10-23',
            '2002-07-02', 'expired', ['finfet'], verified=V_GP,
            status_note='Google Patents: Expired - Lifetime'),
    _patent('9966471', 'Stacked Gate-All-Around FinFET and method '
            'forming the same', 'TSMC', '2015-03-31', '2018-05-08',
            'active', ['gaa-nanosheet'], verified=V_GP,
            expiry_seen='2035-03-31',
            status_note='Google Patents: Active; priority 2014-06-27 '
                        '(provisional — term runs from the 2015 filing)'),
    _patent('11121044', 'Vertically stacked nanosheet CMOS transistor',
            'IBM', '2019-11-22', '2021-09-14', 'active',
            ['gaa-nanosheet'], priority='2018-10-10', verified=V_GP,
            expiry_seen='2038-10-10',
            status_note='Google Patents: Active'),
    _patent('6891227', 'Self-aligned nanotube field effect transistor '
            'and method of fabricating same', 'Appenzeller, Avouris, '
            'Wong et al. / IBM (now GlobalFoundries US)', '2002-03-20',
            '2005-05-10', 'expired', ['cnt-fet-basic'], verified=V_GP,
            status_note='Google Patents: Expired - Lifetime'),
    _patent('9825229', 'Purification of carbon nanotubes via selective '
            'heating', 'Rogers et al. / Univ. of Illinois, Northwestern, '
            'Univ. of Miami', '2014-04-03', '2017-11-21', 'active',
            ['cnt-aligned-array-process'], verified=V_GP,
            expiry_seen='2034-04-15',
            status_note='Google Patents: Active; priority 2013-04-04 '
                        '(provisional)'),
    _patent('8354291', 'Integrated circuits based on aligned nanotubes',
            'Zhou et al. / University of Southern California',
            '2009-11-24', '2013-01-15', 'fee-lapsed',
            ['cnt-aligned-array-process'], verified=V_GP,
            expiry_seen='2030-10-14',
            status_note='Google Patents: Expired - Fee Related'),
    _patent('7407895', 'Process for producing dielectric insulating '
            'thin film, and dielectric insulating material', 'RIKEN',
            '2004-03-26', '2008-08-05', 'fee-lapsed',
            ['sol-gel-hfo2-formulations'], verified=V_GP,
            expiry_seen='2024-04-03', lapsed='2024-04-03',
            status_note='Google Patents: Expired - Fee Related; nominal '
                        'expiry 2024-04-03 passed anyway'),
    _patent('8802046', 'Granular polycrystalline silicon and production '
            'thereof', 'Wacker Chemie AG', '2013-04-12', '2014-08-12',
            'fee-lapsed', ['fbr-silane'], verified=V_GP,
            expiry_seen='2033-04-12', lapsed='2022-08-12',
            status_note='Google Patents: Expired - Fee Related'),
    _patent('9428830', 'Reverse circulation fluidized bed reactor for '
            'granular polysilicon production', 'GTAT Corp (now '
            'Advanced Material Solutions LLC)', '2014-07-02',
            '2016-08-30', 'active', ['fbr-silane'], verified=V_GP,
            expiry_seen='2034-12-19',
            status_note='Google Patents: Active',
            notes='cnt_ip lists the assignee as REC Silicon and no '
                  'filing date — Google Patents 2026-08-29 says GTAT '
                  'Corp, filed 2014-07-02; the evidence row is the '
                  'verified one.'),
    _patent('2739088', 'Process for controlling solute segregation by '
            'zone-melting', 'Pfann / Bell Telephone Laboratories',
            '1951-11-16', '1956-03-20', 'expired', ['zone-refining'],
            verified=V_GP, expiry_seen='1973-03-20',
            status_note='Google Patents: Expired - Lifetime'),
    # ---- patents NOT in cnt_ip key_patents_json (prior-art fills) --
    _patent('3011877', 'Production of high-purity semiconductor '
            'materials for electrical purposes (Siemens rod process)',
            'Schweickert, Reuschel, Gutsche / Siemens-Schuckertwerke',
            '1957-06-11', '1961-12-05', 'expired', ['siemens-tcs'],
            verified=V_GP, expiry_seen='1978-12-05',
            status_note='Google Patents: Expired - Lifetime',
            notes='the cnt_ip siemens-tcs verify_next candidate — now '
                  'fetched'),
    _patent('4883687', 'Fluid bed process for producing polysilicon',
            'Ethyl Corp (now Albemarle)', '1988-12-27', '1989-11-28',
            'expired', ['fbr-silane'], verified=V_GP,
            expiry_seen='2006-11-28',
            status_note='Google Patents: Expired - Lifetime'),

    # ---- publications: one per citation key --------------------------
    _pub('VS1', 'A Compact Virtual-Source Model for Carbon Nanotube '
         'FETs in the Sub-10-nm Regime — Part I: Intrinsic Elements',
         'Lee, Pop, Franklin, Haensch, Wong; IEEE TED 62(9):3061-3069',
         '10.1109/TED.2015.2457453', '2015-09-01',
         ['vs-compact-model'], detail='published equations = the '
         'model source; equations are not copyrightable; free copy '
         'arXiv:1503.04397', verified=V_XR),
    _pub('VS2', 'A Compact Virtual-Source Model for CNFETs — Part II: '
         'Extrinsic Elements, Performance Assessment, and Design '
         'Optimization', 'Lee et al.; IEEE TED 62(9):3070-3078',
         '10.1109/TED.2015.2457424', '2015-09-01',
         ['vs-compact-model'], detail='extrinsic-element equations; '
         'free copy arXiv:1503.04398', verified=V_XR),
    _pub('KHA09', 'A Simple Semiempirical Short-Channel MOSFET '
         'Current-Voltage Model Continuous Across All Regions of '
         'Operation and Employing Only Physical Parameters',
         'Khakifirooz, Nayfeh, Antoniadis; IEEE TED 56(8):1674-1680',
         '10.1109/TED.2009.2024022', '2009-08-01',
         ['vs-compact-model'], detail='the virtual-source formulation '
         'our model derives from', verified=V_XR),
    _pub('FC10', 'Length scaling of carbon nanotube transistors',
         'Franklin & Chen; Nat. Nanotech. 5:858-862',
         '10.1038/nnano.2010.220', '2010-11-21', ['cnt-fet-basic'],
         proves='prior-art-before', detail='measured Lg scaling of '
         'CNTFETs (calibration anchors)', verified=V_XR),
    _pub('RAH03', 'Theory of Ballistic Nanotransistors',
         'Rahman, Guo, Datta, Lundstrom; IEEE TED 50(9):1853-1864',
         '10.1109/TED.2003.815366', '2003-09-01',
         ['vs-compact-model', 'cnt-fet-basic'],
         detail='top-of-the-barrier ballistic theory (model source; '
         'free copy nanohub.org/resources/122)', verified=V_XR),
    _pub('LUN97', 'Elementary Scattering Theory of the Si MOSFET',
         'Lundstrom; IEEE EDL 18(7):361-363', '10.1109/55.596937',
         '1997-07-01', ['vs-compact-model', 'mosfet-generic'],
         detail='T = λ/(λ+L), B = T/(2−T) — the transmission '
         'framework our transport uses', verified=V_XR),
    _pub('GUO04', 'Multiscale modeling of carbon nanotube transistors',
         'Guo, Datta, Lundstrom et al.', '', '2003-12-01',
         ['vs-compact-model'], detail='free copy arXiv:cond-mat/'
         '0312551 (Dec 2003)', url='https://arxiv.org/abs/cond-mat/'
         '0312551', notes='no DOI recorded; verify_next: resolve the '
         'journal version (Int. J. Multiscale Comp. Eng. 2004?)'),
    _pub('JAV04', 'High-Field Quasiballistic Transport in Short '
         'Carbon Nanotubes', 'Javey et al.; PRL 92:106804',
         '10.1103/PhysRevLett.92.106804', '2004-03-12',
         ['cnt-fet-basic'], proves='prior-art-before',
         detail='mean-free-path data (acoustic/optical phonon)',
         verified=V_XR),
    _pub('PARK04', 'Electron-Phonon Scattering in Metallic '
         'Single-Walled Carbon Nanotubes', 'Park et al.; Nano Lett. '
         '4:517-520', '10.1021/nl035258c', '2004-02-18',
         ['cnt-fet-basic'], proves='prior-art-before',
         detail='mean-free-path data', verified=V_XR),
    _pub('WIL98', 'Electronic structure of atomically resolved carbon '
         'nanotubes', 'Wildoer et al.; Nature 391:59-62',
         '10.1038/34139', '1998-01-01', ['cnt-fet-basic'],
         proves='prior-art-before', detail='STM bandgap vs diameter '
         '(the Eg = 2 a γ / d anchor)', verified=V_XR),
    _pub('ZF92', 'New one-dimensional conductors: Graphitic '
         'microtubules (zone-folding; (n−m) mod 3 rule)', 'Hamada, '
         'Sawada, Oshiyama; PRL 68:1579 (+ Saito et al. APL 60:2204)',
         '10.1103/PhysRevLett.68.1579', '1992-03-09',
         ['cnt-fet-basic'], proves='prior-art-before',
         detail='zone-folding band structure — public since 1992',
         verified=V_XR, notes='second DOI 10.1063/1.107080 not fetched'),
    _pub('FIO05', PAPERS['FIO05']['citation'],
         'Fiori, Iannaccone, Klimeck; IEDM 2005',
         PAPERS['FIO05']['doi'], '2005-12-05', ['cnt-fet-basic'],
         proves='prior-art-before', detail='ballistic NEGF oracle '
         'literature', verified=V_XR,
         bucket=PAPERS['FIO05']['license_bucket'],
         notes='Crossref gives no day; IEDM 2005 ran 5-7 Dec 2005'),
    _pub('HIL19', PAPERS['HIL19']['citation'],
         'Hills et al.; Nature 572:595-602', PAPERS['HIL19']['doi'],
         '2019-08-28', ['cnt-aligned-array-process', 'standard-cells'],
         proves='prior-art-before', detail='RV16X-NANO system '
         'precedent (scientific reference only; design collateral '
         'never released)', verified=V_XR,
         bucket=PAPERS['HIL19']['license_bucket']),
    # taxonomy citations
    _pub('EKV95', 'An analytical MOS transistor model valid in all '
         'regions of operation and dedicated to low-voltage and '
         'low-current applications', 'Enz, Krummenacher, Vittoz; '
         'AICSP 8:83-114', '10.1007/BF01239381', '1995-07-01',
         ['mosfet-generic'], detail='gm/Id weak-inversion limit',
         verified=V_XR),
    _pub('SIL96', 'A gm/ID based methodology for the design of CMOS '
         'analog circuits …', 'Silveira, Flandre, Jespers; IEEE JSSC '
         '31(9):1314-1319', '10.1109/4.535416', '1996-09-01',
         ['mosfet-generic'], detail='gm/Id design variable',
         notes='verify_next: Crossref 10.1109/4.535416'),
    _pub('YAN92', 'Scaling the Si MOSFET: from bulk to SOI to bulk',
         'Yan, Ourmazd, Lee; IEEE TED 39(7):1704-1710',
         '10.1109/16.141237', '1992-07-01', ['soi', 'mosfet-generic'],
         proves='prior-art-before', detail='natural length λ',
         notes='verify_next: Crossref 10.1109/16.141237'),
    _pub('FTW98', 'Generalized scale length for two-dimensional '
         'effects in MOSFETs', 'Frank, Taur, Wong; IEEE EDL '
         '19(10):385-387', '10.1109/55.720194', '1998-10-01',
         ['mosfet-generic'], detail='generalized scale length',
         notes='verify_next: Crossref 10.1109/55.720194'),
    _pub('AP97', "Scaling theory for cylindrical, fully-depleted, "
         "surrounding-gate MOSFET's", 'Auth & Plummer; IEEE EDL '
         '18(2):74-76', '10.1109/55.553049', '1997-02-01',
         ['gaa-nanowire'], proves='prior-art-before',
         detail='GAA nanowire scale length — surrounding-gate MOSFET '
         'theory public since 1997', verified=V_XR,
         notes='also cited as [AP98] in sifet.si_model'),
    _pub('COL08', 'FinFETs and Other Multi-Gate Transistors',
         'Colinge (ed.); Springer', '10.1007/978-0-387-71752-4',
         '2008-01-01', ['finfet', 'gaa-nanowire'], kind='textbook',
         proves='public-domain-textbook', detail='multi-gate '
         'natural length per gate count (2008 — < 20 y)',
         notes='verify_next: Crossref 10.1007/978-0-387-71752-4'),
    _pub('HIS00', 'FinFET — a self-aligned double-gate MOSFET scalable '
         'to 20 nm', 'Hisamoto, Hu et al.; IEEE TED 47(12):2320-2325',
         '10.1109/16.887014', '2000-12-01', ['finfet'],
         proves='prior-art-before', detail='the FinFET structure '
         'published Dec 2000 (same group as US 6,413,802)',
         verified=V_XR),
    _pub('LOU17', 'Stacked nanosheet gate-all-around transistor to '
         'enable scaling beyond FinFET', 'Loubet et al.; VLSI Tech. '
         'Symp. T230-T231', '10.23919/VLSIT.2017.7998183',
         '2017-06-01', ['gaa-nanosheet'], proves='prior-art-before',
         detail='2017 — too young for the 20-y rule and post-dates the '
         'TSMC 2015 filing', verified=V_XR),
    _pub('IR11', 'Tunnel field-effect transistors as energy-efficient '
         'electronic switches', 'Ionescu & Riel; Nature 479:329-337',
         '10.1038/nature10679', '2011-11-17', ['tfet'],
         proves='prior-art-before', detail='TFET review (2011)',
         notes='verify_next: Crossref 10.1038/nature10679'),
    # power citations
    _pub('NAR01', 'Scaling of stack effect and its application for '
         'leakage reduction', 'Narendra, Borkar, De, Antoniadis, '
         'Chandrakasan; ISLPED 2001 pp.195-200',
         '10.1145/383082.383132', '2001-08-01', ['standard-cells'],
         proves='prior-art-before', detail='stack-effect leakage '
         'model', verified=V_XR),
    # sifet.si_model citations
    _pub('CT67', 'Carrier mobilities in silicon empirically related to '
         'doping and field', 'Caughey & Thomas; Proc. IEEE '
         '55(12):2192-2193', '10.1109/PROC.1967.6123', '1967-12-01',
         ['mosfet-generic'], detail='mobility-vs-doping fit',
         verified=V_XR),
    _pub('TAK94', 'On the universality of inversion layer mobility in '
         'Si MOSFETs: Part I', 'Takagi, Toriumi, Iwase, Tango; IEEE '
         'TED 41(12):2357-2362', '10.1109/16.337449', '1994-12-01',
         ['mosfet-generic'], detail='universal mobility curve',
         notes='verify_next: Crossref 10.1109/16.337449'),
    _pub('SUZ93', 'Scaling theory for double-gate SOI MOSFETs',
         'Suzuki, Tanaka, Tosaka, Horie, Arimoto; IEEE TED '
         '40(12):2326-2329', '10.1109/16.249482', '1993-12-01',
         ['soi', 'finfet'], proves='prior-art-before',
         detail='double-gate scale length',
         notes='verify_next: Crossref 10.1109/16.249482'),
    _pub('SG-HFO2', 'Open-literature solution-processed HfO2 gate '
         'dielectrics for TFTs (range prior)', 'e.g. J. Ko et al.; '
         'Y.-H. Kim et al.', '', '', ['sol-gel-hfo2-formulations'],
         proves='prior-art-before', detail='PRIOR bucket: values are '
         'ranges; no specific paper pinned', notes='verify_next: pin '
         'one paper with DOI + date (needed before it can count)'),
    _pub('SG-SIO2', 'Open-literature sol-gel SiO2 (TEOS) spin-on '
         'dielectric for TFTs (range prior)', 'open TFT literature',
         '', '', ['sol-gel-dielectric-generic'],
         proves='prior-art-before', detail='PRIOR bucket; [BS90] '
         'carries the chemistry', notes='verify_next: pin one paper '
         'with DOI + date'),
    # sifet.si_refinement citations
    _pub('TRU60', 'Solid Solubilities of Impurity Elements in Germanium '
         'and Silicon', 'Trumbore; Bell Syst. Tech. J. 39(1):205-233',
         '10.1002/j.1538-7305.1960.tb03928.x', '1960-01-01',
         ['zone-refining', 'directional-solidification'],
         proves='prior-art-before', detail='segregation coefficients',
         verified=V_XR),
    _pub('HOP85', 'Impurity effects in silicon for high efficiency '
         'solar cells', 'Hopkins & Rohatgi; J. Cryst. Growth '
         '75(1):67-79', '10.1016/0022-0248(86)90226-5', '1986-01-01',
         ['directional-solidification'], proves='prior-art-before',
         detail='PV impurity tolerance',
         notes='verify_next: Crossref 10.1016/0022-0248(86)90226-5'),
    _pub('SAF12', 'Processes for Upgrading Metallurgical Grade Silicon '
         'to Solar Grade Silicon', 'Safarian, Tranell, Tangstad; '
         'Energy Procedia 20:88-97', '10.1016/j.egypro.2012.03.011',
         '2012-01-01', ['directional-solidification'],
         proves='prior-art-before', detail='metallurgical route '
         'review (open access)',
         notes='verify_next: Crossref 10.1016/j.egypro.2012.03.011'),
    _pub('CEC12', 'Solar Grade Silicon Feedstock (Handbook of PV '
         'Science and Engineering 2e, ch.5)', 'Ceccaroli & Lohne; '
         'Wiley', '10.1002/9780470974704.ch5', '2011-01-01',
         ['siemens-tcs', 'fbr-silane', 'directional-solidification'],
         proves='prior-art-before', detail='grade definitions, '
         'Siemens/FBR energy figures',
         notes='verify_next: Crossref 10.1002/9780470974704.ch5'),
    _pub('DEL12', 'Purification of silicon for photovoltaic '
         'applications', 'Delannoy; J. Cryst. Growth 360:61-67',
         '10.1016/j.jcrysgro.2011.12.006', '2012-12-01',
         ['directional-solidification'], proves='prior-art-before',
         detail='open metallurgical route to SoG-Si', verified=V_XR),
    _pub('SCH42', 'Bemerkungen zur Schichtkristallbildung (Scheil '
         'equation)', 'Scheil; Z. Metallkunde 34:70-72', '',
         '1942-01-01', ['directional-solidification'],
         proves='prior-art-before', detail='the segregation equation '
         'directional solidification is modelled with — 1942',
         url='', notes='verify_next: locate a DOI / library record'),
    _pub('BCF52', 'The Distribution of Solute in Crystals Grown from '
         'the Melt. Part I', 'Burton, Prim, Slichter; J. Chem. Phys. '
         '21:1987', '10.1063/1.1698728', '1953-11-01',
         ['directional-solidification', 'zone-refining'],
         proves='prior-art-before', detail='k_eff vs k0',
         notes='verify_next: Crossref 10.1063/1.1698728'),
    _pub('ZHE11', 'Separation of Phosphorus from Silicon by Induction '
         'Vacuum Refining', 'Zheng, Engh, Tangstad, Luo; Sep. Purif. '
         'Technol. 82:128-137', '10.1016/j.seppur.2011.09.001',
         '2011-10-01', ['directional-solidification'],
         proves='prior-art-before', detail='P evaporation model',
         notes='verify_next: Crossref 10.1016/j.seppur.2011.09.001'),
    _pub('ALE15', 'Boron Removal in Molten Silicon by a Steam-Added '
         'Plasma Melting Method', 'Nakamura, Baba, Sakaguchi, Kato; '
         'Mater. Trans. 45(3):858-864', '10.2320/matertrans.45.858',
         '2004-03-01', ['directional-solidification'],
         proves='prior-art-before', detail='plasma B removal',
         notes='verify_next: Crossref 10.2320/matertrans.45.858 '
               '(authors/year from memory per si_refinement)'),
    _pub('SCH19', 'Deposition reactors for solar grade silicon: A '
         'comparative thermal analysis of a Siemens reactor and a '
         'fluidized bed reactor', 'Ramos et al.; J. Cryst. Growth '
         '431:1-9', '10.1016/j.jcrysgro.2015.08.023', '2015-12-01',
         ['siemens-tcs', 'fbr-silane'], proves='prior-art-before',
         detail='Siemens vs FBR energy',
         notes='verify_next: Crossref 10.1016/j.jcrysgro.2015.08.023'),
    # prior-art papers not in any CITATIONS dict
    _pub('TANS98', 'Room-temperature transistor based on a single '
         'carbon nanotube', 'Tans, Verschueren, Dekker; Nature '
         '393:49-52', '10.1038/29954', '1998-05-07', ['cnt-fet-basic'],
         kind='prior-art', proves='prior-art-before',
         detail='the first CNTFET, published 1998 — prior art before '
         'every CNTFET claim filed after it', verified=V_XR),
    _pub('COL90', "Silicon-on-insulator 'gate-all-around device'",
         'Colinge, Gao, Romano-Rodriguez, Maes, Claeys; IEDM 1990 '
         'pp.595-598', '10.1109/IEDM.1990.237128', '1990-12-01',
         ['gaa-nanowire'], kind='prior-art', proves='prior-art-before',
         detail='the GAA concept, IEDM 1990', verified=V_XR,
         notes='Crossref gives no date; IEDM 1990 was Dec 1990'),
    _pub('RED95', 'Silicon surface tunnel transistor', 'Reddick & '
         'Amaratunga; APL 67:494-496', '10.1063/1.114547',
         '1995-07-24', ['tfet'], kind='prior-art',
         proves='prior-art-before', detail='gated tunnel transistor '
         'concept, 1995', verified=V_XR),

    # ---- textbooks --------------------------------------------------
    _book('book-weste-eshraghian-1985', 'Principles of CMOS VLSI '
          'Design: A Systems Perspective', 'Weste & Eshraghian; '
          'Addison-Wesley', '0-201-08222-5', '1985-01-01',
          ['standard-cells', 'mirror-adder', 'tg-latch'],
          detail='1st ed. 1985 (OpenLibrary lists the 1988 printing '
          'of this ISBN; 2nd ed. 1993): static CMOS gates, the '
          '28-T mirror adder, transmission-gate latches — all '
          'textbook by 1985/1988 (>= 20 y either way)',
          verified=True,
          notes='date used for the 20-y rule: 1988 printing at worst'),
    _book('book-weste-harris-2010', 'CMOS VLSI Design: A Circuits and '
          'Systems Perspective, 4th ed.', 'Weste & Harris; Addison-'
          'Wesley', '978-0-321-54774-3', '2010-03-01',
          ['standard-cells', 'mirror-adder', 'tg-latch'],
          detail='4th ed. 2010 (< 20 y — the 1985 edition carries '
          'the age rule)', verified=True),
    _book('book-rabaey-2003', 'Digital Integrated Circuits: A Design '
          'Perspective, 2nd ed.', 'Rabaey, Chandrakasan, Nikolić; '
          'Prentice Hall', '0-13-090996-3', '2003-01-01',
          ['standard-cells', 'mirror-adder', 'tg-latch'],
          detail='2nd ed. 2003: mirror adder §11.3, TG latch ch.7, '
          'power ch.5', verified=True, citation_key='[RAB03]'),
    _book('book-sze-1981', 'Physics of Semiconductor Devices, 2nd ed.',
          'Sze; Wiley', '0-471-05661-8', '1981-01-01',
          ['mosfet-generic', 'planar-process'],
          detail='2nd ed. 1981: MOSFET physics + thermal SiO2 gate '
          'oxide — public textbook knowledge >= 20 y',
          verified=True),
    _book('book-sze-ng-2007', 'Physics of Semiconductor Devices, 3rd '
          'ed.', 'Sze & Ng; Wiley', '978-0-471-14323-9', '2007-01-01',
          ['mosfet-generic'], detail='3rd ed. 2007 (< 20 y); the '
          'sifet [SZE07] equations', citation_key='[SZE07]',
          notes='verify_next: OpenLibrary ISBN 9780471143239 (DOI '
                '10.1002/0470068329 not fetched)'),
    _book('book-taur-ning-1998', 'Fundamentals of Modern VLSI Devices',
          'Taur & Ning; Cambridge', '0-521-55056-4', '1998-01-01',
          ['mosfet-generic', 'finfet'],
          detail='1st ed. 1998: short-channel scale length, body '
          'effect', verified=True),
    _book('book-taur-ning-2009', 'Fundamentals of Modern VLSI Devices, '
          '2nd ed.', 'Taur & Ning; Cambridge', '978-0-521-83294-6',
          '2009-01-01', ['mosfet-generic', 'finfet'],
          detail='2nd ed. 2009 (< 20 y); the [TN09] sections',
          citation_key='[TN09]',
          notes='verify_next: OpenLibrary ISBN 9780521832946'),
    _book('book-brinker-scherer', 'Sol-Gel Science: The Physics and '
          'Chemistry of Sol-Gel Processing', 'Brinker & Scherer; '
          'Academic Press', '0-12-134970-5', '1990-01-01',
          ['sol-gel-dielectric-generic', 'sol-gel-hfo2-formulations'],
          detail='1990: alkoxide hydrolysis/condensation, spin-on, '
          'densification — public chemistry >= 20 y', verified=True,
          citation_key='[BS90]'),
    _book('book-lundstrom-2000', 'Fundamentals of Carrier Transport, '
          '2nd ed.', 'Lundstrom; Cambridge', '0-521-63134-3',
          '2000-01-01', ['vs-compact-model', 'cnt-fet-basic'],
          detail='2000: scattering theory / mean free path — the '
          'transport framework', verified=True),
    _book('book-pfann-1966', 'Zone Melting, 2nd ed.', 'Pfann; Wiley',
          '', '1966-01-01', ['zone-refining'],
          detail='1966: single/multi-pass zone-refining equations',
          citation_key='[PFA66]',
          notes='verify_next: library record / LCCN (no ISBN era)'),
    _book('book-razavi-2001', 'Design of Analog CMOS Integrated '
          'Circuits', 'Razavi; McGraw-Hill', '978-0-07-238032-3',
          '2001-01-01', ['mosfet-generic'],
          detail='2001: intrinsic gain, headroom',
          citation_key='[RAZ01]',
          notes='verify_next: OpenLibrary ISBN 9780072380323'),
    _book('book-sansen-2006', 'Analog Design Essentials', 'Sansen; '
          'Springer', '978-0-387-25746-4', '2006-01-01',
          ['mosfet-generic'], detail='2006: gm/Id, gain (< 20 y)',
          citation_key='[SAN06]',
          notes='verify_next: Crossref 10.1007/b135783'),

    # ---- standards ---------------------------------------------------
    _std('std-verilog-ams-2.4', 'Verilog-AMS Language Reference Manual '
         '2.4.0 (Verilog-A subset)', 'Accellera Systems Initiative',
         'Accellera Verilog-AMS LRM 2.4.0', '2014-05-01',
         ['verilog-a', 'vs-compact-model'],
         'https://www.accellera.org/downloads/standards/v-ams',
         detail='open standard (built on IEEE 1364); writing our own '
         '.va carries no licence obligation',
         notes='verify_next: fetch the LRM 2.4.0 release date from '
               'accellera.org'),
    _std('std-ieee-1364-2005', 'IEEE Std 1364-2005 Verilog HDL',
         'IEEE', 'IEEE 1364-2005', '2006-04-07', ['verilog-a'],
         'https://standards.ieee.org/ieee/1364/3641/',
         detail='the base language Verilog-AMS extends',
         notes='verify_next: IEEE standards page'),
    _std('std-liberty', 'Liberty (.lib) library format', 'Synopsys / '
         'Liberty Technical Advisory Board (IEEE-ISTO)',
         'Open Source Liberty', '2007-01-01', ['liberty-format'],
         'https://www.synopsys.com/community/interoperability-programs/'
         'tap-in.html',
         detail='the FORMAT is an open de-facto standard; the Synopsys '
         'reference parser carries its own licence (lic-synopsys-osl-1.0)',
         notes='verify_next: Synopsys Open Source Liberty announcement '
               'date (2007?)'),
    _std('std-semi-pv017', 'SEMI PV017 / PV049 photovoltaic-grade '
         'silicon feedstock', 'SEMI', 'SEMI PV017', '2011-01-01',
         ['siemens-tcs', 'directional-solidification'],
         'https://www.semi.org/en/standards',
         detail='grade definitions (the standard text is copyrighted; '
         'the grade tiers are cited as data)', citation_key='[SEMI]',
         notes='verify_next: exact PV017 revision + year'),

    # ---- licences ----------------------------------------------------
    _lic('GPL-3.0', 'GNU General Public License v3.0', 'Free Software '
         'Foundation', '2007-06-29', 'open-licence',
         'the project licence; OpenVAF + OpenSTA share it — '
         'compatible by identity',
         ['vs-compact-model', 'openvaf', 'opensta', 'standard-cells',
          'mirror-adder', 'tg-latch'],
         'https://spdx.org/licenses/GPL-3.0-only.html', verified=True,
         via='https://spdx.org/licenses/GPL-3.0-only.html'),
    _lic('BSD-3-Clause', 'BSD 3-Clause "New" License', 'ngspice '
         'project (Modified BSD since release 27)', '1999-07-22',
         'open-licence', 'permissive; GPLv3-compatible', ['ngspice'],
         'https://spdx.org/licenses/BSD-3-Clause.html',
         notes='verify_next: ngspice COPYING at the pinned release'),
    _lic('BSD-2-Clause', 'BSD 2-Clause "Simplified" License',
         'Kwant project (LICENSE.rst)', '1999-01-01', 'open-licence',
         'permissive; GPLv3-compatible; fork-pinned dausume/kwant',
         ['kwant'], 'https://spdx.org/licenses/BSD-2-Clause.html',
         notes='verify_next: LICENSE.rst at the fork pin'),
    _lic('LGPL-2.1', 'GNU Lesser General Public License v2.1',
         'Free Software Foundation (ngspice tclspice/adms parts)',
         '1999-02-01', 'open-licence', 'GPLv3-compatible via LGPL '
         'section 3 (relicense as GPL)', ['ngspice'],
         'https://spdx.org/licenses/LGPL-2.1-only.html'),
    _lic('MPL-2.0', 'Mozilla Public License 2.0', 'Mozilla Foundation '
         '(ngspice src/osdi)', '2012-01-03', 'open-licence',
         'GPLv3-compatible (MPL 2.0 §3.3 secondary licences)',
         ['ngspice'], 'https://spdx.org/licenses/MPL-2.0.html'),
    _lic('MIT', 'MIT License', 'ngspice sparse; OpenVAF rustc carve-'
         'outs', '1988-01-01', 'open-licence', 'permissive',
         ['ngspice', 'openvaf'], 'https://spdx.org/licenses/MIT.html'),
    _lic('Synopsys-OSL-1.0', 'Synopsys Open Source License Version 1.0 '
         '(Open Source Liberty reference parser)', 'Synopsys',
         '2007-01-01', 'open-licence', 'attaches to liberty_parse CODE '
         'only, which we do not use; NOT OSI-approved — GPLv3 '
         'compatibility unassessed (irrelevant while unused)',
         ['liberty-format'], 'https://metacpan.org/pod/Parse::Liberty',
         notes='verify_next: read COPYING.pdf verbatim before any '
               'vendoring'),
    _lic('CMC-Modified', 'NEEDS Modified CMC License (Stanford '
         'VS-CNFET nanoHUB source)', 'Stanford / nanoHUB NEEDS',
         '2015-01-01', 'proprietary-licence', 'price restriction + '
         'acknowledgment clause = GPLv3-INCOMPATIBLE; the Stanford '
         '.va was NEVER READ (CNT_FET_SIM_LICENSE_GATE S0 gate) — '
         'recorded so the clean-room boundary is visible, NOT a '
         'dependency', ['vs-compact-model'],
         'https://nanohub.org/publications/12/',
         notes='verify_next: re-fetch the licence text verbatim before '
               'any legal write-up'),
]

SEED_BY_NAME = {s['name']: s for s in SEED_EVIDENCE}
assert len(SEED_BY_NAME) == len(SEED_EVIDENCE), 'duplicate evidence name'

#: Citation-key aliases: the same paper cited under two keys.
CITATION_ALIASES = {'[AP98]': '[AP97]'}

#: citation key -> evidence item name (built from the seeds).
CITATION_ITEMS = {}
for _s in SEED_EVIDENCE:
    if _s['citation_key']:
        CITATION_ITEMS.setdefault(_s['citation_key'], _s['name'])
for _alias, _target in CITATION_ALIASES.items():
    if _target in CITATION_ITEMS:
        CITATION_ITEMS[_alias] = CITATION_ITEMS[_target]


def all_citation_keys():
    """Every citation key across the modules' CITATIONS dicts."""
    keys = set()
    for d in (TAG_CITATIONS, TAXONOMY_CITATIONS, POWER_CITATIONS,
              SI_CITATIONS, SI_REFINEMENT_CITATIONS):
        keys.update(d.keys())
    return sorted(keys)


def citation_item(key):
    return CITATION_ITEMS.get(key)


# ── rows ───────────────────────────────────────────────────────────

_ROW_FIELDS = tuple(SEED_EVIDENCE[0].keys())


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        class_name) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def evidence_items(manager=None):
    """name -> item dict (manager rows win over seeds)."""
    out = {}
    for row in _rows(manager, 'EvidenceItem'):
        name = getattr(row, 'name', '')
        if name:
            out[name] = {k: getattr(row, k, None) for k in _ROW_FIELDS}
    for name, seed in SEED_BY_NAME.items():
        out.setdefault(name, dict(seed))
    return out


def _today():
    return _dt.date.today()


def item_payload(it, today=None):
    """An item with its JSON decoded, age, and the satisfaction
    verdict the proof rules give it."""
    r = dict(it)
    r['subjects'] = json.loads(r.get('subjects_json') or '[]')
    age = age_years(r.get('date'), today)
    r['age_years'] = round(age, 1) if age is not None else None
    r['old_enough'] = bool(age is not None and age >= PRIOR_ART_YEARS)
    r['satisfies'] = _satisfies(r)
    r['is_active_claim'] = r['proves'] == 'active'
    r['detailPath'] = f'/api/cntfet/evidence/{r["name"]}'
    r['satisfies_rule'] = SATISFIES.get(r['proves'], '')
    return r


def _satisfies(r):
    """Does this item, on its own, satisfy a green record under
    PROOF_RULES['proven-free']?"""
    if not r.get('verified'):
        return False
    p = r.get('proves')
    if p == 'expired':
        return True
    if p == 'open-licence':
        return True
    if p in ('prior-art-before', 'public-domain-textbook',
             'model-source'):
        return bool(r.get('old_enough'))
    return False


def item_summary(r):
    return {'name': r['name'], 'kind': r['kind'], 'ref': r['ref'],
            'proves': r['proves'], 'date': r['date'],
            'verified': bool(r['verified']),
            'satisfies': r['satisfies'], 'detailPath': r['detailPath']}


# ── evidence for a record (the JOIN) ───────────────────────────────

def record_evidence(manager, rec, items=None, today=None):
    """[item payloads] named by the record's evidence_json, plus any
    item whose subjects_json names the record (so a newly POSTed
    item attaches without editing the record)."""
    items = items if items is not None else evidence_items(manager)
    names = []
    for n in json.loads(rec.get('evidence_json') or '[]'):
        if n in items and n not in names:
            names.append(n)
    for n, it in items.items():
        if n not in names and rec['name'] in json.loads(
                it.get('subjects_json') or '[]'):
            names.append(n)
    return [item_payload(items[n], today) for n in names]


def _record_status(rec, evidence):
    """(status, reasons, gaps) for ONE record under the rules."""
    verdict = rec.get('verdict', 'red')
    active = [e for e in evidence if e['is_active_claim']]
    proprietary = [e for e in evidence
                   if e['proves'] == 'proprietary-licence']
    good = [e for e in evidence if e['satisfies']]
    reasons, gaps = [], []
    if not evidence:
        gaps.append(f'{rec["name"]}: no evidence attached — add a '
                    f'patent / publication / textbook item '
                    f'(verify_next: {rec.get("verify_next", "")})')
        return 'unknown', reasons, gaps
    if verdict in ('amber', 'red') and active:
        for e in active:
            reasons.append(f'{rec["name"]} is {verdict} with active '
                           f'claim {e["ref"]} ({e["title"]}) to '
                           f'{e["expiry"]}')
        gaps.append(f'{rec["name"]}: active claim(s) '
                    + ', '.join(e['ref'] for e in active)
                    + ' — need expiry, licence, invalidity or a '
                      'design-around (US)')
        return 'encumbered', reasons, gaps
    if verdict in ('amber', 'red'):
        gaps.append(f'{rec["name"]}: verdict {verdict} without a known '
                    f'active claim — {rec.get("verify_next", "search")}')
        return 'free-unverified', reasons, gaps
    # green
    if proprietary:
        reasons.append(f'{rec["name"]}: proprietary item '
                       + ', '.join(e['name'] for e in proprietary)
                       + ' recorded as NOT a dependency')
    if good:
        for e in good[:3]:
            reasons.append(f'{rec["name"]} ← {e["ref"]} {e["proves"]}'
                           + (f' (expired {e["expiry"]})'
                              if e['proves'] == 'expired' else
                              f' ({e["date"][:4]})'))
        return 'proven-free', reasons, gaps
    unverified = [e for e in evidence if not e['verified']
                  and e['proves'] not in ('active', 'proprietary-licence')]
    young = [e for e in evidence if e['verified'] and not e['satisfies']]
    if unverified:
        gaps.append(f'{rec["name"]}: verify '
                    + ', '.join(f'{e["name"]} ({e["notes"] or e["ref"]})'
                                for e in unverified[:3]))
    if young:
        gaps.append(f'{rec["name"]}: verified evidence is younger than '
                    f'{PRIOR_ART_YEARS} y ('
                    + ', '.join(f'{e["name"]} {e["date"][:4]}'
                                for e in young[:3])
                    + ') — add an older prior-art / textbook item')
    if not unverified and not young:
        gaps.append(f'{rec["name"]}: evidence does not satisfy any '
                    'SATISFIES path')
    return 'free-unverified', reasons, gaps


def _combine(statuses):
    for s in PROOF_RULES['precedence']:
        if s in statuses:
            return s
    return 'unknown'


# ── subjects ───────────────────────────────────────────────────────

def _subject_records(manager, subject_kind, subject_name):
    """[(record, why)] governing a subject, + meta."""
    recs = ip.ip_records(manager)
    meta = {}
    if subject_kind == 'device':
        dev = ip._find_device(manager, subject_name)
        if dev is None:
            return None, {'error': f'no device "{subject_name}"'}
        subj = ip.subjects_for_device(manager, dev)
        meta = {'shape': subj.get('shape'),
                'dielectric': subj.get('dielectric')}
        return [(s['record'], s['why']) for s in subj['subjects']], meta
    if subject_kind == 'cell':
        subj = ip.subjects_for_cell(manager, subject_name)
        if not subj:
            return None, {'error': f'no cell records for '
                                   f'"{subject_name}"'}
        return [(s['record'], s['why']) for s in subj], meta
    if subject_kind == 'record':
        if subject_name not in recs:
            return None, {'error': f'no TechnologyIPRecord '
                                   f'"{subject_name}"'}
        return [(recs[subject_name], 'the record itself')], meta
    if subject_kind == 'route':
        rep = ip.route_ip_report(manager, subject_name)
        if not rep.get('ok'):
            return None, {'error': rep.get('error')}
        meta = {'openness': rep.get('openness'),
                'steps': rep.get('steps')}
        pairs = []
        for st in rep['steps']:
            if st.get('record') and st['record'] in recs and all(
                    p[0]['name'] != st['record'] for p in pairs):
                pairs.append((recs[st['record']], f'step {st["step"]}'))
        return pairs, meta
    return None, {'error': f'unknown subject_kind "{subject_kind}" '
                           f'(device | cell | record | route)'}


def _detail_path(subject_kind, subject_name):
    return {'device': f'/api/cntfet/device/{subject_name}/proof',
            'cell': f'/api/cntfet/cell/{subject_name}/proof',
            'record': f'/api/cntfet/ip/{subject_name}/proof',
            'route': f'/api/cntfet/route/{subject_name}/proof',
            }.get(subject_kind, '/api/cntfet/proof')


# ── freedom_proof ──────────────────────────────────────────────────

def freedom_proof(manager, subject_kind, subject_name, today=None):
    """{status, chain: [{record, verdict, why, recordStatus,
    evidence: [item summaries with detailPath]}], gaps,
    rule_applied, reasons, scope, disclaimer}."""
    pairs, meta = _subject_records(manager, subject_kind, subject_name)
    base = {'subject_kind': subject_kind, 'subject': subject_name,
            'jurisdiction': JURISDICTION, 'scope': SCOPE_LINE,
            'detailPath': _detail_path(subject_kind, subject_name),
            'disclaimer': DISCLAIMER}
    if pairs is None:
        return {**base, 'ok': False, 'status': 'unknown',
                'error': meta.get('error'), 'chain': [], 'gaps': [
                    meta.get('error', '')],
                'rule_applied': PROOF_RULES['unknown']}
    items = evidence_items(manager)
    chain, gaps, reasons, statuses = [], [], [], []
    for rec, why in pairs:
        ev = record_evidence(manager, rec, items, today)
        st, rs, gs = _record_status(rec, ev)
        statuses.append(st)
        reasons.extend(rs)
        gaps.extend(gs)
        chain.append({'record': rec['name'],
                      'display_name': rec.get('display_name', ''),
                      'verdict': rec.get('verdict'), 'why': why,
                      'ip_kind': rec.get('ip_kind'),
                      'recordStatus': st,
                      'recordDetailPath': f'/api/cntfet/ip/'
                                          f'{rec["name"]}/proof',
                      'evidence': [item_summary(e) for e in ev]})
    status = _combine(statuses)
    if status == 'proven-free':
        gaps = []
    worst = ip.worst_verdict([c['verdict'] for c in chain])
    return {**base, 'ok': True, 'status': status,
            'statusIndex': STATUS_INDEX[status],
            'ipVerdict': worst, 'gate': ip.ip_gate(worst),
            'chain': chain, 'reasons': reasons, 'gaps': gaps,
            'rule_applied': PROOF_RULES[status],
            'rules': PROOF_RULES, 'expiry_rules': EXPIRY_RULES,
            'evidenceCount': sum(len(c['evidence']) for c in chain),
            'verifiedCount': sum(1 for c in chain for e in c['evidence']
                                 if e['verified']),
            'reviewed_at': REVIEWED_AT, **meta}


# ── index / detail / provenance ────────────────────────────────────

def evidence_index(manager, kind=None, subject=None, today=None):
    items = [item_payload(i, today) for i in evidence_items(manager)
             .values()]
    if kind:
        items = [i for i in items if i['kind'] == kind]
    if subject:
        items = [i for i in items if subject in i['subjects']]
    items.sort(key=lambda i: (i['kind'], i['name']))
    counts = {'total': len(items),
              'verified': sum(1 for i in items if i['verified']),
              'by_kind': {k: sum(1 for i in items if i['kind'] == k)
                          for k in KINDS},
              'by_proves': {p: sum(1 for i in items if i['proves'] == p)
                            for p in PROVES},
              'active_claims': sum(1 for i in items
                                   if i['is_active_claim'])}
    return {'ok': True, 'items': items, 'counts': counts,
            'filter': {'kind': kind, 'subject': subject},
            'kinds': KINDS, 'proves': PROVES, 'rules': PROOF_RULES,
            'expiry_rules': EXPIRY_RULES, 'satisfies': SATISFIES,
            'citation_keys': all_citation_keys(),
            'citation_items': CITATION_ITEMS,
            'jurisdiction': JURISDICTION, 'scope': SCOPE_LINE,
            'disclaimer': DISCLAIMER}


_CITED_BY_CLASSES = ('FETCharacteristic', 'ScatteringMechanism',
                     'FETRegime', 'TransportRegime', 'FETOperatingState',
                     'CNTFETParameterRow', 'CNTCalibrationAnchor')


def _row_mentions(row, key, doi):
    for attr in ('citations_json', 'notes', 'description', 'source',
                 'source_reference', 'doi', 'figure',
                 'enforced_properties_json'):
        v = getattr(row, attr, None)
        if isinstance(v, str) and (key in v or (doi and doi in v)):
            return True
    return False


def evidence_detail(manager, name, today=None):
    items = evidence_items(manager)
    if name not in items:
        return {'ok': False, 'name': name,
                'error': f'no EvidenceItem "{name}"',
                'affordance': 'POST an EvidenceItem row or pick from '
                              '/api/cntfet/evidence',
                'scope': SCOPE_LINE, 'disclaimer': DISCLAIMER}
    it = item_payload(items[name], today)
    recs = ip.ip_records(manager)
    # supports: records naming it (evidence_json) or named by it
    records = []
    for rname, rec in recs.items():
        if name in json.loads(rec.get('evidence_json') or '[]') \
                or rname in it['subjects']:
            records.append({'record': rname,
                            'verdict': rec.get('verdict'),
                            'display_name': rec.get('display_name'),
                            'detailPath': f'/api/cntfet/ip/{rname}/proof'})
    rec_names = {r['record'] for r in records}
    devices, cells = [], []
    for cls in ('AlignedCNTFETDevice', 'SiliconMOSFET'):
        for dev in _rows(manager, cls):
            subj = ip.subjects_for_device(manager, dev)
            if any(s['record']['name'] in rec_names
                   for s in subj['subjects']) \
                    or dev.name in it['subjects']:
                devices.append({'device': dev.name, 'class': cls,
                                'detailPath': _detail_path('device',
                                                           dev.name)})
    for key in _cell_keys():
        if any(s['record']['name'] in rec_names
               for s in ip.subjects_for_cell(manager, key)) \
                or key in it['subjects']:
            cells.append({'cell': key,
                          'detailPath': _detail_path('cell', key)})
    cited_by = {}
    key, doi = it.get('citation_key'), (it['ref'][4:] if
                                        it['ref'].startswith('doi:')
                                        else '')
    aliases = [key] + [a for a, t in CITATION_ALIASES.items()
                       if t == key] if key else []
    if aliases:
        for cls in _CITED_BY_CLASSES:
            hits = [getattr(r, 'name', '') for r in _rows(manager, cls)
                    if any(_row_mentions(r, k, doi) for k in aliases)]
            if hits:
                cited_by[cls] = hits
    return {'ok': True, 'item': it,
            'supports': {'records': records, 'devices': devices,
                         'cells': cells},
            'citedBy': cited_by,
            'citedByCount': sum(len(v) for v in cited_by.values()),
            'citation_key': key, 'aliases': aliases[1:],
            'jurisdiction': JURISDICTION, 'scope': SCOPE_LINE,
            'disclaimer': DISCLAIMER}


def _cell_keys():
    try:
        from cntfet.cnt_cell_library import CELL_LIBRARY
        return sorted(CELL_LIBRARY) + (['cdff'] if 'cdff' not in
                                       CELL_LIBRARY else [])
    except ImportError:
        return []


def provenance_summary(manager, subject_kind, name, today=None):
    """The compact block the FET / cell payloads embed."""
    proof = freedom_proof(manager, subject_kind, name, today)
    ev = [e for c in proof['chain'] for e in c['evidence']]
    # best first: satisfying, then verified, then expired/old
    ev.sort(key=lambda e: (not e['satisfies'], not e['verified'],
                           e['name']))
    return {'ipVerdict': proof.get('ipVerdict'),
            'proofStatus': proof['status'],
            'evidenceCount': len(ev),
            'verifiedCount': sum(1 for e in ev if e['verified']),
            'topEvidence': [{'name': e['name'], 'kind': e['kind'],
                             'ref': e['ref'], 'proves': e['proves'],
                             'detailPath': e['detailPath']}
                            for e in ev[:3]],
            'gaps': proof.get('gaps', [])[:3],
            'detailPath': proof['detailPath'],
            'jurisdiction': JURISDICTION, 'scope': SCOPE_LINE,
            'disclaimer': DISCLAIMER}


# ── library ────────────────────────────────────────────────────────

def library_proof(manager, today=None):
    subjects = []
    for cls in ('AlignedCNTFETDevice', 'SiliconMOSFET'):
        for dev in _rows(manager, cls):
            p = freedom_proof(manager, 'device', dev.name, today)
            subjects.append({'kind': 'device', 'subject': dev.name,
                             'class': cls, 'shape': p.get('shape'),
                             'proofStatus': p['status'],
                             'ipVerdict': p.get('ipVerdict'),
                             'records': [c['record'] for c in p['chain']],
                             'gaps': p['gaps'],
                             'detailPath': p['detailPath']})
    for key in _cell_keys():
        p = freedom_proof(manager, 'cell', key, today)
        subjects.append({'kind': 'cell', 'subject': key,
                         'proofStatus': p['status'],
                         'ipVerdict': p.get('ipVerdict'),
                         'records': [c['record'] for c in p['chain']],
                         'gaps': p['gaps'], 'detailPath': p['detailPath']})
    route_names = [getattr(r, 'name', '') for r in
                   _rows(manager, 'RefinementRoute')]
    if not route_names:
        try:
            from sifet.si_refinement import SEED_REFINEMENT_ROUTES
            route_names = [r['name'] for r in SEED_REFINEMENT_ROUTES]
        except ImportError:
            route_names = []
    for rn in route_names:
        p = freedom_proof(manager, 'route', rn, today)
        if p.get('ok'):
            subjects.append({'kind': 'route', 'subject': rn,
                             'openness': p.get('openness'),
                             'proofStatus': p['status'],
                             'ipVerdict': p.get('ipVerdict'),
                             'records': [c['record'] for c in p['chain']],
                             'gaps': p['gaps'],
                             'detailPath': p['detailPath']})
    subjects.sort(key=lambda s: (STATUS_INDEX[s['proofStatus']],
                                 s['kind'], s['subject']))
    counts = {s: sum(1 for x in subjects if x['proofStatus'] == s)
              for s in STATUSES}
    counts['total'] = len(subjects)
    idx = evidence_index(manager, today=today)['counts']
    return {'ok': True, 'subjects': subjects, 'counts': counts,
            'gaps_by_subject': {s['subject']: s['gaps'] for s in subjects
                                if s['gaps']},
            'evidence_counts': idx,
            'proof_rows': proof_rows(subjects),
            'rules': PROOF_RULES, 'expiry_rules': EXPIRY_RULES,
            'statuses': STATUSES, 'reviewed_at': REVIEWED_AT,
            'jurisdiction': JURISDICTION, 'scope': SCOPE_LINE,
            'disclaimer': DISCLAIMER}


# ── long-form rows + graph seed + curve builder ────────────────────

def proof_rows(subjects):
    """Categorical x = subject, y = status index 0..3, label = status;
    one series per subject kind."""
    return [{'series': s['kind'], 'style': 'dot', 'dash': False,
             'x': s['subject'], 'y': STATUS_INDEX[s['proofStatus']],
             'label': s['proofStatus']} for s in subjects]


def device_proof_rows(manager, device, today=None):
    """The device's chain as rows: x = record, y = record status
    index, label = status + evidence count."""
    p = freedom_proof(manager, 'device', getattr(device, 'name', device),
                      today)
    if not p.get('ok'):
        return []
    return [{'series': c['verdict'], 'style': 'dot', 'dash': False,
             'x': c['record'], 'y': STATUS_INDEX[c['recordStatus']],
             'label': f'{c["recordStatus"]} ({len(c["evidence"])} '
                      f'items, {sum(1 for e in c["evidence"] if e["verified"])} verified)'}
            for c in p['chain']]


def _build_proof_status(id_fn, p, device, manager, knobs):
    return device_proof_rows(manager, device)


CURVE_BUILDERS = {'proof-status': _build_proof_status}

_Y_TICKS = {str(i): s for i, s in enumerate(STATUSES)}

SEED_CNT_EVIDENCE_GRAPHS = [{
    'name': 'cnt-library-proof-status',
    'description': 'Proof-of-freedom status per governing IP record '
                   'of the device (0 proven-free / 1 free-unverified / '
                   '2 encumbered / 3 unknown); series = record verdict. '
                   + SCOPE_LINE + '. ' + DISCLAIMER +
                   ' — data: /api/cntfet/device/{name}/points?curve='
                   'proof-status; library table: /api/cntfet/proof',
    'source_class': 'AlignedCNTFETDevice',
    'definition': json.dumps({'graphConfig': {
        'renderStyle': 'lineY',
        'xDimension': 'x',
        'yDimensions': ['y'],
        'seriesDimension': 'series',
        'styleDimension': 'style',
        'seriesColors': [],
        'options': {'showLegend': True, 'showGrid': True,
                    'xLabel': 'governing IP record',
                    'yLabel': 'proof status (0 proven-free … 3 unknown)',
                    'yType': 'linear', 'yTickLabels': _Y_TICKS},
        'aggregation': None,
    }}),
}]
