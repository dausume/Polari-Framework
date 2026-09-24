// rv32_add — the ADD datapath of a RISC-V core, as PicoRV32 writes it (picorv32.v:1231:
//   alu_add_sub <= instr_sub ? reg_op1 - reg_op2 : reg_op1 + reg_op2;) isolated: two 32-bit
// operands in, one out. Verilog-2001, synthesizable; the teaching path's RTL rung for `add`.
module rv32_add (
    input  wire [31:0] reg_op1,
    input  wire [31:0] reg_op2,
    output wire [31:0] alu_out
);
    assign alu_out = reg_op1 + reg_op2;
endmodule
