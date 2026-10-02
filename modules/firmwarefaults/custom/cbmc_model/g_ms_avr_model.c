/*
 * g_ms_avr_model.c — the AVR side of FormalCheck `hal-millis-not-torn` (sc-2b): how the core READS the 4-byte tick and
 * WHEN the tick interrupt may run. Its own translation unit because goto-instrument's volatile model rewrites EVERY
 * expression naming the volatile g_ms — even `&g_ms` — so the model cannot name it as declared. Here g_ms is declared
 * without `volatile` (the same object: hal.c's g_ms, external through the harness's `#define static`), so these reads are
 * the model's own and are not re-modelled. CBMC treats `volatile` as plain C otherwise; nothing else differs.
 */
#include <stdint.h>

#ifndef POLARI_K
#define POLARI_K 2            /* at most K ticks in any one gap between two loads (the bound k) */
#endif

extern uint32_t g_ms;               /* hal.c: static volatile uint32_t g_ms (its linkage opened by the harness) */
extern uint8_t polari_sreg_i;
void polari_isr_timer2_compa(void);  /* hal.c: ISR(TIMER2_COMPA_vect) { g_ms++; } through stubs/avr/interrupt.h */
_Bool nondet_bool(void);

/* the tick as the core takes it: only with I set; I cleared for the ISR (hardware), set again by its reti */
void polari_tick(void)
{
    if (polari_sreg_i && nondet_bool()) {
        polari_sreg_i = 0u;
        polari_isr_timer2_compa();
        polari_sreg_i = 1u;
    }
}

static void polari_gap(void)
{
    for (int n = 0; n < POLARI_K; n++)
        polari_tick();
}

/* a read of g_ms on the AVR: lds r22,g_ms · lds r23,g_ms+1 · lds r24,g_ms+2 · lds r25,g_ms+3 (plan §3) */
uint32_t polari_avr_read_g_ms(void)
{
    const uint8_t *p = (const uint8_t *)&g_ms;
    if (!polari_sreg_i)            /* interrupts masked (an ISR, or inside ATOMIC_BLOCK): nothing can split the loads */
        return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
    uint32_t b0 = p[0];
    polari_gap();
    uint32_t b1 = p[1];
    polari_gap();
    uint32_t b2 = p[2];
    polari_gap();
    uint32_t b3 = p[3];
    return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24);
}

uint32_t polari_plain_g_ms(void) { return g_ms; }
void polari_set_g_ms(uint32_t v) { g_ms = v; }
