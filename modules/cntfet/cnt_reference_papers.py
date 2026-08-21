"""
@module cntfet.cnt_reference_papers

Dustin's supplied reference papers (2026-08-21, license-gated per
the plan's paper-storage rule) as CITED DATA: a paper registry with
the license bucket each landed in, plus reference-anchor rows
(CNTCalibrationAnchor) carrying every extracted value with its
full citation — DOI, figure/table or text location, extraction
method, error. The PDFs themselves stay OFF-GIT (local disk only:
~/Desktop/Research_Papers/) — both are cite+link+values bucket,
neither is CC-licensed.

Citation-linkage rule (Dustin 2026-08-21): every value row names
its source; cnt_citations aggregates the reverse map (source ->
every row that cites it) so linkage is queryable, not implicit.

@consumers
  - polariServer seed tuples (rows exist from boot)
  - cntfet.cnt_citations (the linkage query)
  - microchip.chip_basis (the RV16X-NANO precedent nodes cite
    [HIL19] through these anchors)
"""

import json

# The paper registry — license verdicts recorded WITH the papers.
PAPERS = {
    'FIO05': {
        'citation': 'G. Fiori, G. Iannaccone, G. Klimeck, '
                    '"Performance of Carbon Nanotube Field Effect '
                    'Transistors with doped source and drain '
                    'extensions and arbitrary geometry", IEDM '
                    'Tech. Dig. 2005',
        'doi': '10.1109/IEDM.2005.1609397',
        'journal_sibling': 'IEEE TED 53(8):1782-1788 (2006), DOI '
                           '10.1109/TED.2006.878018 (expanded '
                           'journal version, distinct paper)',
        'license_bucket': 'cite+link+values ONLY — "(c) 2005 IEEE" '
                          'on the PDF; not CC; PDF stays off-git '
                          '(local: ~/Desktop/Research_Papers/)',
        'role': 'NEGF-oracle literature: ballistic 3D NEGF '
                '(atomistic pz TB, self-consistent 3D Poisson) — '
                'the validation-triangle NEGF edge from papers; '
                'authors = the NanoTCAD ViDES group',
    },
    'HIL19': {
        'citation': 'G. Hills et al., "Modern microprocessor '
                    'built from complementary carbon nanotube '
                    'transistors", Nature 572:595-602 (2019)',
        'doi': '10.1038/s41586-019-1493-8',
        'license_bucket': 'cite+link+values ONLY — "(c) The '
                          'Author(s), under exclusive licence to '
                          'Springer Nature Limited 2019"; NOT open '
                          'access; PDF stays off-git (local: '
                          '~/Desktop/Research_Papers/CNT-RISCV.pdf)',
        'role': 'system precedent (RV16X-NANO) — scientific '
                'reference only per the S0 gate; design collateral '
                'was never released',
    },
}

_FIO = PAPERS['FIO05']['citation']
_HIL = PAPERS['HIL19']['citation']


def _anchor(name, doi, figure, method, err, value, unit, cond,
            notes, status='ready', source_reference=''):
    return {
        'name': name, 'source_reference': source_reference,
        'doi': doi, 'figure': figure, 'extraction_method': method,
        'digitization_error': err,
        'axis_scaling_json': '{}', 'raw_points_json': '[]',
        'normalizations_json': '{}', 'fitted_params_json': '{}',
        'value': value, 'unit': unit,
        'conditions_json': json.dumps(cond),
        'status': status, 'notes': notes,
    }


# [FIO05] — simulated (ballistic NEGF) values; the device is a
# (11,0) tube, d = 0.9 nm, n-doped 10 nm S/D extensions in SiO2.
# DG-geometry mapping onto our GAA compact model is S2 comparison
# work — these rows are recorded, not force-fit at S1.
_FIO05_ANCHORS = [
    _anchor('fio05-device-d09', PAPERS['FIO05']['doi'],
            '[FIO05] Results, first paragraph',
            'reported-value (text)', 'n/a (stated)',
            0.9, 'nm',
            {'chirality': '(11,0)', 'extensions_nm': 10.0,
             'extension_doping': 'n-type, molar fraction f',
             'matrix': 'SiO2', 'transport': 'ballistic NEGF',
             'purpose': 'negf-oracle-literature'},
            'the simulated tube', source_reference=_FIO),
    _anchor('fio05-ion-vs-hp32', PAPERS['FIO05']['doi'],
            '[FIO05] text at Fig.6',
            'reported-value (text: "almost 7 times larger")',
            'qualitative multiplier ("almost")',
            7.0, 'ratio',
            {'quantity': 'Ion per unit width vs ITRS hp32 HP '
                         'requirement', 'packing': 'most densely '
             'packed parallel-CNT array', 'vgs_v': 0.8,
             'vds_v': 0.8, 'tox_nm': 2.0, 'f': 5e-3,
             'purpose': 'negf-oracle-literature'},
            '', source_reference=_FIO),
    _anchor('fio05-ion-vs-hp22', PAPERS['FIO05']['doi'],
            '[FIO05] text at Fig.6',
            'reported-value (text: "6 times for the 22 nm node")',
            'qualitative multiplier',
            6.0, 'ratio',
            {'quantity': 'Ion per unit width vs ITRS hp22',
             'purpose': 'negf-oracle-literature'},
            '', source_reference=_FIO),
    _anchor('fio05-ioff-vs-itrs', PAPERS['FIO05']['doi'],
            '[FIO05] text at Fig.7',
            'reported-value (text: "15 times larger than '
            'required for both the hp32 and hp22 nodes")',
            'qualitative multiplier',
            15.0, 'ratio',
            {'quantity': 'Ioff vs ITRS requirement',
             'vgs_v': 0.0, 'vds_v': 0.8,
             'mechanism': 'valence-band bound states filled by '
                          'hole tunneling from the drain '
                          'reservoir (paper Fig.8)',
             'purpose': 'negf-oracle-literature'},
            'the honest bad news rides along with the good',
            source_reference=_FIO),
    _anchor('fio05-f-sensitivity', PAPERS['FIO05']['doi'],
            '[FIO05] Fig.2 + text',
            'reported-value (text: "variation of the current of '
            'almost two orders of magnitude" for small f change)',
            'order-of-magnitude statement',
            100.0, 'ratio',
            {'quantity': 'off-current sensitivity to S/D doping '
                         'molar fraction f (1e-3..1e-2)',
             'vds_v': 0.5, 'vgs_v': 0.0, 'lg_nm': 7.0,
             'gate': 'double', 'tox_nm': 2.0,
             'purpose': 'negf-oracle-literature',
             's3_note': 'dopant-count fluctuation = a variability '
                        'axis for S3 process objects'},
            '', source_reference=_FIO),
    _anchor('fio05-curves', PAPERS['FIO05']['doi'],
            '[FIO05] Figs 2,4,5,6,7,9,10,11',
            'NOT PERFORMED', 'unquantified — that is WHY this '
            'row refuses',
            0.0, '',
            {'purpose': 'negf-oracle-literature'},
            'Curve digitization (SS/DIBL vs tox, Ion vs L and d, '
            'Ioff vs L, transfer curves, gm, tau/fT) is S2 work '
            'with quantified error; until then curve queries '
            'REFUSE.', status='refusing', source_reference=_FIO),
]

