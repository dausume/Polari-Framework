"""
@module cntfet.custom.cnt_digitized_fc10

S2c (2026-08-21): PROGRAMMATIC digitization of [VS1] Fig.7(a) —
the Lg = 15 nm Id-Vds families of the [FC10] calibration device
(polarity flipped to n-type by [VS1]; v_xo extraction context:
Rs = 5.5 kOhm, SS = 135 mV/dec assumed, Cox = 0.156 fF/um).

This file IS the D18 record: raw pixel centroids + the complete
transformation history + the quantified error budget. Nothing here
was eyeballed — symbols were extracted by color-mask + white-
interior connected components from a 300-dpi render of the legally
free arXiv:1503.04397 author copy, and verified by a cross-marker
overlay re-render.

Transformation history (D18):
  source render   pdftoppm -r 300, page 5 -> 2550x3301 px
  x calibration   least-squares over the five Vds tick labels
                  (0..0.4 V): vds = (px - 474.3)/1106.7
                  [residuals <= 3 px ~ 3 mV]
  y calibration   the '0','5','10','15' Id label centers
                  (1125.5 / 1028.8 / 932.0 / 834.5 px — linear to
                  <1 px): id_ua = (1125.5 - py)/19.4
  symbol finding  color masks (blue/green/red/cyan rims) + white
                  circle interiors (scipy.ndimage.label), ring-
                  color vote at radius+3 px; centroid of interior
  error budget    per point: calibration +-3 px systematic +
                  centroid +-2 px random -> +-0.005 V, +-0.26 uA;
                  symbol radius ~9 px (0.46 uA) bounds worst case
  coverage        22/17/13/6 symbols per curve (ov +0.50/+0.25/
                  +0.00/-0.25); symbols whose rims fuse with the
                  model line or a neighbour have no separable
                  white interior and are NOT extracted — missing
                  points are a stated method limit, never
                  interpolated in.

@consumers
  - cntfet.cnt_reference_papers_seed (the anchor row wrapping this)
  - cntfet.cnt_calibration_seed (curve residuals)
  - cntfet.cntfet_selftest
"""

# Overdrive label -> |Vgs - Vt| in volts (Vg step 0.25 V per the
# figure legend; 'ov-0.25' is 0.25 V below threshold).
OVERDRIVES_V = {'ov+0.50': 0.50, 'ov+0.25': 0.25,
                'ov+0.00': 0.00, 'ov-0.25': -0.25}

X_CALIBRATION = {'intercept_px': 474.3, 'px_per_v': 1106.7,
                 'residual_px': 3}
Y_CALIBRATION = {'zero_px': 1125.5, 'px_per_ua': 19.4,
                 'label_centers_px': {'0': 1125.5, '5': 1028.8,
                                      '10': 932.0, '15': 834.5}}
ERROR_BUDGET = {'sigma_vds_v': 0.005, 'sigma_id_ua': 0.26,
                'worst_case_id_ua': 0.46,
                'basis': 'calibration +-3 px + centroid +-2 px; '
                         'symbol radius ~9 px'}

