"""
@module cntfet.cnt_ip

IP / licensing / freedom-to-operate (FTO) TRACKING for the FET +
cell + silicon technologies the cntfet / sifet modules model —
as ROWS, in the cnt_states style: every technology the suite
simulates or proposes to build carries a TechnologyIPRecord saying
what kind of IP governs it, the verdict, WHY, and what "I make my
own" changes (usually: nothing about an active patent — a patent
covers make/use/sell, 35 U.S.C. §271(a); own manufacture IS
"making").

DISCLAIMER (carried on every payload as `disclaimer`):
  ENGINEERING FTO RECORD — NOT LEGAL ADVICE — verify with counsel
  before commercial use.

Verdict vocabulary mirrors the suite's licence gates
(AI-Notes/evaluations/*LICENSE_GATE.md): green = proceed
(incorporate / build); amber = proceed for research, verify before
commercial use; red = blocker (NC / active claim squarely on the
thing / GPL-incompatible). Project licence: GPLv3; NC = hard
blocker; adopted upstreams are FORKED under dausume/ pins.

Patent expiry rule used for `expiry_est`: US utility patents filed
on/after 1995-06-08 expire 20 years from the EARLIEST non-provisional
filing date (plus PTA, ignored here); patents filed before that
expire at the later of 17 years from grant or 20 years from filing
(1960s patents: long expired either way). Maintenance-fee lapses
("Expired - Fee Related") make a patent unenforceable EARLIER —
recorded as status 'lapsed' with the fetched date.

`confidence`: 'verified' = number, title, assignee, filing date and
status fetched from Google Patents / USPTO on reviewed_at;
'partially-verified' = number+title verified, dates/claims from
secondary sources; 'unverified' = representative claim NOT checked —
`verify_next` says what to search.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/ip, /device/{name}/ip)
  - cntfet.cnt_device_viz (CURVE_BUILDERS 'ip-verdicts';
    SEED_CNT_IP_GRAPHS)
  - cntfet.selftest_ip
  - polariServer (TechnologyIPRecord registration + SEED_TECHNOLOGY_IP)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_taxonomy import shape_of

REVIEWED_AT = '2026-08-29'

DISCLAIMER = ('ENGINEERING FTO RECORD — NOT LEGAL ADVICE — verify with '
              'counsel before commercial use. Patent status/expiry are '
              'engineering estimates (20 years from US filing, no PTA/'
              'terminal-disclaimer analysis, no claim construction, no '
              'non-US family search).')

VERDICT_RANK = {'green': 0, 'amber': 1, 'red': 2}
VERDICT_GATE = {
    'green': 'proceed — incorporate / build; no active claim or '
             'licence obstacle known',
    'amber': 'proceed for research; VERIFY (search + counsel) before '
             'commercial make/use/sell',
    'red': 'blocker — active claim squarely on the subject, NC '
           'licence, or GPLv3-incompatible; do not ship without a '
           'licence or a design-around',
}

SUBJECT_KINDS = ('device-shape', 'device-material', 'process', 'cell',
                 'model', 'tool', 'format', 'chemistry')
IP_KINDS = ('public-domain', 'patent-expired', 'patent-active',
            'patent-mixed', 'trade-secret', 'open-licence',
            'proprietary-licence')

#: The one sentence every self-manufacture note must contain the
#: substance of (the selftest looks for the key phrase).
MAKE_YOUR_OWN_RULE = ('Making it yourself does NOT clear an active '
                      'patent: a US patent excludes others from MAKING, '
                      'using, selling, offering or importing the claimed '
                      'invention (35 U.S.C. 271(a)) — own manufacture is '
                      '"making". It DOES remove any copyright/licence '
                      'obligation on someone else\'s design files or '
                      'code, and trade secrets you never accessed cannot '
                      'be asserted against an independent re-derivation.')


class TechnologyIPRecord(treeObject):
    """One technology (shape / material / process / cell / model /
    tool / format / chemistry) and the IP posture that governs it —
    verdict + reasoning + self-manufacture note as data."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        subject_kind: str = 'process',
        # the row name it governs ('finfet', 'cnt-gaa', 'siemens-tcs',
        # 'cfa', 'vs-model', 'liberty-format', ...)
        subject_ref: str = '',
        ip_kind: str = 'public-domain',
        verdict: str = 'green',
        # JSON list of {number, title, assignee, filed, expiry_est,
        # status, claims_gist, source_url}
        key_patents_json: str = '[]',
        # SPDX id or text (software / formats)
        licence: str = '',
        # our own implementation and ITS licence
        what_we_own: str = '',
        fto_reasoning: str = '',
        self_manufacture_note: str = '',
        jurisdiction: str = 'US',
        verify_next: str = '',
        sources_json: str = '[]',
        confidence: str = 'unverified',
        reviewed_at: str = REVIEWED_AT,
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.subject_kind = subject_kind
        self.subject_ref = subject_ref
        self.ip_kind = ip_kind
        self.verdict = verdict
        self.key_patents_json = key_patents_json
        self.licence = licence
        self.what_we_own = what_we_own
        self.fto_reasoning = fto_reasoning
        self.self_manufacture_note = self_manufacture_note
        self.jurisdiction = jurisdiction
        self.verify_next = verify_next
        self.sources_json = sources_json
        self.confidence = confidence
        self.reviewed_at = reviewed_at
        self.notes = notes
        self.is_prior = is_prior


# ── seed helpers ───────────────────────────────────────────────────

def _pat(number, title, assignee, filed, expiry_est, status,
         claims_gist, source_url=''):
    return {'number': number, 'title': title, 'assignee': assignee,
            'filed': filed, 'expiry_est': expiry_est, 'status': status,
            'claims_gist': claims_gist,
            'source_url': source_url or
            f'https://patents.google.com/patent/US{number.replace(",", "")}'}


def _rec(name, display_name, subject_kind, subject_ref, ip_kind,
         verdict, fto_reasoning, self_manufacture_note, verify_next,
         patents=(), licence='', what_we_own='', jurisdiction='US',
         sources=(), confidence='unverified', notes=''):
    assert subject_kind in SUBJECT_KINDS, subject_kind
    assert ip_kind in IP_KINDS, ip_kind
    assert verdict in VERDICT_RANK, verdict
    return {
        'name': name, 'display_name': display_name,
        'subject_kind': subject_kind, 'subject_ref': subject_ref,
        'ip_kind': ip_kind, 'verdict': verdict,
        'key_patents_json': json.dumps(list(patents)),
        'licence': licence, 'what_we_own': what_we_own,
        'fto_reasoning': fto_reasoning,
        'self_manufacture_note': self_manufacture_note,
        'jurisdiction': jurisdiction, 'verify_next': verify_next,
        'sources_json': json.dumps(list(sources)),
        'confidence': confidence, 'reviewed_at': REVIEWED_AT,
        'notes': notes, 'is_prior': True,
    }


_OWN_MAKE_EXPIRED = ('Expired patent: anyone may make, use and sell '
                     'the claimed device — own manufacture changes '
                     'nothing because nothing is left to clear. ' +
                     MAKE_YOUR_OWN_RULE)
