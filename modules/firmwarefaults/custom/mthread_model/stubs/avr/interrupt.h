/* avr/interrupt.h — the Mthread BRIDGE's stand-in (sc-2c, FIRMWARE_SCENARIO_PLAN.md §5 tier 2; the model's assumptions are in
 * ../../polari_mthread.h, stated once). It shadows the CBMC stub of the same name (this directory is searched first) and
 * exists only under -DPOLARI_MTHREAD:
 *
 *   cli()  → acquire THE interrupt lock (one global Mthread mutex = the AVR's SREG.I masking)
 *   sei()  → release it
 *   ISR(v) → a plain function; the harness runs its body in a Frama_C_thread_create'd thread that holds the interrupt
 *            lock for the whole body (the core clears I on entry and `reti` sets it again — no ISR nests, none splits
 *            a masked section of the main loop)
 */
#ifndef POLARI_MTHREAD_AVR_INTERRUPT_H
#define POLARI_MTHREAD_AVR_INTERRUPT_H
#ifndef POLARI_MTHREAD
#error "mthread_model/stubs is the Mthread bridge: preprocess with -DPOLARI_MTHREAD (the CBMC stubs serve every other use)"
#endif
#include "polari_mthread.h"
#define cli() polari_irq_lock()
#define sei() polari_irq_unlock()
#define ISR(vector) void vector(void)
#define TIMER2_COMPA_vect polari_isr_timer2_compa
#define USART_RX_vect polari_isr_usart_rx
#define INT0_vect polari_isr_int0
#endif
