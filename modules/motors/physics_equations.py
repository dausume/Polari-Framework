"""
@module motors.physics_equations

mag-20: THE PHYSICS AS CONFIGURATION, not code.

Dustin 2026-07-30: "we have configurable matrix equations we can use
to solve for complex math, if possible we should not be writing
custom code and instead be using configuration to solve problems or
using existing open source libraries or engines we already have so
it can be modularized and re-used wherever possible to prevent bloat
and duplication."

That is a fair correction and this module is the fix. mag-15..19
hard-coded closed-form physics into Python — Hertz contact, Archard
wear, subcritical-crack life, the Weibull derate, eddy loss,
planetary ratios, hand imbalance. Every one of those is a formula,
and Polari already has the machinery to hold a formula AS DATA:
EquationDefinition rows carrying LaTeX, executed through
polariNoCode.equation_executor on sympy.

WHAT MOVES TO CONFIGURATION (this file): the closed-form maths. It
becomes inspectable, editable without a deploy, reusable by any
module, and citable — a reviewer can read the LaTeX rather than
reverse-engineering Python.

WHAT LEGITIMATELY STAYS IN CODE, and why (so this boundary is a
decision rather than an excuse):
  - REFUSALS and gap reporting: policy, not arithmetic.
  - CRITERION SELECTION (von Mises vs max-principal): a decision
    about which formula applies, which is exactly the thing a
    single formula cannot encode.
  - ROLE predicates: set logic over declared roles.
  - UNIT handling and row plumbing.
  - Calls into ENGINES that already exist (scikit-fem for
    elasticity) — the same principle, one layer up: use the engine,
    do not re-implement it.

@consumers motors.* (via evaluate_named), polariServer seed
"""

PROV = 'mag-20'