_OWN_MAKE_ACTIVE = ('An ACTIVE claim on the process/structure is '
                    'infringed by making it in your own lab exactly as '
                    'by buying it. ' + MAKE_YOUR_OWN_RULE +
                    ' Research-use exemption in the US is very narrow '
                    '(Madey v. Duke) — do not rely on it.')
_OWN_CODE = ('Software: writing our own implementation from the '
             'published equations/standard removes any copyright or '
             'licence obligation on the third-party code we never '
             'read; it does not change patent exposure (none known). ' +
             MAKE_YOUR_OWN_RULE)


# ── the seeds ──────────────────────────────────────────────────────

SEED_TECHNOLOGY_IP = [
    # ---- device physics / shapes ---------------------------------
    _rec('mosfet-generic', 'MOSFET (insulated-gate FET)', 'device-shape',
         'planar-bulk', 'patent-expired', 'green',
         'The foundational MOSFET patent (Kahng/Atalla, Bell Labs) '
         'was filed 1960 and issued 1963 — expired for decades; the '
         'device physics (surface inversion under a gate oxide) is '
         'textbook public domain [SZE07]. Nothing about a generic '
         'MOSFET is patent-encumbered.',
         _OWN_MAKE_EXPIRED,
         'nothing for the generic device; FTO on a SPECIFIC modern '
         'node still needs a search of process/structure claims '
         '(strain, HKMG, spacer, contact schemes) filed after 2006.',
         patents=[_pat('3,102,230', 'Electric field controlled '
                       'semiconductor device', 'Bell Telephone '
                       'Laboratories', '1960-05-31', '1980-08-27',
                       'expired', 'insulated-gate FET with an oxide '
                       'between the gate and the semiconductor '
                       'channel (issued 1963-08-27)')],
         sources=['https://patents.google.com/patent/US3102230A/en'],
         confidence='verified'),
    _rec('cmos', 'CMOS (complementary pair logic)', 'device-shape',
         'planar-bulk', 'patent-expired', 'green',
         'Wanlass (Fairchild) filed 1963-06-18, granted 1967-12-05 '
         '(3,356,858): complementary n/p pair with a common gate '
         'signal — the whole cell library rests on it and it expired '
         'in the 1980s. CMOS as a circuit style is public domain.',
         _OWN_MAKE_EXPIRED,
         'nothing for CMOS as a style; well/isolation schemes on a '
         'named node (latch-up, STI, DTI) may carry live claims — '
         'search when a node is chosen.',
         patents=[_pat('3,356,858', 'Low stand-by power complementary '
                       'field effect circuitry', 'Fairchild Camera and '
                       'Instrument Corp', '1963-06-18', '1984-12-05',
                       'expired', 'a pair of complementary insulated-'
                       'gate FETs, source/drain in series, gates '
                       'driven by one signal (issued 1967-12-05)')],
         sources=['https://patents.google.com/patent/US3356858A/en',
                  'https://www.computerhistory.org/siliconengine/'
                  'complementary-mos-circuit-configuration-is-invented/'],
         confidence='verified'),
    _rec('planar-process', 'Planar process (oxide-masked diffusion)',
         'process', 'planar-bulk', 'patent-expired', 'green',
         'Hoerni (Fairchild) filed 1959-05-01, issued 1962-03-20: '
         'oxide passivation + windows for diffusion, the basis of '
         'every planar device. Expired ~1979. Public domain.',
         _OWN_MAKE_EXPIRED,
         'nothing for the planar process; modern implant/anneal/'
         'lithography equipment claims are a separate matter (buy '
         'tools, or search when building them).',
         patents=[_pat('3,025,589', 'Method of manufacturing '
                       'semiconductor devices', 'Fairchild '
                       'Semiconductor', '1959-05-01', '1979-03-20',
                       'expired', 'oxide layer left in place over the '
                       'junction edges; diffusion through windows '
                       '(issued 1962-03-20)')],
         sources=['https://patents.google.com/patent/US3025589A/en',
                  'https://www.computerhistory.org/siliconengine/'
                  'invention-of-the-planar-manufacturing-process/'],
         confidence='verified'),
    _rec('soi', 'SOI / FD-SOI (thin film on buried oxide)', 'device-shape',
         'soi', 'patent-mixed', 'amber',
         'The thin-film SOI transistor is old (SIMOX 1978, Smart Cut '
         'CEA 1992 — Bruel US 5,374,564 filed 1992-09-15, ceased, '
         'expiry 2012). The DEVICE physics is clear. But the '
         'SUBSTRATE supply is patent-dense (Soitec Smart Cut family '
         'continued into the 2010s; FD-SOI back-bias / body schemes '
         'from STMicro/GF are 2010s filings and may be active).',
         'Making your own SOI wafer by the 1992 Smart Cut claim is '
         'clear (expired); using a LATER Soitec/ST claim (thin-BOX, '
         'back-bias, strained SOI) is not. ' + MAKE_YOUR_OWN_RULE,
         'search Soitec / STMicro / GlobalFoundries families '
         '2006-2020 for FD-SOI (UTBB, back-gate, 22FDX); confirm '
         'the specific substrate + device stack before commercial '
         'use.',
         patents=[_pat('5,374,564', 'Process for the production of '
                       'thin semiconductor material films (Smart Cut)',
                       'CEA', '1992-09-15', '2012-09-15', 'expired',
                       'H implant to a depth + stiffener + thermal '
                       'split to transfer a thin film (issued '
                       '1994-12-20; ceased)')],
         sources=['https://patents.google.com/patent/US5374564A/en'],
         confidence='partially-verified',
         notes='Basic device: green. Substrate + back-bias: amber '
               'until searched.'),
    _rec('finfet', 'FinFET (tri-gate fin)', 'device-shape', 'finfet',
         'patent-expired', 'green',
         'The Berkeley FinFET patent (Hu, Bokor, King et al.) US '
         '6,413,802 was filed 2000-10-23 and expired 2020-10-23 '
         '(Google Patents: "Expired - Lifetime"). The fin + wrapped '
         'gate structure and the SOI-fin fabrication method are '
         'therefore free to make. Later foundry claims (bulk fins, '
         'fin-cut, SiGe fins, specific spacers) are separate.',
         _OWN_MAKE_EXPIRED + ' The 2000 claim covered an SOI fin; '
         'a BULK fin with STI recess is a later (Intel ~2011) '
         'structure — search before choosing it.',
         'a bulk-FinFET build needs a search of Intel/TSMC/Samsung '
         'fin-formation claims 2008-2016 (bulk fin, STI recess, '
         'fin-cut, SiGe p-fin); the SOI-fin build in the 2000 claim '
         'needs nothing.',
         patents=[_pat('6,413,802', 'FinFET transistor structures '
                       'having a double gate channel extending '
                       'vertically from a substrate and methods of '
                       'manufacture', 'Regents of the University of '
                       'California', '2000-10-23', '2020-10-23',
                       'expired', 'SOI substrate, etch a fin, gate '
                       'dielectric + gate wrapping the fin, spacers, '
                       'S/D doping (granted 2002-07-02)')],
         sources=['https://patents.google.com/patent/US6413802B1/en'],
         confidence='verified'),
    _rec('gaa-nanowire', 'GAA nanowire', 'device-shape', 'gaa-nanowire',
         'patent-mixed', 'amber',
         'The round-wire GAA concept is old (Colinge GAA 1990, '
         'Samsung/IBM nanowire FETs 2000s — early filings expired or '
         'near expiry). Stacked-nanowire release (SiGe sacrificial '
         'etch) and inner-spacer claims from 2010-2018 are likely '
         'ACTIVE and are exactly what a practical build uses.',
         _OWN_MAKE_ACTIVE,
         'pick a representative: Colinge (1990) or Samsung 2004-2007 '
         'multi-bridge-channel (MBCFET) patents — check status; then '
         'search the SiGe-release + inner-spacer claims of the 2010s '
         'for the build you intend.',
         confidence='unverified',
         notes='No representative patent fetched — the nanosheet '
               'record carries the verified active claims that '
               'also read on stacked wires.'),
    _rec('gaa-nanosheet', 'GAA nanosheet (stacked ribbons)',
         'device-shape', 'gaa-nanosheet', 'patent-active', 'amber',
         'Stacked-nanosheet GAA is a 2014-2019 invention and its '
         'structural + process claims are in force: TSMC US '
         '9,966,471 (filed 2015-03-31, active to 2035) and IBM US '
         '11,121,044 (filed 2019-11-22, priority 2018-10-10, active '
         'to 2038) both verified active. Simulating a nanosheet is '
         'free; MAKING one along those claims is not. Amber (not '
         'red) because the claims are narrow-ish (specific stacks, '
         'rare-earth-oxide layers, specific release flows) and a '
         'design-around may exist — needs counsel.',
         _OWN_MAKE_ACTIVE,
         'claim-by-claim read of 9,966,471 / 11,121,044 plus the '
         'IBM/Samsung/Intel nanosheet families 2015-2022 against the '
         'intended stack; confirm the Loubet 2017 VLSI structure is '
         'not covered by an active IBM claim.',
         patents=[_pat('9,966,471', 'Stacked Gate-All-Around FinFET '
                       'and method forming the same', 'TSMC',
                       '2015-03-31', '2035-03-31', 'active',
                       'semiconductor strips each with a surrounding '
                       'gate dielectric and electrode — stacked GAA '
                       'channels (priority 2014-06-27, granted '
                       '2018-05-08)'),
                  _pat('11,121,044', 'Vertically stacked nanosheet '
                       'CMOS transistor', 'IBM', '2019-11-22',
                       '2038-10-10', 'active', 'forming stacked '
                       'nanosheet CMOS with alternating rare-earth-'
                       'oxide / semiconductor nanosheet stacks '
                       '(priority 2018-10-10, granted 2021-09-14)')],
         sources=['https://patents.google.com/patent/US9966471B2/en',
                  'https://patents.google.com/patent/US11121044B2/en'],
         confidence='verified'),
    _rec('tfet', 'Tunnel FET', 'device-shape', 'tfet', 'patent-mixed',
         'amber',
         'The gated p-i-n tunnel transistor concept dates to the '
         '1990s (Reddick/Amaratunga 1995; Appenzeller CNT TFET 2004) '
         'so the concept is old, but heterojunction / vertical TFET '
         'structure claims from 2008-2018 (IBM, Intel, TSMC, '
         'universities) are likely active. Our taxonomy row is a '
         'taxonomy, not a build — the model cannot even represent it.',
         _OWN_MAKE_ACTIVE,
         'find 1-2 representative TFET patents (e.g. Intel/IBM '
         'heterojunction TFET 2010-2016) and check status before any '
         'TFET build; nothing to do while it stays taxonomy-only.',
         confidence='unverified'),
    # ---- CNT ------------------------------------------------------
    _rec('cnt-fet-basic', 'CNT FET (basic device)', 'device-material',
         'cnt-gaa', 'patent-expired', 'green',
         'The first-generation CNTFET patents are expired: IBM US '
         '6,891,227 (Appenzeller, Avouris, Wong et al.; filed '
         '2002-03-20, granted 2005-05-10, "Expired - Lifetime") '
         'claimed a nanotube on a substrate with metal S/D and a '
         'gate separated by dielectric — i.e. the generic CNTFET. '
         'Tans/Dekker 1998 and Martel/Avouris 1998 are papers, and '
         'the Delft/IBM 1998-2001 filings are all past 20 years. A '
         'single-tube GAA CNTFET as the S1 device is free to make.',
         _OWN_MAKE_EXPIRED,
         'confirm no IBM continuation of 6,891,227 (e.g. 7,253,065 — '
         'same title, later filing) carries a later-filed claim '
         'that is still live; check its filing date.',
         patents=[_pat('6,891,227', 'Self-aligned nanotube field '
                       'effect transistor and method of fabricating '
                       'same', 'IBM (now GlobalFoundries US)',
                       '2002-03-20', '2022-03-20', 'expired',
                       'CNT on a substrate, metal S/D at each end, '
                       'gate separated by dielectric layers (granted '
                       '2005-05-10)')],
         sources=['https://patents.google.com/patent/US6891227B2/en'],
         confidence='verified'),
    _rec('cnt-aligned-array-process',
         'Aligned semiconducting CNT arrays (growth/transfer/sort/'
         'purify)', 'process', 'cnt-gaa', 'patent-active', 'amber',
         'The DEVICE is free but the way a real aligned-array line is '
         'built is not: Rogers et al. US 9,825,229 (thermocapillary '
         'purification of aligned CNT arrays; filed 2014-04-03, '
         'active to 2034) and USC/Zhou US 8,354,291 (grow aligned '
         'tubes on quartz/sapphire, transfer, fabricate; filed '
         '2009-11-24 — LAPSED for fees but nominal expiry 2030) are '
         'verified; Stanford/MIT (VMR, RINSE, DREAM) and IBM (DNA '
         'self-assembly, dielectrophoresis US 9,923,160 / 10,090,481) '
         'families from 2013-2020 are very likely active. Amber not '
         'red: several routes exist (quartz-growth transfer is '
         'lapsed; solution DLSA from Peking is a different claim '
         'set) — a design-around is plausible but must be chosen '
         'consciously.',
         _OWN_MAKE_ACTIVE + ' Growing/transferring your own aligned '
         'arrays IS practising the process claims.',
         'for the chosen alignment route (quartz CVD + transfer / '
         'Langmuir-Schaefer / DLSA / dielectrophoresis) search '
         'Stanford (Mitra/Wong), MIT (Shulaker), IBM, Peking (Peng) '
         'and Illinois (Rogers) families 2012-2022 and check status; '
         'confirm 8,354,291 fee-lapse is final (no reinstatement).',
         patents=[_pat('9,825,229', 'Purification of carbon nanotubes '
                       'via selective heating', 'Univ. of Illinois / '
                       'Northwestern / Univ. of Miami', '2014-04-03',
                       '2034-04-15', 'active', 'aligned CNT layer + '
                       'thermocapillary resist; selectively heat '
                       'metallic tubes, expose and remove them '
                       '(priority 2013-04-04, granted 2017-11-21)'),
                  _pat('8,354,291', 'Integrated circuits based on '
                       'aligned nanotubes', 'University of Southern '
                       'California', '2009-11-24', '2030-10-14',
                       'lapsed', 'grow aligned nanotubes on wafer-'
                       'scale quartz/sapphire, transfer to a target '
                       'substrate, fabricate devices (granted '
                       '2013-01-15; "Expired - Fee Related")')],
         sources=['https://patents.google.com/patent/US9825229B2/en',
                  'https://patents.google.com/patent/US8354291B2/en'],
         confidence='partially-verified',
         notes='Two representatives verified; the Stanford/MIT/IBM '
               'families named in verify_next were NOT fetched.'),
    # ---- dielectric chemistry ------------------------------------
    _rec('sol-gel-dielectric-generic', 'Sol-gel oxide chemistry '
         '(alkoxide hydrolysis/condensation)', 'chemistry',
         'solgel-sio2-teos-4nm', 'public-domain', 'green',
         'Alkoxide sol-gel (TEOS hydrolysis, spin-on, densification) '
         'is 19th/20th-century chemistry, fully described in Brinker '
         '& Scherer, "Sol-Gel Science" (1990) [BS90]; spin-on glass '
         'dielectrics were in production by the 1980s. No live claim '
         'on the generic chemistry.',
         'Mixing and spinning your own TEOS sol is practising public-'
         'domain chemistry — nothing to clear. ' + MAKE_YOUR_OWN_RULE,
         'nothing for the generic chemistry; specific precursor '
         'formulations / additives / cure recipes are covered by the '
         'sol-gel-hfo2-formulations record.',
         sources=['Brinker & Scherer, Sol-Gel Science, Academic '
                  'Press 1990 (ISBN 978-0-12-134970-7)'],
         confidence='verified'),
    _rec('sol-gel-hfo2-formulations', 'Sol-gel / solution HfO2 '
         'high-k formulations', 'chemistry', 'solgel-hfo2-4nm',
         'patent-mixed', 'amber',
         'Solution-processed HfO2 gate dielectrics: the RIKEN '
         'surface sol-gel patent US 7,407,895 (filed 2004-03-26) '
         'lapsed/expired 2024 — clear. But 2010-2020 filings on '
         'specific precursor chemistries (Hf-alkoxide + chelating '
         'agents, aqueous nitrate, combustion synthesis, photochemical '
         'cure, HfO2-based TFT gate stacks from Oregon State / '
         'Northwestern / display makers) are plausibly active and '
         'may read on our "Hf-alkoxide in 2-methoxyethanol, 400 C" '
         'recipe. Mixed: generic route clear, specific recipes not '
         'searched.',
         'A home-mixed HfO2 sol that matches an active formulation '
         'claim is still "making". ' + MAKE_YOUR_OWN_RULE,
         'search solution-processed HfO2/ZrO2 gate-dielectric claims '
         '2008-2022 (Oregon State/Keszler, Northwestern/Marks, LG/'
         'Samsung display) against the exact precursor/solvent/cure '
         'used on the solgel-hfo2-4nm row.',
         patents=[_pat('7,407,895', 'Process for producing dielectric '
                       'insulating thin film, and dielectric insulating '
                       'material', 'RIKEN', '2004-03-26', '2024-04-03',
                       'expired', 'sequential adsorption + hydrolysis '
                       'of metal alkoxide on a hydroxylated substrate, '
                       'then plasma/thermal treatment (granted '
                       '2008-08-05; "Expired - Fee Related")')],
         sources=['https://patents.google.com/patent/US7407895B2/en'],
         confidence='partially-verified'),
    # ---- cells ----------------------------------------------------
    _rec('standard-cells', 'Standard-cell circuits (all 25 library '
         'cells)', 'cell', '*', 'public-domain', 'green',
         'Every CELL_LIBRARY topology (inverter, NAND/NOR 2-4, AND/'
         'OR, AOI/OAI 21/22, XOR/XNOR 2-3, MUX 2/4, buffers, tri-'
         'state, half/full adder, latch, DFF) is a textbook static '
         'CMOS circuit (Weste & Harris, CMOS VLSI Design, 4th ed. '
         '2010; Rabaey 2003) with roots in 1960s-80s literature. '
         'No patent can cover them now; our SPICE/Liberty artefacts '
         'are our own GPLv3 work.',
         'Laying out your own cells removes any question of copying '
         'a foundry\'s copyrighted GDS/Liberty; the circuits '
         'themselves were never encumbered. ' + MAKE_YOUR_OWN_RULE,
         'nothing for the circuits; if a foundry cell library\'s '
         'LAYOUT or characterization data were ever imported, that '
         'file\'s licence (not patents) is what to check.',
         licence='GPL-3.0-or-later (our netlists, Liberty, layouts)',
         what_we_own='cnt_cell_library.CELL_LIBRARY (25 cells, '
                     'generated netlists) + characterization — GPLv3',
         sources=['Weste & Harris, CMOS VLSI Design 4e (2010) ch.1, '
                  '10-11', 'Rabaey, Chandrakasan, Nikolic, Digital '
                  'Integrated Circuits 2e (2003)'],
         confidence='verified'),
    _rec('mirror-adder', 'Mirror adder (full-adder cell)', 'cell', 'cfa',
         'public-domain', 'green',
         'The mirror adder is the classic 28-transistor symmetric '
         'full adder (Weste & Eshraghian 1985; Rabaey §11.3). Any '
         'claim from the 1980s expired long ago.',
         'Building your own mirror adder is building a textbook '
         'circuit. ' + MAKE_YOUR_OWN_RULE,
         'nothing.',
         licence='GPL-3.0-or-later (our cfa netlist)',
         what_we_own='CELL_LIBRARY["cfa"] — GPLv3',
         sources=['Rabaey et al. 2003 §11.3.2 (mirror adder)'],
         confidence='verified'),
    _rec('tg-latch', 'Transmission-gate latch / master-slave DFF',
         'cell', 'clatch', 'public-domain', 'green',
         'The transmission-gate latch and the master-slave DFF built '
         'from two are 1970s-80s textbook sequential circuits '
         '(Weste & Harris ch.10; Rabaey ch.7). Public domain. Covers '
         'clatch and cdff.',
         'Building your own TG latch/DFF is building a textbook '
         'circuit. ' + MAKE_YOUR_OWN_RULE,
         'nothing; pulsed / sense-amplifier / dual-edge flops from '
         'the 2000s (Intel/IBM) would need a search if ever added.',
         licence='GPL-3.0-or-later (our clatch/cdff netlists)',
         what_we_own='CELL_LIBRARY["clatch"], cnt_sequential cdff — '
                     'GPLv3',
         sources=['Weste & Harris 2010 ch.10'],
         confidence='verified'),
    # ---- silicon refinement --------------------------------------
    _rec('siemens-tcs', 'Siemens process (TCS distillation + CVD)',
         'process', 'siemens-tcs', 'trade-secret', 'amber',
         'The Siemens TCS chemistry (SiHCl3 distillation, H2 '
         'reduction on hot rods) was patented in the 1950s-60s '
         '(Siemens; e.g. DE 1,061,593 / US 3,011,877 era) — all '
         'expired. What reaches 9N-11N is PRACTISED know-how: '
         'column design, ppb analytics, rod-growth control (Wacker, '
         'Hemlock, OCI, GCL). Trade secrets cannot be asserted '
         'against an independent re-derivation, but they mean the '
         'open build reaches SoG, not EG (si_refinement '
         'siemens-route: openness industrial-proprietary).',
         'Making your own Siemens reactor practises expired claims — '
         'clear — and any trade secret you never accessed is not '
         'yours to worry about. Newer reactor-specific claims (Wacker/'
         'GCL 2005-2020 on rod configurations, energy recovery, TCS '
         'converters) might read on a modern design — search. ' +
         MAKE_YOUR_OWN_RULE,
         'verify the 1950s Siemens US numbers (candidates US '
         '3,011,877 / 3,042,494) and their expiry; search Wacker/'
         'GCL/Hemlock 2005-2020 reactor + STC-converter claims for '
         'any modern feature copied.',
         confidence='unverified',
         sources=['Chalamala, Sandia SAND2018-1814 (Siemens process '
                  'review)', 'si_refinement [SCH19] [CEC12]'],
         notes='Original Siemens patent numbers NOT fetched — '
               'expired by age with certainty (1950s filing) but '
               'the numbers are unverified.'),
    _rec('fbr-silane', 'Fluidised-bed silane / TCS granular polysilicon',
         'process', 'fbr-silane', 'patent-active', 'amber',
         'The FBR concept is old (Union Carbide / Ethyl 1980s, US '
         '4,883,687 expired) but every practical FBR is wrapped in '
         'live claims: Wacker US 8,802,046 (filed 2013-04-12; LAPSED '
         'for fees 2022, so unenforceable) is the verified '
         'representative, and REC Silicon (US 9,428,830 reverse-'
         'circulation FBR, granted 2016), GTAT/SunEdison-MEMC and '
         'Hanwha families from 2012-2020 are very likely ACTIVE. '
         'Amber: the base process is free, the reactor designs that '
         'work are not.',
         _OWN_MAKE_ACTIVE + ' Building your own FBR that uses a '
         'claimed heating / gas-distribution / seed-handling scheme '
         'is infringing "making".',
         'fetch US 9,428,830 (REC) status and filing date; search '
         'REC Silicon, GTAT, SunEdison/MEMC, Hanwha, Wacker FBR '
         'families 2010-2022 against the intended reactor; confirm '
         '8,802,046 lapse is final.',
         patents=[_pat('8,802,046', 'Granular polycrystalline silicon '
                       'and production thereof', 'Wacker Chemie AG',
                       '2013-04-12', '2033-04-12', 'lapsed',
                       'FBR deposition of Si from a halosilane with '
                       'HCl offgas as the control variable; granule '
                       'Cl 10-40 ppmw (granted 2014-08-12; "Expired - '
                       'Fee Related" 2022-09-19)'),
                  _pat('9,428,830', 'Reverse circulation fluidized bed '
                       'reactor for granular polysilicon production',
                       'REC Silicon', '', '', 'active-unverified',
                       'thermally-insulated vertical divider; particles '
                       'circulate up through a heating zone into the '
                       'silane reaction zone (granted 2016-08-30; '
                       'filing date NOT fetched)',
                       'https://patents.justia.com/patent/9428830')],
         sources=['https://patents.google.com/patent/US8802046B2/en',
                  'https://patents.justia.com/patent/9428830'],
         confidence='partially-verified'),
    _rec('directional-solidification', 'Directional solidification '
         '(Bridgman / HEM ingot casting)', 'process',
         'directional-solidification', 'patent-mixed', 'amber',
         'Segregation refining by controlled solidification is '
         '19th-century metallurgy (Scheil 1942 equation is the model) '
         'and HEM/Bridgman furnaces for Si date from the 1970s '
         '(Crystal Systems, expired). Modern furnace claims (GT '
         'Solar/GTAT 2008-2016 DSS furnaces, mono-like seeding, '
         'crucible coatings) may be active. Mixed.',
         'Doing DS in a home-built furnace along the 1970s claims is '
         'clear; copying a GTAT DSS heater/seed layout may not be. '
         + MAKE_YOUR_OWN_RULE,
         'search GTAT / ALD / Ferrotec DS-furnace families 2008-2018 '
         'and mono-like (seeded) casting claims if the furnace copies '
         'a commercial design.',
         confidence='unverified',
         sources=['si_refinement [DEL12] [CEC12]']),
    _rec('zone-refining', 'Zone refining (Pfann)', 'process',
         'zone-refining', 'patent-expired', 'green',
         'Pfann (Bell Labs) US 2,739,088 "Process for controlling '
         'solute segregation by zone-melting" was filed 1951-11-16 '
         '(granted 1956) — expired 1973. Float-zone growth (Keck & '
         'Golay 1953, Theuerer/Bell US 3,060,123) is equally expired. '
         'Public domain.',
         _OWN_MAKE_EXPIRED,
         'nothing for the process; RF induction heater / crystal '
         'puller equipment claims from the 2000s would only matter if '
         'a commercial puller design were copied.',
         patents=[_pat('2,739,088', 'Process for controlling solute '
                       'segregation by zone-melting', 'Bell Telephone '
                       'Laboratories', '1951-11-16', '1973-03-20',
                       'expired', 'move a molten zone along a solid '
                       'charge repeatedly so solute segregates to one '
                       'end (granted 1956-03-20)')],
         sources=['https://patents.google.com/patent/US2739088A/en',
                  'https://www.computerhistory.org/siliconengine/'
                  'development-of-zone-refining/'],
         confidence='verified'),
    # ---- models / tools / formats --------------------------------
    _rec('vs-compact-model', 'VS-CNFET-derived compact model (ours)',
         'model', 'vs-model', 'open-licence', 'green',
         'Our model is a CLEAN-ROOM implementation from the published '
         'equations ([VS1] Lee et al. IEEE TED 2015 / arXiv:1503.04397; '
         '[KHA09]); cnt_vs_model docstring: "the Stanford source was '
         'never read (NEEDS Modified CMC License; S0 gate)". Equations '
         'in a paper are not copyrightable and no patent on the VS '
         'formulation is known. The Stanford nanoHUB code is NEEDS '
         'Modified CMC-licensed (price restriction + acknowledgment '
         'clause = GPLv3-incompatible, see CNT_FET_SIM_LICENSE_GATE) '
         'and is therefore NOT in our tree — which is exactly why '
         'ours is green.',
         _OWN_CODE + ' Keep the "never read" discipline: any future '
         'contributor who has read the Stanford .va must not touch '
         'cnt_vs_model / cnt_verilog_a.',
         'a quick patent search for "virtual source" compact-model '
         'claims (MIT/Antoniadis, Stanford/Wong) — none expected, '
         'equations are not patentable as such; re-confirm the '
         'nanoHUB NEEDS licence text verbatim before any legal '
         'write-up.',
         licence='GPL-3.0-or-later',
         what_we_own='cnt_vs_model.py + cnt_verilog_a.py (revision '
                     'cntfet-vs-s1-r1), OSDI equivalence regression — '
                     'GPLv3, model_family "VS-CNFET-derived", '
                     'implementation "independent"',
         sources=['cntfet/cnt_vs_model.py docstring',
                  'AI-Notes/evaluations/CNT_FET_SIM_LICENSE_GATE.md '
                  '(Stanford/CCAM gate)', 'arXiv:1503.04397'],
         confidence='verified'),
    _rec('liberty-format', 'Liberty (.lib) library format', 'format',
         'liberty-format', 'open-licence', 'green',
         'Liberty is published by Synopsys under the "Synopsys Open '
         'Source License Version 1.0" (Open Source Liberty / '
         'liberty_parse, COPYING.pdf); the FORMAT is an open '
         'de-facto standard (Liberty TAB under IEEE-ISTO since '
         '2006). Writing .lib files with our own writer creates no '
         'obligation; the licence attaches to Synopsys\'s '
         'liberty_parse CODE, which we do not use (OpenSTA has its '
         'own GPL-3.0 parser).',
         _OWN_CODE,
         'if Synopsys liberty_parse code is ever vendored, read the '
         'Synopsys Open Source License v1.0 for GPLv3 compatibility '
         '(NOT OSI-approved — expect an attribution/notice clause); '
         'our writer + OpenSTA parser avoid the question.',
         licence='Synopsys Open Source License v1.0 (reference code); '
                 'format itself: open standard',
         what_we_own='cnt_cell_library Liberty writer — GPLv3',
         sources=['https://metacpan.org/pod/Parse::Liberty',
                  'https://news.synopsys.com/index.php?s=20295&'
                  'item=123415'],
         confidence='partially-verified'),
    _rec('ngspice', 'ngspice circuit simulator', 'tool', 'ngspice',
         'open-licence', 'green',
         'ngspice base licence is BSD-3-Clause ("Modified BSD", '
         'since release 27); COPYING lists the exceptions: tclspice.c '
         'LGPL-2.1, adms admst LGPL-2.1, src/osdi MPL-2.0, sparse '
         'MIT, xspice + ndev public domain. All GPLv3-compatible; we '
         'run ngspice as a subprocess anyway (no linking).',
         _OWN_CODE,
         'none for subprocess use; if ngspice is ever linked/vendored, '
         're-read COPYING at the pinned version (BSD-3 + LGPL-2.1 + '
         'MPL-2.0 are all GPLv3-compatible).',
         licence='BSD-3-Clause (+ LGPL-2.1 tclspice/adms, MPL-2.0 '
                 'osdi, MIT sparse, public-domain xspice)',
         what_we_own='cnt_osdi / cnt_cells drivers — GPLv3',
         sources=['https://github.com/ngspice/ngspice/blob/master/'
                  'COPYING', 'https://ngspice.sourceforge.io/devel.html'],
         confidence='verified'),
    _rec('openvaf', 'OpenVAF / OpenVAF-Reloaded Verilog-A compiler',
         'tool', 'openvaf', 'open-licence', 'green',
         'GPL-3.0 (+ MIT rustc-derived carve-outs) per the S0 gate; a '
         'build tool whose licence does not attach to the .osdi it '
         'emits. Same licence as the project → compatible.',
         _OWN_CODE,
         'none; re-check the Reloaded fork LICENSE at the pinned '
         'commit when pinning dausume/OpenVAF.',
         licence='GPL-3.0',
         sources=['AI-Notes/evaluations/CNT_FET_SIM_LICENSE_GATE.md '
                  '(OpenVAF/OSDI gate)',
                  'https://github.com/arpadbuermen/OpenVAF'],
         confidence='verified'),
    _rec('opensta', 'OpenSTA static timing analyser', 'tool', 'opensta',
         'open-licence', 'green',
         'GPL-3.0 (parallaxsw/OpenSTA, dual-licensed commercially). '
         'Identical licence family to ours → compatible for '
         'subprocess AND linking.',
         _OWN_CODE,
         'none.',
         licence='GPL-3.0',
         sources=['AI-Notes/evaluations/CNT_FET_SIM_LICENSE_GATE.md '
                  '(ASAP7 + characterization gate)',
                  'https://github.com/parallaxsw/OpenSTA'],
         confidence='verified'),
    _rec('kwant', 'Kwant quantum-transport (F3 NEGF kernel)', 'tool',
         'kwant', 'open-licence', 'green',
         'BSD-2-Clause (LICENSE.rst verified in the S0 gate) — '
         'permissive, GPLv3-compatible; fork-pinned as dausume/kwant.',
         _OWN_CODE,
         'none; keep the fork pin\'s LICENSE.rst intact.',
         licence='BSD-2-Clause',
         sources=['AI-Notes/evaluations/CNT_FET_SIM_LICENSE_GATE.md '
                  '(NEGF engine gate)',
                  'https://gitlab.kwant-project.org/kwant/kwant'],
         confidence='verified'),
    _rec('verilog-a', 'Verilog-A / Verilog-AMS language', 'format',
         'verilog-a', 'open-licence', 'green',
         'Verilog-AMS is an Accellera standard (LRM 2.4.0) built on '
         'IEEE 1364; using the language to write our own models '
         'carries no licence obligation (the LRM document copyright '
         'is Accellera\'s; the language is open).',
         _OWN_CODE,
         'none.',
         licence='Accellera / IEEE standard (open use)',
         what_we_own='cnt_verilog_a.py emitted .va — GPLv3',
         sources=['https://www.accellera.org/downloads/standards/v-ams'],
         confidence='verified'),
]

