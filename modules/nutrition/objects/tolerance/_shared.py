"""@module nutrition.objects.tolerance._shared — what the tolerance row classes share (constants, seeds, helpers); split from tolerance_basis.py (sap-2c)."""

TOLERANCE_PERIODS = ('dose', 'meal', 'day')
CONFIDENCE_GRADES = ('ul-grade', 'moderate', 'low')
def _t(name, substance, period, amount, unit, symptom, citation,
       confidence, qualifier='', per_kg=False, notes=''):
    return {'name': name, 'substance': substance, 'period': period,
            'threshold_amount': amount, 'unit': unit,
            'per_kg_body_mass': per_kg, 'symptom': symptom,
            'citation': citation, 'confidence': confidence,
            'qualifier': qualifier, 'is_prior': True,
            'provenance_id': 'nmp-2', 'notes': notes}
SEED_TOLERANCE_THRESHOLDS = [
    # ── fiber (no NASEM UL exists — say so) ──────────────
    _t('fermenting-fiber-dose', 'inulin-type-fiber', 'dose', 10.0,
       'g', 'bloating/flatulence from rapid colonic fermentation',
       'Bonnema et al. 2010 (J Am Diet Assoc); Grabitske & Slavin '
       '2009 review — GI onset commonly 5-10 g/dose for inulin-type '
       'fructans', 'moderate',
       qualifier='no NASEM UL exists for fiber; this is a comfort '
                 'threshold, not toxicity',
       notes='lower bound of the reported range is 5 g — sensitive '
             'people warn earlier'),
    # ── protein per-meal utilization (NOT toxicity) ──────
    _t('protein-meal-utilization', 'protein', 'meal', 0.4, 'g',
       'diminishing muscle-protein-synthesis return above the dose',
       'Schoenfeld & Aragon 2018 (JISSN) — ~0.4 g/kg/meal MPS '
       'plateau', 'moderate', per_kg=True,
       qualifier='UTILIZATION plateau, NOT toxicity — excess is '
                 'oxidized, not harmful at these doses'),
    # ── sugar alcohols (laxation) ────────────────────────
    _t('sorbitol-laxation', 'sorbitol', 'dose', 0.5, 'g',
       'osmotic laxation/diarrhea',
       'EFSA 2011 evaluations; Grabitske & Slavin 2009 — ~0.5 g/kg '
       'single-dose laxation threshold', 'moderate', per_kg=True),
    _t('xylitol-laxation', 'xylitol', 'dose', 0.3, 'g',
       'osmotic laxation/diarrhea',
       'Grabitske & Slavin 2009 review — ~0.3 g/kg single dose',
       'moderate', per_kg=True),
    _t('erythritol-laxation', 'erythritol', 'dose', 0.66, 'g',
       'osmotic laxation (better tolerated than other polyols)',
       'Storey et al. 2007 — no effect at 0.66 g/kg in adults',
       'moderate', per_kg=True,
       qualifier='threshold is the highest NO-effect dose tested'),
    # ── FODMAP per-serving cutoffs (Monash published VALUES,
    #    cited as facts; their database stays untouched) ───
    _t('fructan-serving', 'fructans', 'meal', 0.3, 'g',
       'FODMAP-driven bloating in sensitive people',
       'Varney et al. 2017 (J Gastroenterol Hepatol) — published '
       'Monash low-FODMAP cutoff per serve for oligos', 'low',
       qualifier='general-population sensitivity varies widely; '
                 'IBS management itself is out of scope '
                 '(decision 3)'),
    _t('lactose-serving', 'lactose', 'meal', 1.0, 'g',
       'lactose-intolerance symptoms in low-lactase people',
       'Varney et al. 2017 — published low-FODMAP lactose cutoff '
       'per serve', 'low',
       qualifier='most lactase-persistent adults tolerate far more'),
    # ── sodium / UL-grade rows that carry symptoms ───────
    _t('sodium-cdrr-day', 'sodium', 'day', 2300.0, 'mg',
       'chronic blood-pressure elevation risk',
       'NASEM 2019 sodium CDRR', 'ul-grade'),
    _t('vitamin-c-gi-day', 'vitamin-c', 'day', 2000.0, 'mg',
       'osmotic diarrhea/GI distress',
       'NASEM UL (2000); NIH ODS vitamin C fact sheet', 'ul-grade'),
    _t('niacin-flush-day', 'vitamin-b3', 'day', 35.0, 'mg',
       'skin flushing (supplemental nicotinic acid)',
       'NASEM UL — flushing endpoint', 'ul-grade',
       qualifier='applies to SUPPLEMENTAL nicotinic acid, not food '
                 'niacin'),
    _t('iron-gi-day', 'iron', 'day', 45.0, 'mg',
       'acute GI upset (constipation/nausea)',
       'NASEM UL — GI endpoint', 'ul-grade'),
    _t('magnesium-supplemental-day', 'magnesium-supplemental', 'day',
       350.0, 'mg', 'osmotic diarrhea',
       'NASEM UL — supplemental Mg only', 'ul-grade',
       qualifier='food magnesium does not cause this; the row is '
                 'about supplements'),
    # ── decision 9: glycemic load ────────────────────────
    _t('glycemic-load-meal', 'glycemic-load', 'meal', 20.0, 'GL',
       'a glycemic spike-and-dip (energy slump) in healthy people',
       'Atkinson, Foster-Powell & Brand-Miller 2008 (Diabetes '
       'Care) international GI/GL tables; GL>20 = the published '
       '"high" convention', 'moderate',
       qualifier='healthy-person imbalance framing — diabetes '
                 'management is out of scope (decision 3); GI '
                 'values come from published papers, never the '
                 'proprietary Sydney database'),
    # ── decision 9: acidity / reflux triggers (LOW confidence,
    #    labeled — the evidence is weaker than UL-grade) ───
    _t('meal-acid-share', 'meal-acidity', 'meal', 0.5, 'fraction',
       'reflux/heartburn in susceptible people',
       'dietary-trigger surveys (heterogeneous evidence)', 'low',
       qualifier='citrus/tomato mass share of the meal; a comfort '
                 'flag, not a rule',
       notes='threshold = half the meal by mass being high-acid '
             'ingredients'),
    _t('highfat-large-meal', 'meal-fat-load', 'meal', 40.0, 'g',
       'reflux risk + delayed gastric emptying discomfort',
       'reflux trigger literature (heterogeneous)', 'low',
       qualifier='the high-fat x LARGE-meal combination is the '
                 'trigger; fat alone in modest meals is fine'),
    _t('trigger-categories', 'reflux-trigger-categories', 'meal',
       0.0, 'flag',
       'reflux triggers for some people (carbonation, caffeine, '
       'mint, chocolate)',
       'trigger-category surveys (heterogeneous)', 'low',
       qualifier='presence flag, not a dose — noted, never blocked'),
]
