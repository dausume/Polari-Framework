/*
 * rx_ring_race.c — the Mthread harness for FormalCheck `rx-ring-race` (sc-2c, FIRMWARE_SCENARIO_PLAN.md §3 1b, §5). The bridge and
 * its assumptions: polari_mthread.h (A1–A6).
 *
 * The variant's own hal.c, unedited, #included (FEATURE_COMMANDS 1 in the shipped rig: the RX ISR and the ring exist):
 *
 *   thread polari_rx_isr : the real ISR(USART_RX_vect) — reads rx_tail, writes rx_ring[rx_head] and rx_head — under the
 *                          interrupt lock, as often as a byte may arrive
 *   thread <main>        : the real hal_rx_pop() — reads rx_head, reads rx_ring[rx_tail], writes rx_tail — lock NOT held
 *
 * Expected: Mthread lists rx_head, rx_tail and rx_ring as shared with main's accesses unprotected; the byte rule (A5)
 * decides them — one byte each, one writer each (the single-producer / single-consumer discipline).
 *
 * POLARI_BROKEN_FLUSH=1 is the NEGATIVE CONTROL (the selftest's and the probe's): main also runs a "flush" that writes
 * rx_head = rx_tail — the HARNESS's broken code, not the firmware's — so rx_head has two writers and must be refuted.
 */
#include "hal.c"

__fc_mthread_id polari_irq;
int polari_irq_mutex;
volatile int polari_irq_pending;
volatile int polari_main_runs;
volatile uint8_t POLARI_IO[0x100];
int polari_rx_isr;                         /* names the ISR thread in Mthread's report */

POLARI_ISR_THREAD(polari_rx_thread, USART_RX_vect)

void Frama_C_show_each_polari_size_rx_head(unsigned);
void Frama_C_show_each_polari_size_rx_tail(unsigned);
void Frama_C_show_each_polari_size_rx_ring(unsigned);

#if POLARI_BROKEN_FLUSH
static void polari_broken_flush(void) { rx_head = rx_tail; }   /* WRONG on purpose: the consumer writes the producer's index */
#endif

int main(void)
{
    Frama_C_show_each_polari_size_rx_head(sizeof rx_head);
    Frama_C_show_each_polari_size_rx_tail(sizeof rx_tail);
    Frama_C_show_each_polari_size_rx_ring(sizeof rx_ring[0]);   /* the element: one slot is one access */
    POLARI_IRQ_INIT();
    POLARI_SPAWN(polari_rx_isr, polari_rx_thread);                 /* created suspended, then started (A2) */
    while (polari_main_runs) {
        uint8_t b;
        (void)hal_rx_pop(&b);
#if POLARI_BROKEN_FLUSH
        polari_broken_flush();
#endif
    }
    return 0;
}