SEED_BY_NAME = {s['name']: s for s in SEED_TECHNOLOGY_IP}


# ── rows ───────────────────────────────────────────────────────────

_ROW_FIELDS = tuple(SEED_TECHNOLOGY_IP[0].keys())


def _rows_from_manager(manager, class_name):
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        class_name) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def ip_records(manager=None):
    """name -> record dict (manager rows win over seeds so a page
    edit — a new patent found, a verdict changed — is live)."""
    out = {}
    for row in _rows_from_manager(manager, 'TechnologyIPRecord'):
        name = getattr(row, 'name', '')
        if name:
            out[name] = {k: getattr(row, k, None) for k in _ROW_FIELDS}
    for name, seed in SEED_BY_NAME.items():
        out.setdefault(name, dict(seed))
    return out


def record_payload(rec):
    """A record with its JSON columns decoded and its gate text."""
    r = dict(rec)
    r['key_patents'] = json.loads(r.get('key_patents_json') or '[]')
    r['sources'] = json.loads(r.get('sources_json') or '[]')
    r['gate'] = ip_gate(r['verdict'])
    return r


def ip_gate(verdict):
    """The suite's licence-gate vocabulary for a verdict."""
    return {'verdict': verdict, 'rank': VERDICT_RANK.get(verdict, 2),
            'meaning': VERDICT_GATE.get(verdict, VERDICT_GATE['red']),
            'blocker': verdict == 'red'}


