"""
@module sifet.si_ladder

The OPEN-SILICON FET LADDER (Dustin 2026-08-30): which silicon
process nodes can we LEGITIMATELY reconstruct from public / openly
licensed material, and how well proven is each one?

Two INDEPENDENT axes on every rung — never collapsed:
  * `rights_class`        — what we may DO with it (licence / IP)
  * `fabrication_evidence` — how real the numbers are (measured die
                             ... hypothetical)
A node can be legally clean AND physically predictive (ASAP7) while an
older node has stronger real-silicon evidence (a measured 90 nm die).
`manufacturable` is a THIRD, evidence-only flag: True only when an
actually available open process exists (today: none — every rung says
so and why). An open predictive PDK never implies manufacturability.

Decision S1 = FreePDK45 (NC State, Apache-2.0): the best rung that is
BOTH rights-clean and calibrated against published silicon. Our own
VS-parameterised device (`si-nmos-freepdk45-class`, sifet.si_basis)
is CALIBRATED AGAINST the FreePDK45 documented numbers — we never
incorporate the FreePDK45 BSIM4 card itself; the anchors + the gap
report (`compare_to_anchors`) are the honesty surface.

Licence facts recorded here were fetched on LADDER_REVIEWED_AT (see
each row's source_url / `licence_verified`); PTM's terms could not be
fetched (ptm.asu.edu unreachable that day) → 'to-verify', never
assumed. GPLv3 direction: Apache-2.0 and BSD-3-Clause are ONE-WAY
compatible INTO a GPLv3 project (their material may be combined into
GPLv3 work; the combined work is GPLv3). NC / research-only terms are
a hard blocker per the suite licence gate.

@consumers
  - polariServer (SiliconProcessNode registration + seeds; the
    anchors into CNTCalibrationAnchor; SEED_LADDER_EVIDENCE into
    EvidenceItem; SEED_LADDER_IP into TechnologyIPRecord;
    SEED_SI_LADDER_GRAPHS into GraphDefinition) — to be wired
  - cntfet.cnt_api (GET /api/sifet/ladder → ladder_report) — to be wired
  - sifet.selftest_ladder
"""

import json
import math

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_metrics import extract_metrics
from sifet.si_device import (
    derive_si_device, frame_aware_id_fn, get_row, metric_spec,
    params_from_rows, resolve_components,
)
from sifet import si_model as sm

LADDER_REVIEWED_AT = '2026-08-30'
LADDER_REVISION = 'sifet-ladder-r1'

# ── the two axes (+ the evidence-only manufacturability flag) ──────

FABRICATION_EVIDENCE = {
    'measured-fabricated-device': 'numbers come from a physically '
        'fabricated device that was measured and published (IEDM / '
        'VLSI / JSSC die data)',
    'reconstructed-from-published-silicon': 'no card or die of our own; '
        'the device is re-derived from PUBLISHED process physics '
        '(dimensions, materials, doping, EOT) and compared to '
        'published measurements',
    'calibrated-predictive': 'a predictive model whose authors tuned '
        'it against published silicon of that node (FreePDK45 ← '
        'Fujitsu IEDM 2007 via PTM; PTM ← early silicon data)',
    'predictive-only': 'a predictive PDK / model with NO tie to a '
        'measured device of that node (ASAP7: assumptions for 7 nm, '
        'no foundry)',
    'hypothetical': 'extrapolated by us or others beyond any '
        'published calibration',
}
#: evidence strength order (higher = better proven)
FABRICATION_RANK = {
    'hypothetical': 0, 'predictive-only': 1, 'calibrated-predictive': 2,
    'reconstructed-from-published-silicon': 3,
    'measured-fabricated-device': 4,
}
# legacy names kept for the brief's vocabulary → new field name
FABRICATION_MATURITY = {
    'measured-silicon': 'measured-fabricated-device',
    'reconstructed-published-process': 'reconstructed-from-published-silicon',
    'predictive-model': 'calibrated-predictive | predictive-only',
    'hypothetical-extrapolated': 'hypothetical',
}

RIGHTS_CLASS = {
    'incorporable-open': 'artefact carries a VERIFIED open licence we '
        'may combine into the GPLv3 tree (Apache-2.0 / BSD-3 are one-'
        'way compatible INTO GPLv3)',
    'clean-room-reconstructable': 'no artefact to incorporate, but '
        'enough PUBLISHED physics/numbers to derive our own model '
        'without reading anyone\'s card or code',
    'reference-oracle': 'published numbers we may CITE and compare '
        'against; not enough public detail (doping / work-function / '
        'curves) to instantiate a defensible model ourselves',
    'encumbered': 'NC / research-only / proprietary terms or an active '
        'claim — a hard blocker per the suite licence gate',
    'unresolved': 'licence or provenance not yet verified — treated as '
        'reference-only until it is',
}
OPENNESS_CLASS = {   # brief vocabulary → rights_class
    'incorporable-model': 'incorporable-open',
    'clean-room-reconstructable': 'clean-room-reconstructable',
    'oracle-only': 'reference-oracle',
    'encumbered': 'encumbered',
}
RIGHTS_CLEAN = ('incorporable-open', 'clean-room-reconstructable')
EVIDENCE_REAL = ('measured-fabricated-device',
                 'reconstructed-from-published-silicon',
                 'calibrated-predictive')

MANUFACTURABLE_RULE = ('manufacturable is True ONLY with evidence of an '
                       'actually available open process (an MPW / '
                       'foundry that accepts the rules). An open '
                       'predictive PDK is NOT such evidence. Today: '
                       'no rung qualifies.')

#: What "enough public information to instantiate a model" means —
#: the search protocol, as data (FET_LADDER_PLAN.md §5).
SEARCH_PROTOCOL = ('dimensions', 'materials', 'doping-or-work-function',
                   'eot', 'measured-id-vg-id-vd', 'capacitance',
                   'variability', 'temperature')


