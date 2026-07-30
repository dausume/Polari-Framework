"""
@module motors.motor_basis

SECTION C (mag-5 core): MOTORS AS A LADDER OF BUILDABLE SAMPLES
(Dustin 2026-07-29: "start as simple as we can and go to more
advanced, both in terms of tolerances and in terms of samples
people can build", end goal = the dual-stator axial-flux machine).

- MotorDesignDefinition rows: one motor design per row, carrying
  its LADDER RUNG (M0..M3), its §2c tolerance tier (T0..T3), its
  topology + parameters, the materials BY CATALOG REFERENCE
  (mag-2r roles decide viability; gates/watermarks travel), and
  build_requirements_json — the builder-facing sample spec (tools,
  materials, skills, rough hours), easiest rung first.
- MotorVerificationRun rows: NEVER seeded — observed state only.
  M0's verification method is TIME ITSELF: command N pulses at
  1 Hz, count steps taken, compare accumulated rotation against
  wall-clock progression; missed steps over hours ARE the quality
  metric. Measured runs are what earn made-and-measured.

@consumers motors.motor_designer, motors.motor_api, polariServer
"""

from objectTreeDecorators import treeObject, treeObjectInit

MOTOR_TOPOLOGIES = ('lavet-clock-stepper', 'radial-reluctance',
                    'axial-dual-stator')
LADDER_RUNGS = ('M0', 'M1', 'M2', 'M3')
TOLERANCE_TIERS = ('T0', 'T1', 'T2', 'T3')


