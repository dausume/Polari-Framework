"""
@module mech.objects.motion.MechMotionRun

Row class MechMotionRun of the mech module — one class per file (design §7).
MECH_FREECAD_INTERCHANGE_PLAN §3.5 / §9.1: one execution of a motion case
under a load case. Rides core simulations (D-mxc-11): `simulation_run_ref`
names the SimulationRun whose MechMotionSimState rows hold the time series.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechMotionRun(treeObject):
    """A run = motion case × load case × engine. `report_json` carries
    EVERY check with its number, pass or fail. The structural side of the
    same load case is NAMED here (`fem_model_ref` → a FEMModelDefinition)
    and executed by materialsScience's fem_engine — mech computes no
    stress or deflection itself (D-mxc-7)."""

    @treeObjectInit
    def __init__(self, name='', motion_case_ref='', load_case_ref='',
                 engine='polari', engine_version='', worker='',
                 simulation_run_ref='', fem_model_ref='', started='',
                 finished='', ok=False, report_json='{}',
                 provenance_json='{}', freecad_artifact_sha='',
                 inputs_sha256='', confirmation_json='{}',
                 manager=None):
        self.name = name
        self.motion_case_ref = motion_case_ref
        self.load_case_ref = load_case_ref
        #: polari | freecad_motion (ENGINE_KINDS).
        self.engine = engine
        #: e.g. 'mech.motion_engine 1' or 'FreeCAD 1.1.4'.
        self.engine_version = engine_version
        #: Host that ran it ('' = in-process; 'econ', 'isle-core' for FreeCAD).
        self.worker = worker
        #: core SimulationRun name; its MechMotionSimState rows are the series.
        self.simulation_run_ref = simulation_run_ref
        #: '' | FEMModelDefinition name — named only, run by fem_engine.
        self.fem_model_ref = fem_model_ref
        self.started = started
        self.finished = finished
        #: Every check passed.
        self.ok = ok
        #: JSON {checks: [{name, criterion, knob, value, units, ok, note}],
        #: summary: {...}} — every check with its number.
        self.report_json = report_json
        #: JSON {rows: {class: name}, model: {...}, engine_dt_s, ...}.
        self.provenance_json = provenance_json
        #: sha256 of the FreeCAD-produced artifact (motion CSV / FCStd) when
        #: the engine is freecad_motion; '' otherwise.
        self.freecad_artifact_sha = freecad_artifact_sha
        #: sha256 over the canonical JSON (sort_keys, compact separators) of
        #: {motion case, load case, the assembly's joint / contact / instance
        #: rows, engine version, knobs} — the run's reproducible initial
        #: conditions (Dustin's standing rule: reproducible by sha256,
        #: confirmations voided on change). Computed by
        #: mech.custom.motion_runs.inputs_sha256; the cmod SolveRun
        #: `inputs_sha256` convention.
        self.inputs_sha256 = inputs_sha256
        #: JSON with the keys of cmod's StructNodeConfirmation
        #: (modules/cmod/objects/cmod/StructNodeConfirmation.py: by, run,
        #: hex_sha256, state confirmed | voided, voided_why, who, words, at)
        #: plus `voided_at` from board's SimInstallConfirmation
        #: (modules/board/objects/board/SimInstallConfirmation.py). Here
        #: `by` is sim | hardware | person and `hex_sha256` holds the
        #: inputs_sha256 the confirmation was given for. '{}' = none.
        #: Voided, never deleted, by motion_runs.void_if_changed when the
        #: inputs sha differs.
        self.confirmation_json = confirmation_json