def worst_verdict(verdicts):
    vs = [v for v in verdicts if v in VERDICT_RANK]
    if not vs:
        return 'green'
    return max(vs, key=lambda v: VERDICT_RANK[v])


# ── subject resolution ─────────────────────────────────────────────

SHAPE_RECORDS = {
    'planar-bulk': ['mosfet-generic', 'cmos', 'planar-process'],
    'soi': ['mosfet-generic', 'cmos', 'planar-process', 'soi'],
    'finfet': ['mosfet-generic', 'cmos', 'finfet'],
    'gaa-nanowire': ['mosfet-generic', 'cmos', 'gaa-nanowire'],
    'gaa-nanosheet': ['mosfet-generic', 'cmos', 'gaa-nanosheet'],
    'cnt-gaa': ['cnt-fet-basic', 'cnt-aligned-array-process'],
    'tfet': ['tfet'],
}

CELL_EXTRA_RECORDS = {'cfa': ['mirror-adder'], 'clatch': ['tg-latch'],
                      'cdff': ['tg-latch']}


def _dielectric_row(manager, device):
    """The device's dielectric row (sifet SolGelDielectric by name) or
    the CNT gate stack; returns (kind, material) with kind in
    thermal | sol-gel | ald | unknown."""
    name = getattr(device, 'dielectric', None)
    if name:
        for row in _rows_from_manager(manager, 'SolGelDielectric'):
            if getattr(row, 'name', '') == name:
                pre = str(getattr(row, 'precursor', '')).lower()
                mat = getattr(row, 'material', '')
                if 'thermal' in pre:
                    return 'thermal', mat
                return 'sol-gel', mat
        return 'unknown', name
    gs = getattr(device, 'gate_stack', None)
    if gs:
        for row in _rows_from_manager(manager, 'GateStack'):
            if getattr(row, 'name', '') == gs:
                return 'ald', getattr(row, 'dielectric_material', '')
    return 'unknown', ''