class SiliconProcessNode(treeObject):
    """One rung of the open-silicon ladder: a process node as a row
    with its two independent axes, the licence facts, the numbers we
    may use (each with its own source) and what we must NOT assume."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        node_nm: float = 0.0,
        architecture: str = 'planar-bulk',   # planar-bulk|finfet|tri-gate|soi
        vdd_v: float = 1.0,
        source: str = 'literature',   # FreePDK45|PTM|ASAP7|FreePDK15|literature|polari-model
        source_url: str = '',
        licence: str = '',            # SPDX; '' when none applies
        licence_verified: bool = False,
        licence_gplv3_compatible: str = 'to-verify',   # yes|no|to-verify
        rights_class: str = 'unresolved',
        fabrication_evidence: str = 'hypothetical',
        manufacturable=None,          # bool | None (evidence-only)
        manufacturable_reason: str = '',
        model_family: str = '',       # BSIM4|BSIM-CMG|VS|none
        key_numbers_json: str = '{}',
        what_we_can_use: str = '',
        what_we_must_not_assume: str = '',
        search_json: str = '{}',      # per SEARCH_PROTOCOL: have/missing
        evidence_json: str = '[]',    # EvidenceItem names
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.node_nm = node_nm
        self.architecture = architecture
        self.vdd_v = vdd_v
        self.source = source
        self.source_url = source_url
        self.licence = licence
        self.licence_verified = licence_verified
        self.licence_gplv3_compatible = licence_gplv3_compatible
        self.rights_class = rights_class
        self.fabrication_evidence = fabrication_evidence
        self.manufacturable = manufacturable
        self.manufacturable_reason = manufacturable_reason
        self.model_family = model_family
        self.key_numbers_json = key_numbers_json
        self.what_we_can_use = what_we_can_use
        self.what_we_must_not_assume = what_we_must_not_assume
        self.search_json = search_json
        self.evidence_json = evidence_json
        self.notes = notes
        self.is_prior = is_prior


# ── sources (URLs fetched 2026-08-30) ─────────────────────────────

URL_FREEPDK45 = 'https://eda.ncsu.edu/freepdk/freepdk45/'
URL_FREEPDK15 = 'https://eda.ncsu.edu/freepdk/freepdk15/'
URL_ASAP7 = 'https://github.com/The-OpenROAD-Project/asap7'
URL_ASAP7_LIC = ('https://raw.githubusercontent.com/The-OpenROAD-Project/'
                 'asap7/master/LICENSE')
URL_PTM = 'http://ptm.asu.edu/'
URL_PTM45_MIRROR = ('https://github.com/verilog-to-routing/vtr-verilog-to-'
                    'routing/blob/master/vtr_flow/tech/PTM_45nm/45nm.pm')
URL_BSIM4 = 'https://bsim.berkeley.edu/models/bsim4/'
URL_BSIMCMG = 'https://bsim.berkeley.edu/models/bsimcmg/'
DOI_FREEPDK = '10.1109/MSE.2007.44'
DOI_PTM = '10.1109/TED.2006.884077'
DOI_ASAP7 = '10.1016/j.mejo.2016.04.006'


def _num(value, unit, source, note=''):
    d = {'value': value, 'unit': unit, 'source': source}
    if note:
        d['note'] = note
    return d


def _search(have, missing, where=''):
    """search_json: which SEARCH_PROTOCOL items exist publicly,
    which are missing, and what to search next."""
    assert set(have) <= set(SEARCH_PROTOCOL) and \
        set(missing) <= set(SEARCH_PROTOCOL), (have, missing)
    return json.dumps({'have': list(have), 'missing': list(missing),
                       'enough_for_own_model': not missing,
                       'search_next': where,
                       'protocol': list(SEARCH_PROTOCOL)})


def _node(name, display_name, node_nm, architecture, vdd_v, source,
          source_url, licence, licence_verified, gplv3, rights,
          evidence, manufacturable, manufacturable_reason, model_family,
          key_numbers, what_we_can_use, what_we_must_not_assume,
          search, evidence_items, notes):
    assert rights in RIGHTS_CLASS, rights
    assert evidence in FABRICATION_EVIDENCE, evidence
    assert gplv3 in ('yes', 'no', 'to-verify'), gplv3
    assert manufacturable in (True, False, None)
    if manufacturable is True:
        raise AssertionError(MANUFACTURABLE_RULE)   # no rung qualifies
    return {
        'name': name, 'display_name': display_name, 'node_nm': node_nm,
        'architecture': architecture, 'vdd_v': vdd_v, 'source': source,
        'source_url': source_url, 'licence': licence,
        'licence_verified': bool(licence_verified),
        'licence_gplv3_compatible': gplv3, 'rights_class': rights,
        'fabrication_evidence': evidence,
        'manufacturable': manufacturable,
        'manufacturable_reason': manufacturable_reason,
        'model_family': model_family,
        'key_numbers_json': json.dumps(key_numbers),
        'what_we_can_use': what_we_can_use,
        'what_we_must_not_assume': what_we_must_not_assume,
        'search_json': search,
        'evidence_json': json.dumps(list(evidence_items)),
        'notes': notes, 'is_prior': True,
    }


_NO_OPEN_PROCESS = ('no openly available process accepts these rules — '
                    + MANUFACTURABLE_RULE)
_FPDK45_SRC = f'FreePDK45 documentation v1.4 (2011-04-07), {URL_FREEPDK45}'
_PTM45_SRC = ('PTM 45 nm HP card ("PTM High Performance 45nm Metal Gate / '
              f'High-K / Strained-Si", Vdd 1.0 V), mirror {URL_PTM45_MIRROR}')

SEED_SILICON_PROCESS_NODES = [
    _node('polari-si-90-class', 'Polari 90 nm-class planar (our rows)',
          90.0, 'planar-bulk', 1.0, 'polari-model',
          'sifet.si_basis (si-nmos-planar-90 / si-pmos-planar-90)',
          'GPL-3.0-or-later', True, 'yes', 'clean-room-reconstructable',
          'reconstructed-from-published-silicon', False,
          'our own composition of textbook process physics; no process '
          'exists that builds it — ' + MANUFACTURABLE_RULE, 'VS',
          {'lg_nm': _num(90.0, 'nm', 'si_basis row'),
           'eot_nm': _num(2.0, 'nm', 'thermal-sio2-2nm row ([SZE07])'),
           'vt_v': _num(None, 'V', 'DERIVED by derive_si_device from '
                        'doping + Vfb prior ([SZE07] eq.6.28)'),
           'ion_ua_per_um': _num(None, 'uA/um',
                                 'DERIVED (extract_metrics at 1 V)'),
           'ioff_na_per_um': _num(None, 'nA/um',
                                  'DERIVED (extract_metrics at 1 V)')},
          'everything — it is ours (GPLv3): Vt from doping/Vfb, Cox, '
          'Caughey-Thomas mu, v_xo, scale length ([SZE07]/[TN09]/'
          '[KHA09]).',
          'that it matches any measured 90 nm die: NO anchor row exists '
          'for a published 90 nm device yet — the numbers are textbook '
          'physics, not a measurement (fabrication_evidence says '
          'reconstructed, and the reconstruction is un-anchored).',
          _search(['dimensions', 'materials', 'eot', 'temperature'],
                  ['doping-or-work-function', 'measured-id-vg-id-vd',
                   'capacitance', 'variability'],
                  'a published 90 nm bulk NMOS/PMOS with Id-Vg/Id-Vd '
                  'figures (e.g. IEDM 2002-2003 90 nm logic papers) to '
                  'digitize as anchors like fc10-vxo-lg15'),
          ['book-sze-ng-2007', 'book-taur-ning-2009', 'pub-KHA09',
           'pub-CT67'],
          'THE current reference rows. Rights-clean by construction; '
          'evidence axis is the weaker one.'),
    _node('lit-65-planar', '65 nm planar bulk (literature)', 65.0,
          'planar-bulk', 1.2, 'literature', '', '', False, 'to-verify',
          'reference-oracle', 'measured-fabricated-device', False,
          'foundry processes of 2005 — proprietary; ' + _NO_OPEN_PROCESS,
          'none',
          {'lg_nm': _num(35.0, 'nm', 'TO VERIFY: Intel 65 nm, Bai et al. '
                         'IEDM 2004 (35 nm Lg, 1.2 nm SiON)'),
           'ion_ua_per_um': _num(None, 'uA/um', 'TO SEARCH: published '
                                 'NMOS/PMOS Idsat at 1.2 V, 100 nA/um')},
          'published headline numbers as ORACLE anchors (cite + compare) '
          'once verified; the PTM 65 nm card as a second oracle.',
          'doping / halo / work-function — never published; do not '
          'invent a doping row and call it 65 nm.',
          _search(['dimensions', 'materials', 'eot'],
                  ['doping-or-work-function', 'measured-id-vg-id-vd',
                   'capacitance', 'variability', 'temperature'],
                  'Bai et al., "A 65nm logic technology featuring 35nm '
                  'gate lengths, enhanced channel strain ...", IEDM 2004 '
                  '(verify DOI); PTM 65nm_HP card; a 65 nm Id-Vg figure '
                  'to digitize'),
          [], 'oracle-only placeholder: what to search is in search_json.'),
    _node('freepdk45', 'FreePDK45 (NC State, 45 nm generic PDK)', 45.0,
          'planar-bulk', 1.0, 'FreePDK45', URL_FREEPDK45, 'Apache-2.0',
          True, 'yes', 'incorporable-open', 'calibrated-predictive',
          False, 'generic, not a foundry process: "FreePDK45 is a '
          'generic 45 nm PDK" — no MPW or foundry accepts its rules; '
          + MANUFACTURABLE_RULE, 'BSIM4',
          {'ion_ua_per_um': _num(975.5, 'uA/um', _FPDK45_SRC,
                                 'VTG NMOS, nominal corner, 1.0 V'),
           'ioff_na_per_um': _num(10.0, 'nA/um', _FPDK45_SRC, 'VTG NMOS'),
           'ion_lowvt_ua_per_um': _num(1246.0, 'uA/um', _FPDK45_SRC,
                                       'VTL NMOS, Ioff 100 nA/um'),
           'ioff_lowvt_na_per_um': _num(100.0, 'nA/um', _FPDK45_SRC),
           'ion_highvt_ua_per_um': _num(570.0, 'uA/um', _FPDK45_SRC,
                                        'VTH NMOS, Ioff 0.2 nA/um'),
           'pmos_ion_ua_per_um': _num(650.3, 'uA/um', _FPDK45_SRC,
                                      'VTG PMOS (documented as -650.3)'),
           'pmos_ioff_na_per_um': _num(10.0, 'nA/um', _FPDK45_SRC),
           'pmos_ion_lowvt_ua_per_um': _num(801.0, 'uA/um', _FPDK45_SRC),
           'lg_drawn_nm': _num(50.0, 'nm', _FPDK45_SRC,
                               'POLY.1 minimum poly width'),
           'lg_nm': _num(45.0, 'nm', _FPDK45_SRC, '"it is assumed that '
                         'the actual gate length is 45nm"'),
           'eot_nm': _num(1.25, 'nm', _PTM45_SRC, 'toxe (electrical) '
                          '1.25 nm NMOS / 1.30 nm PMOS; toxp 1.0 nm'),
           'vt_v': _num(0.469, 'V', _PTM45_SRC, 'vth0 NMOS 0.46893 V; '
                        'PMOS -0.49158 V'),
           'ndep_cm3': _num(3.24e18, 'cm^-3', _PTM45_SRC,
                            'NMOS ndep; PMOS 2.44e18'),
           'vdd_v': _num(1.0, 'V', _FPDK45_SRC)},
          'device numbers + design rules as CALIBRATION ANCHORS for OUR '
          'VS-parameterised device (si-nmos-freepdk45-class) and as the '
          'rung the cell layer characterizes; the PDK itself (rules, '
          'cells, decks) is Apache-2.0 and may be incorporated one-way '
          'into the GPLv3 tree with its NOTICE — but the BSIM4 card is '
          'NOT our model; we compare against it, we do not ship it as '
          'ours.',
          'that FreePDK45 is a fab: it is "generic"; that the PTM card '
          'equals a Fujitsu die: FreePDK45 says its models were "tuned '
          'according to the Bulk-Si, poly-gate technology from Fujitsu" '
          '(Miyashita et al. IEDM 2007) while the PTM 45 nm HP header '
          'says metal gate / high-k — the stack is a PREDICTIVE blend, '
          'so fabrication_evidence is calibrated-predictive, not '
          'measured.',
          _search(['dimensions', 'materials', 'doping-or-work-function',
                   'eot', 'temperature'],
                  ['measured-id-vg-id-vd', 'capacitance', 'variability'],
                  'Miyashita et al. IEDM 2007 pp.251-254 (the silicon '
                  'PTM was tuned to) for measured curves; FreePDK45 '
                  'variation files for variability'),
          ['lic-apache-2.0', 'pub-FreePDK45', 'pub-PTM', 'pub-BSIM4',
           'std-bsim4'],
          'S1 DECISION rung. Licence text: FreePDK45 docs — "This '
          'information may be freely used, modified, and distributed '
          'under the open-source Apache License (see the file '
          'APACHE-LICENSE-2.0.txt in the root install directory)". '
          'Apache-2.0 → GPLv3: one-way compatible (FSF).'),
    _node('lit-45-planar', '45 nm planar HKMG (literature)', 45.0,
          'planar-bulk', 1.0, 'literature', '', '', False, 'to-verify',
          'reference-oracle', 'measured-fabricated-device', False,
          'foundry processes of 2007 — proprietary; ' + _NO_OPEN_PROCESS,
          'none',
          {'ion_ua_per_um': _num(None, 'uA/um', 'TO VERIFY: Intel 45 nm '
                                 'HKMG, Mistry et al. IEDM 2007 (NMOS/'
                                 'PMOS Idsat at 1.0 V, 100 nA/um)'),
           'eot_nm': _num(None, 'nm', 'TO VERIFY: ~1.0 nm EOT (Mistry '
                          '2007)')},
          'the measured-silicon oracle FreePDK45 should be judged '
          'against (same node, real die).',
          'doping / work-function / strain recipe — trade secret.',
          _search(['dimensions', 'materials', 'eot'],
                  ['doping-or-work-function', 'measured-id-vg-id-vd',
                   'capacitance', 'variability', 'temperature'],
                  'Mistry et al., "A 45nm logic technology with high-k+'
                  'metal gate transistors ...", IEDM 2007; Miyashita et '
                  'al. IEDM 2007 (Fujitsu)'),
          [], 'oracle-only placeholder.'),
    _node('ptm32', 'PTM 32 nm HP (ASU predictive bulk)', 32.0,
          'planar-bulk', 0.9, 'PTM', URL_PTM, '', False, 'to-verify',
          'unresolved', 'calibrated-predictive', False,
          'a model card, not a process; ' + _NO_OPEN_PROCESS, 'BSIM4',
          {'lg_nm': _num(32.0, 'nm', 'PTM 32nm_HP card (TO VERIFY '
                         'values: site unreachable 2026-08-30)'),
           'error_vs_silicon': _num('<10 %', '1', f'doi:{DOI_PTM} '
                                    '(Zhao & Cao 2006 abstract claim, '
                                    '130-32 nm) — TO VERIFY on the PDF')},
          'as an ORACLE: run the PTM card in ngspice locally to compare '
          'curves; cite [PTM]. Redistribution / incorporation NOT until '
          'the terms are read.',
          'that PTM is "open source": the site states users "agree to '
          'acknowledge this URL and related publications" (search '
          'snippet, unverified) — an acknowledgment condition, no SPDX '
          'licence found; do not vendor the cards.',
          _search(['dimensions', 'materials', 'doping-or-work-function',
                   'eot', 'temperature'],
                  ['measured-id-vg-id-vd', 'capacitance', 'variability'],
                  'fetch ptm.asu.edu terms verbatim; 32nm_HP.pm header; '
                  'Zhao & Cao TED 2006 Fig. comparisons to silicon'),
          ['pub-PTM', 'pub-BSIM4', 'std-bsim4'],
          'rights UNRESOLVED (terms not fetched); evidence calibrated-'
          'predictive per the TED 2006 claim. Becomes reference-oracle '
          'or incorporable-open only after the terms are read.'),
    _node('lit-32-planar', '32/28 nm planar HKMG (literature)', 32.0,
          'planar-bulk', 1.0, 'literature', '', '', False, 'to-verify',
          'reference-oracle', 'measured-fabricated-device', False,
          'foundry processes of 2009 — proprietary; ' + _NO_OPEN_PROCESS,
          'none',
          {'ion_ua_per_um': _num(None, 'uA/um', 'TO VERIFY: Intel 32 nm, '
                                 'Natarajan et al. IEDM 2008 (Idsat at '
                                 '1.0 V, 100 nA/um)')},
          'measured oracle for the 32 nm rung.', 'doping / strain recipe.',
          _search(['dimensions', 'materials', 'eot'],
                  ['doping-or-work-function', 'measured-id-vg-id-vd',
                   'capacitance', 'variability', 'temperature'],
                  'Natarajan et al., "A 32nm logic technology featuring '
                  '2nd-generation high-k + metal-gate transistors ...", '
                  'IEDM 2008; 28 nm foundry papers (TSMC/GF VLSI 2010)'),
          [], 'oracle-only placeholder.'),
    _node('lit-22-trigate', '22 nm tri-gate FinFET (literature)', 22.0,
          'tri-gate', 0.8, 'literature', '', '', False, 'to-verify',
          'reference-oracle', 'measured-fabricated-device', False,
          'Intel 22 nm — proprietary; ' + _NO_OPEN_PROCESS, 'none',
          {'fin_pitch_nm': _num(None, 'nm', 'TO VERIFY: Auth et al. VLSI '
                                '2012 (fin pitch 60 nm, Hfin 34 nm)'),
           'ion_ua_per_um': _num(None, 'uA/um', 'TO VERIFY: Auth 2012 '
                                 'Idsat at 0.8 V, 100 nA/um')},
          'measured FinFET oracle; fin geometry feeds our finfet-class '
          'shape row as a PRIOR once verified.',
          'fin doping (undoped?) / work-function metals — unpublished.',
          _search(['dimensions', 'materials'],
                  ['doping-or-work-function', 'eot',
                   'measured-id-vg-id-vd', 'capacitance', 'variability',
                   'temperature'],
                  'Auth et al., "A 22nm high performance and low-power '
                  'CMOS technology featuring fully-depleted tri-gate '
                  'transistors ...", VLSI 2012; PTM-MG 20 nm card'),
          [], 'oracle-only placeholder.'),
    _node('freepdk15', 'FreePDK15 (NC State, 15 nm FinFET)', 15.0,
          'finfet', 0.8, 'FreePDK15', URL_FREEPDK15,
          'BSD-3-Clause AND CC-BY-NC-SA-4.0', True, 'no', 'encumbered',
          'predictive-only', False,
          'predictive kit; ' + _NO_OPEN_PROCESS, 'BSIM-CMG',
          {'node_nm': _num(15.0, 'nm', URL_FREEPDK15)},
          'CITE only. The code files are "open sourced under the New BSD '
          'Licence" but "The Free PDK Design Rule Kit is licensed under '
          'Creative Commons Attribution-NonCommercial-ShareAlike 4.0" and '
          '"commercial use could require a commercial license" — the '
          'NC half is a HARD BLOCKER (suite licence gate).',
          'that the BSD part makes the kit usable: the design-rule kit '
          '(the thing a cell library needs) is NC. Do not vendor any '
          'FreePDK15 file.',
          _search(['dimensions'],
                  ['materials', 'doping-or-work-function', 'eot',
                   'measured-id-vg-id-vd', 'capacitance', 'variability',
                   'temperature'],
                  'nothing to search until NCSU relicenses; PTM-MG '
                  '14/16 nm as the oracle instead'),
          ['lic-cc-by-nc-sa-4.0'],
          'Licence fetched 2026-08-30 from ' + URL_FREEPDK15 + '. '
          'Verdict red.'),
    _node('lit-14-finfet', '14/16 nm FinFET (literature)', 14.0,
          'finfet', 0.7, 'literature', '', '', False, 'to-verify',
          'reference-oracle', 'measured-fabricated-device', False,
          'Intel 14 / TSMC 16 — proprietary; ' + _NO_OPEN_PROCESS, 'none',
          {'fin_pitch_nm': _num(None, 'nm', 'TO VERIFY: Natarajan et al. '
                                'IEDM 2014 (fin pitch 42, Hfin 42, gate '
                                'pitch 70)'),
           'ion_ua_per_um': _num(None, 'uA/um', 'TO VERIFY: IEDM 2014 '
                                 'Idsat at 0.7 V')},
          'measured FinFET oracle for the 14 nm rung; PTM-MG 14 nm card '
          'as a second oracle (same licence caveat as ptm32).',
          'fin doping / WF metals / SiGe channel details.',
          _search(['dimensions', 'materials'],
                  ['doping-or-work-function', 'eot',
                   'measured-id-vg-id-vd', 'capacitance', 'variability',
                   'temperature'],
                  'Natarajan et al., "A 14nm logic technology featuring '
                  '2nd-generation FinFET ...", IEDM 2014; PTM-MG 14nm'),
          [], 'oracle-only placeholder.'),
    _node('asap7', 'ASAP7 (ASU/ARM 7 nm predictive FinFET PDK)', 7.0,
          'finfet', 0.7, 'ASAP7', URL_ASAP7, 'BSD-3-Clause', True, 'yes',
          'incorporable-open', 'predictive-only', False,
          'ASU: predictive, not tied to any foundry; no MPW; cannot tape '
          'out — ' + MANUFACTURABLE_RULE, 'BSIM-CMG',
          {'lg_nm': _num(20.0, 'nm', f'doi:{DOI_ASAP7} (Clark et al. '
                         '2016) — TO VERIFY exact Lg/fin numbers on the '
                         'PDF'),
           'vdd_v': _num(0.7, 'V', f'doi:{DOI_ASAP7} — TO VERIFY'),
           'fin_pitch_nm': _num(27.0, 'nm', f'doi:{DOI_ASAP7} — TO '
                                'VERIFY'),
           'gate_pitch_nm': _num(54.0, 'nm', f'doi:{DOI_ASAP7} — TO '
                                 'VERIFY')},
          'the PDK, cell libraries and BSIM-CMG cards under BSD-3-Clause '
          '("ASAP7 PDK and libraries have a BSD 3-Clause license", '
          'README; LICENSE: "Copyright 2020 Lawrence T. Clark, Vinay '
          'Vashishtha, or Arizona State University") — one-way '
          'compatible into GPLv3. Use: characterize our cells on it, '
          'compare our finfet-class VS device to its cards as an '
          'oracle. It is a RESEARCH AID.',
          'that 7 nm predictive numbers are better proven than a '
          'measured 90 nm die — the two axes: rights clean, evidence '
          'predictive-only (no silicon of this node behind it).',
          _search(['dimensions', 'materials', 'eot', 'capacitance',
                   'variability', 'temperature'],
                  ['doping-or-work-function', 'measured-id-vg-id-vd'],
                  'Clark et al. 2016 §2 device assumptions; no measured '
                  'curves exist by construction'),
          ['lic-bsd-3-clause', 'pub-ASAP7', 'std-bsim-cmg'],
          'PREDICTIVE frontier (rights-clean). Licence fetched '
          '2026-08-30 from ' + URL_ASAP7_LIC + '.'),
]

# ── evidence + IP rows (cnt_evidence / cnt_ip seed shapes) ─────────

_EV_KINDS = ('patent', 'publication', 'textbook', 'standard', 'licence',
             'prior-art')
_EV_PROVES = ('expired', 'active', 'prior-art-before',
              'public-domain-textbook', 'open-licence',
              'proprietary-licence', 'model-source')


def _ev(name, kind, title, parties, ref, date, proves, proves_detail,
        subjects, url='', verified=False, verified_via='',
        licence_bucket='', citation_key='', notes='', role=None,
        role_reason=''):
    """EvidenceItem seed — the exact cnt_evidence._item key set,
    built locally so a helper rename upstream cannot break us."""
    assert kind in _EV_KINDS and proves in _EV_PROVES, (kind, proves)
    if role is None:
        if kind == 'licence':
            role = 'usable' if proves == 'open-licence' else 'reference'
            role_reason = (role_reason or (
                'open licence — our artefacts can carry or depend on it'
                if role == 'usable' else
                'proprietary / NC licence — recorded as a boundary we do '
                'NOT cross, never used'))
        elif kind == 'standard':
            role, role_reason = 'usable', (
                role_reason or 'a model standard we emit/consume in open '
                               'artefacts')
        else:
            role, role_reason = 'reference', (
                role_reason or 'cited to validate our equations, anchors '
                               'and simulations')
    return {
        'name': name, 'kind': kind, 'title': title, 'parties': parties,
        'ref': ref, 'date': date, 'url': url, 'proves': proves,
        'proves_detail': proves_detail, 'expiry': '',
        'jurisdiction': 'US', 'verified': bool(verified),
        'verified_via': verified_via if verified else '',
        'verified_at': LADDER_REVIEWED_AT if verified else '',
        'licence_bucket': licence_bucket,
        'subjects_json': json.dumps(list(subjects)),
        'citation_key': citation_key, 'notes': notes, 'is_prior': True,
        'role': role, 'role_reason': role_reason,
    }


#: `lic-bsd-3-clause` already exists in cnt_evidence.SEED_EVIDENCE
#: (ngspice) — reused by name, NOT re-seeded here.
REUSED_EVIDENCE = ('lic-bsd-3-clause',)

SEED_LADDER_EVIDENCE = [
    _ev('lic-apache-2.0', 'licence', 'Apache License 2.0 (FreePDK45)',
        'NC State EDA / Apache Software Foundation', 'Apache-2.0',
        '2004-01-01', 'open-licence',
        'FreePDK45 docs: "freely used, modified, and distributed under '
        'the open-source Apache License (see APACHE-LICENSE-2.0.txt in '
        'the root install directory)". Apache-2.0 is GPLv3-compatible '
        'ONE-WAY (Apache material may be combined into a GPLv3 work; '
        'the whole is GPLv3) — FSF licence list.',
        ['freepdk45'], url='https://spdx.org/licenses/Apache-2.0.html',
        verified=True, verified_via=URL_FREEPDK45,
        licence_bucket='GPLv3-compatible (one-way, into GPLv3)',
        notes='verify_next: read APACHE-LICENSE-2.0.txt in the '
              'downloaded kit (click-through SVRF agreement noted on '
              'the site — check it does not add terms).'),
    _ev('lic-cc-by-nc-sa-4.0', 'licence',
        'Creative Commons BY-NC-SA 4.0 (FreePDK15 design-rule kit)',
        'NC State EDA / Creative Commons', 'CC-BY-NC-SA-4.0',
        '2013-11-25', 'proprietary-licence',
        'FreePDK15: "The Free PDK Design Rule Kit is licensed under '
        'Creative Commons Attribution-NonCommercial-ShareAlike 4.0"; '
        '"commercial use could require a commercial license" — NC = '
        'HARD BLOCKER (suite licence gate); not in tree.',
        ['freepdk15'], url='https://spdx.org/licenses/CC-BY-NC-SA-4.0.html',
        verified=True, verified_via=URL_FREEPDK15,
        licence_bucket='NOT in tree',
        notes='the code half is New BSD, irrelevant while the rule kit '
              'is NC.'),
    _ev('pub-FreePDK45', 'publication',
        'FreePDK: An Open-Source Variation-Aware Design Kit',
        'Stine, Castellanos, Wood, Henson, Love, Davis, Franzon, Bucher, '
        'Basavarajaiah, Oh, Jenkal (IEEE MSE 2007)', f'doi:{DOI_FREEPDK}',
        '2007-06-03', 'model-source',
        'the FreePDK45 paper; the device numbers used as anchors come '
        'from the v1.4 documentation page (' + URL_FREEPDK45 + ')',
        ['freepdk45'], url=f'https://doi.org/{DOI_FREEPDK}',
        verified=True, verified_via='https://ieeexplore.ieee.org/document/'
                                    '4231502/',
        licence_bucket='cite+link+values (publisher copyright; not CC)',
        citation_key='[FREEPDK45]',
        notes='DOI resolved via IEEE Xplore 4231502 / ACM DL on '
              '2026-08-30.'),
    _ev('pub-PTM', 'publication',
        'New generation of predictive technology model for sub-45 nm '
        'early design exploration', 'W. Zhao, Y. Cao (IEEE TED 53(11):'
        '2816-2823)', f'doi:{DOI_PTM}', '2006-11-01', 'model-source',
        'PTM bulk cards 130-32 nm from physical models + early silicon '
        'data (the abstract\'s <10 % error claim is TO VERIFY on the '
        'paper); the FreePDK45 card is the PTM 45 nm card',
        ['freepdk45', 'ptm32'], url=f'https://doi.org/{DOI_PTM}',
        verified=True, verified_via='https://asu.elsevierpure.com/en/'
                                    'publications/new-generation-of-'
                                    'predictive-technology-model-for-'
                                    'sub-45-nm-early/',
        licence_bucket='cite+link+values (publisher copyright; not CC)',
        citation_key='[PTM]',
        notes='PTM model-file TERMS not fetched (ptm.asu.edu '
              'unreachable 2026-08-30) — ptm32 rights stay unresolved.'),
    _ev('pub-ASAP7', 'publication',
        'ASAP7: A 7-nm finFET predictive process design kit',
        'L. T. Clark, V. Vashishtha, L. Shifren, A. Gujja, S. Sinha, '
        'B. Cline, C. Ramamurthy, G. Yeric (Microelectronics J. 53:'
        '105-115)', f'doi:{DOI_ASAP7}', '2016-07-01', 'model-source',
        '"realistic, based on current assumptions for the 7-nm '
        'technology node, but is not tied to any specific foundry" — '
        'predictive-only by the authors\' own statement',
        ['asap7'], url=f'https://doi.org/{DOI_ASAP7}', verified=True,
        verified_via='https://www.sciencedirect.com/science/article/pii/'
                     'S002626921630026X',
        licence_bucket='cite+link+values (publisher copyright; not CC)',
        citation_key='[ASAP7]'),
    _ev('pub-BSIM4', 'publication', 'BSIM4 MOSFET Model User\'s Manual '
        '(v4.8.3, 2025-05-19)', 'BSIM Group, UC Berkeley', '', '2025-05-19',
        'model-source', 'the model equations FreePDK45 / PTM cards '
        'parameterize; manual copyright UC Regents',
        ['freepdk45', 'ptm32', 'bsim4-model'], url=URL_BSIM4,
        verified=True, verified_via=URL_BSIM4,
        licence_bucket='cite only (copyrighted manual)',
        citation_key='[BSIM4]'),
    _ev('std-bsim4', 'standard', 'BSIM4 — CMC standard bulk MOSFET '
        'compact model', 'UC Berkeley BSIM Group / Si2 Compact Model '
        'Coalition', 'BSIM4 4.8.3', '2025-05-19', 'open-licence',
        'CMC-standard model; the bsim.berkeley.edu page points to an '
        '"Agreement for Use" that was NOT fetched — the widely repeated '
        'claim that BSIM code is BSD-licensed is TO VERIFY against that '
        'agreement (ngspice ships BSIM4 under a UC BSD-style header, '
        'which is the strongest public indicator).',
        ['freepdk45', 'ptm32', 'bsim4-model'], url=URL_BSIM4,
        verified=False, licence_bucket='open standard (code licence '
                                       'to-verify)',
        citation_key='[BSIM4]',
        notes='verify_next: fetch the BSIM "Agreement for Use" text; '
              'check the ngspice src/spicelib/devices/bsim4 header.'),
    _ev('std-bsim-cmg', 'standard', 'BSIM-CMG — CMC standard multi-gate '
        '(FinFET) compact model', 'UC Berkeley BSIM Group / Si2 CMC',
        'BSIM-CMG 112.1.0', '2026-04-28', 'open-licence',
        'CMC-standard FinFET model used by ASAP7 and PTM-MG cards; '
        'licence of the reference code TO VERIFY (same "Agreement for '
        'Use" as BSIM4; a newer beta may be CMC-members-only).',
        ['asap7'], url=URL_BSIMCMG, verified=False,
        licence_bucket='open standard (code licence to-verify)',
        citation_key='[BSIM-CMG]',
        notes='verify_next: as std-bsim4.'),
]

_IP_REVIEWED_AT = LADDER_REVIEWED_AT
_MAKE_RULE = ('Making it yourself does NOT clear an active patent: a US '
              'patent excludes others from MAKING, using, selling, '
              'offering or importing the claimed invention (35 U.S.C. '
              '271(a)) — own manufacture is "making". It DOES remove '
              'any copyright/licence obligation on someone else\'s '
              'design files or code, and trade secrets you never '
              'accessed cannot be asserted against an independent '
              're-derivation.')


def _ip(name, display_name, subject_kind, subject_ref, ip_kind, verdict,
        fto_reasoning, self_manufacture_note, verify_next, licence='',
        what_we_own='', sources=(), confidence='unverified', notes='',
        evidence=(), intended_use='open-chip-candidate'):
    """TechnologyIPRecord seed — the exact cnt_ip._rec key set."""
    assert verdict in ('green', 'amber', 'red'), verdict
    return {
        'name': name, 'display_name': display_name,
        'subject_kind': subject_kind, 'subject_ref': subject_ref,
        'intended_use': intended_use, 'ip_kind': ip_kind,
        'verdict': verdict, 'key_patents_json': '[]',
        'licence': licence, 'what_we_own': what_we_own,
        'fto_reasoning': fto_reasoning,
        'self_manufacture_note': self_manufacture_note,
        'jurisdiction': 'US', 'verify_next': verify_next,
        'sources_json': json.dumps(list(sources)),
        'confidence': confidence, 'reviewed_at': _IP_REVIEWED_AT,
        'evidence_json': json.dumps(list(evidence)),
        'notes': notes, 'is_prior': True,
    }


SEED_LADDER_IP = [
    _ip('freepdk45', 'FreePDK45 generic 45 nm PDK', 'model', 'freepdk45',
        'open-licence', 'green',
        'Apache-2.0 (verified on the NC State page 2026-08-30) — '
        'permissive, GPLv3-compatible one-way into our tree. The kit '
        'is a generic PDK, not a foundry process; no patent covers '
        '"a 45 nm design-rule set" as such. Our device is a clean-room '
        'VS reconstruction calibrated to the documented numbers; the '
        'BSIM4 card is compared against, not shipped as ours.',
        _MAKE_RULE + ' Nothing here is a process we could make anyway '
        '(generic PDK).',
        'read APACHE-LICENSE-2.0.txt + the SVRF click-through in the '
        'downloaded kit; confirm no added terms.',
        licence='Apache-2.0',
        what_we_own='si-nmos/pmos-freepdk45-class rows + '
                    'SEED_SILICON_ANCHORS + compare_to_anchors (GPLv3)',
        sources=(URL_FREEPDK45, f'https://doi.org/{DOI_FREEPDK}'),
        confidence='partially-verified',
        notes='fabrication_evidence: calibrated-predictive (PTM 45 nm '
              'tuned to Fujitsu IEDM 2007 silicon); manufacturable '
              'False.',
        evidence=('lic-apache-2.0', 'pub-FreePDK45', 'pub-PTM',
                  'std-bsim4')),
    _ip('ptm32', 'PTM 32 nm HP predictive card', 'model', 'ptm32',
        'proprietary-licence', 'amber',
        'PTM terms NOT read (ptm.asu.edu unreachable 2026-08-30); the '
        'only public statement found is an acknowledgment condition. '
        'Amber: use as a local oracle for research, do not '
        'redistribute or vendor the cards until the terms are read.',
        _MAKE_RULE + ' A model card is not a process; own manufacture '
        'is moot.',
        'fetch ptm.asu.edu terms verbatim; if permissive, re-verdict '
        'green and re-class the node incorporable-open.',
        licence='to-verify',
        what_we_own='nothing yet — oracle only',
        sources=(URL_PTM, f'https://doi.org/{DOI_PTM}'),
        confidence='unverified',
        notes='fabrication_evidence: calibrated-predictive ([PTM] '
              '<10 % claim to-verify); manufacturable False.',
        evidence=('pub-PTM', 'std-bsim4'), intended_use='reference-only'),
    _ip('asap7', 'ASAP7 7 nm predictive FinFET PDK', 'model', 'asap7',
        'open-licence', 'green',
        'BSD-3-Clause (LICENSE fetched from the OpenROAD repo '
        '2026-08-30: "Copyright 2020 Lawrence T. Clark, Vinay '
        'Vashishtha, or Arizona State University") — GPLv3-compatible '
        'one-way. Green for the SOFTWARE/PDK artefacts; it is a '
        'research aid, explicitly not manufacturable.',
        _MAKE_RULE + ' There is no foundry for ASAP7 rules; "making" '
        'does not arise.',
        'read the LICENSE at the pinned commit; confirm the Calibre '
        'decks (separate download) carry no extra terms before use.',
        licence='BSD-3-Clause',
        what_we_own='nothing yet — our finfet-class VS device will be '
                    'compared against its BSIM-CMG cards',
        sources=(URL_ASAP7, URL_ASAP7_LIC, f'https://doi.org/{DOI_ASAP7}'),
        confidence='partially-verified',
        notes='fabrication_evidence: predictive-only; manufacturable '
              'False (ASU: not tied to any foundry).',
        evidence=('lic-bsd-3-clause', 'pub-ASAP7', 'std-bsim-cmg')),
    _ip('bsim4-model', 'BSIM4 compact model (CMC standard)', 'model',
        'bsim4-model', 'open-licence', 'amber',
        'CMC-standard equations are public (manual); the reference '
        'code licence is behind an "Agreement for Use" not yet read. '
        'We do not incorporate BSIM4 code — our VS model is the '
        'engine; BSIM4 cards are oracles run in ngspice (whose bundled '
        'BSIM4 carries a UC BSD-style header, to-verify).',
        _MAKE_RULE + ' Model equations are not patentable as such.',
        'fetch the BSIM Agreement for Use; check the ngspice bsim4 '
        'source header; state the exact licence here.',
        licence='to-verify (UC Regents copyright; BSD-style claimed)',
        what_we_own='nothing — reference model',
        sources=(URL_BSIM4, URL_BSIMCMG), confidence='unverified',
        notes='fabrication_evidence n/a (a model standard).',
        evidence=('pub-BSIM4', 'std-bsim4', 'std-bsim-cmg'),
        intended_use='reference-only'),
]

# ── FreePDK45 calibration anchors (CNTCalibrationAnchor rows) ──────

_FPDK45_REF = ('FreePDK45 v1.4 documentation, NC State EDA — '
               '"Process Information / HSPICE models" section')
_FPDK45_COND = {'vdd_v': 1.0, 'corner': 'nominal', 'lg_nm': 45.0,
                'model': 'PTM 45 nm BSIM4 card (FreePDK45)',
                'per_um': True}


def _anchor(name, value, unit, flavour, polarity, metric):
    return {
        'name': name, 'source_reference': _FPDK45_REF, 'doi': DOI_FREEPDK,
        'figure': f'{URL_FREEPDK45} — device table ({flavour} {polarity}MOS)',
        'extraction_method': 'documented value (quoted from the FreePDK45 '
                             'documentation page; no digitization)',
        'digitization_error': 'n/a (documented scalar)',
        'axis_scaling_json': '{}', 'raw_points_json': '[]',
        'normalizations_json': json.dumps({'width': 'per um of W'}),
        'fitted_params_json': '{}', 'value': value, 'unit': unit,
        'conditions_json': json.dumps({**_FPDK45_COND, 'flavour': flavour,
                                       'polarity': polarity,
                                       'metric': metric}),
        'status': 'ready',
        'notes': f'FreePDK45 {flavour} {polarity}MOS {metric} at 1.0 V — '
                 'the number our si-{p}mos-freepdk45-class reconstruction '
                 'is COMPARED against (compare_to_anchors), never fitted '
                 'silently.'.replace('{p}', polarity.lower()),
    }


SEED_SILICON_ANCHORS = [
    _anchor('freepdk45-nmos-vtg-ion', 975.5, 'uA/um', 'VTG', 'N', 'ion'),
    _anchor('freepdk45-nmos-vtg-ioff', 10.0, 'nA/um', 'VTG', 'N', 'ioff'),
    _anchor('freepdk45-nmos-vtl-ion', 1246.0, 'uA/um', 'VTL', 'N', 'ion'),
    _anchor('freepdk45-nmos-vtl-ioff', 100.0, 'nA/um', 'VTL', 'N', 'ioff'),
    _anchor('freepdk45-nmos-vth-ion', 570.0, 'uA/um', 'VTH', 'N', 'ion'),
    _anchor('freepdk45-nmos-vth-ioff', 0.2, 'nA/um', 'VTH', 'N', 'ioff'),
    _anchor('freepdk45-pmos-vtg-ion', 650.3, 'uA/um', 'VTG', 'P', 'ion'),
    _anchor('freepdk45-pmos-vtg-ioff', 10.0, 'nA/um', 'VTG', 'P', 'ioff'),
    _anchor('freepdk45-pmos-vtl-ion', 801.0, 'uA/um', 'VTL', 'P', 'ion'),
    _anchor('freepdk45-pmos-vth-ion', 379.2, 'uA/um', 'VTH', 'P', 'ion'),
]

#: device name → (anchor flavour, polarity) it is calibrated against
DEVICE_ANCHOR_FLAVOUR = {
    'si-nmos-freepdk45-class': ('VTG', 'N'),
    'si-pmos-freepdk45-class': ('VTG', 'P'),
}
DEVICE_NODE = {
    'si-nmos-freepdk45-class': 'freepdk45',
    'si-pmos-freepdk45-class': 'freepdk45',
    'si-nmos-planar-90': 'polari-si-90-class',
    'si-pmos-planar-90': 'polari-si-90-class',
}

ION_TOL = 0.30       # ±30 % on Ion = "within tolerance"
IOFF_TOL_DEC = 1.0   # 10x on Ioff


# ── per-µm metrics + the honest gap report ────────────────────────

def _rows_of(manager, cls):
    tables = getattr(manager, 'objectTables', None) or {}
    t = tables.get(cls) or {}
    return list(t.values()) if isinstance(t, dict) else list(t)


def _anchors(manager, flavour, polarity):
    rows = _rows_of(manager, 'CNTCalibrationAnchor')
    seeds = {s['name']: s for s in SEED_SILICON_ANCHORS}
    found = {}
    for r in rows:
        c = json.loads(getattr(r, 'conditions_json', '{}') or '{}')
        if c.get('flavour') == flavour and c.get('polarity') == polarity:
            found[c['metric']] = {'name': r.name, 'value': r.value,
                                  'unit': r.unit}
    if not found:   # fall back to the seed list (no manager rows)
        for s in seeds.values():
            c = json.loads(s['conditions_json'])
            if c['flavour'] == flavour and c['polarity'] == polarity:
                found[c['metric']] = {'name': s['name'],
                                      'value': s['value'],
                                      'unit': s['unit']}
    return found


def per_um_metrics(id_fn, device):
    """Ion (uA/um) / Ioff (nA/um) at the device's Vdd from
    extract_metrics, normalized by the row's W."""
    m = extract_metrics(id_fn, metric_spec(device))
    w_um = max(device.w_nm / 1000.0, 1e-6)
    return {'ion_ua_per_um': m['ion_a'] / w_um * 1e6,
            'ioff_na_per_um': m['ioff_a'] / w_um * 1e9,
            'ss_mv_per_dec': m['ss_mv_per_dec'],
            'dibl_mv_per_v': m['dibl_mv_per_v'],
            'vt_cc_sat_v': m['vt_cc_sat_v'], 'vdd_v': device.vdd_v,
            'refusals': m['refusals']}


