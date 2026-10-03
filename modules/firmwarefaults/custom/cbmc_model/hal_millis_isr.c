/*
 * hal_millis_isr.c — the CBMC harness for FormalCheck `hal-millis-not-torn` (sc-2b, FIRMWARE_SCENARIO_PLAN.md §5 tier 2),
 * with its companion translation unit g_ms_avr_model.c.
 *
 * The firmware is NOT edited: this file #includes the variant's own generated hal.c (its board_config.h sets
 * HAL_MILLIS_ATOMIC), compiled against stubs/ (registers as bytes, SREG.I as `polari_sreg_i`, ATOMIC_BLOCK = save I,
 * clear, restore). `static` is defined away around the include so g_ms and the tick ISR get external linkage — the
 * companion unit then names g_ms WITHOUT `volatile` (see there why). The INTERRUPT is CBMC nondeterminism:
 *
 *   - every read of the volatile g_ms in hal.c is replaced (goto-instrument --nondet-volatile-model
 *     g_ms:polari_avr_read_g_ms) by the AVR's four one-byte loads, low byte first (the disassembly of both builds, plan
 *     §3), with the tick ISR possibly running between any two loads — up to POLARI_K times per gap, ONLY while SREG.I is set;
 *   - goto-instrument --isr polari_tick lets the tick also run between any two statements that touch g_ms (the
 *     statement-level interleaving), again only while SREG.I is set.
 *
 * The property: hal_millis() returns a value g_ms actually HELD during the call — the value before a tick or after it,
 * never a mix of bytes from both. g_ms only ever increments by one per tick, so "held" = pre <= r <= post.
 *
 * Honest limits (said on the FormalCheck row): CBMC has no AVR architecture. It runs with --16 (LP32: int 16 bits as
 * avr-gcc, long 32) on a little-endian target (as the AVR); pointers are 32 bits, not 16. The byte-wise read is OUR model
 * of the instruction sequence, cross-checked by the simulation tier (the twin forced the tear at hal_millis+0x4); CBMC
 * decides the C-level property under that model up to the bound — `decided (bounded)`, never `proved`.
 */
#define static
#include "hal.c"
#undef static

uint8_t polari_sreg_i = 1u;
volatile uint8_t POLARI_IO[0x100];

uint32_t nondet_u32(void);
uint32_t polari_plain_g_ms(void);          /* g_ms_avr_model.c: the value in memory now (a ghost read, not the firmware's) */
void polari_set_g_ms(uint32_t v);

int main(void)
{
    uint32_t init = nondet_u32();
    __CPROVER_assume(init <= 0xFFFFFF00ul);   /* no 32-bit wrap inside the bound (49.7 days of uptime) */
    polari_set_g_ms(init);
    polari_sreg_i = 1u;
    uint32_t pre = polari_plain_g_ms();
    uint32_t r = hal_millis();
    uint32_t post = polari_plain_g_ms();
    __CPROVER_assert(r >= pre && r <= post, "hal_millis returns g_ms before or after a tick, never a torn mix of both");
    __CPROVER_assert(polari_sreg_i == 1u, "interrupts are enabled again when hal_millis returns");
    return 0;
}