def subjects_for_device(manager, device):
    """[{record, why}] — every IP record that governs this device:
    shape (cnt_taxonomy.shape_of), material, dielectric, model."""
    recs = ip_records(manager)
    picked = []

    def add(name, why):
        if name in recs and all(p['record']['name'] != name
                                for p in picked):
            picked.append({'record': recs[name], 'why': why})

    shape = shape_of(device, manager)
    if shape.get('ok'):
        for n in SHAPE_RECORDS.get(shape['shape'], []):
            add(n, f'shape {shape["shape"]} ({shape["how"]})')
    material = str(getattr(device, 'material', '') or '')
    cls = type(device).__name__
    if cls == 'AlignedCNTFETDevice' or material.startswith('cnt'):
        add('cnt-fet-basic', f'material {material or "CNT"}')
        add('cnt-aligned-array-process', 'aligned-array process line')
    elif cls == 'SiliconMOSFET' or getattr(device, 'channel_doping',
                                           None):
        add('mosfet-generic', 'silicon MOSFET')
        add('cmos', 'complementary silicon logic')
    kind, mat = _dielectric_row(manager, device)
    if kind == 'sol-gel':
        add('sol-gel-dielectric-generic', f'sol-gel {mat} dielectric')
        if str(mat).lower() in ('hfo2', 'zro2'):
            add('sol-gel-hfo2-formulations',
                f'sol-gel high-k ({mat}) formulation')
    add('vs-compact-model', 'model that produces its curves')
    out = {'ok': True, 'device': getattr(device, 'name', ''),
           'shape': shape.get('shape'), 'dielectric': {'kind': kind,
                                                       'material': mat},
           'subjects': picked}
    if not shape.get('ok'):
        out['shape_refusal'] = shape
    return out


