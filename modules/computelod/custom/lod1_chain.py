"""
@module computelod.custom.lod1_chain

THE TEACHING PATH, RUN FOR REAL (lod-1, plan §C Phase 4, §F5):

    C  `c = a + b`  →  GCC (rv32i)  →  `add a0,a0,a1` = 0x00b50533  →  PicoRV32 decodes it (picorv32.v:1068)
    and adds (alu_add_sub <= reg_op1 + reg_op2, :1231)  →  the adder as its own RTL module (rv32_add.v)
    →  Yosys: the core = N gates, the adder = M gates  →  iverilog: the RTL and its gate netlist give the same sums.

Every row on the ladder comes from this script having RUN — never typed in. `run` executes the tools (on the
PATH, else in the pinned image modules/computelod/tools/Dockerfile) into a work dir and writes lod1/report.json
+ the small artifacts (source, assembly, objdump, the adder RTL, the stat histograms; the 570 kB core netlist is
NOT committed — its histogram is). `rows(report)` turns that report into the seed rows, so a boot without the
tools still shows the path with its evidence named (tool versions, files, the pin of PicoRV32).

Evidence levels, as ruled (§F2): a tool's own OUTPUT (gcc's assembly, yosys' cell count) is `measured` — it is
the artifact, observed; a SIMULATION result (iverilog) is `simulated`; a timing number needs a Liberty and is
an honest gap here (evidence_level none, notes say lod-2).

    python3 -m computelod.custom.lod1_chain run [--work DIR]     run the chain, write lod1/report.json
    python3 -m computelod.custom.lod1_chain show                 print the committed report
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
RTL = os.path.join(MOD, 'rtl', 'picorv32')
OUT = os.path.join(MOD, 'lod1')
IMAGE = os.environ.get('POLARI_COMPUTELOD_TOOLS_IMAGE', 'polari-computelod-tools:noble')

C_SOURCE = 'int add(int a, int b) { int c = a + b; return c; }\n'
RV32_ADD = '''// rv32_add — the ADD datapath of a RISC-V core, as PicoRV32 writes it (picorv32.v:1231:
//   alu_add_sub <= instr_sub ? reg_op1 - reg_op2 : reg_op1 + reg_op2;) isolated: two 32-bit
// operands in, one out. Verilog-2001, synthesizable; the teaching path's RTL rung for `add`.
module rv32_add (
    input  wire [31:0] reg_op1,
    input  wire [31:0] reg_op2,
    output wire [31:0] alu_out
);
    assign alu_out = reg_op1 + reg_op2;
endmodule
'''
TB = '''`timescale 1ns/1ps
module tb;
    reg [31:0] a, b; wire [31:0] c; integer fails = 0;
    rv32_add dut(.reg_op1(a), .reg_op2(b), .alu_out(c));
    task chk(input [31:0] x, input [31:0] y); begin
        a = x; b = y; #1; if (c !== x + y) begin $display("FAIL %h + %h = %h", x, y, c); fails = fails + 1; end
    end endtask
    initial begin
        chk(32'd3, 32'd4); chk(32'hFFFFFFFF, 32'd1); chk(32'h7FFFFFFF, 32'd1); chk(32'hDEADBEEF, 32'h01234567);
        if (fails == 0) $display("PASS rv32_add 4/4"); $finish;
    end
endmodule
'''
TOOLS = ('riscv64-unknown-elf-gcc', 'riscv64-unknown-elf-objdump', 'yosys', 'iverilog', 'vvp')


def tools_available():
    """'path' when every tool is on the PATH, 'docker' when the pinned image can run, else ''."""
    if all(shutil.which(t) for t in TOOLS):
        return 'path'
    try:
        r = subprocess.run(['docker', 'image', 'inspect', IMAGE], capture_output=True, timeout=20)
        return 'docker' if r.returncode == 0 else ''
    except Exception:
        return ''


def sh(work, cmd, how):
    if how == 'docker':
        full = ['docker', 'run', '--rm', '-v', '%s:/w' % work, '-w', '/w', IMAGE, 'sh', '-c', cmd]
    else:
        full = ['sh', '-c', cmd]
    r = subprocess.run(full, capture_output=True, text=True, timeout=600, cwd=work)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def decode_rtype(word):
    """The R-type fields of a 32-bit RISC-V instruction word (the ISA rung's own arithmetic)."""
    opcode = word & 0x7f; rd = (word >> 7) & 0x1f; f3 = (word >> 12) & 7; rs1 = (word >> 15) & 0x1f; rs2 = (word >> 20) & 0x1f; f7 = word >> 25
    return {'opcode': '0b%07d' % int(bin(opcode)[2:]), 'rd': rd, 'funct3': f3, 'rs1': rs1, 'rs2': rs2, 'funct7': f7,
            'is_add': opcode == 0b0110011 and f3 == 0 and f7 == 0}


def run(work=None):
    how = tools_available()
    if not how:
        raise SystemExit('no toolchain: put riscv64-unknown-elf-gcc/yosys/iverilog on the PATH, or build the image: '
                         'docker build -t %s modules/computelod/tools' % IMAGE)
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-lod1')
    os.makedirs(work, exist_ok=True)
    open(os.path.join(work, 'add.c'), 'w').write(C_SOURCE)
    open(os.path.join(work, 'rv32_add.v'), 'w').write(RV32_ADD)
    open(os.path.join(work, 'tb_rv32_add.v'), 'w').write(TB)
    shutil.copy(os.path.join(RTL, 'picorv32.v'), work)
    rep = {'how': how, 'picorv32_pin': dict(l.split('=', 1) for l in open(os.path.join(RTL, 'PIN')).read().split('\n') if '=' in l)}
    rc, out = sh(work, 'riscv64-unknown-elf-gcc --version | head -1; yosys -V; iverilog -V 2>&1 | head -1', how)
    rep['tool_versions'] = [l.strip() for l in out.strip().split('\n') if l.strip()][:3]
    rc, out = sh(work, 'riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -O1 -S -o add.s add.c && '
                       'riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -O1 -c -o add.o add.c && '
                       'riscv64-unknown-elf-objdump -d add.o > add.objdump && cat add.objdump', how)
    if rc != 0:
        raise SystemExit('gcc failed: ' + out[-800:])
    asm = [l.strip() for l in open(os.path.join(work, 'add.s')).read().split('\n') if l.strip() and not l.strip().startswith('.')]
    m = re.search(r'^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s+add\s+(\S+)', out, re.M)
    if not m:
        raise SystemExit('no `add` in the objdump: ' + out[-600:])
    word = int(m.group(1), 16)
    rep['compile'] = {'flags': '-march=rv32i -mabi=ilp32 -O1', 'assembly': asm, 'add_instruction': 'add ' + m.group(2), 'encoding': '0x%08x' % word,
                      'decoded': decode_rtype(word), 'objdump': out.strip().split('\n')[-4:]}
    rc, out = sh(work, 'yosys -q -p "read_verilog picorv32.v; synth -top picorv32; tee -o core_stat.json stat -json" > core_yosys.log 2>&1; echo rc=$?', how)
    core = json.load(open(os.path.join(work, 'core_stat.json')))['modules']
    core = core[list(core)[0]]
    rep['core_synth'] = {'cells': core['num_cells'], 'by_type': dict(sorted(core['num_cells_by_type'].items(), key=lambda kv: -kv[1])),
                         'decode_line': 'picorv32.v:1068  instr_add <= is_alu_reg_reg && funct3 == 000 && funct7 == 0000000',
                         'add_line': 'picorv32.v:1231  alu_add_sub <= instr_sub ? reg_op1 - reg_op2 : reg_op1 + reg_op2'}
    rc, out = sh(work, 'yosys -q -p "read_verilog rv32_add.v; synth -top rv32_add; tee -o add_stat.json stat -json; write_verilog -noattr rv32_add_netlist.v" > add_yosys.log 2>&1; echo rc=$?', how)
    add = json.load(open(os.path.join(work, 'add_stat.json')))['modules']
    add = add[list(add)[0]]
    rep['adder_synth'] = {'cells': add['num_cells'], 'by_type': dict(sorted(add['num_cells_by_type'].items(), key=lambda kv: -kv[1]))}
    rc, out = sh(work, 'iverilog -o tb_add tb_rv32_add.v rv32_add.v && vvp -n tb_add | grep -E "PASS|FAIL"; '
                       'iverilog -o tb_net tb_rv32_add.v rv32_add_netlist.v /usr/share/yosys/simlib.v /usr/share/yosys/simcells.v 2>/dev/null && vvp -n tb_net | grep -E "PASS|FAIL"', how)
    lines = [l for l in out.split('\n') if 'PASS' in l or 'FAIL' in l]
    rep['simulation'] = {'rtl': lines[0] if lines else 'no verdict', 'netlist': lines[1] if len(lines) > 1 else 'no verdict',
                         'vectors': ['3+4', '0xFFFFFFFF+1 (wrap)', '0x7FFFFFFF+1 (sign)', '0xDEADBEEF+0x01234567']}
    os.makedirs(OUT, exist_ok=True)
    for f in ('add.c', 'add.s', 'add.objdump', 'rv32_add.v', 'tb_rv32_add.v', 'add_stat.json', 'core_stat.json'):
        shutil.copy(os.path.join(work, f), OUT)
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep):
    """The ladder rows the report proves. Returns (compiler_artifacts, compute_mappings, characterizations)."""
    if not rep:
        return [], [], []
    ev_c = 'lod1/report.json compile — %s (%s)' % (rep['tool_versions'][0] if rep.get('tool_versions') else 'gcc', rep['compile']['flags'])
    ev_y = 'lod1/report.json core_synth/adder_synth — %s' % (rep['tool_versions'][1] if len(rep.get('tool_versions', [])) > 1 else 'yosys')
    ev_s = 'lod1/report.json simulation — iverilog: %s | %s' % (rep['simulation']['rtl'], rep['simulation']['netlist'])
    pin = rep.get('picorv32_pin', {})
    core_ref = 'picorv32 @ %s (ISC)' % pin.get('commit', '?')[:12]
    enc = rep['compile']['encoding']; ins = rep['compile']['add_instruction']
    arts = [
        {'name': 'lod1/add.c', 'description': 'the C source of the teaching path', 'kind': 'source', 'compiler': '', 'source_ref': '', 'content_ref': 'modules/computelod/lod1/add.c', 'notes': C_SOURCE.strip()},
        {'name': 'lod1/add.s', 'description': 'GCC\'s RV32I assembly', 'kind': 'assembly', 'compiler': rep['tool_versions'][0] if rep.get('tool_versions') else 'gcc', 'source_ref': 'lod1/add.c',
         'content_ref': 'modules/computelod/lod1/add.s', 'notes': ' ; '.join(rep['compile']['assembly'])},
        {'name': 'lod1/add.o', 'description': 'the object file; objdump shows the encoded instructions', 'kind': 'object', 'compiler': rep['tool_versions'][0] if rep.get('tool_versions') else 'gcc',
         'source_ref': 'lod1/add.c', 'content_ref': 'modules/computelod/lod1/add.objdump', 'notes': '%s = %s' % (ins, enc)},
    ]
    d = rep['compile']['decoded']
    uarch_ref = core_ref + ': decode → register file → ALU (alu_add_sub) → writeback'   # ONE string, so the chain links
    M = lambda **k: dict({'description': '', 'validity_json': '{}', 'loss_note': '', 'uncertainty_json': '{}', 'notes': ''}, **k)
    maps = [
        M(name='lod1: c → gcc', kind='one-to-one', source_rung='c-source', source_ref='lod1/add.c: c = a + b', target_rung='compiler', target_ref='lod1/add.s',
          mapping_status='validated', evidence_level='measured', evidence_ref=ev_c, loss_note='the variable names and the statement boundary are gone after this step',
          notes='gcc %s — the compiler rung\'s row is what the compiler PRODUCED (the assembly artifact)' % rep['compile']['flags']),
        M(name='lod1: gcc → isa add', kind='one-to-one', source_rung='compiler', source_ref='lod1/add.s', target_rung='isa', target_ref='%s = %s' % (ins, enc),
          mapping_status='validated', evidence_level='measured', evidence_ref=ev_c,
          notes='R-type: opcode %s rd=x%d rs1=x%d rs2=x%d funct3=%d funct7=%d' % (d['opcode'], d['rd'], d['rs1'], d['rs2'], d['funct3'], d['funct7'])),
        M(name='lod1: isa add → picorv32 decode+alu', kind='one-to-many', source_rung='isa', source_ref='%s = %s' % (ins, enc), target_rung='microarchitecture', target_ref=uarch_ref,
          mapping_status='implemented', evidence_level='analytical', evidence_ref=rep['core_synth']['decode_line'] + ' ; ' + rep['core_synth']['add_line'],
          notes='one instruction becomes several micro-steps (fetch, decode, operand read, add, writeback) — a one-to-many mapping; the lines are cited, the cycle count is not measured here (Verilator: lod-2)'),
        M(name='lod1: picorv32 alu → rtl rv32_add', kind='approximate', source_rung='microarchitecture', source_ref=uarch_ref, target_rung='rtl', target_ref='lod1/rv32_add.v',
          mapping_status='implemented', evidence_level='analytical', evidence_ref='picorv32.v:1231 isolated verbatim (the subtract mux dropped)',
          loss_note='rv32_add keeps the + and drops the instr_sub mux — the adder, not the whole ALU'),
        M(name='lod1: rtl rv32_add → netlist', kind='one-to-one', source_rung='rtl', source_ref='lod1/rv32_add.v', target_rung='logic-netlist', target_ref='yosys synth rv32_add: %d cells' % rep['adder_synth']['cells'],
          mapping_status='validated', evidence_level='measured', evidence_ref=ev_y, notes=json.dumps(rep['adder_synth']['by_type'])),
        M(name='lod1: rtl picorv32 → netlist', kind='one-to-one', source_rung='rtl', source_ref=core_ref + ' picorv32.v', target_rung='logic-netlist', target_ref='yosys synth picorv32: %d cells' % rep['core_synth']['cells'],
          mapping_status='validated', evidence_level='measured', evidence_ref=ev_y, notes=json.dumps(dict(list(rep['core_synth']['by_type'].items())[:8]))),
        M(name='lod1: netlist → standard cells', kind='unresolved', source_rung='logic-netlist', source_ref='yosys synth rv32_add: %d cells' % rep['adder_synth']['cells'], target_rung='standard-cells', target_ref='',
          mapping_status='proposed', evidence_level='none', evidence_ref='', notes='technology mapping needs a Liberty (abc -liberty; SKY130 or the cntfet/sifet cells) — lod-2. Left UNRESOLVED on purpose.'),
    ]
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    chars = [
        C(name='lod1: rv32_add gate count', source_rung='logic-netlist', source_ref='yosys synth rv32_add', target_rung='rtl', target_ref='lod1/rv32_add.v', characteristic='gate_count', method='yosys stat',
          conditions_json=json.dumps({'synth': 'yosys synth (generic gate library, no Liberty)', 'tool': rep['tool_versions'][1] if len(rep.get('tool_versions', [])) > 1 else 'yosys'}),
          result=float(rep['adder_synth']['cells']), units='cells', mapping_status='validated', evidence_level='measured', evidence_ref=ev_y),
        C(name='lod1: picorv32 gate count', source_rung='logic-netlist', source_ref='yosys synth picorv32', target_rung='microarchitecture', target_ref=core_ref, characteristic='gate_count', method='yosys stat',
          conditions_json=json.dumps({'synth': 'yosys synth (generic gate library)', 'params': 'defaults (ENABLE_MUL=0)'}), result=float(rep['core_synth']['cells']), units='cells',
          mapping_status='validated', evidence_level='measured', evidence_ref=ev_y),
        C(name='lod1: rv32_add correctness (rtl)', source_rung='rtl', source_ref='lod1/rv32_add.v', target_rung='isa', target_ref=ins, characteristic='correctness', method='iverilog',
          conditions_json=json.dumps({'vectors': rep['simulation']['vectors']}), result=1.0 if 'PASS' in rep['simulation']['rtl'] else 0.0, units='pass',
          mapping_status='validated', evidence_level='simulated', evidence_ref=ev_s),
        C(name='lod1: rv32_add correctness (netlist)', source_rung='logic-netlist', source_ref='yosys synth rv32_add', target_rung='isa', target_ref=ins, characteristic='correctness', method='iverilog + yosys simcells',
          conditions_json=json.dumps({'vectors': rep['simulation']['vectors']}), result=1.0 if 'PASS' in rep['simulation']['netlist'] else 0.0, units='pass',
          mapping_status='validated', evidence_level='simulated', evidence_ref=ev_s, notes='the gate netlist gives the same sums as the RTL — synthesis preserved the meaning'),
        C(name='lod1: rv32_add propagation delay', source_rung='logic-netlist', source_ref='yosys synth rv32_add', target_rung='rtl', target_ref='lod1/rv32_add.v', characteristic='propagation_delay', method='',
          conditions_json='{}', result=0.0, units='ns', mapping_status='proposed', evidence_level='none', evidence_ref='',
          notes='an HONEST GAP: a delay needs a Liberty and OpenSTA (voltage, temperature, load, corner) — lod-2. No number is invented here.'),
    ]
    return arts, maps, chars


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'show'
    if cmd == 'run':
        work = sys.argv[sys.argv.index('--work') + 1] if '--work' in sys.argv else None
        rep = run(work)
        print(json.dumps({k: rep[k] for k in ('how', 'tool_versions', 'compile', 'simulation')}, indent=1))
        print('core %d cells, adder %d cells → %s/report.json' % (rep['core_synth']['cells'], rep['adder_synth']['cells'], OUT))
    else:
        print(json.dumps(report(), indent=1) if report() else 'no report yet: python3 -m computelod.custom.lod1_chain run')
