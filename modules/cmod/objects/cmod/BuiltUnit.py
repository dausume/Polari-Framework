"""
@module cmod.objects.cmod.BuiltUnit

BuiltUnit - one class per file (design section 7); msv-0 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BuiltUnit(treeObject):
    """What it is: ONE PHYSICAL BUILT DEVICE - a soldered / wired / assembled copy of a Bench Solution, on a bench, flashed with one build. It
    carries who built it and how, never its readings (MeasurementReading names it). The user (2026-11-04): "proof out that the physical device was done
    properly and/or gauge what real soldered device variance is from the simulated device."
    Related concepts: `BenchSolution`, `MeasurementReading`, `StructNodeConfirmation`.
    """

    plain_words = ('One real copy of a bench design that someone built by hand, and which firmware build is on it; its measurements are kept separately and point at it.')

    @treeObjectInit
    def __init__(self, name: str = '', bench_solution: str = '', hex_sha256: str = '', layout: str = '', build_method: str = 'breadboard', built_by: str = '', notes: str = '', at: str = '', manager=None):
        self.name = name    # '<bench solution>-unit-<n>' (generic; never a real serial or a person's name in tracked seeds)
        self.bench_solution = bench_solution    # a BenchSolution name
        self.hex_sha256 = hex_sha256    # the build flashed on it (a reading on another build is said to be stale)
        self.layout = layout    # the layout / breadboard plan it was built from, when one exists
        self.build_method = build_method    # breadboard | perfboard | wire-wrap | pcb | other
        self.built_by = built_by    # who built it
        self.notes = notes
        self.at = at