def subjects_for_cell(manager, cell_key):
    recs = ip_records(manager)
    names = ['standard-cells'] + CELL_EXTRA_RECORDS.get(cell_key, [])
    return [{'record': recs[n], 'why': f'cell {cell_key}'}
            for n in names if n in recs]


def _find_device(manager, device_name):
    for cls in ('AlignedCNTFETDevice', 'SiliconMOSFET'):
        for row in _rows_from_manager(manager, cls):
            if getattr(row, 'name', '') == device_name:
                return row
    return None


# ── reports ────────────────────────────────────────────────────────

def _summarise(records):
    payloads = [record_payload(r) for r in records]
    worst = worst_verdict([p['verdict'] for p in payloads])
    verify = []
    for p in payloads:
        v = (p.get('verify_next') or '').strip()
        if v and not v.lower().startswith(('none', 'nothing')) \
                and v not in verify:
            verify.append(f'{p["name"]}: {v}')
    return payloads, worst, verify


def _self_manufacture_answer(payloads, worst):
    active = [p['display_name'] for p in payloads
              if p['ip_kind'] in ('patent-active', 'patent-mixed')]
    expired = [p['display_name'] for p in payloads
               if p['ip_kind'] in ('patent-expired', 'public-domain')]
    secret = [p['display_name'] for p in payloads
              if p['ip_kind'] == 'trade-secret']
    parts = []
    if expired:
        parts.append('Expired / public-domain pieces (' +
                     ', '.join(expired) + '): building them yourself '
                     'needs no permission from anyone.')
    if active:
        parts.append('Pieces with active or unsearched claims (' +
                     ', '.join(active) + '): making your own does NOT '
                     'clear them — a patent excludes MAKING as much as '
                     'selling (35 U.S.C. 271(a)); you would need the '
                     'claim to be expired, invalid, licensed, or '
                     'designed around.')
    if secret:
        parts.append('Trade-secret know-how (' + ', '.join(secret) +
                     '): independent re-derivation is lawful; the cost '
                     'is that the open route may not reach the '
                     'industrial endpoint.')
    parts.append('Software/design files you write yourself carry no '
                 'third-party licence obligation (ours are GPLv3).')
    parts.append(f'Net: {VERDICT_GATE[worst]}.')
    return ' '.join(parts)


