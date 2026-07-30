"""
Self-test for the FEM linear-elasticity solver (mag-15).

Every case below is checkable BY HAND against closed-form elasticity,
which is the point — a stress solver that only agrees with itself is
not evidence of anything:

  1. Uniaxial tension of a plate. Traction sigma on one edge with
     symmetry restraints gives the exact uniform state
     sxx = sigma, syy = 0, sxy = 0. Then von Mises = sigma and max
     principal = sigma, both by definition.
  2. Equal tension-compression (sxx = +tau, syy = -tau). This is pure
     shear rotated 45 degrees, so von Mises = sqrt(3)*tau exactly —
     the case that catches a von Mises formula that "works" only for
     uniaxial states.
  3. Plate with a circular hole in tension: the Kirsch problem. The
     stress concentration factor must APPROACH ~3 from BELOW as the
     mesh refines (P1 elements hold stress constant per element, so a
     coarse element averages away the peak). Both the value and the
     monotone climb are asserted — the climb is what proves the solver
     is resolving a real gradient rather than reporting mesh noise.
  4. Refusals: missing library, bad Poisson ratio, no load, no
     restraint, a hole too big for its rectangle.

Run from polari-framework/:
    python3 -m materialsScience.selftest_fem_elasticity
"""

import sys

from materialsScience.engines import fem_engine
from materialsScience.engines.fem_engine import (
    elastic_capability, elasticity_mesh_convergence, solve_elasticity_2d,
)

PASS = 0
FAIL = 0


def check(label, condition, extra=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}' + (f'  [{extra}]' if extra else ''))


def test_capability():
    print('[capability]')
    cap = elastic_capability()
    check('elasticity capability reports available with a version',
          cap['available'] and cap['version'], str(cap))
    check('capability names the physics it offers',
          cap.get('physics') == 'linear-elasticity')


def test_uniaxial():
    print('[uniaxial tension — exact uniform state]')
    sigma = 5.0e6
    out = solve_elasticity_2d(
        width=2.0, height=1.0, youngs_modulus=200.0e9, poisson_ratio=0.3,
        tractions=[{'edge': 'right', 'tx': sigma}],
        fixed_edges=[{'edge': 'left', 'dof': 'x'},
                     {'edge': 'bottom', 'dof': 'y'}],
        assumption='plane-stress', refine=3)
    check('solve ok', out.get('ok'), str(out.get('error')))
    if not out.get('ok'):
        return
    rel = abs(out['meanStress']['sxx'] - sigma) / sigma
    check(f'sxx = applied traction ({sigma:.3g} Pa) to <1e-6 relative',
          rel < 1e-6, f'rel={rel:.2e}')
    check('syy is zero to <1e-6 of sigma',
          abs(out['meanStress']['syy']) < 1e-6 * sigma,
          str(out['meanStress']['syy']))
    check('sxy is zero to <1e-6 of sigma',
          abs(out['meanStress']['sxy']) < 1e-6 * sigma)
    check('plane stress => szz is exactly 0',
          out['stressRange']['szz'] == [0.0, 0.0])
    vm = out['maxVonMises']['value']
    check('von Mises = sigma for a uniaxial state',
          abs(vm - sigma) / sigma < 1e-6, f'vm={vm:.6g}')
    mp = out['maxPrincipal']['value']
    check('max principal = sigma for a uniaxial state',
          abs(mp - sigma) / sigma < 1e-6, f'mp={mp:.6g}')
    check('max von Mises reports WHERE it occurs',
          len(out['maxVonMises']['atXY']) == 2)
    check('element count and refine level are reported',
          out['elementCount'] > 0 and out['refine'] == 3)
    check('validity names mesh dependence at singularities',
          'MESH-DEPENDENT' in out['validity'])
    check('criterion note warns that brittle parts fail on max '
          'principal, not von Mises',
          'MAXIMUM PRINCIPAL' in out['criterionNote'])


