"""
@module magnetics.objects.magnet_circuit.MagneticElementDefinition

Row class MagneticElementDefinition of the magnetics module — one class per file (design §7), split
from magnet_circuit_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from magnetics.objects.magnet_circuit._shared import ELEMENT_KINDS

class MagneticElementDefinition(treeObject):
    """One placed element. nodes_json wires it: an ordered JSON list
    of TWO flux-node names (positive terminal first for sources).

    params_json per kind:
      mmf-coil     {'turns': N, 'amps': I}   (MMF = N*I, + at first
                                              node)
      core-segment {'length_m': l, 'area_m2': A,
                    'material_ref': '<MagneticMaterialOption>'}
      air-gap      {'length_m': l, 'area_m2': A,
                    'fringing_factor': f?}   (effective area = f*A,
                                              default 1.0 — the
                                              honesty knob, fringing
                                              widens the gap area)
      magnet       {'length_m': l_m, 'area_m2': A,
                    'material_ref': '<hard option>'}  (Thevenin: MMF
                    = H_c*l_m, internal reluctance from the row's
                    mu_r_eff — refuses a material without h_c_ka_m)
      leakage-path {'reluctance_per_wb': R}  (an explicit modeled
                    leakage — a prior until measured)
      flux-probe   {}                        (zero-MMF source branch:
                    the ammeter of the analogy)
    """

    @treeObjectInit
    def __init__(self, name: str = '', circuit_name: str = '',
                 kind: str = 'core-segment', params_json: str = '{}',
                 nodes_json: str = '[]', description: str = '',
                 manager=None):
        self.name = name
        self.circuit_name = circuit_name
        self.kind = (kind if kind in ELEMENT_KINDS
                     else 'core-segment')
        self.params_json = params_json
        self.nodes_json = nodes_json
        self.description = description
