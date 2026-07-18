"""
@cross-cutting
@module waxprint.auger_melt
@tags @xc:bindings

Pure physics for the pellet-fed auger-screw wax extruder — the "magic
3D printer" melt path. NO manager, NO I/O, stdlib `math` only (so the
selftest and the analysis layer both import it freely, exactly like
mathshapes.shape_geometry).

The device is a single-screw extruder with TWO independently controlled
thermal zones (Dustin 2026-07-17): an AUGER zone (the screw softens /
pre-heats the pellets) and a HOTEND zone (the spout, where the wax is
fully liquid as it exits the nozzle). We emulate discrete pellets being
conveyed through both zones and coming out as a liquid that behaves
according to its COMPUTED material properties (viscosity from an
Arrhenius η(T), flow from Hagen-Poiseuille).

Physics, all first-principles and hand-checkable:

  1. Screw drag conveying (magic feed — no hopper dynamics):
       v_axial = pitch * (rpm/60) * drag_efficiency        [m/s]
       A_channel = (pi/4)(bore^2 - core^2)                 [m^2]
       Q = v_axial * A_channel                             [m^3/s]
     Residence time in a zone = zone_length / v_axial.

  2. Pellet heating — lumped capacitance with an honest Biot gate:
       tau  = m*cp / (h*A)                                 [s]
       T(t) = T_wall + (T0 - T_wall) * exp(-t / tau)       [K]
     Biot = h*(r/3)/k_wax; lumped is valid for Bi < 0.1. Above that the
     pellet interior lags the surface and a radial FEM solve is needed —
     we still return the lumped result as an OPTIMISTIC bound and flag it
     (knobs-and-suggestions), never silently.

  3. Melt fraction — enthalpy method over the two zones. The wall
     delivers E_delivered = integral of h*A*(T_wall - T) dt (closed form
     for the exponential T(t)); melting consumes latent heat at the melt
     plateau. melt_fraction = clamp((E_delivered - E_sensible)/E_latent).

  4. Nozzle pressure — Hagen-Poiseuille for the molten wax:
       eta(T) = eta_ref * exp(B*(1/T - 1/T_ref))           [Pa.s]
       dP = 8 * eta * L_land * Q / (pi * r_nozzle^4)        [Pa]

  5. SAFETY — every natural wax has a thermal-degradation ceiling
     (volatilization / discoloration / smoke point). The hotend set
     temperature must stay at or below safe_melt_max_c, and must clear
     melt_point + margin so the wax actually flows. Both are reported as
     evidence-bearing verdicts, not booleans in a vacuum.

@consumers
  - waxprint.melt_analysis (wraps these with manager lookups + gate)
  - waxprint.selftest_auger_melt (validates against hand computed numbers)
@see /MVW_PRINT_SIM_PLAN.md, /WAX_PRINT_VOXEL_PLAN.md
"""

import math

C_TO_K = 273.15


# --------------------------------------------------------------------------
# small conversions
# --------------------------------------------------------------------------
def c_to_k(t_c):
    return t_c + C_TO_K


def k_to_c(t_k):
    return t_k - C_TO_K


# --------------------------------------------------------------------------
# 1. screw drag conveying (magic feed)
# --------------------------------------------------------------------------
def channel_area_m2(bore_m, core_m):
    """Cross-sectional flow area of the screw channel (annulus between the
    barrel bore and the screw root)."""
    bore_m = max(0.0, bore_m)
    core_m = max(0.0, min(core_m, bore_m))
    return (math.pi / 4.0) * (bore_m * bore_m - core_m * core_m)


def axial_velocity_m_s(pitch_m, rpm, drag_efficiency=0.6):
    """Axial advance of the melt: one screw pitch per revolution at 100%
    drag, scaled by a drag efficiency (real single screws convey well
    below the kinematic ideal; magic-feed so no starvation)."""
    return max(0.0, pitch_m) * (max(0.0, rpm) / 60.0) * max(0.0, drag_efficiency)


def volumetric_flow_m3_s(pitch_m, rpm, bore_m, core_m, drag_efficiency=0.6):
    """Q = v_axial * A_channel — the throughput the nozzle must pass."""
    return (axial_velocity_m_s(pitch_m, rpm, drag_efficiency)
            * channel_area_m2(bore_m, core_m))


