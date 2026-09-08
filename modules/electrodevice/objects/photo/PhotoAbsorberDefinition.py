"""
@module electrodevice.objects.photo.PhotoAbsorberDefinition

Row class PhotoAbsorberDefinition of the electrodevice module — one class per file (design §7), split
from photo_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PhotoAbsorberDefinition(treeObject):
    """One tunable absorber: candidates (fragment sims and/or
    literature-gap records) + the target-wavelength knob + the
    orientation knob. Tuning EXECUTES the candidate sims and picks
    the best absorption-edge match."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # THE TUNING KNOB: what light this sensor is for.
        target_wavelength_nm: float = 450.0,
        # JSON list of candidates: {name, simModel} (executed) or
        # {name, gapRecord: {value_ev, ...structured record}}.
        candidates_json: str = '[]',
        # Orientation knob: 'aligned' absorbers (drawn CNT films /
        # rubbed acenes) couple ~cos^2(theta) to the polarization;
        # 'random' averages to 1/3.
        orientation: str = 'aligned',
        polarization_angle_deg: float = 0.0,
        # Derived by the tune act:
        chosen_candidate: str = '',
        chosen_gap_ev: float = 0.0,
        absorption_edge_nm: float = 0.0,
        match_error_nm: float = 0.0,
        orientation_factor: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.target_wavelength_nm = target_wavelength_nm
        self.candidates_json = candidates_json
        self.orientation = orientation
        self.polarization_angle_deg = polarization_angle_deg
        self.chosen_candidate = chosen_candidate
        self.chosen_gap_ev = chosen_gap_ev
        self.absorption_edge_nm = absorption_edge_nm
        self.match_error_nm = match_error_nm
        self.orientation_factor = orientation_factor
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes
