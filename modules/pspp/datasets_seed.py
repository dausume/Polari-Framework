"""
@module pspp.datasets_seed

Geopolymer book Ch.5 transcriptions as DigitizedDataset seed rows —
the operational form of /PSPP_DIGITIZED_DATASETS.json at the suite
root (the transcription record with the full qualitative-claims list).
Transcribed 2026-07-18 from Dustin's page photographs of Davidovits,
"Geopolymer Chemistry and Applications" (title confirmed by Dustin
2026-07-18; edition still to note when the copyright page is in hand).

Tables 5.4/5.5/5.6 are exact transcriptions (zero digitization error).
Fig 5.20's markers carry printed value labels (reliable), but the
shared concentration is unstated → relative reference curves only.
Fig 5.22 is points-empty (angled photo) with status
provisional-low-confidence — the engine refuses it until a re-shoot,
which is the honest behavior, not a gap.
"""

import json

_BOOK = ('Davidovits, Geopolymer Chemistry and Applications, Ch.5')

SEED_DIGITIZED_DATASETS = [
    {
        'name': 'na-silicate-solution-polymerization',
        'source_reference': f'{_BOOK}, Table 5.4, p.101 '
                            '(after Engler 1974)',
        'status': 'ready',
        'independent_variables_json': '["MR"]',
        'dependent_variables_json':
            '["molecular_weight", "polymerization_n"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol Na2O',
            'molecular_weight': 'g/mol of (SiO2)n',
            'polymerization_n': 'dimensionless'}),
        'source_conditions_json': json.dumps({
            'system': 'Na-silicate aqueous solution (equilibrium)',
            'note': 'p.101: equilibrium develops per composition; '
                    'rapid rearrangement on dilution or extra alkali; '
                    'equilibrium reached more quickly at lower MR.'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [0.48, 3.30]}',
        'digitization_method': 'exact table transcription from photo',
        'digitization_error': '',
        'points_json': json.dumps([
            {'MR': 0.48, 'molecular_weight': 60, 'polymerization_n': 1},
            {'MR': 1.01, 'molecular_weight': 90,
             'polymerization_n': 1.5},
            {'MR': 1.69, 'molecular_weight': 120, 'polymerization_n': 2},
            {'MR': 2.09, 'molecular_weight': 160,
             'polymerization_n': 2.6},
            {'MR': 2.62, 'molecular_weight': 265,
             'polymerization_n': 4.4},
            {'MR': 3.30, 'molecular_weight': 320,
             'polymerization_n': 5.3},
        ]),
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
    {
        'name': 'k-silicate-solution-polymerization',
        'source_reference': f'{_BOOK}, Table 5.5, p.101 '
                            '(after Engler 1974)',
        'status': 'ready',
        'independent_variables_json': '["MR"]',
        'dependent_variables_json':
            '["molecular_weight", "polymerization_n"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol K2O',
            'molecular_weight': 'g/mol of (SiO2)n',
            'polymerization_n': 'dimensionless'}),
        'source_conditions_json': json.dumps({
            'system': 'K-silicate aqueous solution (equilibrium)',
            'note': 'Steep jump n=5.3 -> 14.1 between MR 3.62 and '
                    '3.97 — interpolation in that interval carries a '
                    'wide honest band; same Engler equilibrium caveats '
                    'as Table 5.4.'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [0.60, 3.97]}',
        'digitization_method': 'exact table transcription from photo',
        'digitization_error': '',
        'points_json': json.dumps([
            {'MR': 0.60, 'molecular_weight': 60, 'polymerization_n': 1},
            {'MR': 1.75, 'molecular_weight': 90,
             'polymerization_n': 1.5},
            {'MR': 2.50, 'molecular_weight': 120, 'polymerization_n': 2},
            {'MR': 2.80, 'molecular_weight': 160,
             'polymerization_n': 2.6},
            {'MR': 3.31, 'molecular_weight': 265,
             'polymerization_n': 4.4},
            {'MR': 3.62, 'molecular_weight': 320,
             'polymerization_n': 5.3},
            {'MR': 3.97, 'molecular_weight': 848,
             'polymerization_n': 14.1},
        ]),
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
    {
        'name': 'na-siloxonate-glass-to-solution-q',
        'source_reference': f'{_BOOK}, Table 5.6, p.103',
        'status': 'ready',
        'independent_variables_json': '["MR", "physical_state"]',
        'dependent_variables_json': '["Q0", "Q1", "Q2", "Q3", "Q4"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol Na2O',
            'Q0-Q4': 'percent of Si sites'}),
        'source_conditions_json': json.dumps({
            'system': 'Na-siloxonate: parent glass vs its dissolution '
                      'solution',
            'note': 'Fixed reference mappings at the listed MRs ONLY '
                    '(no general kinetic law in source). Fig 5.12 '
                    'caption caveat: liquid-state 29Si NMR Q4 can be '
                    'an equipment artifact — note Q4=7% for MR 3.28 '
                    'solution.',
            'sum_anomaly': 'AS PRINTED, two solution rows do not sum '
                           'to 100%: MR 1.0 solution = 92, MR 2.0 '
                           'solution = 110 (photo re-checked, digits '
                           'confirmed). Glass rows all sum to 100. '
                           'Either the book rounds/omits minor '
                           'species or the book itself has a typo — '
                           'verify against another copy before '
                           'normalizing; do NOT silently rescale.'}),
        'interpolation_policy': 'none',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [1.0, 3.28]}',
        'digitization_method': 'exact table transcription from photo',
        'digitization_error': '',
        'points_json': json.dumps([
            {'MR': 1.0, 'physical_state': 'glass',
             'Q0': 1, 'Q1': 14, 'Q2': 68, 'Q3': 17, 'Q4': 0},
            {'MR': 1.0, 'physical_state': 'solution',
             'Q0': 20, 'Q1': 31, 'Q2': 41, 'Q3': 0, 'Q4': 0},
            {'MR': 1.33, 'physical_state': 'glass',
             'Q0': 0, 'Q1': 2, 'Q2': 52, 'Q3': 46, 'Q4': 0},
            {'MR': 1.33, 'physical_state': 'solution',
             'Q0': 12, 'Q1': 25, 'Q2': 58, 'Q3': 6, 'Q4': 0},
            {'MR': 2.0, 'physical_state': 'glass',
             'Q0': 0, 'Q1': 0, 'Q2': 13, 'Q3': 75, 'Q4': 12},
            {'MR': 2.0, 'physical_state': 'solution',
             'Q0': 0, 'Q1': 25, 'Q2': 60, 'Q3': 25, 'Q4': 0},
            {'MR': 3.28, 'physical_state': 'glass',
             'Q0': 0, 'Q1': 0, 'Q2': 2, 'Q3': 55, 'Q4': 43},
            {'MR': 3.28, 'physical_state': 'solution',
             'Q0': 1, 'Q1': 7, 'Q2': 33, 'Q3': 53, 'Q4': 7},
        ]),
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
    {
        'name': 'na-glass-q-distribution-vs-mr',
        'source_reference': f'{_BOOK}, Figure 5.4, p.90 (adapted from '
                            'Maekawa et al. 1991) + Table 5.6 p.103 '
                            'glass rows + p.90 anchor text',
        'status': 'ready',
        'independent_variables_json': '["MR"]',
        'dependent_variables_json': '["Q0", "Q1", "Q2", "Q3", "Q4"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol Na2O',
            'Q0-Q4': 'percent of Si sites'}),
        'source_conditions_json': json.dumps({
            'system': 'solid Na-silicate GLASS (not solution — the '
                      'glass->solution transform is the Table 5.6 '
                      'dataset)',
            'note': 'Anchor text p.90: MR=1 Na-metasilicate -> almost '
                    'completely Q2 with small Q1+Q3 (phase III, 50% '
                    'SiO2); MR=2 Na-disilicate -> virtually only Q3, '
                    'small Q2+Q4 (phase IV); MR=4 Na-tetrasilicate -> '
                    'Q3 and Q4 at 50% each. Points at MR '
                    '1.0/1.33/2.0/3.28 are EXACT (Table 5.6 glass '
                    'rows, cross-confirmed against the Fig 5.4 '
                    'curves); MR 4.0 from the anchor statement; '
                    'MR 0.5 is a curve read.'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [0.5, 4.0]}',
        'digitization_method': 'exact table rows + text anchors + '
                               'photo curve read (MR 0.5 only)',
        'digitization_error': 'MR 1.0-3.28 exact; MR 4.0 per anchor '
                              'text; MR 0.5 curve read est. +/-5 Qn%',
        'points_json': json.dumps([
            {'MR': 0.5, 'Q0': 8, 'Q1': 27, 'Q2': 52, 'Q3': 8, 'Q4': 0},
            {'MR': 1.0, 'Q0': 1, 'Q1': 14, 'Q2': 68, 'Q3': 17, 'Q4': 0},
            {'MR': 1.33, 'Q0': 0, 'Q1': 2, 'Q2': 52, 'Q3': 46, 'Q4': 0},
            {'MR': 2.0, 'Q0': 0, 'Q1': 0, 'Q2': 13, 'Q3': 75, 'Q4': 12},
            {'MR': 3.28, 'Q0': 0, 'Q1': 0, 'Q2': 2, 'Q3': 55, 'Q4': 43},
            {'MR': 4.0, 'Q0': 0, 'Q1': 0, 'Q2': 0, 'Q3': 50, 'Q4': 50},
        ]),
        'provenance_id': 'pspp book transcription 2026-07-18 (p.90)',
    },
    {
        'name': 'k-glass-q-distribution-vs-mr',
        'source_reference': f'{_BOOK}, Figure 5.5, p.90 (adapted from '
                            'Maekawa et al. 1991) + p.90 anchor text',
        'status': 'ready',
        'independent_variables_json': '["MR"]',
        'dependent_variables_json': '["Q0", "Q1", "Q2", "Q3", "Q4"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol K2O',
            'Q0-Q4': 'percent of Si sites'}),
        'source_conditions_json': json.dumps({
            'system': 'solid K-silicate GLASS',
            'note': 'Anchor text p.90: MR=1 K-metasilicate -> almost '
                    'completely Q2, small Q1+Q3 (phase I); MR=2 '
                    'K-disilicate -> virtually only Q3, small Q2+Q4 '
                    '(phase II); MR=4 K-tetrasilicate -> Q3 and Q4 at '
                    '50% each (phase III of K-glass). NO exact table '
                    'exists for K-glass — all non-anchor points are '
                    'curve reads; bands honestly wider than the Na '
                    'dataset.'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [0.6, 4.0]}',
        'digitization_method': 'photo curve read anchored by the p.90 '
                               'text statements (MR=1/2/4)',
        'digitization_error': 'curve reads est. +/-5 Qn%, +/-0.1 MR; '
                              'anchor-point splits (small Q1/Q3, '
                              'small Q2/Q4) estimated from the curves',
        'points_json': json.dumps([
            {'MR': 0.6, 'Q0': 5, 'Q1': 25, 'Q2': 58, 'Q3': 5, 'Q4': 0},
            {'MR': 1.0, 'Q0': 0, 'Q1': 10, 'Q2': 80, 'Q3': 8, 'Q4': 0},
            {'MR': 1.5, 'Q0': 0, 'Q1': 2, 'Q2': 55, 'Q3': 40, 'Q4': 0},
            {'MR': 2.0, 'Q0': 0, 'Q1': 0, 'Q2': 12, 'Q3': 78, 'Q4': 8},
            {'MR': 2.4, 'Q0': 0, 'Q1': 0, 'Q2': 5, 'Q3': 85, 'Q4': 8},
            {'MR': 3.3, 'Q0': 0, 'Q1': 0, 'Q2': 2, 'Q3': 68, 'Q4': 28},
            {'MR': 4.0, 'Q0': 0, 'Q1': 0, 'Q2': 0, 'Q3': 50, 'Q4': 50},
        ]),
        'provenance_id': 'pspp book transcription 2026-07-18 (p.90)',
    },
    {
        'name': 'silicate-solution-viscosity-vs-temperature',
        'source_reference': f'{_BOOK}, Figure 5.20, p.110',
        'status': 'ready',
        'independent_variables_json':
            '["temperature_C", "series"]',
        'dependent_variables_json': '["viscosity_cP"]',
        'units_json': json.dumps({
            'temperature_C': 'degC', 'viscosity_cP': 'cP (mPa.s)'}),
        'source_conditions_json': json.dumps({
            'series': {'na': 'Na-silicate MR=2',
                       'k': 'K-silicate MR=2.2'},
            'note': 'SAME concentration both series but the value is '
                    'NOT stated on the page — relative reference '
                    'curves, not absolute predictions. p.110: K '
                    'silicate viscosity ~10x lower than Na at same '
                    'MR.'}),
        'interpolation_policy': 'log-linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"temperature_C": [5, 30]}',
        'digitization_method': 'printed point-value labels read from '
                               'photo (each marker labeled) — not a '
                               'curve trace',
        'digitization_error': 'labels exact; temperatures from axis '
                              'gridlines, est. +/-1 degC',
        'points_json': json.dumps([
            {'series': 'Na-silicate MR=2', 'temperature_C': 5,
             'viscosity_cP': 5000},
            {'series': 'Na-silicate MR=2', 'temperature_C': 10,
             'viscosity_cP': 4500},
            {'series': 'Na-silicate MR=2', 'temperature_C': 15,
             'viscosity_cP': 3000},
            {'series': 'Na-silicate MR=2', 'temperature_C': 20,
             'viscosity_cP': 2000},
            {'series': 'Na-silicate MR=2', 'temperature_C': 25,
             'viscosity_cP': 1500},
            {'series': 'Na-silicate MR=2', 'temperature_C': 30,
             'viscosity_cP': 1000},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 5,
             'viscosity_cP': 420},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 10,
             'viscosity_cP': 400},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 15,
             'viscosity_cP': 270},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 20,
             'viscosity_cP': 200},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 25,
             'viscosity_cP': 160},
            {'series': 'K-silicate MR=2.2', 'temperature_C': 30,
             'viscosity_cP': 120},
        ]),
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
    {
        'name': 'mk750-strength-ph-vs-curing-time',
        'source_reference': f'{_BOOK.replace("Ch.5", "Ch.8")}, '
                            'Fig 8.18 + text pp.177-179 '
                            '(Na-silicate MR=1.70 100g + MK-750 '
                            '63.47g, Na:Al=1, cured at 80C)',
        'status': 'ready',
        'independent_variables_json': '["curing_hours"]',
        'dependent_variables_json':
            '["split_tensile_mpa", "ph_broken_sample"]',
        'units_json': json.dumps({
            'curing_hours': 'h at 80C',
            'split_tensile_mpa': 'MPa (Brazilian test, demolded hot, '
                                 'no drying)',
            'ph_broken_sample': 'pH'}),
        'source_conditions_json': json.dumps({
            'al_species_roles': 'Al(V) (-Al=O) reacts first — 1h '
                                'hardening; Al(IV) (-Al-O-Al-) slower '
                                '— 2h peak; Al(VI) (-Al-OH) needs '
                                'more energy/time — 4-4.5h peak',
            'dip_mechanism': 'pp.178-179: after ~5h strength DROPS '
                             '(min 4.26 MPa at 8h) while pH RISES to '
                             '12.44 — alkaline depolymerization/'
                             'cleavage of the freshly formed '
                             'framework; then NEW polymerization '
                             'phases; 20h plateau 6.90 MPa at lowest '
                             'pH 12.22. Strength and pH are '
                             'anticorrelated mirrors. Free water '
                             'sustains the polymerization/'
                             'depolymerization equilibrium — '
                             'subsequent DRYING STOPS IT.',
            'note': 'Strength values stated exactly in text (p.178 '
                    'says 6.80, p.179 says 6.83 for the 4h optimum — '
                    'as-printed variance, both kept); pH values from '
                    'printed figure labels, time-association '
                    'approximate.'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': json.dumps({
            'curing_hours': [1, 24],
            'note': 'NON-MONOTONIC (dip 5-8h) — linear interpolation '
                    'inside 4.5-20h carries the dip mechanism note; '
                    'the band spans honestly wide values there.'}),
        'digitization_method': 'text-stated values (strength) + '
                               'printed figure labels (pH)',
        'digitization_error': 'strength exact per text; pH '
                              'time-association est. +/-1h',
        'points_json': json.dumps([
            {'curing_hours': 1.0, 'split_tensile_mpa': 2.83},
            {'curing_hours': 2.0, 'split_tensile_mpa': 5.66,
             'ph_broken_sample': 12.38},
            {'curing_hours': 4.5, 'split_tensile_mpa': 6.80,
             'ph_broken_sample': 12.22},
            {'curing_hours': 8.0, 'split_tensile_mpa': 4.26,
             'ph_broken_sample': 12.44},
            {'curing_hours': 20.0, 'split_tensile_mpa': 6.90,
             'ph_broken_sample': 12.22},
        ]),
        'provenance_id': 'pspp book transcription 2026-07-18 '
                         '(pp.177-179)',
    },
    {
        'name': 'mk750-k-silicate-setting-class-vs-mr',
        'source_reference': f'{_BOOK.replace("Ch.5", "Ch.8")}, '
                            '§8.2.8 pp.179-180 + Fig 8.19 '
                            '(K-silicate 100g + MK-750 80g, 80C, '
                            'penetrometer)',
        'status': 'ready',
        'independent_variables_json': '["MR", "setting_class"]',
        'dependent_variables_json': '["setting_class_code"]',
        'units_json': json.dumps({
            'MR': 'mol SiO2 / mol K2O',
            'setting_class_code': '1=ultra-rapid(<1h), 2=complete-'
                                  'at-4h, 3=incomplete-at-4h, '
                                  '4=no-hardening-in-timeframe'}),
        'source_conditions_json': json.dumps({
            'note': 'Seven mixtures, text-stated classes: MR=1.23 '
                    'ultra rapid (<1h); MR=1.83 and 1.96 complete at '
                    '4h; MR>1.96 (2.08/2.24/2.43) need >4h; regular '
                    'commercial MR=2.85 does NOT harden within the '
                    'experiment timeframe at 80C. Fig 8.19 setting '
                    'curves exist for finer digitization later '
                    '(angled photo).'}),
        'interpolation_policy': 'none',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"MR": [1.23, 2.85]}',
        'digitization_method': 'text-stated classes',
        'digitization_error': '',
        'points_json': json.dumps([
            {'MR': 1.23, 'setting_class': 'ultra-rapid',
             'setting_class_code': 1},
            {'MR': 1.83, 'setting_class': 'complete-at-4h',
             'setting_class_code': 2},
            {'MR': 1.96, 'setting_class': 'complete-at-4h',
             'setting_class_code': 2},
            {'MR': 2.08, 'setting_class': 'incomplete-at-4h',
             'setting_class_code': 3},
            {'MR': 2.24, 'setting_class': 'incomplete-at-4h',
             'setting_class_code': 3},
            {'MR': 2.43, 'setting_class': 'incomplete-at-4h',
             'setting_class_code': 3},
            {'MR': 2.85, 'setting_class': 'no-hardening',
             'setting_class_code': 4},
        ]),
        'provenance_id': 'pspp book transcription 2026-07-18 '
                         '(pp.179-180)',
    },
    {
        'name': 'k-pss-exotherm-vs-cure-temperature',
        'source_reference': f'{_BOOK.replace("Ch.5", "Ch.8")}, '
                            '§8.2.9 p.180 + Fig 8.20 (Davidovits '
                            '1988; K-silicate MR=1.83 100g + MK-750 '
                            '80g)',
        'status': 'ready',
        'independent_variables_json': '["cure_temperature_c"]',
        'dependent_variables_json':
            '["exotherm_peak_c", "peak_time_min"]',
        'units_json': json.dumps({
            'cure_temperature_c': 'degC oven',
            'exotherm_peak_c': 'degC sample peak',
            'peak_time_min': 'minutes to peak'}),
        'source_conditions_json': json.dumps({
            'note': 'The cure-temperature kinetics ladder: heating '
                    'method changes KINETICS not chemistry; the '
                    'measured-curve floor for ReactionProgressModel '
                    'v1 (no Arrhenius fit until a cited Ea exists — '
                    'invariant I5).'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{"cure_temperature_c": [40, 85]}',
        'digitization_method': 'text-stated values',
        'digitization_error': '',
        'points_json': json.dumps([
            {'cure_temperature_c': 40, 'exotherm_peak_c': 70,
             'peak_time_min': 210},
            {'cure_temperature_c': 60, 'exotherm_peak_c': 100,
             'peak_time_min': 90},
            {'cure_temperature_c': 85, 'exotherm_peak_c': 115,
             'peak_time_min': 45},
        ]),
        'provenance_id': 'pspp book transcription 2026-07-18 (p.180)',
    },
    {
        'name': 'k-geopolymer-porosity-phases-vs-temperature',
        'source_reference': f'{_BOOK.replace("Ch.5", "Ch.8")}, '
                            'Table 8.8 p.194 (after Dan Perera and '
                            'Trautman 2005; K-geopolymer cured '
                            '80C/24h, heated ambient->1400C in air)',
        'status': 'ready',
        'independent_variables_json': '["temperature_c"]',
        'dependent_variables_json':
            '["open_porosity_pct", "xrd_phases"]',
        'units_json': json.dumps({
            'temperature_c': 'degC',
            'open_porosity_pct': '% open porosity',
            'xrd_phases': 'phase list (m=major, Am=amorphous, '
                          'Q=quartz, G=gehlenite 2CaO.Al2O3.SiO2, '
                          'K=kalsilite KAlSiO4, L=leucite KAlSi2O6, '
                          'CaP=Ca8Si5O18)'}),
        'source_conditions_json': json.dumps({
            'note': 'The thermal phase-evolution + porosity-evolution '
                    'benchmark (Findings 8/9 concrete): amorphous to '
                    '800C; kalsilite major at 1000C; leucite major '
                    'at 1200C; distorted kalsilite 1250-1400C; NO '
                    'significant melting at 1400C. Residual Q1-Q3 '
                    'siloxonates may precipitate as the insoluble '
                    'Ca-pentamer Ca8Si5O18 — a FUSING ingredient '
                    '(softens >1400C, lowers kalsilite melting from '
                    '1750C) that worsens thermal properties.'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': json.dumps({
            'temperature_c': [20, 1400],
            'note': 'xrd_phases is categorical — exact-temperature '
                    'rows only; porosity may interpolate with bands'}),
        'digitization_method': 'exact table transcription from photo',
        'digitization_error': '',
        'points_json': json.dumps([
            {'temperature_c': 20, 'open_porosity_pct': 29.5,
             'xrd_phases': 'Am(m), Q, CaP'},
            {'temperature_c': 500, 'open_porosity_pct': 58.5,
             'xrd_phases': 'Am(m), Q, CaP'},
            {'temperature_c': 800, 'open_porosity_pct': 50.4,
             'xrd_phases': 'Am(m), Q, CaP'},
            {'temperature_c': 1000, 'open_porosity_pct': 37.8,
             'xrd_phases': 'K(m), Q, G, CaP, L(trace)'},
            {'temperature_c': 1200, 'open_porosity_pct': 37.7,
             'xrd_phases': 'L(m), K'},
            {'temperature_c': 1250,
             'xrd_phases': 'distorted K(m), L'},
            {'temperature_c': 1300, 'open_porosity_pct': 30.5,
             'xrd_phases': 'distorted K(m), L(trace)'},
            {'temperature_c': 1350, 'xrd_phases': 'distorted K'},
            {'temperature_c': 1400, 'open_porosity_pct': 27.6,
             'xrd_phases': 'distorted K'},
        ]),
        'provenance_id': 'pspp book transcription 2026-07-18 (p.194)',
    },
    {
        'name': 'na-siloxonate-solubility-vs-temperature',
        'source_reference': f'{_BOOK}, Figure 5.22, p.112',
        'status': 'provisional-low-confidence',
        'independent_variables_json':
            '["temperature_C", "series"]',
        'dependent_variables_json': '["solubility_g_per_L"]',
        'units_json': json.dumps({
            'temperature_C': 'degC', 'solubility_g_per_L': 'g/liter'}),
        'source_conditions_json': json.dumps({
            'series': {'mr1': 'MR=1 Na-metasilicate pentahydrate',
                       'mr2': 'MR=2 Na-disilicate, 17% water',
                       'mr33': 'MR=3.3 Na-trisilicate, 17% water'}}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': json.dumps({
            'temperature_C': [10, 90],
            'solubility_g_per_L': [300, 900]}),
        'digitization_method': 'angled-photo curve read — axes and '
                               'shape reliable, point values NOT; '
                               'RE-SHOOT REQUESTED',
        'digitization_error': 'est. +/-50 g/L, +/-5 degC',
        'points_json': '[]',
        'qualitative_shape': 'All three series rise with temperature '
                             'over 10-90 degC within 300-900 g/L; '
                             'MR=1 and MR=2 lie well above MR=3.3 and '
                             'cross mid-range; MR=3.3 stays lowest. '
                             'Points intentionally absent pending '
                             're-digitization.',
        'provenance_id': 'pspp-1 book transcription 2026-07-18',
    },
]
