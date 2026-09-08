// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

bool Vtop___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_anySet__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        if (in[n]) {
            return (1U);
        }
        n = ((IData)(1U) + n);
    } while ((1U > n));
    return (0U);
}

void Vtop___024root___nba_sequent__TOP__0(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___nba_sequent__TOP__0\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    SData/*15:0*/ __Vdly__top__DOT__dut__DOT__heartbeat;
    __Vdly__top__DOT__dut__DOT__heartbeat = 0;
    CData/*7:0*/ __Vdly__top__DOT__dut__DOT__sim_counter;
    __Vdly__top__DOT__dut__DOT__sim_counter = 0;
    CData/*7:0*/ __Vdly__top__DOT__dut__DOT__waddr_l;
    __Vdly__top__DOT__dut__DOT__waddr_l = 0;
    CData/*0:0*/ __Vdly__top__DOT__dut__DOT__aw_got;
    __Vdly__top__DOT__dut__DOT__aw_got = 0;
    CData/*0:0*/ __Vdly__top__DOT__dut__DOT__w_got;
    __Vdly__top__DOT__dut__DOT__w_got = 0;
    CData/*0:0*/ __Vdly__bvalid;
    __Vdly__bvalid = 0;
    CData/*0:0*/ __Vdly__arready;
    __Vdly__arready = 0;
    CData/*0:0*/ __Vdly__rvalid;
    __Vdly__rvalid = 0;
    // Body
    __Vdly__top__DOT__dut__DOT__heartbeat = vlSelfRef.top__DOT__dut__DOT__heartbeat;
    __Vdly__top__DOT__dut__DOT__sim_counter = vlSelfRef.top__DOT__dut__DOT__sim_counter;
    __Vdly__top__DOT__dut__DOT__waddr_l = vlSelfRef.top__DOT__dut__DOT__waddr_l;
    __Vdly__top__DOT__dut__DOT__aw_got = vlSelfRef.top__DOT__dut__DOT__aw_got;
    __Vdly__top__DOT__dut__DOT__w_got = vlSelfRef.top__DOT__dut__DOT__w_got;
    __Vdly__bvalid = vlSelfRef.bvalid;
    __Vdly__arready = vlSelfRef.arready;
    __Vdly__rvalid = vlSelfRef.rvalid;
    if (vlSelfRef.rst) {
        __Vdly__top__DOT__dut__DOT__heartbeat = (0x0000ffffU 
                                                 & ((IData)(1U) 
                                                    + (IData)(vlSelfRef.top__DOT__dut__DOT__heartbeat)));
        __Vdly__top__DOT__dut__DOT__sim_counter = (0x000000ffU 
                                                   & ((IData)(1U) 
                                                      + (IData)(vlSelfRef.top__DOT__dut__DOT__sim_counter)));
        __Vdly__arready = (((IData)(vlSelfRef.arvalid) 
                            & (~ (IData)(vlSelfRef.rvalid))) 
                           & (~ (IData)(vlSelfRef.arready)));
        if ((((IData)(vlSelfRef.arready) & (IData)(vlSelfRef.arvalid)) 
             & (~ (IData)(vlSelfRef.rvalid)))) {
            __Vdly__rvalid = 1U;
            vlSelfRef.rresp = 0U;
            vlSelfRef.top__DOT__rdata32 = (((((((((0U 
                                                   == 
                                                   (0x000000ffU 
                                                    & (IData)(vlSelfRef.araddr))) 
                                                  | (4U 
                                                     == 
                                                     (0x000000ffU 
                                                      & (IData)(vlSelfRef.araddr)))) 
                                                 | (8U 
                                                    == 
                                                    (0x000000ffU 
                                                     & (IData)(vlSelfRef.araddr)))) 
                                                | (0x0cU 
                                                   == 
                                                   (0x000000ffU 
                                                    & (IData)(vlSelfRef.araddr)))) 
                                               | (0x10U 
                                                  == 
                                                  (0x000000ffU 
                                                   & (IData)(vlSelfRef.araddr)))) 
                                              | (0x20U 
                                                 == 
                                                 (0x000000ffU 
                                                  & (IData)(vlSelfRef.araddr)))) 
                                             | (0x24U 
                                                == 
                                                (0x000000ffU 
                                                 & (IData)(vlSelfRef.araddr)))) 
                                            | (0x30U 
                                               == (0x000000ffU 
                                                   & (IData)(vlSelfRef.araddr))))
                                            ? ((0U 
                                                == 
                                                (0x000000ffU 
                                                 & (IData)(vlSelfRef.araddr)))
                                                ? 0x504c0001U
                                                : (
                                                   (4U 
                                                    == 
                                                    (0x000000ffU 
                                                     & (IData)(vlSelfRef.araddr)))
                                                    ? 0x00010000U
                                                    : 
                                                   ((8U 
                                                     == 
                                                     (0x000000ffU 
                                                      & (IData)(vlSelfRef.araddr)))
                                                     ? 
                                                    ((((1U 
                                                        & vlSelfRef.top__DOT__dut__DOT__r_mode_mux)
                                                        ? 0xb7U
                                                        : (IData)(vlSelfRef.top__DOT__dut__DOT__sim_counter)) 
                                                      << 0x00000010U) 
                                                     | (IData)(vlSelfRef.top__DOT__dut__DOT__heartbeat))
                                                     : 
                                                    ((0x0cU 
                                                      == 
                                                      (0x000000ffU 
                                                       & (IData)(vlSelfRef.araddr)))
                                                      ? 0U
                                                      : 
                                                     ((0x10U 
                                                       == 
                                                       (0x000000ffU 
                                                        & (IData)(vlSelfRef.araddr)))
                                                       ? vlSelfRef.top__DOT__dut__DOT__r_commands
                                                       : 
                                                      ((0x20U 
                                                        == 
                                                        (0x000000ffU 
                                                         & (IData)(vlSelfRef.araddr)))
                                                        ? vlSelfRef.top__DOT__dut__DOT__r_config
                                                        : 
                                                       ((0x24U 
                                                         == 
                                                         (0x000000ffU 
                                                          & (IData)(vlSelfRef.araddr)))
                                                         ? vlSelfRef.top__DOT__dut__DOT__r_mode_mux
                                                         : vlSelfRef.top__DOT__dut__DOT__r_led_matrix)))))))
                                            : 0U);
        } else if (((IData)(vlSelfRef.rvalid) & (IData)(vlSelfRef.rready))) {
            __Vdly__rvalid = 0U;
        }
        if ((((IData)(vlSelfRef.awvalid) & (~ (IData)(vlSelfRef.top__DOT__dut__DOT__aw_got))) 
             & (~ (IData)(vlSelfRef.awready)))) {
            vlSelfRef.awready = 1U;
            __Vdly__top__DOT__dut__DOT__waddr_l = (0x000000ffU 
                                                   & (IData)(vlSelfRef.awaddr));
            __Vdly__top__DOT__dut__DOT__aw_got = 1U;
        } else {
            vlSelfRef.awready = 0U;
        }
        if ((((IData)(vlSelfRef.wvalid) & (~ (IData)(vlSelfRef.top__DOT__dut__DOT__w_got))) 
             & (~ (IData)(vlSelfRef.wready)))) {
            vlSelfRef.wready = 1U;
            __Vdly__top__DOT__dut__DOT__w_got = 1U;
        } else {
            vlSelfRef.wready = 0U;
        }
        if ((((IData)(vlSelfRef.top__DOT__dut__DOT__aw_got) 
              & (IData)(vlSelfRef.top__DOT__dut__DOT__w_got)) 
             & (~ (IData)(vlSelfRef.bvalid)))) {
            if ((0x10U == (IData)(vlSelfRef.top__DOT__dut__DOT__waddr_l))) {
                vlSelfRef.top__DOT__dut__DOT__r_commands 
                    = (IData)(vlSelfRef.wdata);
            } else if ((0x20U == (IData)(vlSelfRef.top__DOT__dut__DOT__waddr_l))) {
                vlSelfRef.top__DOT__dut__DOT__r_config 
                    = (IData)(vlSelfRef.wdata);
            } else if ((0x24U == (IData)(vlSelfRef.top__DOT__dut__DOT__waddr_l))) {
                vlSelfRef.top__DOT__dut__DOT__r_mode_mux 
                    = (IData)(vlSelfRef.wdata);
            } else if ((0x30U == (IData)(vlSelfRef.top__DOT__dut__DOT__waddr_l))) {
                vlSelfRef.top__DOT__dut__DOT__r_led_matrix 
                    = (IData)(vlSelfRef.wdata);
            }
            __Vdly__bvalid = 1U;
            vlSelfRef.bresp = 0U;
            __Vdly__top__DOT__dut__DOT__aw_got = 0U;
            __Vdly__top__DOT__dut__DOT__w_got = 0U;
        } else if (((IData)(vlSelfRef.bvalid) & (IData)(vlSelfRef.bready))) {
            __Vdly__bvalid = 0U;
        }
    } else {
        __Vdly__top__DOT__dut__DOT__heartbeat = 0U;
        __Vdly__top__DOT__dut__DOT__sim_counter = 0U;
        __Vdly__arready = 0U;
        __Vdly__rvalid = 0U;
        vlSelfRef.top__DOT__rdata32 = 0U;
        vlSelfRef.rresp = 0U;
        vlSelfRef.awready = 0U;
        vlSelfRef.wready = 0U;
        __Vdly__bvalid = 0U;
        vlSelfRef.bresp = 0U;
        __Vdly__top__DOT__dut__DOT__aw_got = 0U;
        __Vdly__top__DOT__dut__DOT__w_got = 0U;
        __Vdly__top__DOT__dut__DOT__waddr_l = 0U;
        vlSelfRef.top__DOT__dut__DOT__r_commands = 0U;
        vlSelfRef.top__DOT__dut__DOT__r_config = 0U;
        vlSelfRef.top__DOT__dut__DOT__r_mode_mux = 0U;
        vlSelfRef.top__DOT__dut__DOT__r_led_matrix = 0U;
    }
    vlSelfRef.arready = __Vdly__arready;
    vlSelfRef.rvalid = __Vdly__rvalid;
    vlSelfRef.top__DOT__dut__DOT__sim_counter = __Vdly__top__DOT__dut__DOT__sim_counter;
    vlSelfRef.top__DOT__dut__DOT__heartbeat = __Vdly__top__DOT__dut__DOT__heartbeat;
    vlSelfRef.rdata = (QData)((IData)(vlSelfRef.top__DOT__rdata32));
    vlSelfRef.top__DOT__dut__DOT__waddr_l = __Vdly__top__DOT__dut__DOT__waddr_l;
    vlSelfRef.top__DOT__dut__DOT__aw_got = __Vdly__top__DOT__dut__DOT__aw_got;
    vlSelfRef.top__DOT__dut__DOT__w_got = __Vdly__top__DOT__dut__DOT__w_got;
    vlSelfRef.bvalid = __Vdly__bvalid;
}

