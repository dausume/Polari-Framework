// stress_mac — sigma_ij = C_ijkl eps_kl as a TIME-MULTIPLEXED kernel (tensormath tt-3 / plan §18).
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
