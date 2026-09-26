module rv32_add (alu_out,
    reg_op1,
    reg_op2);
 output [31:0] alu_out;
 input [31:0] reg_op1;
 input [31:0] reg_op2;

 wire _000_;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _004_;
 wire _005_;
 wire _006_;
 wire _007_;
 wire _008_;
 wire _009_;
 wire _010_;
 wire _011_;
 wire _012_;
 wire _013_;
 wire _014_;
 wire _015_;
 wire _016_;
 wire _017_;
 wire _018_;
 wire _019_;
 wire _020_;
 wire _021_;
 wire _022_;
 wire _023_;
 wire _024_;
 wire _025_;
 wire _026_;
 wire _027_;
 wire _028_;
 wire _029_;
 wire _030_;
 wire _031_;
 wire _032_;
 wire _033_;
 wire _034_;
 wire _035_;
 wire _036_;
 wire _037_;
 wire _038_;
 wire _039_;
 wire _040_;
 wire _041_;
 wire _042_;
 wire _043_;
 wire _044_;
 wire _045_;
 wire _046_;
 wire _047_;
 wire _048_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire _059_;
 wire _060_;
 wire _061_;
 wire _062_;
 wire _063_;
 wire net1;
 wire net18;
 wire net19;
 wire net20;
 wire net32;
 wire net21;
 wire net22;
 wire net23;
 wire net24;
 wire net25;
 wire net26;
 wire net27;
 wire net28;
 wire net29;
 wire net30;
 wire net31;
 wire net17;

 sky130_fd_sc_hd__xnor2_1 _064_ (.A(reg_op1[10]),
    .B(reg_op2[10]),
    .Y(_061_));
 sky130_fd_sc_hd__xnor2_1 _065_ (.A(reg_op1[6]),
    .B(reg_op2[6]),
    .Y(_062_));
 sky130_fd_sc_hd__xnor2_1 _066_ (.A(reg_op1[4]),
    .B(reg_op2[4]),
    .Y(_063_));
 sky130_fd_sc_hd__xnor2_1 _067_ (.A(reg_op1[2]),
    .B(reg_op2[2]),
    .Y(_000_));
 sky130_fd_sc_hd__nand2_1 _068_ (.A(reg_op1[1]),
    .B(reg_op2[1]),
    .Y(_001_));
 sky130_fd_sc_hd__nand2_1 _069_ (.A(reg_op1[0]),
    .B(reg_op2[0]),
    .Y(_002_));
 sky130_fd_sc_hd__nor2_2 _070_ (.A(reg_op1[1]),
    .B(reg_op2[1]),
    .Y(_003_));
 sky130_fd_sc_hd__lpflow_isobufsrc_1 _071_ (.A(_001_),
    .SLEEP(_003_),
    .X(_004_));
 sky130_fd_sc_hd__o21ai_1 _072_ (.A1(_002_),
    .A2(_003_),
    .B1(_001_),
    .Y(_005_));
 sky130_fd_sc_hd__maj3_2 _073_ (.A(reg_op1[2]),
    .B(reg_op2[2]),
    .C(_005_),
    .X(_006_));
 sky130_fd_sc_hd__xnor2_1 _074_ (.A(reg_op1[3]),
    .B(reg_op2[3]),
    .Y(_007_));
 sky130_fd_sc_hd__maj3_2 _075_ (.A(reg_op1[3]),
    .B(reg_op2[3]),
    .C(_006_),
    .X(_008_));
 sky130_fd_sc_hd__maj3_2 _076_ (.A(reg_op1[4]),
    .B(reg_op2[4]),
    .C(_008_),
    .X(_009_));
 sky130_fd_sc_hd__xnor2_1 _077_ (.A(reg_op1[5]),
    .B(reg_op2[5]),
    .Y(_010_));
 sky130_fd_sc_hd__maj3_2 _078_ (.A(reg_op1[5]),
    .B(reg_op2[5]),
    .C(_009_),
    .X(_011_));
 sky130_fd_sc_hd__maj3_2 _079_ (.A(reg_op1[6]),
    .B(reg_op2[6]),
    .C(_011_),
    .X(_012_));
 sky130_fd_sc_hd__maj3_2 _080_ (.A(reg_op1[7]),
    .B(reg_op2[7]),
    .C(_012_),
    .X(_013_));
 sky130_fd_sc_hd__xnor2_1 _081_ (.A(reg_op1[8]),
    .B(reg_op2[8]),
    .Y(_014_));
 sky130_fd_sc_hd__maj3_2 _082_ (.A(reg_op1[8]),
    .B(reg_op2[8]),
    .C(_013_),
    .X(_015_));
 sky130_fd_sc_hd__maj3_2 _083_ (.A(reg_op1[9]),
    .B(reg_op2[9]),
    .C(_015_),
    .X(_016_));
 sky130_fd_sc_hd__maj3_2 _084_ (.A(reg_op1[10]),
    .B(reg_op2[10]),
    .C(_016_),
    .X(_017_));
 sky130_fd_sc_hd__maj3_2 _085_ (.A(reg_op1[11]),
    .B(reg_op2[11]),
    .C(_017_),
    .X(_018_));
 sky130_fd_sc_hd__xnor2_1 _086_ (.A(reg_op1[12]),
    .B(reg_op2[12]),
    .Y(_019_));
 sky130_fd_sc_hd__maj3_2 _087_ (.A(reg_op1[12]),
    .B(reg_op2[12]),
    .C(_018_),
    .X(_020_));
 sky130_fd_sc_hd__xnor2_1 _088_ (.A(reg_op1[13]),
    .B(reg_op2[13]),
    .Y(_021_));
 sky130_fd_sc_hd__xnor2_1 _089_ (.A(net26),
    .B(_021_),
    .Y(alu_out[13]));
 sky130_fd_sc_hd__maj3_2 _090_ (.A(reg_op1[13]),
    .B(reg_op2[13]),
    .C(_020_),
    .X(_022_));
 sky130_fd_sc_hd__xnor2_1 _091_ (.A(reg_op1[14]),
    .B(reg_op2[14]),
    .Y(_023_));
 sky130_fd_sc_hd__xnor2_1 _092_ (.A(_022_),
    .B(_023_),
    .Y(alu_out[14]));
 sky130_fd_sc_hd__maj3_2 _093_ (.A(reg_op1[14]),
    .B(reg_op2[14]),
    .C(_022_),
    .X(_024_));
 sky130_fd_sc_hd__xnor2_1 _094_ (.A(reg_op1[15]),
    .B(reg_op2[15]),
    .Y(_025_));
 sky130_fd_sc_hd__xnor2_1 _095_ (.A(net25),
    .B(_025_),
    .Y(alu_out[15]));
 sky130_fd_sc_hd__maj3_2 _096_ (.A(reg_op1[15]),
    .B(reg_op2[15]),
    .C(_024_),
    .X(_026_));
 sky130_fd_sc_hd__xnor2_1 _097_ (.A(reg_op1[16]),
    .B(reg_op2[16]),
    .Y(_027_));
 sky130_fd_sc_hd__xnor2_1 _098_ (.A(net24),
    .B(_027_),
    .Y(alu_out[16]));
 sky130_fd_sc_hd__maj3_2 _099_ (.A(reg_op1[16]),
    .B(reg_op2[16]),
    .C(_026_),
    .X(_028_));
 sky130_fd_sc_hd__xnor2_1 _100_ (.A(reg_op1[17]),
    .B(reg_op2[17]),
    .Y(_029_));
 sky130_fd_sc_hd__xnor2_1 _101_ (.A(net23),
    .B(_029_),
    .Y(alu_out[17]));
 sky130_fd_sc_hd__maj3_2 _102_ (.A(reg_op1[17]),
    .B(reg_op2[17]),
    .C(_028_),
    .X(_030_));
 sky130_fd_sc_hd__xnor2_1 _103_ (.A(reg_op1[18]),
    .B(reg_op2[18]),
    .Y(_031_));
 sky130_fd_sc_hd__xnor2_1 _104_ (.A(net22),
    .B(_031_),
    .Y(alu_out[18]));
 sky130_fd_sc_hd__maj3_2 _105_ (.A(reg_op1[18]),
    .B(reg_op2[18]),
    .C(_030_),
    .X(_032_));
 sky130_fd_sc_hd__xnor2_1 _106_ (.A(reg_op1[19]),
    .B(reg_op2[19]),
    .Y(_033_));
 sky130_fd_sc_hd__xnor2_1 _107_ (.A(net21),
    .B(_033_),
    .Y(alu_out[19]));
 sky130_fd_sc_hd__maj3_2 _108_ (.A(reg_op1[19]),
    .B(reg_op2[19]),
    .C(_032_),
    .X(_034_));
 sky130_fd_sc_hd__xnor2_1 _109_ (.A(reg_op1[20]),
    .B(reg_op2[20]),
    .Y(_035_));
 sky130_fd_sc_hd__xnor2_1 _110_ (.A(_034_),
    .B(_035_),
    .Y(alu_out[20]));
 sky130_fd_sc_hd__maj3_2 _111_ (.A(reg_op1[20]),
    .B(reg_op2[20]),
    .C(_034_),
    .X(_036_));
 sky130_fd_sc_hd__xnor2_1 _112_ (.A(reg_op1[21]),
    .B(reg_op2[21]),
    .Y(_037_));
 sky130_fd_sc_hd__xnor2_1 _113_ (.A(_036_),
    .B(_037_),
    .Y(alu_out[21]));
 sky130_fd_sc_hd__maj3_2 _114_ (.A(reg_op1[21]),
    .B(reg_op2[21]),
    .C(_036_),
    .X(_038_));
 sky130_fd_sc_hd__xnor2_1 _115_ (.A(reg_op1[22]),
    .B(reg_op2[22]),
    .Y(_039_));
 sky130_fd_sc_hd__xnor2_1 _116_ (.A(net20),
    .B(_039_),
    .Y(alu_out[22]));
 sky130_fd_sc_hd__maj3_2 _117_ (.A(reg_op1[22]),
    .B(reg_op2[22]),
    .C(_038_),
    .X(_040_));
 sky130_fd_sc_hd__xnor2_1 _118_ (.A(reg_op1[23]),
    .B(reg_op2[23]),
    .Y(_041_));
 sky130_fd_sc_hd__xnor2_1 _119_ (.A(net19),
    .B(_041_),
    .Y(alu_out[23]));
 sky130_fd_sc_hd__maj3_2 _120_ (.A(reg_op1[23]),
    .B(reg_op2[23]),
    .C(_040_),
    .X(_042_));
 sky130_fd_sc_hd__xnor2_1 _121_ (.A(reg_op1[24]),
    .B(reg_op2[24]),
    .Y(_043_));
 sky130_fd_sc_hd__xnor2_1 _122_ (.A(_042_),
    .B(_043_),
    .Y(alu_out[24]));
 sky130_fd_sc_hd__maj3_2 _123_ (.A(reg_op1[24]),
    .B(reg_op2[24]),
    .C(_042_),
    .X(_044_));
 sky130_fd_sc_hd__xnor2_1 _124_ (.A(reg_op1[25]),
    .B(reg_op2[25]),
    .Y(_045_));
 sky130_fd_sc_hd__xnor2_1 _125_ (.A(_044_),
    .B(_045_),
    .Y(alu_out[25]));
 sky130_fd_sc_hd__maj3_2 _126_ (.A(reg_op1[25]),
    .B(reg_op2[25]),
    .C(_044_),
    .X(_046_));
 sky130_fd_sc_hd__xnor2_1 _127_ (.A(reg_op1[26]),
    .B(reg_op2[26]),
    .Y(_047_));
 sky130_fd_sc_hd__xnor2_1 _128_ (.A(_046_),
    .B(_047_),
    .Y(alu_out[26]));
 sky130_fd_sc_hd__maj3_2 _129_ (.A(reg_op1[26]),
    .B(reg_op2[26]),
    .C(_046_),
    .X(_048_));
 sky130_fd_sc_hd__xnor2_1 _130_ (.A(reg_op1[27]),
    .B(reg_op2[27]),
    .Y(_049_));
 sky130_fd_sc_hd__xnor2_1 _131_ (.A(net18),
    .B(_049_),
    .Y(alu_out[27]));
 sky130_fd_sc_hd__maj3_2 _132_ (.A(reg_op1[27]),
    .B(reg_op2[27]),
    .C(_048_),
    .X(_050_));
 sky130_fd_sc_hd__xnor2_1 _133_ (.A(reg_op1[28]),
    .B(reg_op2[28]),
    .Y(_051_));
 sky130_fd_sc_hd__xnor2_1 _134_ (.A(_050_),
    .B(_051_),
    .Y(alu_out[28]));
 sky130_fd_sc_hd__maj3_2 _135_ (.A(reg_op1[28]),
    .B(reg_op2[28]),
    .C(_050_),
    .X(_052_));
 sky130_fd_sc_hd__xnor2_1 _136_ (.A(reg_op1[29]),
    .B(reg_op2[29]),
    .Y(_053_));
 sky130_fd_sc_hd__xnor2_1 _137_ (.A(_052_),
    .B(_053_),
    .Y(alu_out[29]));
 sky130_fd_sc_hd__maj3_2 _138_ (.A(reg_op1[29]),
    .B(reg_op2[29]),
    .C(_052_),
    .X(_054_));
 sky130_fd_sc_hd__xnor2_1 _139_ (.A(reg_op1[30]),
    .B(reg_op2[30]),
    .Y(_055_));
 sky130_fd_sc_hd__xnor2_1 _140_ (.A(net17),
    .B(_055_),
    .Y(net1));
 sky130_fd_sc_hd__maj3_2 _141_ (.A(reg_op1[30]),
    .B(reg_op2[30]),
    .C(_054_),
    .X(_056_));
 sky130_fd_sc_hd__xnor2_1 _142_ (.A(reg_op1[31]),
    .B(reg_op2[31]),
    .Y(_057_));
 sky130_fd_sc_hd__xnor2_2 _143_ (.A(_056_),
    .B(_057_),
    .Y(alu_out[31]));
 sky130_fd_sc_hd__xor2_1 _144_ (.A(reg_op1[0]),
    .B(reg_op2[0]),
    .X(alu_out[0]));
 sky130_fd_sc_hd__xnor2_1 _145_ (.A(_002_),
    .B(_004_),
    .Y(alu_out[1]));
 sky130_fd_sc_hd__xnor2_1 _146_ (.A(_000_),
    .B(_005_),
    .Y(alu_out[2]));
 sky130_fd_sc_hd__xnor2_1 _147_ (.A(_006_),
    .B(_007_),
    .Y(alu_out[3]));
 sky130_fd_sc_hd__xnor2_1 _148_ (.A(_063_),
    .B(net32),
    .Y(alu_out[4]));
 sky130_fd_sc_hd__xnor2_1 _149_ (.A(net31),
    .B(_010_),
    .Y(alu_out[5]));
 sky130_fd_sc_hd__xnor2_1 _150_ (.A(_062_),
    .B(net30),
    .Y(alu_out[6]));
 sky130_fd_sc_hd__xnor2_1 _151_ (.A(reg_op1[7]),
    .B(reg_op2[7]),
    .Y(_058_));
 sky130_fd_sc_hd__xnor2_1 _152_ (.A(_012_),
    .B(_058_),
    .Y(alu_out[7]));
 sky130_fd_sc_hd__xnor2_1 _153_ (.A(_013_),
    .B(_014_),
    .Y(alu_out[8]));
 sky130_fd_sc_hd__xnor2_1 _154_ (.A(reg_op1[9]),
    .B(reg_op2[9]),
    .Y(_059_));
 sky130_fd_sc_hd__xnor2_1 _155_ (.A(_015_),
    .B(_059_),
    .Y(alu_out[9]));
 sky130_fd_sc_hd__xnor2_1 _156_ (.A(_061_),
    .B(net29),
    .Y(alu_out[10]));
 sky130_fd_sc_hd__xnor2_1 _157_ (.A(reg_op1[11]),
    .B(reg_op2[11]),
    .Y(_060_));
 sky130_fd_sc_hd__xnor2_1 _158_ (.A(net28),
    .B(_060_),
    .Y(alu_out[11]));
 sky130_fd_sc_hd__xnor2_1 _159_ (.A(net27),
    .B(_019_),
    .Y(alu_out[12]));
 sky130_fd_sc_hd__buf_4 place1 (.A(net1),
    .X(alu_out[30]));
 sky130_fd_sc_hd__buf_4 place17 (.A(_054_),
    .X(net17));
 sky130_fd_sc_hd__buf_4 place18 (.A(_048_),
    .X(net18));
 sky130_fd_sc_hd__buf_4 place19 (.A(_040_),
    .X(net19));
 sky130_fd_sc_hd__buf_4 place20 (.A(_038_),
    .X(net20));
 sky130_fd_sc_hd__buf_4 place21 (.A(_032_),
    .X(net21));
 sky130_fd_sc_hd__buf_4 place22 (.A(_030_),
    .X(net22));
 sky130_fd_sc_hd__buf_4 place23 (.A(_028_),
    .X(net23));
 sky130_fd_sc_hd__buf_4 place24 (.A(_026_),
    .X(net24));
 sky130_fd_sc_hd__buf_4 place25 (.A(_024_),
    .X(net25));
 sky130_fd_sc_hd__buf_4 place26 (.A(_020_),
    .X(net26));
 sky130_fd_sc_hd__buf_4 place27 (.A(_018_),
    .X(net27));
 sky130_fd_sc_hd__buf_4 place28 (.A(_017_),
    .X(net28));
 sky130_fd_sc_hd__buf_4 place29 (.A(_016_),
    .X(net29));
 sky130_fd_sc_hd__buf_4 place30 (.A(_011_),
    .X(net30));
 sky130_fd_sc_hd__buf_4 place31 (.A(_009_),
    .X(net31));
 sky130_fd_sc_hd__buf_4 place32 (.A(_008_),
    .X(net32));
endmodule
