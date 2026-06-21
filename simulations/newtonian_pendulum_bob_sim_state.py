"""
@cross-cutting
@module simulations.newtonian_pendulum_bob_sim_state
@tags @xc:bindings, @xc:render-3d

NewtonianPendulumBobSimState — the bob of the *Newtonian* pendulum: a
reality-first reformulation of the Simple pendulum (pendulum-2d) that
drops the magical seeded "energy" and instead integrates real
**Newtonian mechanics in 3D vectors**:

    a = F_applied / m                  (Newton's 2nd law)
    v ← v + a·dt,  p ← p + v·dt         (semi-implicit Euler)
    p ← pivot + L·n̂,  v ← v − (v·n̂)n̂    (RIGID-ROD constraint projection)
    F_tension = −(F_applied·n̂ + m|v|²/L)·n̂   (bilateral — can push AND pull)
    F_net = F_applied + F_tension
    KE = ½m|v|²,  PE = m·g·(p_y − pivot_y + L)   (energies are DERIVED, not seeded)

Distinct from the Simple pendulum on three axes:
  * vectors + matrix calculus instead of a scalar angle integrator;
  * a real `mass` and a metric `bob_radius` (→ surface area / volume /
    cross-section, dormant geometry that wind/buoyancy will use);
  * a RIGID ROD (not a string): the constraint is bilateral, so tension
    is SIGNED (compression allowed past horizontal). We never clamp it.

`f_app_*` is a transient applied-force accumulator (gravity now; wind
later as an additional Partial). It is `derivable` ON PURPOSE: the
runner resets derivable fields to their constructor default (0.0) each
step, so the Partials' `op:'add'` contributions start from zero — this
is what makes adding a wind force a drop-in second Partial.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.seed_data (newtonian-pendulum-3d sim + step solutions)
  - SimSpace3D binding (sphere at px/py/pz)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class NewtonianPendulumBobSimState(treeObject):
    """One persisted timestep of the Newtonian pendulum's bob.

    Identity is composite on (simulation_run_ref, step); the runner names
    rows "<run>-newtonian-pendulum-bob-<step>". Membership in the
    newtonian-pendulum-3d simulation is declared by the class attribute.

    Parameters (mass, g, L, bob_radius, rod_radius, viz_force_scale, plus
    the precomputed geometry constants) live in the SimulationDefinition's
    `parameters_json`, NOT on the row — they're constants of the sim, read
    into each step's context as `self.<param>`.
    """

    simulation_definition_name = 'newtonian-pendulum-3d'

    # t=0 release: 30° to the right, at rest, L=1, m=1, g=9.81, pivot=origin.
    #   p = (L sinθ, −L cosθ, 0) = (0.5, −0.866…, 0)
    # Force/energy diagnostics are pre-filled so the step-0 frame already
    # shows correct arrows + readouts before the integrator runs at step 1.
    #   F_grav   = (0, −mg, 0)                       = (0, −9.81, 0)
    #   |T|      = mg cosθ                           = 8.4957  (rod, at rest)
    #   F_tens   = −|T|·n̂                            = (−4.2479, 7.3573, 0)
    #   F_net    = F_grav + F_tens                   = (−4.2479, −2.4527, 0)
    #   PE       = mg(p_y + L)                        = 1.3143,  KE = 0
    default_initial_field_values = {
        # Real degrees of freedom (3D position + velocity vectors).
        'px': 0.5,
        'py': -0.8660254037844387,
        'pz': 0.0,
        'vx': 0.0,
        'vy': 0.0,
        'vz': 0.0,
        # Force vectors (diagnostic + drive the 3D arrows).
        'fgrav_x': 0.0, 'fgrav_y': -9.81, 'fgrav_z': 0.0,
        'ftens_x': -4.247855, 'ftens_y': 7.357275, 'ftens_z': 0.0,
        'fnet_x': -4.247855, 'fnet_y': -2.452725, 'fnet_z': 0.0,
        # Energies — DERIVED quantities, shown for conservation checking.
        'speed': 0.0,
        'ke': 0.0,
        'pe': 1.3142705,
        'energy_total': 1.3142705,
    }

    # Persistence policy.
    #   core      — persisted every step.
    #   derivable — NOT persisted; the row falls back to the constructor
    #               default (0.0) each step.
    #
    # px/py/pz/vx/vy/vz are core — they carry the integration forward and
    # the 3D binding reads px/py/pz off the row.
    #
    # f_app_x/y/z are derivable BY DESIGN (force accumulator: must reset to
    # 0 each step so Partials' `add` starts from zero — see module docstring).
    #
    # The force vectors + energies are core: the Composition writes them
    # fresh each step (output-mapped, never accumulated), so persisting them
    # is safe and makes them inspectable in the scrubber.
    field_save_policy = {
        'px': 'core', 'py': 'core', 'pz': 'core',
        'vx': 'core', 'vy': 'core', 'vz': 'core',
        # Applied-force accumulator — transient; reset each step.
        'f_app_x': 'derivable', 'f_app_y': 'derivable', 'f_app_z': 'derivable',
        # Force diagnostics (computed fresh each step).
        'fgrav_x': 'core', 'fgrav_y': 'core', 'fgrav_z': 'core',
        'ftens_x': 'core', 'ftens_y': 'core', 'ftens_z': 'core',
        'fnet_x': 'core', 'fnet_y': 'core', 'fnet_z': 'core',
        'speed': 'core',
        'ke': 'core',
        'pe': 'core',
        'energy_total': 'core',
    }

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        simulation_run_ref: str = '',
        step: int = 0,
        time: float = 0.0,
        # --- real DOF: 3D position + velocity (metres, m/s) ---
        px: float = 0.0,
        py: float = 0.0,
        pz: float = 0.0,
        vx: float = 0.0,
        vy: float = 0.0,
        vz: float = 0.0,
        # --- applied-force accumulator (gravity now; wind later) ---
        f_app_x: float = 0.0,
        f_app_y: float = 0.0,
        f_app_z: float = 0.0,
        # --- force vectors (Newtons) — diagnostics + 3D arrows ---
        fgrav_x: float = 0.0,
        fgrav_y: float = 0.0,
        fgrav_z: float = 0.0,
        ftens_x: float = 0.0,
        ftens_y: float = 0.0,
        ftens_z: float = 0.0,
        fnet_x: float = 0.0,
        fnet_y: float = 0.0,
        fnet_z: float = 0.0,
        # --- derived energies (J) ---
        speed: float = 0.0,
        ke: float = 0.0,
        pe: float = 0.0,
        energy_total: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.step = step
        self.time = time
        self.px = px
        self.py = py
        self.pz = pz
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.f_app_x = f_app_x
        self.f_app_y = f_app_y
        self.f_app_z = f_app_z
        self.fgrav_x = fgrav_x
        self.fgrav_y = fgrav_y
        self.fgrav_z = fgrav_z
        self.ftens_x = ftens_x
        self.ftens_y = ftens_y
        self.ftens_z = ftens_z
        self.fnet_x = fnet_x
        self.fnet_y = fnet_y
        self.fnet_z = fnet_z
        self.speed = speed
        self.ke = ke
        self.pe = pe
        self.energy_total = energy_total