def device_ip_report(manager, device_name):
    device = _find_device(manager, device_name)
    if device is None:
        return {'ok': False, 'device': device_name,
                'error': f'no AlignedCNTFETDevice / SiliconMOSFET row '
                         f'named "{device_name}"',
                'affordance': 'seed or POST the device row first',
                'disclaimer': DISCLAIMER}
    subj = subjects_for_device(manager, device)
    payloads, worst, verify = _summarise(
        [s['record'] for s in subj['subjects']])
    for p, s in zip(payloads, subj['subjects']):
        p['why'] = s['why']
    reds = [p['display_name'] for p in payloads if p['verdict'] == 'red']
    ambers = [p['display_name'] for p in payloads
              if p['verdict'] == 'amber']
    summary = (f'{device_name}: {len(payloads)} governing records; '
               f'worst verdict {worst}'
               + (f' — blockers: {", ".join(reds)}' if reds else '')
               + (f' — verify before commercial use: '
                  f'{", ".join(ambers)}' if ambers else '')
               + ('' if (reds or ambers) else
                  ' — every governing patent expired / public domain '
                  'and every tool licence GPLv3-compatible'))
    return {
        'ok': True, 'device': device_name,
        'shape': subj.get('shape'), 'dielectric': subj['dielectric'],
        'records': payloads,
        'worst_verdict': worst, 'gate': ip_gate(worst),
        'summary': summary,
        'self_manufacture_answer': _self_manufacture_answer(payloads,
                                                            worst),
        'verify_next': verify,
        'reviewed_at': REVIEWED_AT,
        'disclaimer': DISCLAIMER,
    }


