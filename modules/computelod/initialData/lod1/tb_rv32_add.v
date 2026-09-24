`timescale 1ns/1ps
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