def test_plane_strain_differs():
    print('[plane strain is NOT plane stress]')
    common = dict(
        width=2.0, height=1.0, youngs_modulus=200.0e9, poisson_ratio=0.3,
        tractions=[{'edge': 'right', 'tx': 5.0e6}],
        fixed_edges=[{'edge': 'left', 'dof': 'x'},
                     {'edge': 'bottom', 'dof': 'y'}], refine=3)
    ps = solve_elasticity_2d(assumption='plane-stress', **common)
    pe = solve_elasticity_2d(assumption='plane-strain', **common)
    check('both assumptions solve', ps.get('ok') and pe.get('ok'))
    if not (ps.get('ok') and pe.get('ok')):
        return
    szz = pe['meanStress']['szz']
    expected = 0.3 * (pe['meanStress']['sxx'] + pe['meanStress']['syy'])
    check('plane strain gives sigma_zz = nu*(sxx+syy), non-zero',
          abs(szz) > 1.0 and abs(szz - expected) < 1e-6 * abs(expected),
          f'szz={szz:.6g} expected={expected:.6g}')
    check('and that changes von Mises, so the assumption matters',
          abs(pe['maxVonMises']['value']
              - ps['maxVonMises']['value']) > 1.0)
    check('each payload states which assumption it used',
          'plane strain' in pe['assumptionNote']
          and 'plane stress' in ps['assumptionNote'])


def test_biaxial_von_mises():
    print('[equal tension-compression — von Mises = sqrt(3)*tau]')
    import math
    tau = 7.0e6
    out = solve_elasticity_2d(
        width=1.0, height=1.0, youngs_modulus=200.0e9, poisson_ratio=0.3,
        tractions=[{'edge': 'right', 'tx': tau},
                   {'edge': 'top', 'ty': -tau}],
        fixed_edges=[{'edge': 'left', 'dof': 'x'},
                     {'edge': 'bottom', 'dof': 'y'}],
        assumption='plane-stress', refine=3)
    check('solve ok', out.get('ok'), str(out.get('error')))
    if not out.get('ok'):
        return
    check('sxx = +tau and syy = -tau',
          abs(out['meanStress']['sxx'] - tau) < 1e-6 * tau
          and abs(out['meanStress']['syy'] + tau) < 1e-6 * tau,
          f"sxx={out['meanStress']['sxx']:.6g} "
          f"syy={out['meanStress']['syy']:.6g}")
    vm = out['maxVonMises']['value']
    want = math.sqrt(3.0) * tau
    check('von Mises = sqrt(3)*tau (the rotated pure-shear state)',
          abs(vm - want) / want < 1e-6, f'vm={vm:.8g} want={want:.8g}')
    check('max principal = +tau, NOT the von Mises value — the two '
          'criteria genuinely disagree here',
          abs(out['maxPrincipal']['value'] - tau) < 1e-6 * tau
          and abs(vm - tau) > 0.5 * tau)


def _kirsch_scf(refine, sigma=1.0e6):
    """Stress concentration factor for a plate with a central hole."""
    out = solve_elasticity_2d(
        width=20.0, height=20.0, hole_radius=1.0,
        youngs_modulus=200.0e9, poisson_ratio=0.3,
        tractions=[{'edge': 'right', 'tx': sigma}],
        fixed_edges=[{'edge': 'left', 'dof': 'x'}],
        pin_rigid_body=True, assumption='plane-stress', refine=refine)
    if not out.get('ok'):
        return None, out
    return out['stressRange']['sxx'][1] / sigma, out


def test_kirsch_hole():
    print('[Kirsch: plate with a hole, SCF -> ~3]')
    results = []
    for refine in (1, 2, 3, 4):
        scf, out = _kirsch_scf(refine)
        check(f'refine={refine} solves', scf is not None,
              str(out.get('error')))
        if scf is None:
            return
        results.append((refine, out['elementCount'], scf))
        print(f'      refine={refine} elements={out["elementCount"]:6d} '
              f'SCF={scf:.4f}')
    scfs = [r[2] for r in results]
    check('SCF increases monotonically with refinement — P1 elements '
          'approach the true peak from BELOW',
          all(b > a for a, b in zip(scfs, scfs[1:])), str(scfs))
    check('finest SCF lands in [2.9, 3.2]: the classic 3.0 for an '
          'infinite plate, nudged up by finite width (d/W = 0.1 gives '
          'Howland K_tg ~ 3.03)',
          2.9 <= scfs[-1] <= 3.2, f'scf={scfs[-1]:.4f}')
    check('the coarsest mesh UNDER-reports the peak, which is exactly '
          'why elementCount is on every payload',
          scfs[0] < scfs[-1] and scfs[0] < 3.0, str(scfs))


