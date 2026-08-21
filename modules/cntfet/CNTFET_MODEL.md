# cntfet — clean-room VS-CNFET-derived compact model (S1)

**Equation revision:** `cntfet-vs-s1-r2` (r2 adds the polarity
transform: p-type = mirrored n-type, [VS1] premise ii; both
implementations bumped together, regression re-proven incl. a
negative-bias p-type grid) ·
**model_family:** VS-CNFET-derived · **implementation:**
independent · **numerically_equivalent_to_stanford:** false

This is, to the best of the S0 license gate's knowledge
(2026-08-20, `AI-Notes/evaluations/CNT_FET_SIM_LICENSE_GATE.md`),
**the first open-license CNFET compact model** — GPL-3.0-or-later,
implemented exclusively from published papers. The Stanford
VS-CNFET package and TU Dresden CCAM carry the NEEDS Modified CMC
License (GPL-incompatible: price restriction + product-doc
acknowledgment clause); **their source was never read**. This
document + `cnt_vs_model.py` + `cnt_verilog_a.py` +
`selftest_cntfet.py` are deliberately standalone-capable (plan
D17): they can leave Polari as their own repository without
carrying the framework.

## Scope (S1 — the ratified narrow target)

ONE aligned semiconducting CNT: one chirality, one gate stack, one
temperature, one contact-resistance prior. **DC Id-Vg and Id-Vd
only.** No variability, no multi-tube aggregation, no BTBT/S-D
tunneling/parasitics (S2+, additive when they come — plan D12
forbids regime switches). Python is the canonical reference;
the generated Verilog-A twin is the circuit implementation; a
mandatory numerical-equivalence regression binds them (plan D3).

## Sources (all cite-values-only; none redistributed)

| tag | reference |
|---|---|
| [VS1] | Lee, Pop, Franklin, Haensch, Wong, *A Compact Virtual-Source Model for CNFETs in the Sub-10-nm Regime — Part I: Intrinsic Elements*, IEEE TED **62**(9):3061 (2015), DOI [10.1109/TED.2015.2457453] — read via the legally free arXiv:1503.04397 author copy |
| [VS2] | *ibid.* Part II: Extrinsic Elements, DOI 10.1109/TED.2015.2457424 (arXiv:1503.04398) — scoping only at S1 |
| [KHA09] | Khakifirooz, Nayfeh, Antoniadis, IEEE TED **56**(8):1674 (2009), DOI 10.1109/TED.2009.2024022 — the original VS formulation ([VS1] ref 24) |
| [FC10] | Franklin & Chen, Nat. Nanotech. **5**:858 (2010), DOI 10.1038/nnano.2010.220 — the v_xo calibration device set (Lg 15 nm/300 nm/3 µm, same tube, d ≈ 1.2 nm) |
| [RAH03] | Rahman, Guo, Datta, Lundstrom, IEEE TED **50**(9):1853 (2003), DOI 10.1109/TED.2003.815366 — top-of-the-barrier reference (F2) |
| [LUN97] | Lundstrom, IEEE EDL **18**(7):361 (1997), DOI 10.1109/55.596937 — T = λ/(λ+L) |
| [GUO04] | Guo et al., arXiv cond-mat/0312551 — hyperbolic E(k), m* = Eg/2vF² |
| [JAV04]/[PARK04] | Javey PRL **92**:106804 (cond-mat/0309242); Park Nano Lett **4**:517 (cond-mat/0309641) — mfp anchors λ_ac ≈ 300 nm, λ_op ≈ 10–15 nm |
| [WIL98] | Wildöer et al., Nature **391**:59 (1998), DOI 10.1038/34139 — STS: γ0 = 2.7 ± 0.1 eV |

## Equations (each with its source)

**Band structure (S1a, `cnt_bandstructure.py`)**

