"""@module pspp.objects.material_states._shared — what the material_states row classes share (constants, seeds, helpers); split from material_states_basis.py (sap-2c)."""

CANONICAL_STATE = 'as-defined'
THERMODYNAMIC_PHASES = ('solid', 'liquid', 'gas', 'plasma', 'mixed')
_STAGE_PROVENANCE = ('pspp-2 stage vocabulary '
                     '(PSPP_MATERIALS_PLAN.md §2, ChatGPT convergence '
                     '2026-07-18)')
SEED_PROCESSING_STAGES = [
    # general
    {'name': 'raw-powder', 'display_name': 'Raw powder',
     'material_family': 'general',
     'description': 'As-received particulate feedstock.'},
    {'name': 'green-body', 'display_name': 'Green body',
     'material_family': 'general', 'typical_prior_stage': 'raw-powder',
     'description': 'Shaped but not yet consolidated/fired.'},
    {'name': 'damaged', 'display_name': 'Damaged',
     'material_family': 'general',
     'description': 'Post-service degraded state (thermal, chemical, '
                    'mechanical) — still a citable state.'},
    # geopolymer route
    {'name': 'activated-slurry', 'display_name': 'Activated slurry',
     'material_family': 'geopolymer', 'typical_prior_stage': 'raw-powder',
     'description': 'Precursor + alkali activator mixed, workable.'},
    {'name': 'reactive-suspension',
     'display_name': 'Reactive suspension',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'activated-slurry',
     'description': 'Dissolution under way — species depolymerizing '
                    'into solution (book §5.6.3).'},
    {'name': 'percolating-gel', 'display_name': 'Percolating gel',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'reactive-suspension',
     'description': 'Network first spans the volume — setting point.'},
    {'name': 'set-gel', 'display_name': 'Set gel',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'percolating-gel',
     'description': 'Demoldable gel, curing continues.'},
    {'name': 'cured-solid', 'display_name': 'Cured solid',
     'material_family': 'geopolymer', 'typical_prior_stage': 'set-gel',
     'description': 'Cure complete to spec (e.g. 7-day sealed cure).'},
    {'name': 'heat-treated-ceramic',
     'display_name': 'Heat-treated ceramic',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'cured-solid',
     'description': 'Post-cure thermal conversion toward ceramic.'},
    {'name': 'carbonated', 'display_name': 'Carbonated',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'cured-solid',
     'description': 'CO2-reacted surface/bulk — a durability branch.'},
    # wax route (maps the existing waxprint world in pspp-11)
    {'name': 'wax-solid', 'display_name': 'Solid wax',
     'material_family': 'wax',
     'description': 'Below melt onset — machinable regime.'},
    {'name': 'wax-softened', 'display_name': 'Softened wax',
     'material_family': 'wax', 'typical_prior_stage': 'wax-solid',
     'description': 'Inside the melt range — smears under cutters.'},
    {'name': 'wax-melt', 'display_name': 'Wax melt',
     'material_family': 'wax', 'typical_prior_stage': 'wax-softened',
     'description': 'Fully molten inside the processing window.'},
    {'name': 'wax-superheated', 'display_name': 'Superheated wax',
     'material_family': 'wax', 'typical_prior_stage': 'wax-melt',
     'description': 'Above the no-volatiles ceiling — REFUSED by the '
                    'thermal gate, named so refusals can cite it.'},
]
for _row in SEED_PROCESSING_STAGES:
    _row.setdefault('provenance_id', _STAGE_PROVENANCE)
