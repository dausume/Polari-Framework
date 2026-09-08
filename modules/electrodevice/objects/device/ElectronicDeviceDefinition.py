"""
@module electrodevice.objects.device.ElectronicDeviceDefinition

Row class ElectronicDeviceDefinition of the electrodevice module — one class per file (design §7), split
from device_basis.py (sap-2c). The class docstring below is the explanation.
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