#: Each row is an EquationDefinition seed: LaTeX + the operation
#: contract the executor understands. `symbols` documents what each
#: binding means, because a formula without its variable meanings is
#: a puzzle rather than a specification.
SEED_PHYSICS_EQUATIONS = [
    {
        'name': 'eq-hertz-line-contact-pmax',
        'description': 'Hertz LINE contact peak pressure between '
                       'two cylinders — the gear-tooth case. p_max '
                       'is COMPRESSIVE; a brittle tooth is judged '
                       'by the surface tensile stress derived from '
                       'it, not by this number.',
        'source_class': 'MotorPartDefinition',
        'latex': r'\sqrt{\frac{F \cdot E}{c \cdot R}}',
        'operation_type': 'evaluate',
        'symbols': {'F': 'load per unit face width, N/m',
                    'E': 'effective modulus E*, Pa',
                    'R': 'relative radius of curvature R*, m',
                    'c': 'pi — bound EXPLICITLY rather than left '
                         'symbolic, so the executor returns a '
                         'number instead of an expression'},
        'returns': 'peak contact pressure, Pa',
    },
    {
        'name': 'eq-hertz-surface-tensile',
        'description': 'Surface TENSILE stress at the trailing edge '
                       'of a Hertz contact — where a brittle tooth '
                       'actually cracks.',
        'source_class': 'MotorPartDefinition',
        'latex': r'\frac{(1 - 2 \cdot n) \cdot p}{3}',
        'operation_type': 'evaluate',
        'symbols': {'n': "Poisson's ratio", 'p': 'peak pressure, Pa'},
        'returns': 'surface tensile stress, Pa',
    },
    {
        'name': 'eq-scg-life-cycles',
        'description': 'Subcritical crack growth life INVERTED: '
                       'cycles to failure for a brittle material at '
                       'a given applied stress. The exponent is why '
                       'small margin changes move life by orders.',
        'source_class': 'MagneticMaterialOption',
        'latex': r'\left(\frac{S}{s}\right)^{n}',
        'operation_type': 'evaluate',
        'symbols': {'S': 'derated strength, MPa',
                    's': 'applied stress, MPa',
                    'n': 'crack-growth exponent'},
        'returns': 'cycles to failure',
    },
    {
        'name': 'eq-scg-allowable-stress',
        'description': 'The forward form: allowable stress after N '
                       'cycles. Brittle materials have NO endurance '
                       'limit, so this keeps falling.',
        'source_class': 'MagneticMaterialOption',
        'latex': r'S \cdot N^{-1/n}',
        'operation_type': 'evaluate',
        'symbols': {'S': 'static strength, MPa', 'N': 'cycles',
                    'n': 'crack-growth exponent'},
        'returns': 'allowable stress, MPa',
    },
    {
        'name': 'eq-weibull-survival-derate',
        'description': 'Strength a design may use for a target '
                       'survival probability. Brittle parts fail '
                       'from the WORST flaw, so the mean is not the '
                       'design number.',
        'source_class': 'MagneticMaterialOption',
        'latex': r'\left(- \ln{P}\right)^{1/m}',
        'operation_type': 'evaluate',
        'symbols': {'P': 'survival probability, 0-1',
                    'm': 'Weibull modulus'},
        'returns': 'derate factor (multiply strength by this)',
    },
    {
        'name': 'eq-archard-wear-volume',
        'description': 'Archard wear volume. k spans SIX orders '
                       'across pairs and lubrication, so this is '
                       'evaluated at both ends of a band, never at '
                       'one value.',
        'source_class': 'MotorPartDefinition',
        'latex': r'\frac{k \cdot F \cdot s}{H}',
        'operation_type': 'evaluate',
        'symbols': {'k': 'wear coefficient', 'F': 'normal load, N',
                    's': 'sliding distance, m',
                    'H': 'hardness, Pa'},
        'returns': 'worn volume, m^3',
    },
    {
        'name': 'eq-eddy-loss-density',
        'description': 'Classical thin-plate eddy loss density. '
                       'Note B is SQUARED — which is why a '
                       'geometric buffer works so well.',
        'source_class': 'MotorPartDefinition',
        'latex': r'\frac{\left(c \cdot t \cdot f \cdot B\right)^{2}'
                 r' \cdot g}{6}',
        'operation_type': 'evaluate',
        'symbols': {'t': 'thickness, m', 'f': 'frequency, Hz',
                    'B': 'local flux density, T',
                    'g': 'conductivity sigma, S/m',
                    'c': 'pi, bound explicitly'},
        'returns': 'loss density, W/m^3',
    },
    {
        'name': 'eq-maxwell-pull',
        'description': 'Magnetic attraction across a gap.',
        'source_class': 'MotorDesignDefinition',
        'latex': r'\frac{B^{2} \cdot A}{2 \cdot u}',
        'operation_type': 'evaluate',
        'symbols': {'B': 'flux density, T', 'A': 'pole area, m^2',
                    'u': 'mu_0, H/m'},
        'returns': 'force, N',
    },
    {
        'name': 'eq-planetary-ring-fixed',
        'description': 'Planetary ratio with the RING held — the '
                       'workhorse configuration.',
        'source_class': 'GearTrainDefinition',
        'latex': r'1 + \frac{R}{S}',
        'operation_type': 'evaluate',
        'symbols': {'R': 'ring teeth', 'S': 'sun teeth'},
        'returns': 'reduction ratio (output same direction)',
    },
    {
        'name': 'eq-planetary-carrier-fixed',
        'description': 'Planetary ratio with the CARRIER held — '
                       'output REVERSES, and the minus sign is the '
                       'design point.',
        'source_class': 'GearTrainDefinition',
        'latex': r'- \frac{R}{S}',
        'operation_type': 'evaluate',
        'symbols': {'R': 'ring teeth', 'S': 'sun teeth'},
        'returns': 'reduction ratio (REVERSED)',
    },
    {
        'name': 'eq-hand-imbalance-torque',
        'description': 'Gravity torque of an unbalanced clock hand '
                       '— what sets the largest face this motor can '
                       'drive.',
        'source_class': 'GearTrainDefinition',
        'latex': r'm \cdot g \cdot r',
        'operation_type': 'evaluate',
        'symbols': {'m': 'hand mass, kg',
                    'g': 'gravity, m/s^2',
                    'r': 'centre-of-gravity radius, m'},
        'returns': 'imbalance torque, Nm',
    },
    {
        'name': 'eq-tooth-load',
        'description': 'Tangential tooth load from transmitted '
                       'torque.',
        'source_class': 'GearDefinition',
        'latex': r'\frac{T}{r}',
        'operation_type': 'evaluate',
        'symbols': {'T': 'torque, Nm', 'r': 'pitch radius, m'},
        'returns': 'tangential force, N',
    },
]

