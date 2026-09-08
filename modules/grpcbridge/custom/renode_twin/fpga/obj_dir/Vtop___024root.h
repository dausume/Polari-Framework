// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vtop.h for the primary calling header

#ifndef VERILATED_VTOP___024ROOT_H_
#define VERILATED_VTOP___024ROOT_H_  // guard

#include "verilated.h"


class Vtop__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vtop___024root final {
  public:

    // DESIGN SPECIFIC STATE
    VL_IN8(clk,0,0);
    VL_IN8(rst,0,0);
    VL_IN8(awvalid,0,0);
    VL_OUT8(awready,0,0);
    VL_IN8(awprot,2,0);
    VL_IN8(wstrb,3,0);
    VL_IN8(wvalid,0,0);
    VL_OUT8(wready,0,0);
    VL_OUT8(bresp,1,0);
    VL_OUT8(bvalid,0,0);
    VL_IN8(bready,0,0);
    VL_IN8(arvalid,0,0);
    VL_OUT8(arready,0,0);
    VL_IN8(arprot,2,0);
    VL_OUT8(rresp,1,0);
    VL_OUT8(rvalid,0,0);
    VL_IN8(rready,0,0);
    CData/*7:0*/ top__DOT__dut__DOT__sim_counter;
    CData/*0:0*/ top__DOT__dut__DOT__aw_got;
    CData/*0:0*/ top__DOT__dut__DOT__w_got;
    CData/*7:0*/ top__DOT__dut__DOT__waddr_l;
    CData/*0:0*/ __VstlFirstIteration;
    CData/*0:0*/ __VstlPhaseResult;
    CData/*0:0*/ __Vtrigprevexpr___TOP__clk__0;
    CData/*0:0*/ __VactPhaseResult;
    CData/*0:0*/ __VnbaPhaseResult;
    SData/*15:0*/ top__DOT__dut__DOT__heartbeat;
    IData/*31:0*/ top__DOT__rdata32;
    IData/*31:0*/ top__DOT__dut__DOT__r_commands;
    IData/*31:0*/ top__DOT__dut__DOT__r_config;
    IData/*31:0*/ top__DOT__dut__DOT__r_mode_mux;
    IData/*31:0*/ top__DOT__dut__DOT__r_led_matrix;
    IData/*31:0*/ __VactIterCount;
    VL_IN64(awaddr,63,0);
    VL_IN64(wdata,63,0);
    VL_IN64(araddr,63,0);
    VL_OUT64(rdata,63,0);
    VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