# --------------------------------------------------------------------------
# 2. pellet heating (lumped capacitance + Biot honesty)
# --------------------------------------------------------------------------
def pellet_mass_kg(diameter_m, density):
    r = max(0.0, diameter_m) / 2.0
    return density * (4.0 / 3.0) * math.pi * r ** 3


def pellet_area_m2(diameter_m):
    r = max(0.0, diameter_m) / 2.0
    return 4.0 * math.pi * r * r


def biot_number(h, radius_m, k_wax):
    """Bi = h * L_c / k with L_c = r/3 (sphere volume-to-area length).
    Lumped-capacitance is trustworthy for Bi < 0.1."""
    if k_wax <= 0:
        return float('inf')
    return h * (radius_m / 3.0) / k_wax


def time_constant_s(mass_kg, cp, h, area_m2):
    """tau = m*cp / (h*A) — the exponential thermal time constant."""
    denom = h * area_m2
    if denom <= 0:
        return float('inf')
    return mass_kg * cp / denom


def exponential_approach(t0_k, t_wall_k, t_s, tau_s):
    """Closed-form lumped temperature after time t against a fixed wall.
    T(t) = T_wall + (T0 - T_wall) * exp(-t/tau). Exact — the selftest
    checks this against a hand computed value."""
    if tau_s == float('inf') or tau_s <= 0:
        return t0_k
    return t_wall_k + (t0_k - t_wall_k) * math.exp(-t_s / tau_s)


def sensible_energy_j(mass_kg, cp, t_start_k, t_end_k):
    """Energy to raise the sample from t_start to t_end (no phase change)."""
    return mass_kg * cp * (t_end_k - t_start_k)


def delivered_energy_j(t0_k, t_wall_k, t_s, tau_s, mass_kg, cp):
    """Heat the wall delivers to a lumped pellet over [0, t]:
        Q = integral h*A*(T_wall - T) dt
          = m*cp * (T_wall - T0) * (1 - exp(-t/tau))
    (using h*A = m*cp/tau and the exponential T(t)). Closed form, exact
    — equals the sensible energy needed to reach the achieved T(t)."""
    if tau_s == float('inf') or tau_s <= 0:
        return 0.0
    return mass_kg * cp * (t_wall_k - t0_k) * (1.0 - math.exp(-t_s / tau_s))


# --------------------------------------------------------------------------
# 4. molten-wax viscosity + nozzle pressure
# --------------------------------------------------------------------------
def viscosity_pa_s(t_c, eta_ref_pa_s, ref_temp_c, activation_k):
    """Arrhenius-form melt viscosity:
        eta(T) = eta_ref * exp(B*(1/T - 1/T_ref))   (T in kelvin)
    B (activation_k) > 0 → viscosity falls as temperature rises (the
    physical sense for a melt). Returns eta at t_c."""
    t = c_to_k(t_c)
    t_ref = c_to_k(ref_temp_c)
    if t <= 0 or t_ref <= 0:
        return eta_ref_pa_s
    return eta_ref_pa_s * math.exp(activation_k * (1.0 / t - 1.0 / t_ref))


def hagen_poiseuille_dp_pa(eta_pa_s, land_length_m, flow_m3_s, radius_m):
    """dP = 8 * eta * L * Q / (pi * r^4) — laminar pressure drop through
    the nozzle land (a straight capillary of radius r)."""
    if radius_m <= 0:
        return float('inf')
    return (8.0 * eta_pa_s * land_length_m * flow_m3_s
            / (math.pi * radius_m ** 4))


def apparent_shear_rate_s(flow_m3_s, radius_m):
    """Wall shear rate of Poiseuille flow, 4Q/(pi r^3) — reported so the
    caller can sanity-check the Newtonian assumption."""
    if radius_m <= 0:
        return float('inf')
    return 4.0 * flow_m3_s / (math.pi * radius_m ** 3)