| eq | source |
|---|---|
| d = √3·a_cc·√(n²+nm+m²)/π, a_cc = 0.142 nm | zone-folding geometry ([VS1] Sec.II context) |
| metallic ⇔ (n−m) mod 3 = 0 | Hamada/Saito 1992 rule |
| Eg = 2·Ep·a_cc/d, Ep = 3 eV (≈ 0.85 eV·nm/d) | [VS1] Sec.II. The STS experiment [WIL98] gives γ0 = 2.7 ± 0.1 (≈ 0.77/d); both recorded, the model uses Ep, the residual stays calibration-visible |
| vF = 3·a_cc·Ep·q/(2ħ) ≈ 9.7×10⁵ m/s | tight-binding cone slope ([GUO04] parameterization) |
| E(k) = √((Eg/2)² + (ħvF·k)²); m* = Eg/2vF² | [GUO04] |
| g(E) = (4/πħvF)·E/√(E²−(Eg/2)²) per unit length | 2 spin × 2 valley; asymptote ≡ [VS1] Cq∞ = 8q²/(3π·a_cc·Ep) |

**Gate electrostatics (S1a)**

| eq | source |
|---|---|
| Cox = 2π·k_ox·ε0 / ln((2·t_ox+d)/d) | [VS1] eq.(1), GAA cylinder |
| Cqe = 0.64·√Eg + 0.1 fF/µm | [VS1] Sec.II.A empirical |
| Cinv = Cox·Cqe/(Cox+Cqe) | [VS1] Sec.II.A |

**Short-channel electrostatics (S1a)**