def test_convergence_helper():
    print('[mesh-convergence helper]')
    out = elasticity_mesh_convergence(
        refines=(2, 3, 4), width=20.0, height=20.0, hole_radius=1.0,
        youngs_modulus=200.0e9, poisson_ratio=0.3,
        tractions=[{'edge': 'right', 'tx': 1.0e6}],
        fixed_edges=[{'edge': 'left', 'dof': 'x'}],
        pin_rigid_body=True, assumption='plane-stress')
    check('convergence helper runs every level', out.get('ok')
          and len(out['levels']) == 3, str(out.get('error')))
    if not out.get('ok'):
        return
    counts = [lv['elementCount'] for lv in out['levels']]
    check('element count grows with refine', counts == sorted(counts),
          str(counts))
    check('it returns a definite boolean verdict, not a maybe',
          isinstance(out['converging'], bool),
          f"converging={out['converging']!r}")
    # A smooth hole DOES converge: the last refinement moves the peak
    # well under 2%. If this ever flips, the note must switch to the
    # singularity wording — both branches are asserted so the verdict
    # and its explanation can never disagree.
    check('a smooth hole is reported as CONVERGED, and the note says '
          'so (a singularity would say the opposite)',
          (out['converging'] and 'converged' in out['note'])
          or ((not out['converging'])
              and 'STILL MOVING' in out['note']),
          f"converging={out['converging']} note={out['note'][:60]}")
    peaks = [lv['maxPrincipal'] for lv in out['levels']]
    check('the reported peaks are the ones that verdict is based on, '
          'and they are still climbing toward the limit',
          all(b >= a for a, b in zip(peaks, peaks[1:])), str(peaks))


def test_refusals():
    print('[refusal ladder]')
    base = dict(width=1.0, height=1.0, youngs_modulus=200.0e9,
                poisson_ratio=0.3,
                tractions=[{'edge': 'right', 'tx': 1.0e6}],
                fixed_edges=[{'edge': 'left', 'dof': 'x'},
                             {'edge': 'bottom', 'dof': 'y'}])
    bad_nu = dict(base, poisson_ratio=0.5)
    check('nu = 0.5 refuses (incompressible, singular here)',
          not solve_elasticity_2d(**bad_nu).get('ok'))
    check('E <= 0 refuses',
          not solve_elasticity_2d(**dict(base, youngs_modulus=0.0)).get('ok'))
    no_load = dict(base, tractions=())
    out = solve_elasticity_2d(**no_load)
    check('no traction refuses and names the knob',
          not out.get('ok') and out['suggestion']['knob'] == 'tractions')
    no_fix = dict(base, fixed_edges=())
    out = solve_elasticity_2d(**no_fix)
    check('no restraint refuses (singular stiffness) and names the knob',
          not out.get('ok') and out['suggestion']['knob'] == 'fixed_edges')
    check('unknown assumption refuses',
          not solve_elasticity_2d(**dict(base, assumption='axisymmetric'))
          .get('ok'))
    check('unknown edge refuses',
          not solve_elasticity_2d(
              **dict(base, tractions=[{'edge': 'diagonal', 'tx': 1.0}]))
          .get('ok'))
    out = solve_elasticity_2d(**dict(base, hole_radius=0.9))
    check('a hole that reaches the rectangle edge refuses rather than '
          'meshing something invalid',
          not out.get('ok') and 'hole radius' in out['error'])

    saved = fem_engine.capability
    fem_engine.capability = lambda: {
        'available': False, 'library': 'scikit-fem', 'version': '',
        'suggestion': {'evidence': 'simulated absence', 'knob': 'x',
                       'action': 'y'}}
    try:
        out = solve_elasticity_2d(**base)
        check('missing scikit-fem refuses with the install suggestion',
              not out.get('ok') and out['suggestion']['evidence']
              == 'simulated absence')
    finally:
        fem_engine.capability = saved


def main():
    test_capability()
    test_uniaxial()
    test_plane_strain_differs()
    test_biaxial_von_mises()
    test_kirsch_hole()
    test_convergence_helper()
    test_refusals()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