# --------------------------------------------------------------------------
# 3. enthalpy state with a latent-heat plateau
# --------------------------------------------------------------------------
def enthalpy_to_state(h_j, mass_kg, cp, latent_j_kg, t0_k, tmelt_k):
    """Map absorbed enthalpy H (J, relative to the T0 start) to
    (temperature_K, melt_fraction) for a material with a latent-heat
    plateau at tmelt. Below the plateau the sample is solid and warming;
    on the plateau it is at tmelt and melting; above it is liquid and
    warming again. This is what makes a phase-change lumped model correct
    where the plain exponential (no latent) is not — the melt STALLS the
    temperature rise, so a fixed wall must keep delivering heat to finish
    the phase change."""
    if mass_kg <= 0 or cp <= 0:
        return t0_k, 0.0
    h_to_melt = mass_kg * cp * (tmelt_k - t0_k)     # sensible, solid
    h_latent = mass_kg * latent_j_kg               # plateau width
    if h_j <= h_to_melt:
        return t0_k + h_j / (mass_kg * cp), 0.0
    if h_latent > 0 and h_j < h_to_melt + h_latent:
        return tmelt_k, (h_j - h_to_melt) / h_latent
    return tmelt_k + (h_j - h_to_melt - h_latent) / (mass_kg * cp), 1.0


def integrate_zone(h_j, t_wall_k, duration_s, tau_s, mass_kg, cp,
                   latent_j_kg, t0_k, tmelt_k, sub_steps=200):
    """Advance the absorbed enthalpy H through one thermal zone held at a
    fixed wall temperature for `duration_s`, using dH/dt = h*A*(T_wall - T)
    with h*A = m*cp/tau and T(H) from enthalpy_to_state. Explicit
    sub-stepping (the plateau makes this stiff-ish; 200 steps is ample for
    the residence/tau ratios here). Returns the new H."""
    if tau_s == float('inf') or tau_s <= 0 or duration_s <= 0:
        return h_j
    hA = mass_kg * cp / tau_s
    dt = duration_s / max(1, int(sub_steps))
    for _ in range(int(sub_steps)):
        temp_k, _mf = enthalpy_to_state(h_j, mass_kg, cp, latent_j_kg,
                                        t0_k, tmelt_k)
        h_j += hA * (t_wall_k - temp_k) * dt
        # a fixed wall cannot heat the sample past its own temperature.
        h_ceiling = mass_kg * cp * (t_wall_k - t0_k) + mass_kg * latent_j_kg
        if h_j > h_ceiling:
            h_j = h_ceiling
    return h_j


