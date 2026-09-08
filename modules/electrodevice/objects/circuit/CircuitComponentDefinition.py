"""
@module electrodevice.objects.circuit.CircuitComponentDefinition

Row class CircuitComponentDefinition of the electrodevice module — one class per file (design §7), split
from circuit_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CircuitComponentDefinition(treeObject):
    """One placed component. pins_json wires it: an ordered JSON
    list of net names (order = the SPICE element's node order)."""

    @treeObjectInit
    def __init__(self, name: str = '', circuit_name: str = '',
                 kind: str = 'resistor',
                 # kind-specific values: vsource {'dc': V},
                 # resistor {'ohms': R}, capacitor {'farads': C,
                 # 'ic': V?}, inductor {'henries': L},
                 # diode/led {'model': name?}.
                 params_json: str = '{}',
                 pins_json: str = '[]',
                 # kind 'device': the ElectronicDeviceDefinition row
                 # whose DERIVED card supplies the subckt (material
                 # provenance rides that card).
                 device_name: str = '',
                 description: str = '', manager=None):
        self.name = name
        self.circuit_name = circuit_name
        self.kind = kind
        self.params_json = params_json
        self.pins_json = pins_json
        self.device_name = device_name
        self.description = description
