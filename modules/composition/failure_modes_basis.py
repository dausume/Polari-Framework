"""
@module composition.failure_modes_basis

arch-2: ONE failure-mode catalogue with TWO loci. Interface modes
live on InterfaceDefinition rows and are DELETED when a promotion
consumes the interface; bulk modes live on the part and are what
promotion buys them with (handover §1.1: promotion trades interface
failure modes for bulk ones, and spends repairability).

A mode without a governing equation names that gap loudly
(equation_ref='') — the Hertzian-contact discipline: a named gap,
never a silent skip.

@consumers composition.node_basis, composition.routing_basis,
polariServer seed passes
"""

from objectTreeDecorators import treeObject, treeObjectInit

from composition.custom.part_roles import DOMAINS  # noqa: F401 — same axis

LOCI = ('interface', 'bulk')


class FailureModeDefinition(treeObject):
    """One way a part or an interface dies."""

    @treeObjectInit
    def __init__(self, name='', display_name='', domain='mechanical',
                 locus='bulk', summary='', equation_ref='',
                 evidence_note='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.domain = domain if domain in DOMAINS else 'mechanical'
        self.locus = locus if locus in LOCI else 'bulk'
        self.summary = summary
        #: EquationDefinition name; '' = NOT MODELLED, stated.
        self.equation_ref = equation_ref
        #: What observation would confirm/deny this mode here.
        self.evidence_note = evidence_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


PROV = 'arch-2'

#: Seeded straight from what the mag arc actually hit. Equation refs
#: point at the LIVE physics_equations rows where one exists.
SEED_FAILURE_MODES = [
    # ----- interface locus (die with the interface) -----
    {'name': 'fm-fretting', 'display_name': 'Fretting wear',
     'domain': 'mechanical', 'locus': 'interface',
     'summary': 'micro-slip at a loaded interface wears both faces; '
                'a clock runs 3.2e8 cycles, so any interface that '
                'can micro-move, will',
     'equation_ref': 'eq-archard-wear-volume',
     'evidence_note': 'debris/polish at the contact after a soak '
                      'run; Archard k spans six orders, so evaluate '
                      'a band',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'fm-turn-to-turn-abrasion',
     'display_name': 'Turn-to-turn / crossover abrasion',
     'domain': 'mechanical', 'locus': 'interface',
     'summary': 'adjacent winding turns rub where they cross; '
                'insulation is the wear part and a worn crossing is '
                'a shorted turn',
     'equation_ref': '',
     'evidence_note': 'megger/continuity after vibration soak; '
                      'NOT MODELLED — named gap',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'fm-fastener-back-out',
     'display_name': 'Fastener loosening / back-out',
     'domain': 'mechanical', 'locus': 'interface',
     'summary': 'cyclic load walks a threaded fastener out; preload '
                'decays and the joint goes loose before anything '
                'breaks',
     'equation_ref': '',
     'evidence_note': 'witness-mark rotation after cycling; '
                      'NOT MODELLED — named gap',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'fm-preload-loss',
     'display_name': 'Joint preload loss (settlement/creep)',
     'domain': 'mechanical', 'locus': 'interface',
     'summary': 'embedding and creep relax the clamp; a joint that '
                'was tight ships loose',
     'equation_ref': '',
     'evidence_note': 'retorque check after thermal cycles; '
                      'NOT MODELLED — named gap',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'fm-interface-friction-drag',
     'display_name': 'Interface friction drag',
     'domain': 'mechanical', 'locus': 'interface',
     'summary': 'a separable interface that moves in service costs '
                'torque budget; in a clock-scale machine friction '
                'is a first-order term, not a loss factor',
     'equation_ref': '',
     'evidence_note': 'free-run coast-down vs bound build',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    # ----- bulk locus (what promotion buys them with) -----
    {'name': 'fm-brittle-fracture',
     'display_name': 'Brittle fracture (worst-flaw)',
     'domain': 'mechanical', 'locus': 'bulk',
     'summary': 'a brittle body fails from its WORST FLAW, so the '
                'mean strength is never the design number',
     'equation_ref': 'eq-weibull-survival-derate',
     'evidence_note': 'Weibull modulus from a bend-bar batch',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'fm-subcritical-crack-growth',
     'display_name': 'Subcritical crack growth (static fatigue)',
     'domain': 'mechanical', 'locus': 'bulk',
     'summary': 'cracks grow below critical load; the exponent is '
                'why small margin changes move life by orders',
     'equation_ref': 'eq-scg-life-cycles',
     'evidence_note': 'life at two stress levels brackets n',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'fm-archard-wear',
     'display_name': 'Sliding wear (Archard)',
     'domain': 'mechanical', 'locus': 'bulk',
     'summary': 'a sliding face loses volume with load and '
                'distance; hardness resists it',
     'equation_ref': 'eq-archard-wear-volume',
     'evidence_note': 'profilometry after distance; k is a BAND',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'fm-potted-winding-crack-short',
     'display_name': 'Potting crack → winding short',
     'domain': 'intersectional', 'locus': 'bulk',
     'summary': 'the promoted coil\'s own mode: sol-gel silica is '
                'brittle, a crack propagates through insulation it '
                'is bonded to, and a crack in a potted winding is a '
                'short. This is exactly what the bound stator '
                'traded fretting for',
     'equation_ref': '',
     'evidence_note': 'bend a dipped sample round a 3 mm former — '
                      'the one-afternoon test (mag-24)',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'fm-bond-line-shear',
     'display_name': 'Adhesive bond line fails in shear',
     'domain': 'mechanical', 'locus': 'interface',
     'summary': 'THE MODE A BONDED PROMOTION KEEPS. A mold-fused '
                'boundary has no interface left to fail — a bonded '
                'one does: the adhesive layer carries the torque '
                'in shear, and it is the weakest material in the '
                'stack even when both parts it joins are strong. '
                'M2\'s magnet ring is bonded to its carrier '
                '(ifm2-ring-carrier), so this is the price of '
                'joining two materials that cannot be poured '
                'together',
     'equation_ref': '',
     'evidence_note': 'bond one ring to one carrier and twist it '
                      'off on the shaft: the torque it takes IS '
                      'the measurement, and it must beat the '
                      'motor\'s pull-out torque with margin',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'm2-4 named this mode on the interface row before a '
              'FailureModeDefinition existed for it — the marker '
              'layer reported it as modeRowsMissing, which is the '
              'gap-naming machinery catching its own author.'},
    {'name': 'fm-thermal-mismatch-stress',
     'display_name': 'Thermal-expansion mismatch → internal stress',
     'domain': 'thermal', 'locus': 'bulk',
     'summary': 'what WAS an interface clearance becomes locked-in '
                'residual stress after promotion; the mismatch does '
                'not go away, it changes address',
     'equation_ref': '',
     'evidence_note': 'thermal-cycle a promoted sample, look for '
                      'crazing at material boundaries',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]