def _verdict(ratio):
    if ratio is None:
        return 'unmeasurable'
    r = max(ratio, 1.0 / ratio) if ratio > 0 else float('inf')
    if r <= 2.0:
        return 'within-2x'
    return f'off-by-{r:.0f}x' if r < 1e3 else f'off-by-{r:.1e}x'


def _metrics_with(rows, device, vfb_v=None, kt_fraction=None):
    """Re-derive p with ONE knob changed (Vfb or the kT-layer
    fraction) WITHOUT touching the row or SI_LIT permanently."""
    dev = device
    if vfb_v is not None:
        dev = type('D', (), {})()
        for k in ('polarity', 'lg_nm', 'w_nm', 'vfb_v', 'rc_ohm_um',
                  'temperature_k', 'vdd_v'):
            setattr(dev, k, getattr(device, k))
        dev.vfb_v = vfb_v
    old = sm.SI_LIT['kt_layer_fraction']['value']
    try:
        if kt_fraction is not None:
            sm.SI_LIT['kt_layer_fraction']['value'] = kt_fraction
        p = params_from_rows(rows, dev)
    finally:
        sm.SI_LIT['kt_layer_fraction']['value'] = old
    return per_um_metrics(frame_aware_id_fn(p, device.polarity), dev)


def _within(m, anchors):
    ion_ok = ioff_ok = True
    if 'ion' in anchors:
        ion_ok = abs(m['ion_ua_per_um'] / anchors['ion']['value'] - 1.0) \
            <= ION_TOL
    if 'ioff' in anchors and m['ioff_na_per_um'] > 0:
        ioff_ok = abs(math.log10(m['ioff_na_per_um']
                                 / anchors['ioff']['value'])) <= IOFF_TOL_DEC
    return ion_ok and ioff_ok


