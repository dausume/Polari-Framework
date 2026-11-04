"""
@module mech.objects.motion.MechMotionVector

Row class MechMotionVector of the mech module — one class per file (design §7).
MECH_FREECAD_INTERCHANGE_PLAN §3.5: one named signal of a run as (t, value)
samples — extracted from the MechMotionSimState rows, never a second source.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechMotionVector(treeObject):
    """A named series of one run: name = '<run>:<signal>'. The series the
    views chart (mxc-6) and the measured runs compare against (mxc-7)."""

    @treeObjectInit
    def __init__(self, name='', run_ref='', signal='', samples_json='[]',
                 units='', basis='', manager=None):
        self.name = name
        #: MechMotionRun name.
        self.run_ref = run_ref
        #: One of SIGNALS.
        self.signal = signal
        #: JSON list of [t_s, value].
        self.samples_json = samples_json
        self.units = units
        #: 'polari engine' | 'freecad motion' | 'measured …'.
        self.basis = basis
