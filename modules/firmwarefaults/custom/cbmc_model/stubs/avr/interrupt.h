/* avr/interrupt.h — the formal tier's stand-in (sc-2b): SREG's I bit is the harness's `polari_sreg_i`; an ISR is a plain
 * function the HARNESS calls (only when polari_sreg_i is 1, clearing it for the ISR's duration, as the AVR core does). */
#ifndef POLARI_FORMAL_AVR_INTERRUPT_H
#define POLARI_FORMAL_AVR_INTERRUPT_H
#include <stdint.h>
extern uint8_t polari_sreg_i;
#define cli() (polari_sreg_i = 0u)
#define sei() (polari_sreg_i = 1u)
#define ISR(vector) void vector(void)
#define TIMER2_COMPA_vect polari_isr_timer2_compa
#define USART_RX_vect polari_isr_usart_rx
#define INT0_vect polari_isr_int0
#endif
