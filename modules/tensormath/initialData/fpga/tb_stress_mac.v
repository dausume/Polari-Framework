`timescale 1ns/1ps
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
