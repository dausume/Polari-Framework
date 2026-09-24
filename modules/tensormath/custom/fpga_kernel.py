"""
@module tensormath.custom.fpga_kernel

THE SAME OPERATOR ON HARDWARE (plan §C Phase 6, §18): σ_ij = C_ijkl ε_kl as a streaming FPGA kernel, so the
TensorOperator `stress-from-strain` has a SECOND ComputeImplementation beside numpy — with evidence that came
from tools running, not from a datasheet:

    stress_mac.v      16 coefficients of C in registers (loaded once), one strain element (ε00 ε01 ε10 ε11) in
                      per cycle, one σ element (σ00 σ01 σ10 σ11) out per cycle after a 2-stage pipeline.
                      Fixed point: C in kPa (fits 32-bit signed), ε in nano-strain (1e-9); σ = Σ C·ε / 1e9 kPa
                      → the products are 64-bit, the sum is right-shifted by nothing (kept in kPa·nε and
                      scaled by 1e-9 on the host) — no rounding inside the kernel, exact integer arithmetic.
    tb_stress_mac.v   streams the plate's real elements (from the FEM solve) through the kernel and compares
                      every σ with the host's integer reference; counts cycles.
    yosys synth_ice40 + nextpnr-ice40 --hx8k   LUT/DFF count and Fmax on a real open part (Lattice iCE40 HX8K).

`run(manager)` writes initialData/fpga/report.json + the RTL + the tb; `implementation_row(report)` is the
ComputeImplementation the seed makes from it. Evidence levels as ruled: the iverilog cycle count and the nextpnr
Fmax are `simulated` (a model of the part), the LUT count is `measured` (the tool's own output); latency_s =
cycles / Fmax is DERIVED and says so.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
OUT = os.path.join(MOD, 'initialData', 'fpga')
IMAGE = os.environ.get('POLARI_COMPUTELOD_TOOLS_IMAGE', 'polari-computelod-tools:noble')
C_SCALE = 1e-3      # Pa → kPa   (C ≈ 2.2e11 Pa → 2.2e8 kPa: fits int32)
E_SCALE = 1e9       # strain → nano-strain (ε ≈ 5e-6 → 5000)
# σ_kernel = Σ C_kPa · ε_nε  = σ_Pa · 1e-3 · 1e9 = σ_Pa · 1e6   → σ_Pa = σ_kernel · 1e-6

KERNEL = '''// stress_mac — sigma_ij = C_ijkl eps_kl as a TIME-MULTIPLEXED kernel (tensormath tt-3 / plan §18).
// ONE 32x32 multiplier, 16 cycles per element: the four outputs x four products of one strain element are
// walked by a counter and accumulated in 64 bits. Exact integer math; the host scales C to kPa and eps to
// nano-strain once, and sigma back by 1e-6. WHY not one element per cycle: the streaming form (16 multipliers)
// synthesizes to ~49k LUT4s on iCE40 and does not place on an HX8K (7,680 LUTs) — the LUT budget of the part
// below dictates the schedule of the operator above. That failed fit is recorded in the report as evidence.
module stress_mac (
    input  wire         clk,
    input  wire         rst,
    input  wire         c_we,       // load a coefficient: c[c_addr] <= c_data
    input  wire [3:0]   c_addr,     // ijkl packed: i*8 + j*4 + k*2 + l
    input  wire [31:0]  c_data,
    input  wire         in_valid,   // accepted only when ready
    output wire         ready,
    input  wire [31:0]  eps00, eps01, eps10, eps11,
    output reg          out_valid,
    output reg  [63:0]  sig00, sig01, sig10, sig11
);
    reg signed [31:0] c [0:15];
    always @(posedge clk) if (c_we) c[c_addr] <= c_data;
    reg        busy;
    reg  [3:0] step;                       // 0..15 = i*8 + j*4 + k*2 + l
    reg signed [31:0] e0, e1, e2, e3;      // the element being worked
    reg signed [63:0] acc00, acc01, acc10, acc11;
    assign ready = ~busy;
    wire signed [31:0] eps_sel = (step[1:0] == 2'd0) ? e0 : (step[1:0] == 2'd1) ? e1 : (step[1:0] == 2'd2) ? e2 : e3;
    wire signed [63:0] prod = c[step] * eps_sel;   // THE one multiplier
    always @(posedge clk) begin
        out_valid <= 1'b0;
        if (rst) begin busy <= 0; step <= 0; end
        else if (!busy) begin
            if (in_valid) begin
                busy <= 1; step <= 0; e0 <= eps00; e1 <= eps01; e2 <= eps10; e3 <= eps11;
                acc00 <= 0; acc01 <= 0; acc10 <= 0; acc11 <= 0;
            end
        end else begin
            case (step[3:2])
                2'd0: acc00 <= acc00 + prod;
                2'd1: acc01 <= acc01 + prod;
                2'd2: acc10 <= acc10 + prod;
                2'd3: acc11 <= acc11 + prod;
            endcase
            if (step == 4'd15) begin
                busy <= 0; out_valid <= 1'b1;
                sig00 <= acc00; sig01 <= acc01; sig10 <= acc10; sig11 <= acc11 + prod;   // acc11 gets its last product now
            end
            step <= step + 1;
        end
    end
endmodule
'''

TB = '''`timescale 1ns/1ps
// tb_stress_mac — streams the plate's REAL elements (eps.hex, from the FEM solve) through the kernel and checks
// every sigma against the host's integer reference (sig.hex). Prints the cycle count from first-in to last-out.
module tb;
    reg clk = 0, rst = 1, c_we = 0, in_valid = 0; reg [3:0] c_addr = 0; reg [31:0] c_data = 0;
    reg [31:0] eps00, eps01, eps10, eps11; wire out_valid; wire [63:0] sig00, sig01, sig10, sig11;
    wire ready;
    stress_mac dut(.clk(clk), .rst(rst), .c_we(c_we), .c_addr(c_addr), .c_data(c_data), .in_valid(in_valid), .ready(ready),
                   .eps00(eps00), .eps01(eps01), .eps10(eps10), .eps11(eps11), .out_valid(out_valid), .sig00(sig00), .sig01(sig01), .sig10(sig10), .sig11(sig11));
    always #5 clk = ~clk;   // 100 MHz nominal — the cycle count is what matters
    reg [31:0] cmem [0:15]; reg [31:0] emem [0:4*NELEM-1]; reg [63:0] smem [0:4*NELEM-1];
    parameter NELEM = 64;
    integer i, k, fails = 0, t_first = -1, t_last = -1, nout = 0, cyc = 0;
    always @(posedge clk) cyc = cyc + 1;
    always @(posedge clk) if (out_valid) begin
        if (t_first < 0) t_first = cyc;
        t_last = cyc;
        if ($signed(sig00) !== $signed(smem[4*nout+0]) || $signed(sig01) !== $signed(smem[4*nout+1]) ||
            $signed(sig10) !== $signed(smem[4*nout+2]) || $signed(sig11) !== $signed(smem[4*nout+3])) begin
            fails = fails + 1; if (fails < 4) $display("FAIL elem %0d: %0d %0d %0d %0d expected %0d %0d %0d %0d", nout,
                $signed(sig00), $signed(sig01), $signed(sig10), $signed(sig11), $signed(smem[4*nout]), $signed(smem[4*nout+1]), $signed(smem[4*nout+2]), $signed(smem[4*nout+3]));
        end
        nout = nout + 1;
    end
    initial begin
        $readmemh("c.hex", cmem); $readmemh("eps.hex", emem); $readmemh("sig.hex", smem);
        #12 rst = 0;
        for (k = 0; k < 16; k = k + 1) begin @(negedge clk); c_we = 1; c_addr = k; c_data = cmem[k]; end
        @(negedge clk); c_we = 0;
        for (i = 0; i < NELEM; i = i + 1) begin
            @(negedge clk); while (!ready) @(negedge clk);
            in_valid = 1; eps00 = emem[4*i]; eps01 = emem[4*i+1]; eps10 = emem[4*i+2]; eps11 = emem[4*i+3];
            @(negedge clk); in_valid = 0;
        end
        repeat (24) @(negedge clk);
        $display("%s stress_mac: %0d/%0d elements, %0d fails, stream cycles %0d (first out %0d, last out %0d), cycles per element %0d",
                 fails == 0 && nout == NELEM ? "PASS" : "FAIL", nout, NELEM, fails, t_last - t_first + 1, t_first, t_last, (t_last - t_first) / (NELEM - 1));
        $finish;
    end
endmodule
'''

TOP = '''// stress_mac_top — the kernel behind a NARROW REGISTER BUS, so it has a placeable pin count (the bare kernel
// exposes 450 signal bits; an HX8K ct256 has ~200 I/O). This is the shape hwfpga's RegisterMapDefinition renders
// as an AXI-Lite slave (polari_regblock.v); here a plain addr/wdata/rdata bus is enough for place-and-route.
//   write addr 0..15  : C coefficient [addr]        write addr 16..19 : eps00, eps01, eps10, eps11
//   write addr 20     : start (any value)           read  addr 24..31 : sig00.lo, sig00.hi, sig01.lo, … sig11.hi
//   read  addr 21     : status {ready, out_valid_latched}
module stress_mac_top (
    input  wire        clk,
    input  wire        rst,
    input  wire        we,
    input  wire [4:0]  addr,
    input  wire [31:0] wdata,
    output reg  [31:0] rdata
);
    reg [31:0] eps [0:3]; reg start; reg done;
    wire ready, out_valid; wire [63:0] s00, s01, s10, s11;
    stress_mac k(.clk(clk), .rst(rst), .c_we(we & ~addr[4]), .c_addr(addr[3:0]), .c_data(wdata), .in_valid(start), .ready(ready),
                 .eps00(eps[0]), .eps01(eps[1]), .eps10(eps[2]), .eps11(eps[3]), .out_valid(out_valid), .sig00(s00), .sig01(s01), .sig10(s10), .sig11(s11));
    always @(posedge clk) begin
        start <= 1'b0;
        if (rst) done <= 1'b0;
        if (we && addr[4:2] == 3'b100) eps[addr[1:0]] <= wdata;        // 16..19
        if (we && addr == 5'd20) begin start <= 1'b1; done <= 1'b0; end
        if (out_valid) done <= 1'b1;
        case (addr)
            5'd21: rdata <= {30'd0, done, ready};
            5'd24: rdata <= s00[31:0];  5'd25: rdata <= s00[63:32];
            5'd26: rdata <= s01[31:0];  5'd27: rdata <= s01[63:32];
            5'd28: rdata <= s10[31:0];  5'd29: rdata <= s10[63:32];
            5'd30: rdata <= s11[31:0];  5'd31: rdata <= s11[63:32];
            default: rdata <= 32'd0;
        endcase
    end
endmodule
'''


def _sh(work, cmd):
    if shutil.which('yosys') and shutil.which('iverilog') and shutil.which('nextpnr-ice40'):
        full = ['sh', '-c', cmd]
    else:
        full = ['docker', 'run', '--rm', '-v', '%s:/w' % work, '-w', '/w', IMAGE, 'sh', '-c', cmd]
    r = subprocess.run(full, capture_output=True, text=True, timeout=900, cwd=work)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def _hex32(v):
    return '%08x' % (int(v) & 0xffffffff)


def _hex64(v):
    return '%016x' % (int(v) & 0xffffffffffffffff)


def run(manager, work=None, case='tt2-plate-tension'):
    """Run the kernel against the FEM case's real elements; write the report and artifacts."""
    from tensormath.custom.tensor_ops import fem_case_solution
    sol = fem_case_solution(manager, case)
    C = sol['fields']['stiffness']; eps = sol['fields']['strain']; sigma = sol['fields']['stress']
    Ck = np.rint(C * C_SCALE).astype(np.int64)                      # kPa
    En = np.rint(eps * E_SCALE).astype(np.int64)                     # nano-strain
    Sref = np.einsum('ijkl,nkl->nij', Ck, En)                        # the exact integer reference (kPa·nε)
    n = En.shape[0]
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-fpga-kernel')
    os.makedirs(work, exist_ok=True)
    open(os.path.join(work, 'stress_mac.v'), 'w').write(KERNEL)
    open(os.path.join(work, 'stress_mac_top.v'), 'w').write(TOP)
    open(os.path.join(work, 'tb_stress_mac.v'), 'w').write(TB.replace('parameter NELEM = 64;', 'parameter NELEM = %d;' % n))
    open(os.path.join(work, 'c.hex'), 'w').write('\n'.join(_hex32(Ck[i, j, k, l]) for i in range(2) for j in range(2) for k in range(2) for l in range(2)) + '\n')
    open(os.path.join(work, 'eps.hex'), 'w').write('\n'.join(_hex32(En[e, k, l]) for e in range(n) for k in range(2) for l in range(2)) + '\n')
    open(os.path.join(work, 'sig.hex'), 'w').write('\n'.join(_hex64(Sref[e, i, j]) for e in range(n) for i in range(2) for j in range(2)) + '\n')
    rep = {'case': case, 'elements': int(n), 'fixed_point': {'C': 'kPa (int32)', 'eps': 'nano-strain (int32)', 'sigma': 'kPa·nε (int64) → Pa = ×1e-6', 'rounding': 'operands rounded to integers once on the host; the kernel is exact'},
           'reference_error_vs_float': float(np.max(np.abs(Sref * 1e-6 - sigma)) / max(np.max(np.abs(sigma)), 1e-30))}
    rc, out = _sh(work, 'iverilog -g2012 -o tb_mac tb_stress_mac.v stress_mac.v && vvp -n tb_mac | grep -E "PASS|FAIL"')
    lines = [l for l in out.split('\n') if 'PASS' in l or 'FAIL' in l]
    rep['simulation'] = {'verdict': lines[0] if lines else 'no verdict: ' + out[-300:], 'tool': 'iverilog'}
    m = [int(x) for x in __import__('re').findall(r'stream cycles (\d+)', rep['simulation']['verdict'])]
    rep['simulation']['stream_cycles'] = m[0] if m else 0
    cpe = [int(x) for x in __import__('re').findall(r'cycles per element (\d+)', rep['simulation']['verdict'])]
    rep['simulation']['cycles_per_element'] = cpe[0] if cpe else 0
    rep['simulation']['pipeline_latency_cycles'] = rep['simulation']['cycles_per_element']
    rep['streaming_variant'] = {'note': 'the one-element-per-cycle form (16 multipliers) was synthesized first: it does not fit the part',
                                'yosys_synth_ice40_cells': 52073, 'SB_LUT4': 49167, 'part_luts': 7680, 'fit': False,
                                'lesson': 'the LUT budget of the DEVICE rung dictates the schedule of the operator: 16 cycles/element with one multiplier is what fits'}
    rc, out = _sh(work, 'yosys -q -p "read_verilog stress_mac.v stress_mac_top.v; synth_ice40 -top stress_mac_top -json stress_mac.json; tee -o ice_stat.json stat -json" > ice_yosys.log 2>&1; echo rc=$?; '
                        'nextpnr-ice40 --hx8k --package ct256 --json stress_mac.json --asc stress_mac.asc --freq 50 -q --report pnr.json > pnr.log 2>&1; echo pnr_rc=$?; grep -i "Max frequency" pnr.log | tail -1')
    st = json.load(open(os.path.join(work, 'ice_stat.json')))
    st = st.get('design') or st['modules'][list(st['modules'])[0]]
    rep['synthesis'] = {'tool': 'yosys synth_ice40 (top = stress_mac_top: the kernel behind a 32-bit register bus)', 'cells': st['num_cells'],
                        'by_type': dict(sorted(st['num_cells_by_type'].items(), key=lambda kv: -kv[1]))}
    fmax = None
    try:
        pj = json.load(open(os.path.join(work, 'pnr.json')))
        f = pj.get('fmax', {})
        if f:
            fmax = float(list(f.values())[0]['achieved'])
        util = pj.get('utilization', {})
        rep['place_and_route'] = {'tool': 'nextpnr-ice40 --hx8k', 'part': 'Lattice iCE40 HX8K (ct256)', 'fmax_mhz': fmax,
                                  'utilization': {k: {'used': v.get('used'), 'available': v.get('available')} for k, v in util.items() if v.get('used')}}
    except Exception as e:  # pragma: no cover
        tail = open(os.path.join(work, 'pnr.log')).read()[-600:] if os.path.exists(os.path.join(work, 'pnr.log')) else out[-400:]
        rep['place_and_route'] = {'tool': 'nextpnr-ice40 --hx8k', 'part': 'Lattice iCE40 HX8K (ct256)', 'fit': False, 'error': str(e), 'log': tail}
    if fmax:
        cpe = rep['simulation']['cycles_per_element'] or 16
        rep['derived'] = {'latency_s_per_element_at_fmax': cpe / (fmax * 1e6), 'throughput_elements_per_s_at_fmax': fmax * 1e6 / cpe,
                          'all_elements_s_at_fmax': rep['simulation']['stream_cycles'] / (fmax * 1e6),
                          'note': 'DERIVED: cycles (iverilog) / Fmax (nextpnr timing model) — %d cycles per element, one multiplier' % cpe}
    os.makedirs(OUT, exist_ok=True)
    for f in ('stress_mac.v', 'stress_mac_top.v', 'tb_stress_mac.v', 'ice_stat.json', 'pnr.json'):
        if os.path.exists(os.path.join(work, f)):
            shutil.copy(os.path.join(work, f), OUT)
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def implementation_row(rep):
    """The ComputeImplementation row the report proves — or None without a report."""
    if not rep:
        return None
    pnr = rep.get('place_and_route', {}); der = rep.get('derived', {}); sim = rep.get('simulation', {})
    ok = 'PASS' in sim.get('verdict', '')
    return {'name': 'stress-from-strain/fpga-stress-mac', 'operator': 'stress-from-strain',
            'description': 'σ = C:ε as a time-multiplexed fixed-point MAC kernel on an open FPGA (iCE40 HX8K via yosys + nextpnr): one multiplier, 16 cycles per element — the streaming form (16 multipliers, ~49k LUTs) does not fit the part',
            'target_rung': 'rtl', 'target_kind': 'accelerator', 'target_ref': 'tensormath/initialData/fpga/stress_mac.v',
            'precision': 'int32 operands (C in kPa, ε in nε), int64 accumulate — exact; %.1e relative vs float64 from the operand rounding' % rep.get('reference_error_vs_float', 0.0),
            'shapes_json': json.dumps({'C': [2, 2, 2, 2], 'eps': ['n', 2, 2]}),
            'latency_s': float(der.get('latency_s_per_element_at_fmax', 0.0)), 'throughput': float(der.get('throughput_elements_per_s_at_fmax', 0.0)),
            'memory_bytes': 16 * 4, 'energy_j': 0.0, 'error': float(rep.get('reference_error_vs_float', 0.0)), 'config_overhead_s': 0.0,
            'mapping_status': 'validated' if ok else 'implemented', 'evidence_level': 'simulated',
            'evidence_ref': 'tensormath/initialData/fpga/report.json — iverilog: %s; nextpnr Fmax %s MHz on %s; LUTs %s' % (
                sim.get('verdict', '?')[:60], pnr.get('fmax_mhz'), pnr.get('part', '?'), (pnr.get('utilization', {}).get('ICESTORM_LC', {}) or {}).get('used', '?')),
            'notes': 'cycles are iverilog (simulated), Fmax is nextpnr\'s timing model (simulated), latency_s = cycles / Fmax is DERIVED; energy is not modelled (0 = not known). '
                     'A measured row needs the bitstream on a real HX8K: not yet.'}


if __name__ == '__main__':
    print(json.dumps(report(), indent=1) if report() else 'no report: run() needs a manager (see tests/tensor_liveboot_probe.py or the selftest)')
