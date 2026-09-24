// stress_mac_top — the kernel behind a NARROW REGISTER BUS, so it has a placeable pin count (the bare kernel
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
