"""
@cross-cutting
@module waxprint.bead_cooling
@tags @xc:bindings

Pure physics for the DEPOSITED bead (wp-2) — the road of molten wax after
it leaves the nozzle. NO manager, NO I/O, stdlib `math` only. Reuses the
latent-plateau enthalpy state from auger_melt (freezing releases latent
heat, exactly the melt in reverse).

What it answers:

  1. How fast does a bead solidify? Newtonian cooling to air + conduction
     into the substrate (a cold metal bed for layer 1, warm wax above),
     with the latent-heat plateau slowing the freeze. t_solidify vs the
     time until the next layer lands is the print-speed gate.

  2. THE FAN QUESTION, answered with data (Dustin suspects a fan just
     adds instability). A fan is a WIND VECTOR. Forced convection over the
     bead (a cylinder in cross-flow) via the Hilpert Nusselt correlation
     raises the heat-transfer coefficient — which SPEEDS solidification
     (good: less spread, finer voxels). But the wind also cools the
     windward face harder than the sheltered leeward face, and that
     asymmetry is a warp/curl driver (bad). We report BOTH, so "gentle
     ducted good, strong bare fan warps" is a computed result, not an
     assumption.

  3. How much does the bead spread/sag before it freezes? Gravity-driven
     viscous leveling, dw/dt ∝ ρ g h² / (η(T) · w), integrated over the
     liquid time. Colder / faster-freezing / more-viscous → less spread →
     the bead lands closer to its commanded width. This is the in-plane
     accuracy the voxel model consumes.

@consumers
  - waxprint.voxel_resolution (achievable voxel + at-height table)
  - waxprint.bead_analysis (row resolution + HTTP)
  - waxprint.selftest_bead_voxel
"""

import math

from waxprint.auger_melt import c_to_k, k_to_c, enthalpy_to_state

G = 9.81                    # m/s^2
P_ATM = 101325.0           # Pa
R_AIR = 287.05             # J/kg.K
MU_AIR = 1.81e-5           # Pa.s (near room temp; weak T-dependence ignored)
K_AIR = 0.026              # W/m.K
PR_AIR = 0.71              # Prandtl


# --------------------------------------------------------------------------
# air + forced convection (the fan as a wind vector)
# --------------------------------------------------------------------------
def air_density(temp_c):
    """Ideal-gas air density at temperature (colder air is denser → a
    fridge fan bites a little harder)."""
    return P_ATM / (R_AIR * c_to_k(temp_c))


def reynolds_number(wind_speed_m_s, char_length_m, temp_c):
    return air_density(temp_c) * wind_speed_m_s * char_length_m / MU_AIR


def hilpert_nusselt(re):
    """Hilpert correlation Nu = C·Re^m·Pr^(1/3) for a cylinder in
    cross-flow, banded by Reynolds number. Returns 0 at Re→0 (no forced
    convection with no wind — natural convection is carried separately as
    the still-air baseline)."""
    if re <= 0:
        return 0.0
    if re < 4:
        c, m = 0.989, 0.330
    elif re < 40:
        c, m = 0.911, 0.385
    elif re < 4000:
        c, m = 0.683, 0.466
    elif re < 40000:
        c, m = 0.193, 0.618
    else:
        c, m = 0.027, 0.805
    return c * re ** m * PR_AIR ** (1.0 / 3.0)


def forced_h(wind_speed_m_s, char_length_m, temp_c):
    """h_forced = Nu·k_air/D from the wind speed and bead width."""
    if char_length_m <= 0:
        return 0.0
    re = reynolds_number(wind_speed_m_s, char_length_m, temp_c)
    return hilpert_nusselt(re) * K_AIR / char_length_m


def bed_conductance_h(k_bed_w_mk, h_max=3000.0, k_half=20.0):
    """Effective bead→substrate contact conductance (W/m^2.K). Real
    contact conductance SATURATES for high-conductivity substrates (it is
    limited by the imperfect contact interface, not the bulk metal), so a
    conductive metal bed and an insulating PEI bed differ but neither runs
    away: h = h_max·k/(k + k_half). Aluminum (167) → ~2.7k, borosilicate
    glass (1.1) → ~160, PEI (0.25) → ~37 W/m^2.K."""
    if k_bed_w_mk <= 0:
        return 0.0
    return h_max * k_bed_w_mk / (k_bed_w_mk + k_half)