def _knob_scan(rows, device, anchors):
    """ONE-parameter tunes that would bring Ion within ±30 % AND Ioff
    within 10x — reported as SUGGESTIONS, never applied."""
    out = []
    # smallest |change| first, so the suggestion is the nearest tune
    steps = sorted(range(-16, 17), key=lambda i: (abs(i), i))
    for vfb in [device.vfb_v + 0.05 * i for i in steps if i]:
        m = _metrics_with(rows, device, vfb_v=vfb)
        if _within(m, anchors):
            out.append({'knob': 'vfb_v', 'value': round(vfb, 3),
                        'current': device.vfb_v,
                        'ion_ua_per_um': m['ion_ua_per_um'],
                        'ioff_na_per_um': m['ioff_na_per_um']})
            break
    for f in (0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.2, 0.3, 0.5):
        m = _metrics_with(rows, device, kt_fraction=f)
        if _within(m, anchors):
            out.append({'knob': 'kt_layer_fraction', 'value': f,
                        'current': sm.SI_LIT['kt_layer_fraction']['value'],
                        'ion_ua_per_um': m['ion_ua_per_um'],
                        'ioff_na_per_um': m['ioff_na_per_um']})
            break
    return out


def compare_to_anchors(manager, device_name):
    """The honest calibration-gap report for a derived
    si-*-freepdk45-class device vs the FreePDK45 documented numbers:
    ours / anchor / ratio / verdict per metric; a knob SUGGESTION
    when one parameter would close the gap (never applied)."""
    device = get_row(manager, 'SiliconMOSFET', device_name)
    if device is None:
        return {'ok': False, 'error': f'no SiliconMOSFET "{device_name}"'}
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': f'"{device_name}" never derived',
                'refusal': 'derive first (derive_si_device)'}
    flav = DEVICE_ANCHOR_FLAVOUR.get(device_name)
    if flav is None:
        return {'ok': False, 'error': f'"{device_name}" has no anchor '
                                      'flavour (DEVICE_ANCHOR_FLAVOUR)'}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False, 'error': f'missing component rows: {missing}'}
    anchors = _anchors(manager, *flav)
    p = params_from_rows(rows, device)
    ours = per_um_metrics(frame_aware_id_fn(p, device.polarity), device)
    comps = {}
    for metric, key in (('ion', 'ion_ua_per_um'), ('ioff', 'ioff_na_per_um')):
        a = anchors.get(metric)
        if a is None:
            comps[metric] = {'refusal': 'no anchor row'}
            continue
        ratio = ours[key] / a['value'] if a['value'] else None
        comps[metric] = {'ours': ours[key], 'anchor': a['value'],
                         'unit': a['unit'], 'anchor_row': a['name'],
                         'ratio_ours_over_anchor': ratio,
                         'verdict': _verdict(ratio)}
    within = _within(ours, anchors)
    knobs = [] if within else _knob_scan(rows, device, anchors)
    return {
        'ok': True, 'device': device_name, 'node': DEVICE_NODE.get(device_name),
        'flavour': flav[0], 'polarity': flav[1], 'vdd_v': device.vdd_v,
        'ours': ours, 'comparisons': comps,
        'within_tolerance': within,
        'tolerance': {'ion': f'+/-{ION_TOL:.0%}',
                      'ioff': f'{10 ** IOFF_TOL_DEC:.0f}x'},
        'verdict': ('calibrated' if within else
                    'GAP — ' + ', '.join(f"{k}: {v.get('verdict')}"
                                         for k, v in comps.items())),
        'knob_suggestions': knobs,
        'rule': 'a gap is REPORTED, never fitted; a knob suggestion is '
                'a KNOB (edit the row / SI_LIT deliberately), not an '
                'auto-apply',
        'this_is_not': 'the FreePDK45 BSIM4 card — ours is a VS '
                       'reconstruction calibrated against its '
                       'documented numbers',
    }


