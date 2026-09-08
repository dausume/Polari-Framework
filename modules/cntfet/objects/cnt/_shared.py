"""@module cntfet.objects.cnt._shared — what the cnt row classes share (constants, seeds, helpers); split from cnt_basis.py (sap-2c)."""

SEED_CNT_MATERIALS = [
    {'name': 'cnt-16-0', 'chirality_n': 16, 'chirality_m': 0,
     'notes': 'S1 tube: zigzag (16,0), nearest clean chirality to '
              'the [FC10] d~1.2 nm calibration tube. Derive before '
              'use.'},
]
SEED_CNT_GEOMETRIES = [
    {'name': 'cnt-s1-lg15', 'lg_nm': 15.0, 'l_ext_nm': 0.0,
     'l_c_nm': 20.0, 'tube_count': 1, 'pitch_nm': 0.0,
     'notes': 'S1: one tube, Lg = 15 nm ([VS1] v_xo calibration '
              'flagship). pitch/tube_count aggregation = S2+.'},
    # fi-4 comparator: the same stack at a relaxed Lg = 30 nm so the
    # competitive scoring page has a real second FET (better SCE /
    # DIBL, lower v_xo and drive — the trade-off the terms expose).
    {'name': 'cnt-s1-lg30', 'lg_nm': 30.0, 'l_ext_nm': 0.0,
     'l_c_nm': 20.0, 'tube_count': 1, 'pitch_nm': 0.0,
     'notes': 'Comparator geometry: Lg = 30 nm, otherwise S1. Inside '
              'the [VS1] v_xo(Lg) fit range.'},
    # fv-6 comparator: AGGRESSIVE Lg = 10 nm — the short-channel
    # end of the trade-off (higher v_xo / drive, WORSE DIBL and
    # n_ss as lambda/Lg grows). Below the [FC10] Lg = 15 nm data
    # point, so the v_xo(Lg) fit is an EXTRAPOLATION here.
    {'name': 'cnt-s1-lg10', 'lg_nm': 10.0, 'l_ext_nm': 0.0,
     'l_c_nm': 20.0, 'tube_count': 1, 'pitch_nm': 0.0,
     'notes': 'fv-6 comparator geometry: Lg = 10 nm, otherwise S1. '
              'Extrapolates the [VS1] v_xo(Lg) fit below its 15 nm '
              'flagship — labeled, not hidden.'},
]
SEED_GATE_STACKS = [
    {'name': 'cnt-s1-hfo2-gaa', 'geometry': 'gaa-cylindrical',
     'dielectric_material': 'HfO2', 't_ox_nm': 3.0, 'k_ox': 16.0,
     'notes': 'GAA idealization ([VS1] Fig.1/eq.(1)); k_ox = 16 as '
              'in [VS1] Fig.5. EOT ~ 0.73 nm (paper Fig.2 context '
              '~0.7 nm). Derive before use.'},
    # fv-6 comparator: THINNER oxide (t_ox = 2 nm, same k_ox = 16,
    # EOT ~ 0.49 nm) — larger Cox -> larger Cinv, gm and Cgg; better
    # electrostatic control (shorter lambda) at the cost of gate
    # leakage the S1 model does NOT represent (honest omission).
    {'name': 'cnt-s1-hfo2-gaa-tox2', 'geometry': 'gaa-cylindrical',
     'dielectric_material': 'HfO2', 't_ox_nm': 2.0, 'k_ox': 16.0,
     'notes': 'fv-6 comparator gate stack: HfO2 t_ox = 2 nm, k_ox = '
              '16 (EOT ~ 0.49 nm). Gate tunnelling leakage is NOT '
              'modeled at S1 — the thinner oxide only shows its '
              'upside here. Derive before use.'},
]
SEED_CNT_CONTACTS = [
    {'name': 'cnt-s1-pd-contact', 'metal': 'Pd', 'rc_ohm': 5500.0,
     'rc_source': '[VS1] Sec.II.D extraction step (a): Rs = 5.5 '
                  'kOhm per the reported [FC10] experimental data',
     'rc_confidence': 'medium',
     'notes': 'Per-terminal prior, includes the quantum share; the '
              'derived rq_floor_ohm (~3.23 kOhm) is the physical '
              'floor. S1 keeps ONE prior; Rc(Lc) sub-model = S2 '
              '(Franklin 2014 six-metal table).'},
]
SEED_CNT_TRANSPORT = [
    {'name': 'cnt-s1-vs-transport',
     'physics_fidelity': 'VS_MINIMAL',
     'vt0_v': 0.3, 'efsd_ev': 0.1,
     'notes': 'VS-CNFET-derived (independent clean-room '
              'implementation; NOT the Stanford code). Derive '
              'stamps vxo/mu/nss/dibl/dvt from [VS1] eqs (4),(8),'
              '(9).'},
]
SEED_CNT_PARASITICS = [
    {'name': 'cnt-s1-no-parasitics', 'c_par_f': 0.0,
     'notes': 'S1 is DC-only; extrinsic parasitics enter with '
              '[VS2] at S2+.'},
]
SEED_CNT_DEVICES = [
    {'name': 'cnt-aligned-s1', 'polarity': 'n',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg15',
     'gate_stack': 'cnt-s1-hfo2-gaa', 'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'THE S1 device: one aligned semiconducting tube, DC '
              'Id-Vg/Id-Vd only. n-type ([VS1] flips the [FC10] '
              'p-type polarity; physics symmetric). Derive before '
              'use.'},
    {'name': 'cnt-aligned-s1-lg30', 'polarity': 'n',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg30',
     'gate_stack': 'cnt-s1-hfo2-gaa', 'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'fi-4 COMPARATOR: S1 stack at Lg = 30 nm, so the '
              'per-FET scoring page ranks two real devices. Until '
              'derived it scores 0 as UNPROVEN (validity gate) — '
              'POST {"action": "derive"} to make it a candidate.'},
    # ---- fv-6 comparator set (FET_VIEWS_PLAN §1 fv-6) -------------
    {'name': 'cnt-aligned-s1-lg10', 'polarity': 'n',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg10',
     'gate_stack': 'cnt-s1-hfo2-gaa', 'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'fv-6 COMPARATOR (aggressive Lg): S1 stack at Lg = 10 '
              'nm. Exposes the short-channel trade-off on the '
              'competitive scoring page — higher v_xo / gm per G0 '
              'bought with WORSE DIBL and n_ss (lambda/Lg grows). '
              'v_xo(Lg) is extrapolated below the [FC10] 15 nm '
              'point. Unproven -> scores 0 until derived — POST '
              '{"action": "derive"}.'},
    {'name': 'cnt-aligned-s1-tox2', 'polarity': 'n',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg15',
     'gate_stack': 'cnt-s1-hfo2-gaa-tox2',
     'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'fv-6 COMPARATOR (thinner oxide): S1 at t_ox = 2 nm '
              'HfO2. Exposes the electrostatics trade-off — larger '
              'Cinv/gm and tighter SCE (shorter lambda) vs the gate '
              'leakage S1 does NOT model, so the page shows only '
              'its upside (stated). Unproven -> scores 0 until '
              'derived — POST {"action": "derive"}.'},
    {'name': 'cnt-aligned-s1-p', 'polarity': 'p',
     'material': 'cnt-16-0', 'geometry': 'cnt-s1-lg15',
     'gate_stack': 'cnt-s1-hfo2-gaa', 'contact': 'cnt-s1-pd-contact',
     'transport': 'cnt-s1-vs-transport',
     'parasitics': 'cnt-s1-no-parasitics',
     'temperature_k': 300.0,
     'manufacturing_regime': 'aggressively_scaled',
     'process_set': 's1-target-line',
     'notes': 'fv-6 COMPARATOR ([VS1] p-twin): S1 rows with polarity '
              '= p. HONESTY: today the polarity flag is a LABEL — '
              'derive/build_vs_params always solve the n-type '
              'system (ptype 0) and the mirrored p-system (solve at '
              '(-Vg,-Vd), negate Id; [VS1] premise ii) is exercised '
              'only inside the inverter/cell twins (ptype 1). So '
              'this row derives to the SAME numbers as S1 and ties '
              'it on the scoring page until derive consumes '
              'polarity; it exists so the pair is visible as a '
              'pair. Unproven -> scores 0 until derived — POST '
              '{"action": "derive"}.'},
]
