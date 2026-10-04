/*
 * hal_millis_race.c — the Mthread harness for FormalCheck `hal-millis-race` (sc-2c, FIRMWARE_SCENARIO_PLAN.md §5 tier 2). The
 * bridge and its assumptions: polari_mthread.h (A1–A6).
 *
 * The firmware is NOT edited: the variant's own generated hal.c is #included here, preprocessed with -DPOLARI_MTHREAD against
 * mt_stubs/ (cli/sei/ATOMIC_BLOCK → the interrupt lock) then stubs/ (the CBMC stubs: registers as bytes, AVR widths). Its
 * board_config.h sets HAL_MILLIS_ATOMIC, so the SAME source gives the shipped read (1: ATOMIC_BLOCK) or the bare one (0).
 *
 *   thread polari_tick_isr : the real ISR(TIMER2_COMPA_vect) — g_ms++ — under the interrupt lock, as often as it may fire
 *   thread <main>          : the real hal_millis(), as often as the main loop calls it
 *
 * The question Mthread answers, unbounded: which of the two threads' accesses to g_ms hold the lock.
 */
#include "hal.c"

__fc_mthread_id polari_irq;
int polari_irq_mutex;
volatile int polari_irq_pending;
volatile int polari_main_runs;
volatile uint8_t POLARI_IO[0x100];
int polari_tick_isr;                       /* names the ISR thread in Mthread's report */

POLARI_ISR_THREAD(polari_tick_thread, TIMER2_COMPA_vect)

void Frama_C_show_each_polari_size_g_ms(unsigned);

int main(void)
{
    Frama_C_show_each_polari_size_g_ms(sizeof g_ms);     /* A5: the size from the source's own type */
    POLARI_IRQ_INIT();
    POLARI_SPAWN(polari_tick_isr, polari_tick_thread);                 /* created suspended, then started (A2) */
    while (polari_main_runs) {
        uint32_t now = hal_millis();
        (void)now;
    }
    return 0;
}