def apply_anchor_knob(manager, device_name):
    """fg-4 (the FreePDK45-class Ioff gap): the EXPLICIT act that
    applies the vfb_v knob suggestion to the device ROW — never
    automatic, never SI_LIT (a literature knob stays a deliberate
    edit). vfb is a per-device PRIOR (vfb_source says so); tuning it
    to sit within the DOCUMENTED FreePDK45 anchors turns the prior
    into an anchor-calibrated value with the calibration recorded in
    vfb_source (old value kept there — reversible). The default
    seeds keep the honest gap until someone posts this act."""
    rep = compare_to_anchors(manager, device_name)
    if not rep.get('ok'):
        return rep
    if rep['within_tolerance']:
        return {'ok': False, 'device': device_name,
                'error': 'already within tolerance — nothing to apply',
                'report': rep}
    vfb = next((s for s in rep['knob_suggestions']
                if s['knob'] == 'vfb_v'), None)
    if vfb is None:
        return {'ok': False, 'device': device_name,
                'error': 'no single-parameter vfb_v tune closes the '
                         'gap — the remaining suggestions (if any) '
                         'are SI_LIT knobs, which stay deliberate '
                         'edits',
                'report': rep}
    device = get_row(manager, 'SiliconMOSFET', device_name)
    old = device.vfb_v
    device.vfb_v = float(vfb['value'])
    device.vfb_source = (
        f'calibrated: vfb {old:+.3f} -> {device.vfb_v:+.3f} V so '
        f'Ion/Ioff sit within the documented anchors '
        f'({", ".join(a["anchor_row"] for a in rep["comparisons"].values() if a.get("anchor_row"))}); '
        f'{_FPDK45_SRC}')
    from sifet.si_device import derive_si_device as _derive
    derive = _derive(manager, device)
    after = compare_to_anchors(manager, device_name)
    return {'ok': bool(derive.get('ok')), 'device': device_name,
            'applied': {'knob': 'vfb_v', 'old': old,
                        'new': device.vfb_v,
                        'vfb_source': device.vfb_source},
            'before': {k: v.get('verdict')
                       for k, v in rep['comparisons'].items()},
            'after': after.get('comparisons'),
            'within_tolerance': after.get('within_tolerance'),
            'derive': {k: derive.get(k) for k in ('ok', 'error')},
            'note': ('an explicit, recorded act — the seeds keep the '
                     'honest gap by default; POST again after editing '
                     'anchors to re-tune, or set vfb_v/vfb_source '
                     'back to revert')}