# --------------------------------------------------------------------------
# bead cross-section
# --------------------------------------------------------------------------
def bead_cross_section(width_m, layer_height_m):
    """Approximate the road as a rectangle: area, air-exposed perimeter
    (top + two sides), and bed-contact width (bottom)."""
    area = width_m * layer_height_m
    air_perim = width_m + 2.0 * layer_height_m
    bed_width = width_m
    return area, air_perim, bed_width


# --------------------------------------------------------------------------
# the bead cooling + spread integrator
# --------------------------------------------------------------------------
def cool_bead(
        exit_temp_c, width_m, layer_height_m,
        # feedstock
        density, cp, latent_j_kg, melt_point_c,
        eta_ref_pa_s, viscosity_ref_temp_c, viscosity_activation_k,
        # environment
        ambient_c, bed_temp_c, still_air_h, wind_speed_m_s,
        k_bed_w_mk, substrate_is_bed=True, substrate_temp_c=None,
        # solve controls / calibration
        max_time_s=20.0, steps=400, k_spread=0.3):
    """Cool one unit-length bead from exit_temp down through solidification
    and accumulate its viscous spread. Returns a dict with t_solidify_s,
    final_width_m, spread_m, the convection coefficients, and a warp
    asymmetry index. All per unit length; widths in metres."""
    from waxprint.auger_melt import viscosity_pa_s

    area, air_perim, bed_width = bead_cross_section(width_m, layer_height_m)
    mass = density * area                       # per unit length (kg/m)
    tmelt_k = c_to_k(melt_point_c)
    t_amb_k = c_to_k(ambient_c)
    # substrate: the bed (layer 1) or the warm layer below.
    sub_temp_c = bed_temp_c if substrate_is_bed else (
        substrate_temp_c if substrate_temp_c is not None else ambient_c)
    sub_temp_k = c_to_k(sub_temp_c)

    # Reference the enthalpy to "fully solid at ambient" (t0 = ambient).
    # Start fully liquid at exit temp.
    h = mass * cp * (c_to_k(exit_temp_c) - t_amb_k) + mass * latent_j_kg

    h_forced = forced_h(wind_speed_m_s, width_m, ambient_c)
    h_air = still_air_h + h_forced
    h_bed = bed_conductance_h(k_bed_w_mk) if substrate_is_bed else \
        bed_conductance_h(0.25)                    # wax-on-wax low-k

    dt = max_time_s / max(1, int(steps))
    t = 0.0
    t_solidify = None
    width = width_m
    for _ in range(int(steps)):
        temp_k, mf = enthalpy_to_state(h, mass, cp, latent_j_kg,
                                       t_amb_k, tmelt_k)
        if mf <= 0.0 and t_solidify is None:
            t_solidify = t
            break
        # spread only while still molten (mf > 0 or above melt).
        if temp_k >= tmelt_k - 1e-9:
            eta = max(1e-4, viscosity_pa_s(
                k_to_c(temp_k), eta_ref_pa_s, viscosity_ref_temp_c,
                viscosity_activation_k))
            # Lubrication-theory gravity leveling: the spreading rate of a
            # proud viscous film goes as ρ g h³ / (η · L) (h³, NOT h² — a
            # 0.2 mm road levels at microns/s, not m/s).
            dwdt = k_spread * density * G * layer_height_m ** 3 / (eta * width)
            width += dwdt * dt
        q_air = h_air * air_perim * (temp_k - t_amb_k)
        q_bed = h_bed * bed_width * (temp_k - sub_temp_k)
        h -= (q_air + q_bed) * dt
        t += dt
    if t_solidify is None:
        t_solidify = max_time_s                  # did not freeze in window

    spread = max(0.0, width - width_m)
    # Warp asymmetry: fraction of cooling that is directional (windward
    # face sees h_air, the sheltered wake ~0.5×). 0 with no wind.
    leeward_h = still_air_h + 0.5 * h_forced
    warp_index = 0.0
    if h_air > 0:
        warp_index = (h_air - leeward_h) / h_air
    return {
        't_solidify_s': t_solidify,
        'final_width_m': width,
        'spread_m': spread,
        'h_air_w_m2k': h_air,
        'h_forced_w_m2k': h_forced,
        'h_bed_w_m2k': h_bed,
        'reynolds': reynolds_number(wind_speed_m_s, width_m, ambient_c),
        'warp_index': warp_index,
        'froze_in_window': t_solidify < max_time_s,
    }


def wind_speed_from_vector(vx_mm_s, vy_mm_s, vz_mm_s):
    """Magnitude of the fan wind vector, mm/s → m/s."""
    return math.sqrt(vx_mm_s ** 2 + vy_mm_s ** 2 + vz_mm_s ** 2) / 1000.0