void Vtop___024root___trigger_orInto__act_vec_vec(VlUnpacked<QData/*63:0*/, 1> &out, const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_orInto__act_vec_vec\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = (out[n] | in[n]);
        n = ((IData)(1U) + n);
    } while ((0U >= n));
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtop___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG

bool Vtop___024root___eval_phase__act(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_phase__act\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    {
        // Inlined CFunc: _eval_triggers_vec__act
        vlSelfRef.__VactTriggered[0U] = (QData)((IData)(
                                                        ((IData)(vlSelfRef.clk) 
                                                         & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__clk__0)))));
        vlSelfRef.__Vtrigprevexpr___TOP__clk__0 = vlSelfRef.clk;
    }
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
    }
#endif
    Vtop___024root___trigger_orInto__act_vec_vec(vlSelfRef.__VnbaTriggered, vlSelfRef.__VactTriggered);
    return (0U);
}

void Vtop___024root___trigger_clear__act(VlUnpacked<QData/*63:0*/, 1> &out) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_clear__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = 0ULL;
        n = ((IData)(1U) + n);
    } while ((1U > n));
}

bool Vtop___024root___eval_phase__nba(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_phase__nba\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = Vtop___024root___trigger_anySet__act(vlSelfRef.__VnbaTriggered);
    if (__VnbaExecute) {
        {
            // Inlined CFunc: _eval_nba
            if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
                Vtop___024root___nba_sequent__TOP__0(vlSelf);
            }
        }
        Vtop___024root___trigger_clear__act(vlSelfRef.__VnbaTriggered);
    }
    return (__VnbaExecute);
}