# ── the ladder report ─────────────────────────────────────────────

def _nodes(manager):
    rows = _rows_of(manager, 'SiliconProcessNode') if manager else []
    if rows:
        return [{k: getattr(r, k) for k in SEED_SILICON_PROCESS_NODES[0]}
                for r in rows]
    return [dict(s) for s in SEED_SILICON_PROCESS_NODES]


def _reconstruction_status(manager, node_name):
    """Have we a derived device on this rung? anchored? gap?"""
    devs = [d for d, n in DEVICE_NODE.items() if n == node_name]
    if not devs or manager is None:
        return {'derived': False, 'anchored': False, 'devices': [],
                'note': 'no Polari device row on this rung'}
    out = {'derived': False, 'anchored': False, 'devices': [], 'gaps': {}}
    for d in devs:
        row = get_row(manager, 'SiliconMOSFET', d)
        if row is None:
            continue
        out['devices'].append(d)
        if getattr(row, 'derived_at', ''):
            out['derived'] = True
            if d in DEVICE_ANCHOR_FLAVOUR:
                rep = compare_to_anchors(manager, d)
                if rep.get('ok'):
                    out['anchored'] = True
                    out['gaps'][d] = {'verdict': rep['verdict'],
                                      'knob_suggestions':
                                          rep['knob_suggestions']}
    return out


