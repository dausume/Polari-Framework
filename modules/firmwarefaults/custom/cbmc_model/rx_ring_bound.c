/*
 * rx_ring_bound.c — the CBMC harness for FormalCheck `rx-ring-index-bound` (sc-2b, FIRMWARE_SCENARIO_PLAN.md §3 1b, §5).
 *
 * The variant's own hal.c (unedited; `static` defined away around the include so the harness can set the ring's state)
 * under stubs/. The ring starts in an ARBITRARY valid state — rx_head, rx_tail any values in 0..RX_RING-1 (every such pair
 * is reachable: the fill is (head - tail) mod RX_RING <= RX_RING-1; the held bytes' values unknown) — so a short bound
 * covers the wrap-around without 2 x RX_RING steps first; the order check starts at the first byte the harness sends.
 * Then POLARI_STEPS nondeterministic steps, each one of:
 *   - the USART RX interrupt (the next sequence byte arrives) — only while SREG.I is set, I cleared for the ISR;
 *   - the main loop's hal_rx_pop();
 * and goto-instrument --isr polari_rx_irq lets the RX interrupt also run between any two statements of hal_rx_pop that
 * touch the ring. Properties after every step: rx_head and rx_tail stay in 0..RX_RING-1; the fill equals bytes accepted
 * minus bytes popped; a pop returns bytes in arrival order (no slot skipped or repeated).
 * Bound k = POLARI_STEPS. `decided (bounded)`, never `proved`. Limits: --16 (LP32), uint8_t indices as avr-gcc sees them.
 */
#define static
#include "hal.c"
#undef static

#ifndef POLARI_STEPS
#define POLARI_STEPS 8
#endif
#ifndef POLARI_CHECK_ORDER
#define POLARI_CHECK_ORDER 1      /* 0: only the index + fill properties (the order check costs the solver the most) */
#endif

uint8_t polari_sreg_i = 0u;          /* masked while the harness sets the start state; main enables it */
volatile uint8_t POLARI_IO[0x100];
static unsigned polari_accepted, polari_out;
static uint8_t polari_seq_in, polari_seq_out;

_Bool nondet_bool(void);
uint8_t nondet_u8(void);

/* the RX interrupt: the byte is the next sequence number, so FIFO order is checkable */
void polari_rx_irq(void)
{
    if (polari_sreg_i && nondet_bool()) {
        polari_sreg_i = 0u;          /* the core clears I first: the ghost bookkeeping below is part of the same ISR */
        uint8_t before = (uint8_t)((rx_head - rx_tail) & (RX_RING - 1u));
        UDR0 = polari_seq_in;
        USART_RX_vect();
        polari_sreg_i = 1u;
        if ((uint8_t)((rx_head - rx_tail) & (RX_RING - 1u)) != before) { polari_accepted++; polari_seq_in++; }   /* full → dropped, by design */
    }
}

int main(void)
{
    uint8_t h = nondet_u8(), t = nondet_u8();
    __CPROVER_assume(h <= RX_RING - 1u && t <= RX_RING - 1u);
    rx_head = h;
    rx_tail = t;
    unsigned fill = (unsigned)((h - t) & (RX_RING - 1u));   /* the held bytes: contents unknown, order checked from the first new one */
    polari_accepted = fill;
    polari_sreg_i = 1u;
    for (int s = 0; s < POLARI_STEPS; s++) {
        if (nondet_bool()) {
            polari_rx_irq();
        } else {
            uint8_t b;
            if (hal_rx_pop(&b)) {
                if (POLARI_CHECK_ORDER && polari_out >= fill) {                    /* past the held bytes: the ones the harness sent, in order */
                    __CPROVER_assert(b == polari_seq_out, "a pop returns the bytes in arrival order (no slot skipped or repeated)");
                    polari_seq_out++;
                }
                polari_out++;
            }
        }
        __CPROVER_assert(rx_head <= RX_RING - 1u && rx_tail <= RX_RING - 1u, "rx_head and rx_tail never exceed RX_RING-1");
        __CPROVER_assert((unsigned)((rx_head - rx_tail) & (RX_RING - 1u)) == polari_accepted - polari_out,
                         "the ring's fill equals bytes accepted minus bytes popped");
    }
    return 0;
}
