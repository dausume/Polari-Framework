"""
@module printing_suite.objects.printing.PrintProfile

PrintProfile — how one material prints on one printer (the slicer's inputs).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PrintProfile(treeObject):
    """What it is: the settings a slicer needs for one material on one
    printer: nozzle, temperatures, layer height, speeds, retraction,
    cooling, and the slicer they are expressed for — the contract between
    the material/mold step and the slice step.
    Related concepts: `MaterialLot` (what), `PrinterDefinition` (voron, which
    printer), `SliceJob` (consumer), waxprint `PrintConditionDefinition`
    (the research-side conditions this profile is derived from when the
    material is wax), `DeviceMaterialDefinition`.
    How it is derived: from the material's rows and the printer's limits
    (derive or cite, never type); `provenance` names the source rows.
    """

    @treeObjectInit
    def __init__(self, name: str = '', material: str = '', printer: str = '', slicer: str = 'kirimoto',
                 nozzle_mm: float = 0.4, layer_mm: float = 0.2, nozzle_temp_c: float = 0.0, bed_temp_c: float = 0.0,
                 speed_mm_s: float = 0.0, retraction_mm: float = 0.0, fan_pct: float = 0.0, infill_pct: float = 20.0,
                 settings_json: str = '{}', provenance: str = '', is_prior: bool = True, notes: str = ''):
        self.name = name
        self.material = material
        self.printer = printer
        self.slicer = slicer
        self.nozzle_mm = nozzle_mm
        self.layer_mm = layer_mm
        self.nozzle_temp_c = nozzle_temp_c
        self.bed_temp_c = bed_temp_c
        self.speed_mm_s = speed_mm_s
        self.retraction_mm = retraction_mm
        self.fan_pct = fan_pct
        self.infill_pct = infill_pct
        self.settings_json = settings_json
        self.provenance = provenance
        self.is_prior = is_prior
        self.notes = notes