# [HIL19] — the RV16X-NANO system precedent (measured, fabricated).
_HIL19_ANCHORS = [
    _anchor('hil19-cnfet-count', PAPERS['HIL19']['doi'],
            '[HIL19] Fig.1 caption/text',
            'reported-value (text: "totalling 14,702 CNFETs")',
            'n/a (stated)', 14702.0, 'CNFETs',
            {'purpose': 'system-precedent',
             'cnts_total': '>10 million'},
            '', source_reference=_HIL),
    _anchor('hil19-cell-library', PAPERS['HIL19']['doi'],
            '[HIL19] text (PDK section)',
            'reported-value (text: "63 unique cells")',
            'n/a (stated)', 63.0, 'cells',
            {'purpose': 'system-precedent',
             'examples': 'full-adder 18p+18n CNFETs, gain 17, '
                         'swing >99%; positive-edge DFF'},
            'the S4/S5 target shape: our minimal set is INV '
            'NAND2 BUF DFF (plan D10)', source_reference=_HIL),
    _anchor('hil19-vdd', PAPERS['HIL19']['doi'],
            '[HIL19] text', 'reported-value', 'n/a (stated)',
            1.8, 'V', {'purpose': 'system-precedent'},
            '', source_reference=_HIL),
    _anchor('hil19-clock-measured', PAPERS['HIL19']['doi'],
            '[HIL19] Methods',
            'reported-value (Methods: measured at 10 kHz, LIMITED '
            'by the 120-channel test setup; EDA-reported max '
            'post-P&R = 1.19 MHz)',
            'test-setup-limited, not device-limited',
            10e3, 'Hz',
            {'purpose': 'system-precedent',
             'eda_reported_max_hz': 1.19e6,
             'logic_depth_stages': 86},
            '', source_reference=_HIL),
    _anchor('hil19-cnts-per-cnfet', PAPERS['HIL19']['doi'],
            '[HIL19] DREAM section',
            'reported-value (text: "around 15-25 CNTs per '
            'CNFET" at pS ~ 99.99%)',
            'range 15-25', 20.0, 'CNTs/CNFET',
            {'purpose': 'system-precedent',
             'semiconducting_purity': 0.9999},
            'S3 variability anchor: tube count per FET',
            source_reference=_HIL),
    _anchor('hil19-dream-purity-relaxation', PAPERS['HIL19']['doi'],
            '[HIL19] DREAM section',
            'reported-value (text: relaxes metallic-CNT purity '
            'requirement "by about 10,000x", 99.999999% -> '
            '99.99%)', 'order-of-magnitude (stated)',
            1e4, 'ratio',
            {'purpose': 'system-precedent',
             's3_note': 'DREAM = circuit-design mitigation of '
                        'metallic fraction — plan S3 explicit '
                        'knob'},
            '', source_reference=_HIL),
    _anchor('hil19-rinse-particle-reduction', PAPERS['HIL19']['doi'],
            '[HIL19] Fig.RINSE caption',
            'reported-value ("decreases particle density by '
            '>250x")', 'lower bound', 250.0, 'ratio',
            {'purpose': 'system-precedent'},
            '', source_reference=_HIL),
    _anchor('hil19-nor-yield', PAPERS['HIL19']['doi'],
            '[HIL19] MIXED section',
            'reported-value ("functional yield 14,400/14,400, '
            'comprising 57,600 total CNFETs", 150-mm wafers)',
            'n/a (stated)', 1.0, 'fraction',
            {'purpose': 'system-precedent',
             'gate_kind': 'NOR', 'wafer_mm': 150},
            '', source_reference=_HIL),
]

SEED_REFERENCE_ANCHORS = _FIO05_ANCHORS + _HIL19_ANCHORS
