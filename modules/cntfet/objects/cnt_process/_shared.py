"""@module cntfet.objects.cnt_process._shared — what the cnt_process row classes share (constants, seeds, helpers); split from cnt_process_basis.py (sap-2c)."""

_PRIOR = ('engineering prior — no measured capability yet; '
          'TUNABLE, replace with line data')
SEED_ALIGNMENT_PROCESSES = [
    {'name': 's1-target-alignment', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'angle_sigma_deg': 3.0, 'source': _PRIOR,
     'confidence': 'low', 'notes': ''},
]
SEED_PLACEMENT_PROCESSES = [
    {'name': 's1-target-placement', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'pitch_mu_nm': 0.0, 'pitch_sigma_nm': 0.0,
     'missing_tube_prob': 0.02, 'source': _PRIOR,
     'confidence': 'low',
     'notes': 'pitch unused at tube_count = 1 (multi-tube arc)'},
]
SEED_PURIFICATION_PROCESSES = [
    {'name': 's1-target-purification',
     'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'semiconducting_purity': 0.9999,
     'diameter_mu_nm': 1.25, 'diameter_sigma_nm': 0.1,
     'rinse_applied': True, 'dream_design_context': False,
     'source': 'purity: [HIL19] DREAM working point pS ~ 99.99% '
               '(anchor hil19-cnts-per-cnfet context); diameter '
               'sigma: ' + _PRIOR,
     'confidence': 'medium',
     'notes': 'DREAM is a CIRCUIT mitigation — at one-tube scope '
              'a metallic tube is simply a dead device'},
]
SEED_CONTACT_PROCESSES = [
    {'name': 's1-target-contacts', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'rc_median_ohm': 5500.0, 'rc_sigma_ln': 0.2,
     'min_contact_length_nm': 20.0,
     'source': 'median: [VS1] extraction step (a) ([FC10] '
               'devices); sigma: ' + _PRIOR,
     'confidence': 'low',
     'notes': 'Franklin 2014 six-metal Rc(Lc) table = the S3+ '
              'upgrade path (anchor list item 11)'},
]
SEED_LITHOGRAPHY_PROCESSES = [
    {'name': 's1-target-litho', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'feature_sigma_nm': 1.0, 'overlay_sigma_nm': 2.0,
     'source': _PRIOR, 'confidence': 'low', 'notes': ''},
]
SEED_GATESTACK_PROCESSES = [
    {'name': 's1-target-gatestack', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'tox_sigma_nm': 0.1, 'kox_sigma': 0.5, 'vt_sigma_v': 0.05,
     'source': _PRIOR, 'confidence': 'low',
     'notes': 'vt sigma = interface/fixed charge; [HIL19] '
              'Extended Data distributions are the cited upgrade '
              'path once digitized'},
]