def _licence_clean(n):
    return (n['rights_class'] == 'clean-room-reconstructable' or
            (n['licence_verified'] and
             n['licence_gplv3_compatible'] == 'yes'))


def ladder_report(manager=None):
    nodes = sorted(_nodes(manager), key=lambda n: (-n['node_nm'], n['name']))
    rungs = []
    for n in nodes:
        rungs.append({
            **{k: n[k] for k in ('name', 'display_name', 'node_nm',
                                 'architecture', 'vdd_v', 'source',
                                 'licence', 'licence_verified',
                                 'licence_gplv3_compatible', 'rights_class',
                                 'fabrication_evidence', 'manufacturable',
                                 'manufacturable_reason', 'model_family',
                                 'what_we_can_use',
                                 'what_we_must_not_assume')},
            'key_numbers': json.loads(n['key_numbers_json']),
            'search': json.loads(n['search_json']),
            'evidence': json.loads(n['evidence_json']),
            'reconstruction': _reconstruction_status(manager, n['name']),
        })

    def smallest(pred, why):
        cands = [r for r in rungs if pred(r)]
        if not cands:
            return {'node': None, 'node_nm': None, 'reasoning':
                    'no rung satisfies: ' + why, 'candidates': []}
        best = min(cands, key=lambda r: r['node_nm'])
        return {'node': best['name'], 'node_nm': best['node_nm'],
                'rights_class': best['rights_class'],
                'fabrication_evidence': best['fabrication_evidence'],
                'licence': best['licence'],
                'reasoning': f"{best['display_name']}: {why}; smallest "
                             f"node among {[c['name'] for c in cands]}",
                'candidates': [c['name'] for c in cands]}

    frontier = smallest(
        lambda r: r['rights_class'] in RIGHTS_CLEAN
        and r['fabrication_evidence'] in EVIDENCE_REAL and _licence_clean(r),
        'rights_class in {incorporable-open, clean-room-reconstructable} '
        'AND fabrication_evidence in {measured, reconstructed, '
        'calibrated-predictive} AND (verified GPLv3-compatible licence '
        'or our own clean-room rows)')
    predictive = smallest(
        lambda r: r['rights_class'] in RIGHTS_CLEAN and _licence_clean(r),
        'rights-clean (any fabrication_evidence) — the smallest node we '
        'may legally build tooling on, however unproven physically')
    manufacturable = smallest(
        lambda r: r['manufacturable'] is True,
        'manufacturable True — evidence of an actually available open '
        'process. ' + MANUFACTURABLE_RULE + ' Our 90-class is '
        'reconstructed-from-published-silicon and NOT proven '
        'manufacturable either')
    return {
        'revision': LADDER_REVISION, 'reviewed_at': LADDER_REVIEWED_AT,
        'axes': {'rights_class': RIGHTS_CLASS,
                 'fabrication_evidence': FABRICATION_EVIDENCE,
                 'rule': 'two independent axes, never collapsed; '
                         'manufacturable is a third evidence-only flag'},
        'rungs': rungs,
        'frontier': frontier,
        'predictive_frontier': predictive,
        'manufacturable_frontier': manufacturable,
        'gplv3_direction': 'Apache-2.0 and BSD-3-Clause are one-way '
                           'compatible INTO GPLv3; NC / research-only '
                           'terms are a hard blocker',
        'disclaimer': 'ENGINEERING LICENCE/FTO EVIDENCE — NOT LEGAL '
                      'ADVICE; "verified" = fetched from the named URL '
                      'on reviewed_at, nothing more',
    }