def cell_ip_report(manager, cell_key):
    subj = subjects_for_cell(manager, cell_key)
    payloads, worst, verify = _summarise([s['record'] for s in subj])
    return {'ok': True, 'cell': cell_key, 'records': payloads,
            'worst_verdict': worst, 'gate': ip_gate(worst),
            'verify_next': verify, 'disclaimer': DISCLAIMER}


STEP_RECORDS = {
    'siemens-tcs': 'siemens-tcs', 'fbr-silane': 'fbr-silane',
    'directional-solidification': 'directional-solidification',
    'zone-refining': 'zone-refining',
    'float-zone-growth': 'zone-refining',
}


def route_ip_report(manager, route_name):
    """A refinement route's verdict = the worst of its steps' records
    (steps with no record are treated as open-literature green and
    listed as such)."""
    recs = ip_records(manager)
    route = None
    for row in _rows_from_manager(manager, 'RefinementRoute'):
        if getattr(row, 'name', '') == route_name:
            route = row
            break
    if route is None:
        try:
            from sifet.si_refinement import SEED_REFINEMENT_ROUTES
            route = next((r for r in SEED_REFINEMENT_ROUTES
                          if r['name'] == route_name), None)
            if route is not None:
                route = type('R', (), route)()
        except ImportError:
            route = None
    if route is None:
        return {'ok': False, 'route': route_name,
                'error': f'no RefinementRoute "{route_name}"',
                'disclaimer': DISCLAIMER}
    steps = json.loads(getattr(route, 'steps_json', '[]') or '[]')
    per_step, records = [], []
    for st in steps:
        rname = STEP_RECORDS.get(st)
        if rname and rname in recs:
            rec = recs[rname]
            per_step.append({'step': st, 'record': rname,
                             'verdict': rec['verdict']})
            if rec not in records:
                records.append(rec)
        else:
            per_step.append({'step': st, 'record': None,
                             'verdict': 'green',
                             'why': 'open-literature metallurgy; no '
                                    'record (no claim known)'})
    payloads, worst, verify = _summarise(records)
    return {'ok': True, 'route': route_name,
            'openness': getattr(route, 'openness', ''),
            'steps': per_step, 'records': payloads,
            'worst_verdict': worst, 'gate': ip_gate(worst),
            'verify_next': verify, 'disclaimer': DISCLAIMER}


def library_ip_report(manager):
    """Every device + every cell + every refinement route + tools/
    formats, each with its worst verdict; plus the full record table."""
    recs = ip_records(manager)
    devices = []
    for cls in ('AlignedCNTFETDevice', 'SiliconMOSFET'):
        for row in _rows_from_manager(manager, cls):
            rep = device_ip_report(manager, row.name)
            devices.append({'device': row.name, 'class': cls,
                            'shape': rep.get('shape'),
                            'worst_verdict': rep['worst_verdict'],
                            'records': [r['name'] for r in
                                        rep['records']]})
    try:
        from cntfet.cnt_cell_library import CELL_LIBRARY
        cell_keys = sorted(CELL_LIBRARY) + (
            ['cdff'] if 'cdff' not in CELL_LIBRARY else [])
    except ImportError:
        cell_keys = []
    cells = []
    for key in cell_keys:
        rep = cell_ip_report(manager, key)
        cells.append({'cell': key, 'worst_verdict': rep['worst_verdict'],
                      'records': [r['name'] for r in rep['records']]})
    route_names = [getattr(r, 'name', '') for r in
                   _rows_from_manager(manager, 'RefinementRoute')]
    if not route_names:
        try:
            from sifet.si_refinement import SEED_REFINEMENT_ROUTES
            route_names = [r['name'] for r in SEED_REFINEMENT_ROUTES]
        except ImportError:
            route_names = []
    routes = []
    for rn in route_names:
        rep = route_ip_report(manager, rn)
        if rep.get('ok'):
            routes.append({'route': rn, 'openness': rep['openness'],
                           'worst_verdict': rep['worst_verdict'],
                           'steps': rep['steps']})
    tools = [record_payload(r) for r in recs.values()
             if r['subject_kind'] in ('tool', 'format', 'model')]
    table = [record_payload(r) for r in recs.values()]
    counts = {v: sum(1 for r in table if r['verdict'] == v)
              for v in VERDICT_RANK}
    everything = ([d['worst_verdict'] for d in devices]
                  + [c['worst_verdict'] for c in cells]
                  + [r['worst_verdict'] for r in routes]
                  + [t['verdict'] for t in tools])
    return {
        'ok': True, 'reviewed_at': REVIEWED_AT,
        'devices': devices, 'cells': cells, 'routes': routes,
        'tools': tools, 'records': table,
        'verdict_counts': counts,
        'worst_verdict': worst_verdict(everything),
        'gate_vocabulary': {v: ip_gate(v) for v in VERDICT_RANK},
        'unverified': [r['name'] for r in table
                       if r['confidence'] == 'unverified'],
        'make_your_own_rule': MAKE_YOUR_OWN_RULE,
        'disclaimer': DISCLAIMER,
    }


# ── long-form rows + graph seed ────────────────────────────────────

def ip_verdict_rows(manager, device):
    """Categorical x = record display name, y = verdict rank 0/1/2
    (label carries the word); one series per confidence."""
    rep = device_ip_report(manager, getattr(device, 'name', device))
    if not rep.get('ok'):
        return []
    rows = []
    for r in rep['records']:
        rows.append({'series': r['confidence'], 'style': 'dot',
                     'dash': False, 'x': r['display_name'],
                     'y': VERDICT_RANK[r['verdict']],
                     'label': f'{r["verdict"]} ({r["ip_kind"]})'})
    return rows


def _build_ip_verdicts(id_fn, p, device, manager, knobs):
    return ip_verdict_rows(manager, device)


CURVE_BUILDERS = {'ip-verdicts': _build_ip_verdicts}

SEED_CNT_IP_GRAPHS = [{
    'name': 'cnt-device-ip-verdicts',
    'description': 'IP / FTO verdict per governing record for the '
                   'device (0 = green proceed, 1 = amber verify before '
                   'commercial, 2 = red blocker); series = evidence '
                   'confidence. ' + DISCLAIMER +
                   ' — data: /api/cntfet/device/{name}/points?curve='
                   'ip-verdicts',
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
                    'yLabel': 'verdict (0 green / 1 amber / 2 red)',
                    'yType': 'linear',
                    'yTickLabels': {'0': 'green', '1': 'amber',
                                    '2': 'red'}},
        'aggregation': None,
    }}),
}]