_BY_NAME = {e['name']: e for e in SEED_PHYSICS_EQUATIONS}


def evaluate_named(name, bindings, manager=None):
    """Evaluate a physics formula BY NAME through the existing
    no-code equation executor (sympy/LaTeX) rather than a Python
    re-implementation.

    Prefers the LIVE EquationDefinition row when one exists, so an
    edited row takes effect without a deploy — which is the whole
    point of holding formulas as configuration. Falls back to the
    seed definition when the row is absent."""
    latex = None
    op = 'evaluate'
    if manager is not None:
        table = (getattr(manager, 'objectTables', None) or {}).get(
            'EquationDefinition') or {}
        for row in table.values():
            if getattr(row, 'name', '') != name:
                continue
            import json
            try:
                blob = json.loads(getattr(row, 'definition', '')
                                  or '{}')
            except (TypeError, ValueError):
                blob = {}
            latex = blob.get('latexExpression')
            op = blob.get('operationType', op)
            break
    if latex is None:
        seed = _BY_NAME.get(name)
        if seed is None:
            return {'ok': False,
                    'refusal': f'no physics equation named '
                               f'"{name}"',
                    'suggestion': {
                        'knob': 'SEED_PHYSICS_EQUATIONS',
                        'action': f'one of {sorted(_BY_NAME)}'}}
        latex, op = seed['latex'], seed['operation_type']

    try:
        from polariNoCode.equation_executor import execute_equation
    except ImportError as exc:
        return {'ok': False,
                'refusal': f'the no-code equation executor is not '
                           f'available ({exc}) — this module '
                           f'deliberately does NOT re-implement the '
                           f'maths in Python'}
    result = execute_equation(latex_expression=latex,
                              operation_type=op,
                              variable_bindings=dict(bindings))
    return {'ok': bool(result.get('success', result.get('ok'))),
            'equation': name, 'latex': latex,
            'bindings': dict(bindings), 'result': result,
            'source': ('live EquationDefinition row' if manager
                       else 'seed definition'),
            'note': 'evaluated through polariNoCode.equation_'
                    'executor (sympy) — the formula is DATA, not '
                    'code, so it can be inspected and edited '
                    'without a deploy'}


def equation_catalog():
    """Every physics formula we hold as configuration, with its
    LaTeX and what each symbol means."""
    return {
        'ok': True,
        'equations': [
            {'name': e['name'], 'description': e['description'],
             'latex': e['latex'], 'symbols': e['symbols'],
             'returns': e['returns'],
             'sourceClass': e['source_class']}
            for e in SEED_PHYSICS_EQUATIONS],
        'count': len(SEED_PHYSICS_EQUATIONS),
        'principle': 'formulas are CONFIGURATION, evaluated by the '
                     'existing no-code executor. What stays in code '
                     'is policy — refusals, which criterion '
                     'applies, role predicates, units — plus calls '
                     'into engines that already exist (scikit-fem), '
                     'because using an engine and re-implementing '
                     'one are opposite acts.',
    }


#: EquationDefinition seed rows, in the shape polariServer seeds.
SEED_EQUATION_ROWS = [
    {'name': e['name'], 'description': e['description'],
     'source_class': e['source_class'],
     'definition': __import__('json').dumps({
         'latexExpression': e['latex'],
         'operationType': e['operation_type'],
         'variableBindings': [{'symbol': s,
                               'source': {'type': 'runtime'},
                               'meaning': meaning}
                              for s, meaning in e['symbols'].items()],
         'resultSpec': {'type': 'scalar'},
         'returns': e['returns'],
         'provenance': PROV,
     })}
    for e in SEED_PHYSICS_EQUATIONS
]
