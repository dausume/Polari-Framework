"""
@module electrodevice.device_basis

The multiscale electronics ladder's first rung
(HARDWARE_SIMULATION_PLAN.md section 4): a SIMPLE electronic device
whose electrical parameters DERIVE from previously-simulated material
data, abstracted into a SPICE card, tested in a circuit driven by the
FPGA's pins.

First device: the **CNT-doped sol-gel composite resistor** — the
current-limiting resistor for the 4x4 LED grid the FPGA already
drives. Its conductivity comes from EXECUTING the existing msci
percolation model (cnt-solgel-percolation: CNT axial sigma in a
xerogel matrix), never from a hand-typed constant; provenance rides
on the row. Object coherence: the device, its SPICE card, and every
circuit run are rows in the tree, configurable AT the row.

@consumers
  - electrodevice.device_derive (derivation + card rendering)
  - electrodevice.spice_run (ngspice circuit tests)
  - electrodevice.device_api (the knob surface)
  - polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ElectronicDeviceDefinition(treeObject):
    """One physical device built from simulated materials. The
    material physics enters ONLY through sim_model (an executable
    msci model row); geometry fields are the design knobs."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # 'resistor' today; 'capacitor' (dielectric sol-gel) and
        # 'diode' (doped Si / CNT p-n) are the next rungs.
        device_type: str = 'resistor',
        # THE MATERIAL KNOB: the msci model row whose EXECUTION
        # yields the transport property (e.g. effectiveSigma S/m).
        sim_model: str = 'cnt-solgel-percolation',
        # Geometry knobs (a printed composite trace). The film
        # thickness makes the footprint honest: width = A / t.
        length_m: float = 0.002,
        cross_section_m2: float = 1.4e-8,
        film_thickness_m: float = 1e-4,
        # Transistor knobs (device_type nfet|pfet): which derived
        # SemiconductorProfile supplies gap/carrier type, and the
        # gate stack (sol-gel dielectric).
        semiconductor_profile: str = '',
        dielectric_material: str = 'sol-gel-silica',
        dielectric_thickness_m: float = 1e-7,
        # Derived at the last 'derive' act (never hand-set):
        sigma_s_per_m: float = 0.0,
        resistance_ohm: float = 0.0,
        threshold_v: float = 0.0,
        kp_a_per_v2: float = 0.0,
        r_on_ohm: float = 0.0,
        r_off_ohm: float = 0.0,
        derived_at: str = '',
        # Where every number came from (model inputs/outputs +
        # formula + the sim's own validity note).
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device_type = device_type
        self.sim_model = sim_model
        self.length_m = length_m
        self.cross_section_m2 = cross_section_m2
        self.film_thickness_m = film_thickness_m
        self.semiconductor_profile = semiconductor_profile
        self.dielectric_material = dielectric_material
        self.dielectric_thickness_m = dielectric_thickness_m
        self.sigma_s_per_m = sigma_s_per_m
        self.resistance_ohm = resistance_ohm
        self.threshold_v = threshold_v
        self.kp_a_per_v2 = kp_a_per_v2
        self.r_on_ohm = r_on_ohm
        self.r_off_ohm = r_off_ohm
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes


class SpiceModelCard(treeObject):
    """The SPICE abstraction of one device — embeddable .subckt text
    generated from the derived parameters, with provenance in the
    comments so the netlist itself says where its numbers came from."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device_name: str = '',
        version: int = 0,
        card_text: str = '',
        derived_from_json: str = '{}',
        generated_at: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.version = version
        self.card_text = card_text
        self.derived_from_json = derived_from_json
        self.generated_at = generated_at


class CircuitRunResult(treeObject):
    """One ngspice run of a circuit using the device — inputs,
    per-pin outputs, and an honest verdict, as a row."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device_name: str = '',
        circuit: str = 'fpga-pin-led',
        inputs_json: str = '{}',
        outputs_json: str = '{}',
        verdict: str = '',
        engine: str = 'ngspice',
        ran_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.circuit = circuit
        self.inputs_json = inputs_json
        self.outputs_json = outputs_json
        self.verdict = verdict
        self.engine = engine
        self.ran_at = ran_at
        self.notes = notes


#: The LED grid's current-limiting resistor: 2 mm trace, cross
#: section sized so the percolation-sim conductivity (~227 S/m at
#: 2 vol%) lands near 630 ohm — a sane LED limiter at 3.3 V.
SEED_DEVICES = [
    {'name': 'cnt-solgel-led-resistor', 'device_type': 'resistor',
     'sim_model': 'cnt-solgel-percolation',
     'length_m': 0.002, 'cross_section_m2': 1.4e-8,
     'film_thickness_m': 1e-4,   # 100 um paste trace -> W 140 um
     'notes': 'Current limiter for the renode-led-grid pins; derive '
              'before use.'},
    # CNT-network FETs (sol-gel gate dielectric): channel on-state
    # from the percolation sim; threshold/type from the doped-CNT
    # frontier-orbital profiles. Short fat channel = switch-grade Ron.
    {'name': 'cnt-nfet-led-switch', 'device_type': 'nfet',
     'sim_model': 'cnt-solgel-percolation',
     'semiconductor_profile': 'cnt-potash-doped',
     'length_m': 2e-5, 'cross_section_m2': 1.4e-8,
     'film_thickness_m': 1e-6,   # 1 um film -> W 14 mm (honest!)
     'notes': 'Low-side LED switch + inverter pull-down.'},
    {'name': 'cnt-pfet-inverter', 'device_type': 'pfet',
     'sim_model': 'cnt-solgel-percolation',
     'semiconductor_profile': 'cnt-p-doped',
     'length_m': 2e-5, 'cross_section_m2': 1.4e-8,
     'film_thickness_m': 1e-6,
     'notes': 'Inverter pull-up (complementary to the nfet).'},
]