class MotorDesignDefinition(treeObject):
    """One motor design = one rung of the ladder made concrete."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 topology='lavet-clock-stepper', ladder_rung='M0',
                 tolerance_tier='T0', params_json='{}',
                 drive_json='{}', build_requirements_json='{}',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.topology = (topology if topology in MOTOR_TOPOLOGIES
                         else 'lavet-clock-stepper')
        self.ladder_rung = (ladder_rung
                            if ladder_rung in LADDER_RUNGS else 'M0')
        self.tolerance_tier = (tolerance_tier
                               if tolerance_tier in TOLERANCE_TIERS
                               else 'T0')
        #: Topology-specific geometry/winding/materials — material
        #: slots are MagneticMaterialOption names (roles checked by
        #: the designer, gates travel). See motor_designer for the
        #: per-topology vocabularies.
        self.params_json = params_json
        #: {'rate_hz': f, 'kind': 'alternating-pulse' | '3-phase'}.
        self.drive_json = drive_json
        #: {'tools': [...], 'materials': [{'ref': catalog-or-item,
        #: 'note': ...}], 'skills': [...], 'rough_hours': h} — the
        #: buildable-sample spec, honest difficulty like the
        #: research-tools tree.
        self.build_requirements_json = build_requirements_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class MotorVerificationRun(treeObject):
    """One verification run — sim or MEASURED (never seeded; runs
    are observed state). For M0 the comparison target is time
    progression itself."""

    @treeObjectInit
    def __init__(self, name='', design_ref='',
                 kind='sim-quasi-static', steps_commanded=0,
                 steps_taken=0, duration_s=0.0,
                 clock_error_s=0.0, notes='', manager=None):
        self.name = name
        self.design_ref = design_ref
        #: 'sim-quasi-static' | 'measured' — only 'measured' rows
        #: count toward made-and-measured.
        self.kind = kind
        self.steps_commanded = steps_commanded
        self.steps_taken = steps_taken
        self.duration_s = duration_s
        #: Accumulated error vs the expected rotation-from-time
        #: (missed steps / rate) — THE clock metric.
        self.clock_error_s = clock_error_s
        self.notes = notes


#: The ladder, easiest buildable sample first. Every rung names its
#: verification method and its builder spec; higher rungs exist as
#: designs TODAY (simulation is open at every realization level)
#: while their claims stay watermarked.
SEED_MOTOR_DESIGNS = [
    {
        'name': 'clock-lavet-m0',
        'display_name': 'M0 — Lavet clock stepper (the control '
                        'case)',
        'description': 'The quartz-clock mechanism: ONE coil, one '
                       'tiny PM rotor disc, asymmetric stator '
                       'notches making detent positions; '
                       'alternating-polarity pulses at 1 Hz step '
                       'it 180 deg. Smallest, lowest-power, '
                       'lowest-tolerance rung — and the clock IS '
                       'the instrument: rotation vs time '
                       'progression, missed steps over hours = '
                       'the metric.',
        'topology': 'lavet-clock-stepper',
        'ladder_rung': 'M0', 'tolerance_tier': 'T0',
        'params_json': '{"rotor_material": '
                       '"opt-bonded-hexaferrite-geopolymer", '
                       '"stator_material": '
                       '"opt-geopolymer-ferrite", '
                       '"rotor_diameter_m": 0.006, '
                       '"rotor_thickness_m": 0.002, '
                       '"gap_base_m": 0.0008, '
                       '"gap_asym_m": 0.0004, '
                       '"overlap_area_m2": 1.2e-5, '
                       '"coil_turns": 1500, '
                       '"wire_awg": 44, '
                       '"bobbin_window_mm2": 12.0, '
                       '"mean_turn_length_mm": 14.0, '
                       '"coil_amps": 0.02, '
                       '"magnet_length_m": 0.002}',
        'drive_json': '{"rate_hz": 1.0, '
                      '"kind": "alternating-pulse"}',
        'build_requirements_json': '{"tools": ["wax-printed or '
                       'hand-cut mold (mold-1 rules)", '
                       '"magnetizing pulse (the buildable coil '
                       'fixture, §1b)", "1 Hz pulse source (555/'
                       'Arduino class)", "hand winder"], '
                       '"materials": [{"ref": "magnet-wire-copper",'
                       ' "note": "~30 AWG, one small spool '
                       '(mag-1 cited)"}, {"ref": '
                       '"opt-bonded-hexaferrite-geopolymer", '
                       '"note": "one 6 mm rotor disc casting"}, '
                       '{"ref": "opt-geopolymer-ferrite", "note": '
                       '"one small stator casting"}], '
                       '"skills": ["casting (the pot workflow)", '
                       '"coil winding (count turns)"], '
                       '"rough_hours": 4}',
        'is_prior': True, 'provenance_id': 'mag-5',
        'notes': 'Rotor material is literature-demonstrated '
                 '(bonded hexaferrite) — sim open, cost via the '
                 'recipe chain, BUSINESS gated until a measured '
                 'run lands. A bought watch-movement rotor is the '
                 'honest fallback while our casting is unproven. '
                 'Pulse current 20 mA: OUR cast detent is far '
                 'coarser than a factory movement, so the pulse '
                 'must overwhelm it (the sim shows the C>2D hop '
                 'condition); commercial clocks run uA-class '
                 'pulses against um-class detents.',
    },
    {
        'name': 'reluctance-6s4p-m1',
        'display_name': 'M1 — 6-slot/4-pole reluctance demo',
        'description': 'Zero permanent magnets: torque from '
                       'saliency alone — every material costed '
                       'TODAY; honestly feeble at mu~2, and the '
                       'point is closing the full loop (cast, '
                       'wind, drive, spin).',
        'topology': 'radial-reluctance',
        'ladder_rung': 'M1', 'tolerance_tier': 'T0',
        'params_json': '{"stator_material": '
                       '"opt-geopolymer-ferrite", '
                       '"rotor_material": '
                       '"opt-geopolymer-ferrite", '
                       '"slots": 6, "poles": 4, '
                       '"gap_base_m": 0.0006, '
                       '"tooth_area_m2": 4e-5, '
                       '"coil_turns": 300, "coil_amps": 0.5, '
                       '"wire_awg": 26, '
                       '"bobbin_window_mm2": 72.0, '
                       '"mean_turn_length_mm": 35.0, '
                       '"saliency_ratio": 3.0, '
                       '"load_angle_deg": -45}',
        'drive_json': '{"rate_hz": 5.0, "kind": "3-phase"}',
        'build_requirements_json': '{"tools": ["molds for 6-tooth '
                       'stator + salient rotor", "3-phase drive '
                       '(SimpleFOC class, mag-1 cited)", "608 '
                       'bearing + 8 mm shaft (mag-1 cited)"], '
                       '"materials": [{"ref": "magnet-wire-copper",'
                       ' "note": "3 phase coils"}, {"ref": '
                       '"opt-geopolymer-ferrite", "note": "stator '
                       '+ rotor castings"}], "skills": ["casting", '
                       '"winding", "SimpleFOC setup"], '
                       '"rough_hours": 12}',
        'is_prior': True, 'provenance_id': 'mag-5',
        'notes': 'The no-PM proof rung.',
    },
    {
        'name': 'ferrite-pm-m2',
        'display_name': 'M2 — small ferrite-PM rotor motor',
        'description': 'Bonded/sintered hexaferrite rotor ring + '
                       'wound stator — the commercial-precedent '
                       'route (cheap BLDC fans are exactly this).',
        'topology': 'radial-reluctance',
        'ladder_rung': 'M2', 'tolerance_tier': 'T1',
        'params_json': '{"stator_material": '
                       '"opt-geopolymer-ferrite", '
                       '"rotor_material": '
                       '"opt-sintered-hexaferrite", '
                       '"slots": 6, "poles": 4, '
                       '"gap_base_m": 0.0004, '
                       '"tooth_area_m2": 6e-5, '
                       '"coil_turns": 200, "coil_amps": 1.0, '
                       '"wire_awg": 22, '
                       '"bobbin_window_mm2": 120.0, '
                       '"mean_turn_length_mm": 35.0, '
                       '"saliency_ratio": 1.0, '
                       '"load_angle_deg": 90, '
                       '"magnet_length_m": 0.004}',
        'drive_json': '{"rate_hz": 20.0, "kind": "3-phase"}',
        'build_requirements_json': '{"tools": ["T1 lapping '
                       '(sandpaper on glass)", "magnetizer", '
                       '"SimpleFOC drive + AS5600"], "materials": '
                       '[{"ref": "ceramic-ring-magnet", "note": '
                       '"BUY the rotor ring first (mag-1 cited '
                       'tiers) — cast your own once M0 proves the '
                       'bonded route"}], "skills": ["casting", '
                       '"lapping", "winding"], "rough_hours": 20}',
        'is_prior': True, 'provenance_id': 'mag-5',
        'notes': 'Intermediate rung between the clock and the '
                 'flagship.',
    },
    {
        'name': 'dual-stator-axial-m3',
        'display_name': 'M3 — dual-stator axial flux (THE END '
                        'GOAL, §2d)',
        'description': 'Two stator disks sandwich one rotor: dual '
                       'working gaps double active area in the '
                       'same envelope — the cheap-material parity '
                       'thesis made geometry. Reluctance-disk '
                       'variant first; ferrite-PM ring for '
                       'torque.',
        'topology': 'axial-dual-stator',
        'ladder_rung': 'M3', 'tolerance_tier': 'T1',
        'params_json': '{"stator_material": '
                       '"opt-geopolymer-ferrite", '
                       '"rotor_material": '
                       '"opt-sintered-hexaferrite", '
                       '"teeth_per_stator": 12, "poles": 8, '
                       '"gap_base_m": 0.0008, '
                       '"tooth_area_m2": 2.5e-4, '
                       '"coil_turns": 100, "coil_amps": 2.0, '
                       '"wire_awg": 20, '
                       '"bobbin_window_mm2": 120.0, '
                       '"mean_turn_length_mm": 50.0, '
                       '"load_angle_deg": 90, '
                       '"magnet_length_m": 0.006, '
                       '"dual_gap": true}',
        'drive_json': '{"rate_hz": 50.0, "kind": "3-phase"}',
        'build_requirements_json': '{"tools": ["disk molds (flat '
                       'faces = castable AND lappable)", "T1 '
                       'lapping", "magnetizer", "two synced or '
                       'paralleled SimpleFOC drives"], '
                       '"materials": [{"ref": '
                       '"opt-geopolymer-ferrite", "note": "two '
                       'stator disk castings (mag-4 arc-segment '
                       'blocks + selective mortar)"}, {"ref": '
                       '"ceramic-ring-magnet", "note": "rotor '
                       'ring segments (buy) or cast bonded once '
                       'proven"}], "skills": ["mag-4 matrix '
                       'assembly", "lapping", "winding x6"], '
                       '"rough_hours": 60}',
        'is_prior': True, 'provenance_id': 'mag-5',
        'notes': 'Bench-demo class FIRST (§2d ladder: bench -> '
                 'e-bike/cart -> in-wheel aspiration); every '
                 'parity claim traces to torque_parity().',
    },
]