FIG7A_POINTS = {
    'ov+0.50': [
        {'vds_v': 0.044, 'id_ua': 2.509, 'px': [523.0, 1076.8]},
        {'vds_v': 0.0587, 'id_ua': 3.317, 'px': [539.3, 1061.2]},
        {'vds_v': 0.078, 'id_ua': 3.584, 'px': [560.6, 1056.0]},
        {'vds_v': 0.0896, 'id_ua': 4.87, 'px': [573.4, 1031.0]},
        {'vds_v': 0.105, 'id_ua': 5.724, 'px': [590.5, 1014.5]},
        {'vds_v': 0.1196, 'id_ua': 6.361, 'px': [606.7, 1002.1]},
        {'vds_v': 0.135, 'id_ua': 7.105, 'px': [623.7, 987.7]},
        {'vds_v': 0.1496, 'id_ua': 7.656, 'px': [639.8, 977.0]},
        {'vds_v': 0.1643, 'id_ua': 8.286, 'px': [656.1, 964.8]},
        {'vds_v': 0.1803, 'id_ua': 9.005, 'px': [673.8, 950.8]},
        {'vds_v': 0.1954, 'id_ua': 9.604, 'px': [690.5, 939.2]},
        {'vds_v': 0.2098, 'id_ua': 10.107, 'px': [706.5, 929.4]},
        {'vds_v': 0.2239, 'id_ua': 10.495, 'px': [722.1, 921.9]},
        {'vds_v': 0.2574, 'id_ua': 11.028, 'px': [759.1, 911.5]},
        {'vds_v': 0.2697, 'id_ua': 12.139, 'px': [772.8, 890.0]},
        {'vds_v': 0.2857, 'id_ua': 12.781, 'px': [790.5, 877.5]},
        {'vds_v': 0.3009, 'id_ua': 13.374, 'px': [807.3, 866.0]},
        {'vds_v': 0.3154, 'id_ua': 13.861, 'px': [823.3, 856.6]},
        {'vds_v': 0.3304, 'id_ua': 14.072, 'px': [840.0, 852.5]},
        {'vds_v': 0.3455, 'id_ua': 14.895, 'px': [856.7, 836.5]},
        {'vds_v': 0.3608, 'id_ua': 15.06, 'px': [873.6, 833.3]},
        {'vds_v': 0.3754, 'id_ua': 15.118, 'px': [889.8, 832.2]},
    ],
    'ov+0.25': [
        {'vds_v': 0.048, 'id_ua': 1.406, 'px': [527.4, 1098.2]},
        {'vds_v': 0.0624, 'id_ua': 1.938, 'px': [543.3, 1087.9]},
        {'vds_v': 0.1043, 'id_ua': 4.008, 'px': [589.8, 1047.8]},
        {'vds_v': 0.1214, 'id_ua': 3.817, 'px': [608.7, 1051.4]},
        {'vds_v': 0.1656, 'id_ua': 6.655, 'px': [657.5, 996.4]},
        {'vds_v': 0.1809, 'id_ua': 7.268, 'px': [674.5, 984.5]},
        {'vds_v': 0.2094, 'id_ua': 6.832, 'px': [706.0, 993.0]},
        {'vds_v': 0.2258, 'id_ua': 7.701, 'px': [724.2, 976.1]},
        {'vds_v': 0.2416, 'id_ua': 6.839, 'px': [741.7, 992.8]},
        {'vds_v': 0.256, 'id_ua': 8.458, 'px': [757.6, 961.4]},
        {'vds_v': 0.2704, 'id_ua': 9.12, 'px': [773.5, 948.6]},
        {'vds_v': 0.2857, 'id_ua': 8.463, 'px': [790.5, 961.3]},
        {'vds_v': 0.3002, 'id_ua': 8.545, 'px': [806.6, 959.7]},
        {'vds_v': 0.3305, 'id_ua': 7.814, 'px': [840.1, 973.9]},
        {'vds_v': 0.3612, 'id_ua': 8.81, 'px': [874.0, 954.6]},
        {'vds_v': 0.3755, 'id_ua': 8.888, 'px': [889.9, 953.1]},
        {'vds_v': 0.3908, 'id_ua': 9.173, 'px': [906.8, 947.5]},
    ],
    'ov+0.00': [
        {'vds_v': 0.0912, 'id_ua': 1.486, 'px': [575.2, 1096.7]},
        {'vds_v': 0.106, 'id_ua': 0.847, 'px': [591.6, 1109.1]},
        {'vds_v': 0.136, 'id_ua': 1.982, 'px': [624.8, 1087.1]},
        {'vds_v': 0.1513, 'id_ua': 2.239, 'px': [641.7, 1082.1]},
        {'vds_v': 0.1657, 'id_ua': 2.413, 'px': [657.7, 1078.7]},
        {'vds_v': 0.1961, 'id_ua': 2.739, 'px': [691.4, 1072.4]},
        {'vds_v': 0.2704, 'id_ua': 1.315, 'px': [773.6, 1100.0]},
        {'vds_v': 0.3008, 'id_ua': 3.011, 'px': [807.2, 1067.1]},
        {'vds_v': 0.3153, 'id_ua': 3.129, 'px': [823.3, 1064.8]},
        {'vds_v': 0.3305, 'id_ua': 4.697, 'px': [840.1, 1034.4]},
        {'vds_v': 0.3454, 'id_ua': 3.143, 'px': [856.6, 1064.5]},
        {'vds_v': 0.3608, 'id_ua': 4.321, 'px': [873.6, 1041.7]},
        {'vds_v': 0.3905, 'id_ua': 3.608, 'px': [906.5, 1055.5]},
    ],
    'ov-0.25': [
        {'vds_v': 0.136, 'id_ua': 0.303, 'px': [624.8, 1119.6]},
        {'vds_v': 0.1809, 'id_ua': 0.311, 'px': [674.5, 1119.5]},
        {'vds_v': 0.2104, 'id_ua': 0.359, 'px': [707.1, 1118.5]},
        {'vds_v': 0.3006, 'id_ua': 0.332, 'px': [807.0, 1119.1]},
        {'vds_v': 0.3455, 'id_ua': 0.404, 'px': [856.7, 1117.7]},
        {'vds_v': 0.3752, 'id_ua': 1.537, 'px': [889.5, 1095.7]},
    ],
}
