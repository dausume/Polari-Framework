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
 wire net65;
 wire net66;
 wire net67;
 wire net68;
 wire net69;
 wire net70;
 wire net71;
 wire net72;
 wire net73;
 wire net74;
 wire net75;
 wire net76;
 wire net77;
 wire net78;
 wire net79;
 wire net80;
 wire net81;
 wire net82;
 wire net83;
 wire net84;
 wire net85;
 wire net86;
 wire net87;
 wire net88;
 wire net89;
 wire net90;
 wire net91;
 wire net92;
 wire net93;
 wire net94;
 wire net95;
 wire net96;
 wire net1;
 wire net2;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire net20;
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
 wire net32;
 wire net33;
 wire net34;
 wire net35;
 wire net36;
 wire net37;
 wire net38;
 wire net39;
 wire net40;
 wire net41;
 wire net42;
 wire net43;
 wire net44;
 wire net45;
 wire net46;
 wire net47;
 wire net48;
 wire net49;
 wire net50;
 wire net51;
 wire net52;
 wire net53;
 wire net54;
 wire net55;
 wire net56;
 wire net57;
 wire net58;
 wire net59;
 wire net60;
 wire net61;
 wire net62;
 wire net63;
 wire net64;
 wire net131;
 wire net163;
 wire net159;
 wire net132;
 wire net153;
 wire net133;
 wire net134;
 wire net135;
 wire net136;
 wire net137;
 wire net138;
 wire net139;
 wire net140;
 wire net141;
 wire net142;
 wire net143;
 wire net144;
 wire net145;
 wire net146;
 wire net147;
 wire net148;
 wire net149;
 wire net150;
 wire net151;
 wire net152;
 wire net154;
 wire net155;
 wire net156;
 wire net157;
 wire net158;
 wire net160;
 wire net161;
 wire net162;
 wire net130;
 wire net164;
 wire net165;
 wire net166;
 wire net167;
 wire net168;
 wire net169;
 wire net170;
 wire net171;
 wire net172;
 wire net173;
 wire net174;
 wire net175;
 wire net176;
 wire net177;
 wire net178;
 wire net179;

 sky130_fd_sc_hd__xnor2_1 _064_ (.A(net2),
    .B(net34),
    .Y(_061_));
 sky130_fd_sc_hd__xnor2_1 _065_ (.A(net29),
    .B(net61),
    .Y(_062_));
 sky130_fd_sc_hd__xnor2_1 _066_ (.A(net158),
    .B(net154),
    .Y(_063_));
 sky130_fd_sc_hd__xnor2_1 _067_ (.A(net160),
    .B(net156),
    .Y(_000_));
 sky130_fd_sc_hd__nand2_2 _068_ (.A(net12),
    .B(net44),
    .Y(_001_));
 sky130_fd_sc_hd__nand2_2 _069_ (.A(net1),
    .B(net33),
    .Y(_002_));
 sky130_fd_sc_hd__nor2_4 _070_ (.A(net12),
    .B(net44),
    .Y(_003_));
 sky130_fd_sc_hd__lpflow_isobufsrc_1 _071_ (.A(_001_),
    .SLEEP(net166),
    .X(_004_));
 sky130_fd_sc_hd__o21ai_2 _072_ (.A1(_003_),
    .A2(_002_),
    .B1(_001_),
    .Y(_005_));
 sky130_fd_sc_hd__maj3_2 _073_ (.A(net23),
    .B(_005_),
    .C(net55),
    .X(_006_));
 sky130_fd_sc_hd__xnor2_1 _074_ (.A(net159),
    .B(net155),
    .Y(_007_));
 sky130_fd_sc_hd__maj3_2 _075_ (.A(_006_),
    .B(net26),
    .C(net58),
    .X(_008_));
 sky130_fd_sc_hd__maj3_2 _076_ (.A(net27),
    .B(_008_),
    .C(net59),
    .X(_009_));
 sky130_fd_sc_hd__xnor2_1 _077_ (.A(net28),
    .B(net60),
    .Y(_010_));
 sky130_fd_sc_hd__maj3_2 _078_ (.A(_009_),
    .B(net28),
    .C(net60),
    .X(_011_));
 sky130_fd_sc_hd__maj3_2 _079_ (.A(_011_),
    .B(net29),
    .C(net61),
    .X(_012_));
 sky130_fd_sc_hd__maj3_2 _080_ (.A(net30),
    .B(_012_),
    .C(net62),
    .X(_013_));
 sky130_fd_sc_hd__xnor2_1 _081_ (.A(net31),
    .B(net63),
    .Y(_014_));
 sky130_fd_sc_hd__maj3_2 _082_ (.A(net63),
    .B(_013_),
    .C(net31),
    .X(_015_));
 sky130_fd_sc_hd__maj3_2 _083_ (.A(_015_),
    .B(net32),
    .C(net64),
    .X(_016_));
 sky130_fd_sc_hd__maj3_2 _084_ (.A(net2),
    .B(_016_),
    .C(net34),
    .X(_017_));
 sky130_fd_sc_hd__maj3_2 _085_ (.A(_017_),
    .B(net3),
    .C(net35),
    .X(_018_));
 sky130_fd_sc_hd__xnor2_1 _086_ (.A(net4),
    .B(net36),
    .Y(_019_));
 sky130_fd_sc_hd__maj3_2 _087_ (.A(net4),
    .B(_018_),
    .C(net36),
    .X(_020_));
 sky130_fd_sc_hd__xnor2_1 _088_ (.A(net5),
    .B(net37),
    .Y(_021_));
 sky130_fd_sc_hd__xnor2_1 _089_ (.A(net143),
    .B(_021_),
    .Y(net69));
 sky130_fd_sc_hd__maj3_2 _090_ (.A(_020_),
    .B(net5),
    .C(net37),
    .X(_022_));
 sky130_fd_sc_hd__xnor2_1 _091_ (.A(net6),
    .B(net38),
    .Y(_023_));
 sky130_fd_sc_hd__xnor2_1 _092_ (.A(net142),
    .B(_023_),
    .Y(net70));
 sky130_fd_sc_hd__maj3_2 _093_ (.A(_022_),
    .B(net6),
    .C(net38),
    .X(_024_));
 sky130_fd_sc_hd__xnor2_1 _094_ (.A(net7),
    .B(net39),
    .Y(_025_));
 sky130_fd_sc_hd__xnor2_1 _095_ (.A(net141),
    .B(_025_),
    .Y(net71));
 sky130_fd_sc_hd__maj3_2 _096_ (.A(_024_),
    .B(net7),
    .C(net39),
    .X(_026_));
 sky130_fd_sc_hd__xnor2_1 _097_ (.A(net8),
    .B(net40),
    .Y(_027_));
 sky130_fd_sc_hd__xnor2_1 _098_ (.A(net140),
    .B(_027_),
    .Y(net72));
 sky130_fd_sc_hd__maj3_2 _099_ (.A(net8),
    .B(_026_),
    .C(net40),
    .X(_028_));
 sky130_fd_sc_hd__xnor2_1 _100_ (.A(net9),
    .B(net41),
    .Y(_029_));
 sky130_fd_sc_hd__xnor2_1 _101_ (.A(net139),
    .B(_029_),
    .Y(net73));
 sky130_fd_sc_hd__maj3_2 _102_ (.A(_028_),
    .B(net9),
    .C(net41),
    .X(_030_));
 sky130_fd_sc_hd__xnor2_1 _103_ (.A(net10),
    .B(net42),
    .Y(_031_));
 sky130_fd_sc_hd__xnor2_1 _104_ (.A(net168),
    .B(_031_),
    .Y(net74));
 sky130_fd_sc_hd__maj3_2 _105_ (.A(_030_),
    .B(net10),
    .C(net42),
    .X(_032_));
 sky130_fd_sc_hd__xnor2_1 _106_ (.A(net11),
    .B(net43),
    .Y(_033_));
 sky130_fd_sc_hd__xnor2_1 _107_ (.A(net138),
    .B(_033_),
    .Y(net75));
 sky130_fd_sc_hd__maj3_2 _108_ (.A(_032_),
    .B(net11),
    .C(net43),
    .X(_034_));
 sky130_fd_sc_hd__xnor2_1 _109_ (.A(net13),
    .B(net45),
    .Y(_035_));
 sky130_fd_sc_hd__xnor2_1 _110_ (.A(net137),
    .B(_035_),
    .Y(net77));
 sky130_fd_sc_hd__maj3_2 _111_ (.A(net13),
    .B(_034_),
    .C(net45),
    .X(_036_));
 sky130_fd_sc_hd__xnor2_1 _112_ (.A(net14),
    .B(net46),
    .Y(_037_));
 sky130_fd_sc_hd__xnor2_1 _113_ (.A(net136),
    .B(_037_),
    .Y(net78));
 sky130_fd_sc_hd__maj3_2 _114_ (.A(net14),
    .B(_036_),
    .C(net46),
    .X(_038_));
 sky130_fd_sc_hd__xnor2_1 _115_ (.A(net15),
    .B(net47),
    .Y(_039_));
 sky130_fd_sc_hd__xnor2_1 _116_ (.A(net135),
    .B(_039_),
    .Y(net79));
 sky130_fd_sc_hd__maj3_2 _117_ (.A(_038_),
    .B(net15),
    .C(net47),
    .X(_040_));
 sky130_fd_sc_hd__xnor2_1 _118_ (.A(net16),
    .B(net48),
    .Y(_041_));
 sky130_fd_sc_hd__xnor2_1 _119_ (.A(net134),
    .B(_041_),
    .Y(net80));
 sky130_fd_sc_hd__maj3_2 _120_ (.A(_040_),
    .B(net16),
    .C(net48),
    .X(_042_));
 sky130_fd_sc_hd__xnor2_1 _121_ (.A(net17),
    .B(net49),
    .Y(_043_));
 sky130_fd_sc_hd__xnor2_1 _122_ (.A(net133),
    .B(_043_),
    .Y(net81));
 sky130_fd_sc_hd__maj3_2 _123_ (.A(_042_),
    .B(net17),
    .C(net49),
    .X(_044_));
 sky130_fd_sc_hd__xnor2_1 _124_ (.A(net18),
    .B(net50),
    .Y(_045_));
 sky130_fd_sc_hd__xnor2_1 _125_ (.A(net171),
    .B(_045_),
    .Y(net82));
 sky130_fd_sc_hd__maj3_2 _126_ (.A(net18),
    .B(_044_),
    .C(net50),
    .X(_046_));
 sky130_fd_sc_hd__xnor2_1 _127_ (.A(net19),
    .B(net51),
    .Y(_047_));
 sky130_fd_sc_hd__xnor2_1 _128_ (.A(net132),
    .B(_047_),
    .Y(net83));
 sky130_fd_sc_hd__maj3_2 _129_ (.A(_046_),
    .B(net19),
    .C(net51),
    .X(_048_));
 sky130_fd_sc_hd__xnor2_1 _130_ (.A(net20),
    .B(net52),
    .Y(_049_));
 sky130_fd_sc_hd__xnor2_1 _131_ (.A(net172),
    .B(_049_),
    .Y(net84));
 sky130_fd_sc_hd__maj3_2 _132_ (.A(_048_),
    .B(net20),
    .C(net52),
    .X(_050_));
 sky130_fd_sc_hd__xnor2_1 _133_ (.A(net21),
    .B(net53),
    .Y(_051_));
 sky130_fd_sc_hd__xnor2_1 _134_ (.A(net164),
    .B(_051_),
    .Y(net85));
 sky130_fd_sc_hd__maj3_2 _135_ (.A(net21),
    .B(_050_),
    .C(net53),
    .X(_052_));
 sky130_fd_sc_hd__xnor2_1 _136_ (.A(net22),
    .B(net54),
    .Y(_053_));
 sky130_fd_sc_hd__xnor2_1 _137_ (.A(net131),
    .B(_053_),
    .Y(net86));
 sky130_fd_sc_hd__maj3_2 _138_ (.A(net22),
    .B(_052_),
    .C(net54),
    .X(_054_));
 sky130_fd_sc_hd__xnor2_1 _139_ (.A(net24),
    .B(net56),
    .Y(_055_));
 sky130_fd_sc_hd__xnor2_1 _140_ (.A(net130),
    .B(_055_),
    .Y(net88));
 sky130_fd_sc_hd__maj3_2 _141_ (.A(net24),
    .B(_054_),
    .C(net56),
    .X(_056_));
 sky130_fd_sc_hd__xnor2_1 _142_ (.A(net25),
    .B(net57),
    .Y(_057_));
 sky130_fd_sc_hd__xnor2_4 _143_ (.A(_057_),
    .B(_056_),
    .Y(net89));
 sky130_fd_sc_hd__xor2_1 _144_ (.A(net161),
    .B(net157),
    .X(net65));
 sky130_fd_sc_hd__xnor2_1 _145_ (.A(net153),
    .B(_004_),
    .Y(net76));
 sky130_fd_sc_hd__xnor2_1 _146_ (.A(_000_),
    .B(net152),
    .Y(net87));
 sky130_fd_sc_hd__xnor2_1 _147_ (.A(net151),
    .B(_007_),
    .Y(net90));
 sky130_fd_sc_hd__xnor2_1 _148_ (.A(_063_),
    .B(net162),
    .Y(net91));
 sky130_fd_sc_hd__xnor2_1 _149_ (.A(net150),
    .B(_010_),
    .Y(net92));
 sky130_fd_sc_hd__xnor2_1 _150_ (.A(_062_),
    .B(net165),
    .Y(net93));
 sky130_fd_sc_hd__xnor2_1 _151_ (.A(net30),
    .B(net62),
    .Y(_058_));
 sky130_fd_sc_hd__xnor2_1 _152_ (.A(net149),
    .B(_058_),
    .Y(net94));
 sky130_fd_sc_hd__xnor2_1 _153_ (.A(net148),
    .B(_014_),
    .Y(net95));
 sky130_fd_sc_hd__xnor2_1 _154_ (.A(net32),
    .B(net64),
    .Y(_059_));
 sky130_fd_sc_hd__xnor2_1 _155_ (.A(net147),
    .B(_059_),
    .Y(net96));
 sky130_fd_sc_hd__xnor2_1 _156_ (.A(_061_),
    .B(net146),
    .Y(net66));
 sky130_fd_sc_hd__xnor2_1 _157_ (.A(net3),
    .B(net35),
    .Y(_060_));
 sky130_fd_sc_hd__xnor2_1 _158_ (.A(net145),
    .B(_060_),
    .Y(net67));
 sky130_fd_sc_hd__xnor2_1 _159_ (.A(net144),
    .B(_019_),
    .Y(net68));
 sky130_fd_sc_hd__clkbuf_2 input1 (.A(reg_op1[0]),
    .X(net1));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input10 (.A(reg_op1[18]),
    .X(net10));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input11 (.A(reg_op1[19]),
    .X(net11));
 sky130_fd_sc_hd__buf_8 input12 (.A(reg_op1[1]),
    .X(net12));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input13 (.A(reg_op1[20]),
    .X(net13));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input14 (.A(reg_op1[21]),
    .X(net14));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input15 (.A(reg_op1[22]),
    .X(net15));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input16 (.A(reg_op1[23]),
    .X(net16));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input17 (.A(reg_op1[24]),
    .X(net17));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input18 (.A(reg_op1[25]),
    .X(net18));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input19 (.A(reg_op1[26]),
    .X(net19));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input2 (.A(reg_op1[10]),
    .X(net2));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input20 (.A(reg_op1[27]),
    .X(net20));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input21 (.A(reg_op1[28]),
    .X(net21));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input22 (.A(reg_op1[29]),
    .X(net22));
 sky130_fd_sc_hd__dlymetal6s2s_1 input23 (.A(reg_op1[2]),
    .X(net23));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input24 (.A(reg_op1[30]),
    .X(net24));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input25 (.A(reg_op1[31]),
    .X(net25));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input26 (.A(reg_op1[3]),
    .X(net26));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input27 (.A(reg_op1[4]),
    .X(net27));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input28 (.A(reg_op1[5]),
    .X(net28));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input29 (.A(reg_op1[6]),
    .X(net29));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input3 (.A(reg_op1[11]),
    .X(net3));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input30 (.A(reg_op1[7]),
    .X(net30));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input31 (.A(reg_op1[8]),
    .X(net31));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input32 (.A(reg_op1[9]),
    .X(net32));
 sky130_fd_sc_hd__clkbuf_2 input33 (.A(reg_op2[0]),
    .X(net33));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input34 (.A(reg_op2[10]),
    .X(net34));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input35 (.A(reg_op2[11]),
    .X(net35));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input36 (.A(reg_op2[12]),
    .X(net36));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input37 (.A(reg_op2[13]),
    .X(net37));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input38 (.A(reg_op2[14]),
    .X(net38));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input39 (.A(reg_op2[15]),
    .X(net39));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input4 (.A(reg_op1[12]),
    .X(net4));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input40 (.A(reg_op2[16]),
    .X(net40));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input41 (.A(reg_op2[17]),
    .X(net41));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input42 (.A(reg_op2[18]),
    .X(net42));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input43 (.A(reg_op2[19]),
    .X(net43));
 sky130_fd_sc_hd__buf_6 input44 (.A(reg_op2[1]),
    .X(net44));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input45 (.A(reg_op2[20]),
    .X(net45));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input46 (.A(reg_op2[21]),
    .X(net46));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input47 (.A(reg_op2[22]),
    .X(net47));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input48 (.A(reg_op2[23]),
    .X(net48));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input49 (.A(reg_op2[24]),
    .X(net49));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input5 (.A(reg_op1[13]),
    .X(net5));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input50 (.A(reg_op2[25]),
    .X(net50));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input51 (.A(reg_op2[26]),
    .X(net51));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input52 (.A(reg_op2[27]),
    .X(net52));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input53 (.A(reg_op2[28]),
    .X(net53));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input54 (.A(reg_op2[29]),
    .X(net54));
 sky130_fd_sc_hd__dlymetal6s2s_1 input55 (.A(reg_op2[2]),
    .X(net55));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input56 (.A(reg_op2[30]),
    .X(net56));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input57 (.A(reg_op2[31]),
    .X(net57));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input58 (.A(reg_op2[3]),
    .X(net58));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input59 (.A(reg_op2[4]),
    .X(net59));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input6 (.A(reg_op1[14]),
    .X(net6));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input60 (.A(reg_op2[5]),
    .X(net60));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input61 (.A(reg_op2[6]),
    .X(net61));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input62 (.A(reg_op2[7]),
    .X(net62));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input63 (.A(reg_op2[8]),
    .X(net63));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input64 (.A(reg_op2[9]),
    .X(net64));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input7 (.A(reg_op1[15]),
    .X(net7));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input8 (.A(reg_op1[16]),
    .X(net8));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input9 (.A(reg_op1[17]),
    .X(net9));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output65 (.A(net65),
    .X(alu_out[0]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output66 (.A(net66),
    .X(alu_out[10]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output67 (.A(net67),
    .X(alu_out[11]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output68 (.A(net68),
    .X(alu_out[12]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output69 (.A(net69),
    .X(alu_out[13]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output70 (.A(net70),
    .X(alu_out[14]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output71 (.A(net71),
    .X(alu_out[15]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output72 (.A(net72),
    .X(alu_out[16]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output73 (.A(net73),
    .X(alu_out[17]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output74 (.A(net74),
    .X(alu_out[18]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output75 (.A(net75),
    .X(alu_out[19]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output76 (.A(net76),
    .X(alu_out[1]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output77 (.A(net77),
    .X(alu_out[20]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output78 (.A(net78),
    .X(alu_out[21]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output79 (.A(net79),
    .X(alu_out[22]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output80 (.A(net80),
    .X(alu_out[23]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output81 (.A(net81),
    .X(alu_out[24]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output82 (.A(net82),
    .X(alu_out[25]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output83 (.A(net83),
    .X(alu_out[26]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output84 (.A(net84),
    .X(alu_out[27]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output85 (.A(net85),
    .X(alu_out[28]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output86 (.A(net86),
    .X(alu_out[29]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output87 (.A(net87),
    .X(alu_out[2]));
 sky130_fd_sc_hd__clkbuf_2 output88 (.A(net88),
    .X(alu_out[30]));
 sky130_fd_sc_hd__buf_6 output89 (.A(net89),
    .X(alu_out[31]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output90 (.A(net90),
    .X(alu_out[3]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output91 (.A(net91),
    .X(alu_out[4]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output92 (.A(net92),
    .X(alu_out[5]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output93 (.A(net93),
    .X(alu_out[6]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output94 (.A(net94),
    .X(alu_out[7]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output95 (.A(net95),
    .X(alu_out[8]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output96 (.A(net96),
    .X(alu_out[9]));
 sky130_fd_sc_hd__buf_4 place130 (.A(_054_),
    .X(net130));
 sky130_fd_sc_hd__buf_4 place131 (.A(_052_),
    .X(net131));
 sky130_fd_sc_hd__buf_4 place132 (.A(_046_),
    .X(net132));
 sky130_fd_sc_hd__buf_4 place133 (.A(_042_),
    .X(net133));
 sky130_fd_sc_hd__buf_4 place134 (.A(_040_),
    .X(net134));
 sky130_fd_sc_hd__buf_4 place135 (.A(net179),
    .X(net135));
 sky130_fd_sc_hd__buf_4 place136 (.A(net176),
    .X(net136));
 sky130_fd_sc_hd__buf_4 place137 (.A(net169),
    .X(net137));
 sky130_fd_sc_hd__buf_4 place138 (.A(net163),
    .X(net138));
 sky130_fd_sc_hd__buf_4 place139 (.A(_028_),
    .X(net139));
 sky130_fd_sc_hd__buf_4 place140 (.A(_026_),
    .X(net140));
 sky130_fd_sc_hd__buf_4 place141 (.A(_024_),
    .X(net141));
 sky130_fd_sc_hd__buf_4 place142 (.A(_022_),
    .X(net142));
 sky130_fd_sc_hd__buf_4 place143 (.A(net175),
    .X(net143));
 sky130_fd_sc_hd__buf_4 place144 (.A(net170),
    .X(net144));
 sky130_fd_sc_hd__buf_4 place145 (.A(net178),
    .X(net145));
 sky130_fd_sc_hd__buf_4 place146 (.A(net177),
    .X(net146));
 sky130_fd_sc_hd__buf_4 place147 (.A(_015_),
    .X(net147));
 sky130_fd_sc_hd__buf_4 place148 (.A(_013_),
    .X(net148));
 sky130_fd_sc_hd__buf_4 place149 (.A(_012_),
    .X(net149));
 sky130_fd_sc_hd__buf_4 place150 (.A(_009_),
    .X(net150));
 sky130_fd_sc_hd__buf_4 place151 (.A(_006_),
    .X(net151));
 sky130_fd_sc_hd__buf_4 place152 (.A(_005_),
    .X(net152));
 sky130_fd_sc_hd__buf_4 place153 (.A(_002_),
    .X(net153));
 sky130_fd_sc_hd__buf_4 place154 (.A(net59),
    .X(net154));
 sky130_fd_sc_hd__buf_4 place155 (.A(net58),
    .X(net155));
 sky130_fd_sc_hd__buf_4 place156 (.A(net55),
    .X(net156));
 sky130_fd_sc_hd__buf_4 place157 (.A(net33),
    .X(net157));
 sky130_fd_sc_hd__buf_4 place158 (.A(net27),
    .X(net158));
 sky130_fd_sc_hd__buf_4 place159 (.A(net26),
    .X(net159));
 sky130_fd_sc_hd__buf_4 place160 (.A(net23),
    .X(net160));
 sky130_fd_sc_hd__buf_4 place161 (.A(net1),
    .X(net161));
 sky130_fd_sc_hd__buf_4 rebuffer162 (.A(_008_),
    .X(net162));
 sky130_fd_sc_hd__buf_4 rebuffer163 (.A(_032_),
    .X(net163));
 sky130_fd_sc_hd__buf_4 rebuffer164 (.A(net173),
    .X(net164));
 sky130_fd_sc_hd__buf_4 rebuffer165 (.A(_011_),
    .X(net165));
 sky130_fd_sc_hd__buf_4 rebuffer166 (.A(net167),
    .X(net166));
 sky130_fd_sc_hd__buf_4 rebuffer167 (.A(_003_),
    .X(net167));
 sky130_fd_sc_hd__buf_4 rebuffer168 (.A(_030_),
    .X(net168));
 sky130_fd_sc_hd__buf_4 rebuffer169 (.A(_034_),
    .X(net169));
 sky130_fd_sc_hd__buf_4 rebuffer170 (.A(net174),
    .X(net170));
 sky130_fd_sc_hd__buf_4 rebuffer171 (.A(_044_),
    .X(net171));
 sky130_fd_sc_hd__buf_4 rebuffer172 (.A(_048_),
    .X(net172));
 sky130_fd_sc_hd__buf_4 rebuffer173 (.A(_050_),
    .X(net173));
 sky130_fd_sc_hd__buf_4 rebuffer174 (.A(_018_),
    .X(net174));
 sky130_fd_sc_hd__buf_4 rebuffer175 (.A(_020_),
    .X(net175));
 sky130_fd_sc_hd__buf_4 rebuffer176 (.A(_036_),
    .X(net176));
 sky130_fd_sc_hd__buf_4 rebuffer177 (.A(_016_),
    .X(net177));
 sky130_fd_sc_hd__buf_4 rebuffer178 (.A(_017_),
    .X(net178));
 sky130_fd_sc_hd__buf_4 rebuffer179 (.A(_038_),
    .X(net179));
endmodule