# ── graph: Ion vs node ────────────────────────────────────────────

def ladder_ion_rows(manager=None):
    """Long-form rows for si-ladder-ion-vs-node: x = node nm, y = Ion
    uA/um, series = source. Documented numbers per rung + our derived
    devices (series 'polari-model (derived)')."""
    rows = []
    for n in _nodes(manager):
        kn = json.loads(n['key_numbers_json'])
        ion = (kn.get('ion_ua_per_um') or {}).get('value')
        if isinstance(ion, (int, float)):
            rows.append({'x': n['node_nm'], 'y': ion, 'series': n['source'],
                         'style': 'dot', 'label': n['name']})
    if manager is not None:
        for d, node in DEVICE_NODE.items():
            row = get_row(manager, 'SiliconMOSFET', d)
            if row is None or not getattr(row, 'derived_at', ''):
                continue
            rs, missing = resolve_components(manager, row)
            if missing:
                continue
            p = params_from_rows(rs, row)
            m = per_um_metrics(frame_aware_id_fn(p, row.polarity), row)
            rows.append({'x': row.lg_nm, 'y': m['ion_ua_per_um'],
                         'series': 'polari-model (derived)',
                         'style': 'dot', 'label': d})
    return rows


def _ladder_graph(kind, description, x_label, y_label, x_type='log',
                  y_type='linear', style='scatter'):
    return {
        'name': f'si-ladder-{kind}',
        'description': description + ' — data: /api/sifet/ladder/points'
                       f'?curve={kind}',
        'source_class': 'SiliconProcessNode',
        'definition': json.dumps({'graphConfig': {
            'renderStyle': style, 'xDimension': 'x', 'yDimensions': ['y'],
            'seriesDimension': 'series', 'styleDimension': 'style',
            'seriesColors': [],
            'options': {'showLegend': True, 'showGrid': True,
                        'xLabel': x_label, 'yLabel': y_label,
                        'xType': x_type, 'yType': y_type},
            'aggregation': None,
        }}),
    }


SEED_SI_LADDER_GRAPHS = [
    _ladder_graph('ion-vs-node',
                  'Open-silicon ladder: documented Ion per rung vs node '
                  '(log x), series = source; our derived devices as '
                  'their own series so the calibration gap is visible',
                  'node (nm)', 'Ion (uA/um)'),
]
CURVE_BUILDERS = {}