| eq | source |
|---|---|
| λ = ((d+2t_ox)/2z0)·[1+b(γ−1)], b = 0.41(ζ0/2−ζ0³/16)(πζ0/2), ζ0 = z0·d/(d+2t_ox), γ = k_cnt/k_ox, z0 = 2.405 | [VS1] eq.(7) (valid branch t_ox > d/2) |
| η = (Lg+2·Lof)/2λ, Lof ≈ t_ox/3 | [VS1] Sec.II.C |
| n_ss = (1−e^−η)⁻¹; DIBL δ = e^−η; ΔVt = (2·E_fsd+Eg)·e^−η | [VS1] eq.(8). Interface states NOT included (paper's own statement) — measured SS (135 mV/dec on [FC10]) exceeds n_ss·60; the gap stays visible |

**Transport (S1c, `cnt_vs_model.py` — the compact model)**

| eq | source |
|---|---|
| v_xo = λv/(λv+2l)·vB, l ≈ Lg; λv = 440 nm; vB = 4.1×10⁷ cm/s·√(d/1.2 nm) | [VS1] eq.(9) + Sec.II.D fit to [FC10]. l ≈ Lg stated for Lg < 30 nm — the 3 µm anchor is out-of-domain and its residual (−40%) is recorded, not hidden |
| µ = µ0·Lg/(λµ+Lg)·d^1.5, µ0 = 1350 cm²/Vs, λµ = 66.2 nm | [VS1] eq.(4) (apparent mobility) |
| Vt = Vt0 − ΔVt − δ·Vdsi | [VS1] Sec.II.C |
| Ff = 1/(1+exp((Vgsi−(Vt−α·φt/2))/(α·φt))), α = 3.5 | [KHA09] via [VS1] Sec.II.D |
| Qxo = Cinv·n_ss·φt·ln(1+exp((Vgsi−(Vt−α·φt·Ff))/(n_ss·φt))) | [KHA09]/[VS1] |
| Vdsat = (v_xo·Lg/µ)(1−Ff) + φt·Ff; Fsat = x/(1+|x|^β)^(1/β), x = Vdsi/Vdsat, β = 1.8 | [KHA09] via [VS1] |
| Id = Qxo·v_xo·Fsat (per tube) | VS ansatz [KHA09]/[VS1] |
| Rs = Rd: per-terminal series prior (5.5 kΩ, [VS1] step (a)); quantum floor RQ/2 = h/(4q²)/2 ≈ 3.23 kΩ | [VS1] Sec.IV; D9: Rc never folds into µ |

The Python solver uses bisection on the monotone residual
f(Id) = channel(Vg−Id·Rs, Vd−Id·(Rs+Rd)) − Id (a damped fixed
point oscillates at high Rc — found live at 20 kΩ). The Verilog-A
twin exposes internal nodes and lets the SPICE solver own the same
unique system.

**F2 reference (S1b, `cnt_tob.py` — NOT the circuit model)**

Top-of-the-barrier self-consistency [RAH03]:
U = −q(αG·VG+αD·VD) + q²ΔN/CΣ with the CNT DOS integrated in
k-space (no van Hove singularity numerically), constant-T Landauer
current in closed form (≡ [VS1] eq.(10)), T ∈ {1, λ_ac/(λ_ac+Lg)}
[LUN97]. Intrinsic only (no Rc) — validation-triangle edge, not a
substitute.

## Numerical-equivalence regression (D3, `cnt_osdi.py`)

Generated `.va` (construct-gated: single flat module, scalar
params, static contributions; no arrays/events/filters/shifts) →
OpenVAF → `.osdi` → ngspice ≥ 42 `pre_osdi`. Grid: 5 variants
{base, Lg 300 nm, d 1.0 nm, T 350 K, Rc 20 kΩ} × Vg × Vd — 220
points. Tolerances: rel 1e-4, abs 1e-12 A.
**Status 2026-08-21: EQUIVALENT, worst rel err 4.2e-9** (after
pinning exact SI-2019 constants in both implementations —
`constants.vams` carries older CODATA values, visible at this
tolerance in subthreshold).

Toolchain notes: OpenVAF-Reloaded binaries (fides.fe.uni-lj.si)
need glibc ≥ 2.36; on older hosts the original openvaf 23.5.0
(OSDI 0.3) works and ngspice-46 loads it. Run bundles (osdi +
netlist + sha256-hashed parameter manifest + provenance JSON) keep
model cards non-opaque.

## Calibration (D18, `cnt_calibration.py`)

Anchors are rows with full provenance (figure id, extraction
method, error, conditions, fitted params). Scalar anchors:
v_xo within 2%/3% at 15/300 nm (in-domain), −40% at 3 µm
(out-of-domain, flagged); gm within 2× of the 40 µS record; G_on
0.35 vs 0.7 G0 (G0 = 4e²/h pinned from the paper's own RQ
statement; the negative residual is evidence about the Rc PRIOR —
a recorded tension: Rs = 5.5 kΩ/terminal alone caps G at 0.59 G0,
below the measured 0.7 G0 record).

**S2c (2026-08-21): [VS1] Fig.7(a) Lg = 15 nm curves DIGITIZED**
programmatically (300-dpi render → color-mask + white-interior
components → centroids; axis calibration least-squares over tick
labels; overlay-verified; ±0.005 V / ±0.26 µA per point; 58 points,
coverage 22/17/13/6 per overdrive — `cnt_digitized_fc10.py` is the
full D18 record). Model-vs-curve residuals in the anchor context:
**ov+0.50 RMS 0.30 µA (AT the digitization noise floor, mean
−0.4%)**; ov+0.25 RMS 0.80 µA (−2.7%); ov+0.00 RMS 1.05 µA (−16%,
threshold-region smoothing); ov−0.25 −90% (the device's leakage
floor is unmodeled — honest miss, recorded). Panels (b),(c) and
the [FC10] originals still refuse pending the same treatment.

**S2a/S2b: metric family + validation triangle.** SS/DIBL/Ion/
Ioff/gm/G_on extracted identically from every engine
(`cnt_metrics.py`); the F1-vs-F2 triangle (`cnt_triangle.py`,
`{action: triangle}`) records the intrinsic edge (VS Rc=0 vs ToB:
SS 66.6 vs 59.8 mV/dec, DIBL 14.4 vs 10.0 mV/V, Ion +21%, gm −4%)
and the adaptive-oracle target list (deep-subthreshold points,
~1.35 dex — where F3/Kwant spend goes at S2+). Physics honesty:
ToB respects G ≤ G0 natively; VS-intrinsic may exceed it because
the VS family carries the quantum resistance in Rs by design
([VS1] Sec.IV) — the intrinsic edge compares transport shape,
never absolute conductance.

## S3 — variability (built 2026-08-21)

Manufacturing processes are FIRST-CLASS OBJECTS contributing
distributions (plan D7): Alignment (angle σ), Placement (pitch σ +
missing-tube), Purification (semiconducting purity + diameter
distribution; RINSE/DREAM as cited knobs), ContactFormation
(lognormal Rc — D9 stays first-class in variability), Lithography
(Lg feature σ), GateStack (t_ox/k_ox/Vt σ). The device binds a
`process_set`; `{action: montecarlo}` samples the population
(deterministic under seed), evaluates every survivor with the SAME
metric ruler, and reports yield + kill/violation counts + the
DOMINANT LIMITATION — the D7 feedback-loop output. Refusals: no
bound set, missing process rows, regime mismatch (D6), confidence
'none'. Priors are listed on every run ("a population built on
priors says so"). First run on the seeded target line: 68.5%
functional at 200 samples, dominant limitation = on/off-ratio
violations driven by the Vt-σ prior.

## S4a — complementary inverter (built 2026-08-21)

First circuit rung (`{action: inverter}`): two OSDI instances of
the twin (n + mirrored p) swept in ngspice for the VTC. Measured:
VM = 0.300 V (= VDD/2 for the symmetric pair), peak gain −19.7
(the Hills full-adder measured ~17 — same class), swing 99.996%,
NML = NMH = 0.25 V. Honesty: the p-device is the same device
mirrored — real p/n asymmetry enters through measured process
data.

## S4b — terminal charge + ring oscillator (built 2026-08-21)

Revision **r3** adds [VS1] eq.(11): Qch = −Lg(Qxo − Qxob) with
Cinvb = Cox·Cq∞/(Cox+Cq∞), Cq∞ = 8q²/(3·a_cc·π·Ep), Vtb =
0.7Eg/q + 0.13 — the twin gains `ddt` charge contributions and the
model becomes DYNAMIC. The Cgg(Vgs) curve reproduces the [VS1]
Fig.9 signature from the equations alone: rise, peak (~0.4 V,
3.6 aF for the S1 device), then DECLINE as the quantum capacitance
collapses past the van Hove singularity.

**Clean-room boundary, stated plainly:** the Qs/Qd Ward-Dutton
partitioning + drift/ballistic blend derivation lives in the
NEEDS-licensed technical manual [26], which this project may not
read. S4b uses an EXPLICIT 50/50 split — a labeled, delay-grade
approximation that travels with every result (`PARTITION_NOTE`).

`{action: ring-oscillator}`: the 5-stage complementary ring
OSCILLATES in ngspice transient — **637 GHz, stage delay 157 fs**
(97 crossings measured). INTRINSIC-ONLY: attofarad one-tube
charges, zero parasitics (S2+/[VS2]) — a bound, not a product
claim (plan D1). Consistency: [VS1] Fig.10 reports τ_int ≈ 50 fs
at Lg = 8 nm; our 15 nm device with the 5.5 kΩ contacts at 157 fs
sits exactly where scaling puts it.

## S4c — the D10 minimal cell set demonstrated (built 2026-08-21)

`{action: cells}`: NAND2 (stepped four-corner truth table — only
(1,1) pulls low, 0.1 mV), BUF (rail-to-rail follow), and a
transmission-gate master-slave positive-edge DFF (18 FETs: correct
capture on four consecutive rising edges + hold through mid-cycle
D flips). With S4a's INV that completes the plan-D10 minimal set
at DEMONSTRATION level — characterization (Liberty, slew/load
grids) is S5 behind the CellCharacterizationRun schema.

Two hard-won testbench lessons recorded in `cnt_cells.py`:
(1) the S1 model has NO junction parasitics ([VS2] scope), so
capacitance-free cell nodes (the NAND series-stack mid, inverter
chains) starve the integrator — a small LABELED stand-in cap
(2 aF ≈ half a device Cgg) + Gear integration is the honest cure;
(2) an aborted ngspice transient leaves a partial wrdata file that
a nearest-point sampler silently misreads — every cell testbench
now REFUSES a truncated run.

## S5 first rung — characterization schema + own loop (2026-08-21)

`CellCharacterizationRun` is the D11/D16 schema ABOVE any
executor. The `polari-own-loop` executor (`{action:
characterize}`) sweeps INV over a sparse slew × load grid in
ngspice (definitions recorded with every run: delay 50→50%,
transitions 20–80%), emits a minimal NLDM Liberty (ps/fF, units
stated), and runs the OpenSTA acceptance gate when `sta` exists —
its absence is a RECORDED refusal, and the mandatory D11
SPICE-vs-STA composed-path regression stays an OPEN box until
OpenSTA is installed. First run: 3×3 grid, monotone, delays
343 fs → 1.84 ps, symmetric rise/fall (the mirrored pair).
CharLib/lctime remain gated executors (fork-pinned; lctime mirror
pending).

## F3 — the Kwant NEGF kernel (2026-08-21)

D13/D14 realized: kwant 1.5.0 lives in its OWN virtualenv
(`~/tools/kwant-venv`, numpy<2 — kwant's pregenerated Cython C is
incompatible with numpy 2.x) and `cnt_kwant.py` drives it by
SUBPROCESS through `kwant_worker.py`; the polari process never
imports it, and the capability endpoint probes live. The worker
builds the zigzag (n,0) tube with EXPLICIT pz-TB connectivity
(4n atoms / 3a_cc period) under the [VS1] eq.(5) barrier
(C = vt0 − vg alignment, BCs at ±(Lg/2+Lof)).

Self-pinning physics: TB gap ≡ compact-model Eg by construction
(0.6802 eV); T = 2.000 valleys above the edge — independently
confirming the 4q/h degeneracy the closed forms assume.
`{action: f3-oracle}` spends F3 exactly where the F1/F2 triangle
disagreed (the adaptive-oracle discipline): at those
deep-subthreshold points **F3 lands BETWEEN the two — ~5.6× above
thermionic-only F2 (S/D tunneling through the 1.4 nm-λ barrier is
real) and ~3.8× below F1's α-smoothed tail**; on-state all three
agree within 40% (22.6/27.6/31.9 µA). 2816 atoms, ~7 s/bias
point. Limits riding every result: coherent-only, fixed eq.(5)
potential (self-consistent Poisson = ours to build), zigzag only;
F3 sees the second subband (T→4) that F1/F2 cannot.

## [VS2] extrinsics (built 2026-08-21 evening)

Clean-room from Part II (arXiv:1503.04398), `cnt_extrinsics.py`:

- **Rc(Lc, d)** transmission-line contact model (eqs 2–3) with the
  paper's extracted constants (E00 32 meV, λc 380 nm, gco
  0.49 µS/nm). Reproduces the paper pin: **2Rc = 71.4 kΩ at
  d = 1.2 nm, Lc = 12.9 nm** (paper ~70), φb = −0.045 eV and
  gc = 2.0 µS/nm matching the published extraction. Polarity
  matters: the calibrated case is Pd on p-type (barrier-free);
  applying the n-type form to Pd numbers is a real error (made
  and caught live — Rc came out 10⁹ kΩ). **This RESOLVES the
  recorded Rs tension**: long FC10-style contacts → ~1.2 kΩ
  extrinsic + RQ/2 ≈ 4.4 kΩ/terminal (compatible with the 0.7 G0
  record); short 12.9 nm contacts → 35 kΩ/terminal. The tension
  was contact LENGTH, not physics.
- **Rext** (eq 5) and **Lof(kspa)** (eq 11).
- **I_SDT** (eqs 6–8): WKB through our eq.(5) barrier, numeric
  Landauer (as the paper itself evaluates it — the analytic
  Verilog-A recast is in the NEEDS-blocked manual [31], so the
  OSDI twin stays thermionic-only, labeled). Exponential in Lg:
  0.034 nA at 15 nm vs 281 nA at 5 nm (vg=0, vd=0.6).
- **I_BTBT** (eqs 12–14): closed-form tb; **exactly zero for
  Vds < Eg** — the mechanism vanishes naturally (D12), and the
  S1 device at VDD 0.6 V < Eg 0.68 eV sits below the window.
- **Profile VS_FULL** = thermionic + SDT + BTBT, additive, with
  the per-point decomposition always reported
  (`{action: iv, profile: VS_FULL}`). Parasitic capacitance
  models ([VS2]'s ref [36], paywalled) are NOT implemented.

## What this model must never claim

- It is NOT the Stanford VS-CNFET and is not numerically
  equivalent to it (never validated against their code — by
  design, the code is unreadable to this project).
- No simulated result here is a fabrication prediction (plan D1).
- Vt0 and E_fsd are uncalibrated priors (role: calibration,
  confidence: low) until real device data arrives.
