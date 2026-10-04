/* avr/io.h — the formal tier's stand-in (sc-2b, FIRMWARE_SCENARIO_PLAN.md §5): every ATmega328P register hal.c names is a
 * byte of POLARI_IO (data-space address, DS40002061B §36 "Register Summary"), and every bit name is its bit number. CBMC
 * reads the firmware's OWN hal.c through these; nothing here is behaviour — the interrupt model is in the harness. */
#ifndef POLARI_FORMAL_AVR_IO_H
#define POLARI_FORMAL_AVR_IO_H
#include <stdint.h>
extern volatile uint8_t POLARI_IO[0x100];
#define _BV(b) (1u << (b))
#define POLARI_R8(a) (POLARI_IO[(a)])
#define POLARI_R16(a) (*(volatile uint16_t *)&POLARI_IO[(a)])
/* PORTB/PORTD/DDR */
#define DDRB POLARI_R8(0x24)
#define PORTB POLARI_R8(0x25)
#define DDRD POLARI_R8(0x2A)
#define PORTD POLARI_R8(0x2B)
#define PB1 1
#define PB2 2
#define PD2 2
#define PD5 5
#define PD6 6
/* external interrupt */
#define EIFR POLARI_R8(0x3C)
#define EIMSK POLARI_R8(0x3D)
#define EICRA POLARI_R8(0x69)
#define INTF0 0
#define INT0 0
#define ISC01 1
#define MCUSR POLARI_R8(0x54)
#define WDRF 3
/* Timer0 / Timer1 / Timer2 */
#define TCCR0A POLARI_R8(0x44)
#define TCCR0B POLARI_R8(0x45)
#define OCR0A POLARI_R8(0x47)
#define OCR0B POLARI_R8(0x48)
#define TCCR1A POLARI_R8(0x80)
#define TCCR1B POLARI_R8(0x81)
#define OCR1A POLARI_R16(0x88)
#define OCR1B POLARI_R16(0x8A)
#define TIMSK2 POLARI_R8(0x70)
#define TCCR2A POLARI_R8(0xB0)
#define TCCR2B POLARI_R8(0xB1)
#define OCR2A POLARI_R8(0xB3)
#define COM0A1 7
#define COM0B1 5
#define WGM01 1
#define WGM00 0
#define CS01 1
#define CS00 0
#define COM1A1 7
#define COM1B1 5
#define WGM10 0
#define WGM12 3
#define CS11 1
#define CS10 0
#define WGM21 1
#define CS22 2
#define CS20 0
#define OCIE2A 1
/* ADC */
#define ADC POLARI_R16(0x78)
#define ADCSRA POLARI_R8(0x7A)
#define ADMUX POLARI_R8(0x7C)
#define ADEN 7
#define ADSC 6
#define ADPS2 2
#define ADPS1 1
#define ADPS0 0
#define REFS0 6
/* USART0 */
#define UCSR0A POLARI_R8(0xC0)
#define UCSR0B POLARI_R8(0xC1)
#define UCSR0C POLARI_R8(0xC2)
#define UBRR0L POLARI_R8(0xC4)
#define UBRR0H POLARI_R8(0xC5)
#define UDR0 POLARI_R8(0xC6)
#define FE0 4
#define DOR0 3
#define UDRE0 5
#define U2X0 1
#define RXCIE0 7
#define RXEN0 4
#define TXEN0 3
#define UCSZ01 2
#define UCSZ00 1
#endif