void Vtop___024root___eval(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VnbaIterCount;
    // Body
    __VnbaIterCount = 0U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VnbaIterCount)))) {
#ifdef VL_DEBUG
            Vtop___024root___dump_triggers__act(vlSelfRef.__VnbaTriggered, "nba"s);
#endif
            VL_FATAL_MT("top.v", 4, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                VL_FATAL_MT("top.v", 4, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
            }
            vlSelfRef.__VactIterCount = ((IData)(1U) 
                                         + vlSelfRef.__VactIterCount);
            vlSelfRef.__VactPhaseResult = Vtop___024root___eval_phase__act(vlSelf);
        } while (vlSelfRef.__VactPhaseResult);
        vlSelfRef.__VnbaPhaseResult = Vtop___024root___eval_phase__nba(vlSelf);
    } while (vlSelfRef.__VnbaPhaseResult);
}

#ifdef VL_DEBUG
void Vtop___024root___eval_debug_assertions(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_debug_assertions\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if (VL_UNLIKELY(((vlSelfRef.clk & 0xfeU)))) {
        Verilated::overWidthError("clk");
    }
    if (VL_UNLIKELY(((vlSelfRef.rst & 0xfeU)))) {
        Verilated::overWidthError("rst");
    }
    if (VL_UNLIKELY(((vlSelfRef.awvalid & 0xfeU)))) {
        Verilated::overWidthError("awvalid");
    }
    if (VL_UNLIKELY(((vlSelfRef.awprot & 0xf8U)))) {
        Verilated::overWidthError("awprot");
    }
    if (VL_UNLIKELY(((vlSelfRef.wstrb & 0xf0U)))) {
        Verilated::overWidthError("wstrb");
    }
    if (VL_UNLIKELY(((vlSelfRef.wvalid & 0xfeU)))) {
        Verilated::overWidthError("wvalid");
    }
    if (VL_UNLIKELY(((vlSelfRef.bready & 0xfeU)))) {
        Verilated::overWidthError("bready");
    }
    if (VL_UNLIKELY(((vlSelfRef.arvalid & 0xfeU)))) {
        Verilated::overWidthError("arvalid");
    }
    if (VL_UNLIKELY(((vlSelfRef.arprot & 0xf8U)))) {
        Verilated::overWidthError("arprot");
    }
    if (VL_UNLIKELY(((vlSelfRef.rready & 0xfeU)))) {
        Verilated::overWidthError("rready");
    }
}
#endif  // VL_DEBUG