# --------------------------------------------------------------------------
# 3 + 5. the two-zone melt with safety verdict
# --------------------------------------------------------------------------
def two_zone_melt(
        # feedstock (SI)
        pellet_diameter_m, density, cp, latent_heat_fusion,
        k_wax, melt_point_c,
        # geometry (SI)
        bore_m, core_m, pitch_m, barrel_length_m, auger_zone_fraction,
        nozzle_radius_m, nozzle_land_m,
        # process
        rpm, ambient_c, auger_temp_c, hotend_temp_c,
        # wall→pellet coupling and drag
        h_wall=250.0, drag_efficiency=0.6,
        # viscosity model
        eta_ref_pa_s=5.0, viscosity_ref_temp_c=100.0, viscosity_activation_k=6000.0,
        # safety
        safe_melt_max_c=180.0, melt_margin_c=10.0, melt_fraction_floor=0.98):
    """Convey a pellet through the auger zone then the hotend zone and
    report the exit state, melt completeness, nozzle pressure, and the
    thermal-safety verdict. All SI in, a plain dict out. Every physical
    step is one of the closed forms above so the whole thing is
    hand-verifiable."""
    r = pellet_diameter_m / 2.0
    mass = pellet_mass_kg(pellet_diameter_m, density)
    area = pellet_area_m2(pellet_diameter_m)
    bi = biot_number(h_wall, r, k_wax)
    tau = time_constant_s(mass, cp, h_wall, area)

    v_ax = axial_velocity_m_s(pitch_m, rpm, drag_efficiency)
    flow = volumetric_flow_m3_s(pitch_m, rpm, bore_m, core_m, drag_efficiency)
    auger_len = barrel_length_m * max(0.0, min(1.0, auger_zone_fraction))
    hotend_len = barrel_length_m - auger_len
    t_auger = auger_len / v_ax if v_ax > 0 else float('inf')
    t_hotend = hotend_len / v_ax if v_ax > 0 else float('inf')

    t0 = c_to_k(ambient_c)
    tw1 = c_to_k(auger_temp_c)
    tw2 = c_to_k(hotend_temp_c)
    tmelt = c_to_k(melt_point_c)

    # Enthalpy integration WITH the latent plateau through both zones —
    # the physically correct lumped melt model (the plain exponential is
    # only valid with no phase change; see enthalpy_to_state).
    h = 0.0
    h = integrate_zone(h, tw1, t_auger, tau, mass, cp,
                       latent_heat_fusion, t0, tmelt)
    t_after_auger_k, mf_after_auger = enthalpy_to_state(
        h, mass, cp, latent_heat_fusion, t0, tmelt)
    h = integrate_zone(h, tw2, t_hotend, tau, mass, cp,
                       latent_heat_fusion, t0, tmelt)
    t_exit_k, melt_fraction = enthalpy_to_state(
        h, mass, cp, latent_heat_fusion, t0, tmelt)
    t_after_auger = t_after_auger_k
    t_exit = t_exit_k
    e_delivered = h
    e_sensible = sensible_energy_j(mass, cp, t0, tmelt)
    e_latent = mass * latent_heat_fusion

    fully_molten = melt_fraction >= melt_fraction_floor
    eta = viscosity_pa_s(k_to_c(t_exit), eta_ref_pa_s,
                         viscosity_ref_temp_c, viscosity_activation_k)
    dp = hagen_poiseuille_dp_pa(eta, nozzle_land_m, flow, nozzle_radius_m)
    shear = apparent_shear_rate_s(flow, nozzle_radius_m)

    # ---- safety + printability verdicts (evidence-bearing) ----
    findings = []
    safe = True
    if hotend_temp_c > safe_melt_max_c:
        safe = False
        findings.append({
            'code': 'over-safe-ceiling', 'severity': 'block',
            'evidence': f'hotend set {hotend_temp_c:.1f}C exceeds this wax '
                        f'thermal-safety ceiling {safe_melt_max_c:.1f}C '
                        f'(degradation / volatilization).',
            'knob': 'condition.hotend_temp_c',
            'action': f'Lower the hotend to <= {safe_melt_max_c:.1f}C.'})
    if hotend_temp_c < melt_point_c + melt_margin_c:
        findings.append({
            'code': 'below-melt-margin', 'severity': 'warn',
            'evidence': f'hotend set {hotend_temp_c:.1f}C is under melt point '
                        f'{melt_point_c:.1f}C + margin {melt_margin_c:.1f}C — '
                        f'flow will be sluggish / incomplete.',
            'knob': 'condition.hotend_temp_c',
            'action': f'Raise the hotend toward '
                      f'{melt_point_c + melt_margin_c:.1f}C.'})
    if not fully_molten:
        findings.append({
            'code': 'under-melted', 'severity': 'warn',
            'evidence': f'melt fraction {melt_fraction:.3f} below floor '
                        f'{melt_fraction_floor:.2f} — unmelted core will '
                        f'clog the nozzle.',
            'knob': 'condition.rpm / assembly.barrel_length / condition.'
                    'hotend_temp_c',
            'action': 'Slow the screw (more residence), lengthen the barrel, '
                      'or raise the hotend within the safety ceiling.'})
    if bi >= 0.1:
        findings.append({
            'code': 'lumped-optimistic', 'severity': 'note',
            'evidence': f'Biot {bi:.3f} >= 0.1 — pellet interior lags the '
                        f'surface; lumped melt fraction is an OPTIMISTIC '
                        f'bound.',
            'knob': 'feedstock.pellet_diameter_m',
            'action': 'Use smaller pellets, or run a radial FEM solve for '
                      'the true melt time.'})

    printable = safe and fully_molten and (
        hotend_temp_c >= melt_point_c + melt_margin_c)

    return {
        'flow_m3_s': flow,
        'axial_velocity_m_s': v_ax,
        'residence_auger_s': t_auger,
        'residence_hotend_s': t_hotend,
        'time_constant_s': tau,
        'biot': bi,
        'lumped_valid': bi < 0.1,
        'temp_after_auger_c': k_to_c(t_after_auger),
        'exit_temp_c': k_to_c(t_exit),
        'energy_delivered_j': e_delivered,
        'energy_sensible_to_melt_j': e_sensible,
        'energy_latent_j': e_latent,
        'melt_fraction': melt_fraction,
        'fully_molten': fully_molten,
        'exit_viscosity_pa_s': eta,
        'nozzle_pressure_pa': dp,
        'nozzle_shear_rate_s': shear,
        'thermally_safe': safe,
        'printable': printable,
        'findings': findings,
    }
