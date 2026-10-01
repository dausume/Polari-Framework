/*
 * hal.c — the UNO's peripherals (brd-fi; the brd-1 code split out of main.c so every variant shares it). See hal.h.
 * Pins are Arduino digital pin numbers (the silkscreen): D0..D7 = PORTD bit n, D8..D13 = PORTB bit n-8. D0/D1 are
 * USART0 and refused by `pol board gen`; PWM is OC0A (D6), OC0B (D5), OC1A (D9) or OC1B (D10) — D3/D11 are Timer2's,
 * which is the 1 ms tick.
 */
#include <avr/interrupt.h>
#include <avr/io.h>
#include <util/atomic.h>

#include "hal.h"

#if USART_U2X
#define UBRR0_VALUE 16u            /* U2X0 = 1: +2.1 % (what Optiboot and the 16U2 side use) */
#else
#define UBRR0_VALUE 8u             /* U2X0 = 0: -3.5 % (works on the twin; marginal against the 16U2) */
#endif
#define RX_RING 64u                /* power of two */

/* ---- USART0 RX: an ISR-fed ring, drained by the main loop into the header's resync-safe parser. A variant with no
 * command path (FEATURE_COMMANDS 0) never enables the receiver: no ISR, no ring — smaller, and nothing a host sends
 * can disturb it. ---- */
#if FEATURE_COMMANDS
static volatile uint8_t rx_ring[RX_RING];
static volatile uint8_t rx_head, rx_tail;

ISR(USART_RX_vect)
{
    uint8_t b = UDR0, next = (uint8_t)((rx_head + 1u) & (RX_RING - 1u));
    if (next != rx_tail) {         /* full: the byte is dropped; the parser's CRC + resync recovers */
        rx_ring[rx_head] = b;
        rx_head = next;
    }
}

int hal_rx_pop(uint8_t *b)
{
    if (rx_tail == rx_head) return 0;
    *b = rx_ring[rx_tail];
    rx_tail = (uint8_t)((rx_tail + 1u) & (RX_RING - 1u));
    return 1;
}
#endif

void hal_usart_init(void)
{
    UBRR0H = (uint8_t)(UBRR0_VALUE >> 8);
    UBRR0L = (uint8_t)UBRR0_VALUE;
#if USART_U2X
    UCSR0A = _BV(U2X0);
#else
    UCSR0A = 0;
#endif
    UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);               /* 8N1 */
#if FEATURE_COMMANDS
    UCSR0B = _BV(RXEN0) | _BV(TXEN0) | _BV(RXCIE0);
#else
    UCSR0B = _BV(TXEN0);                               /* transmit only */
#endif
}

void hal_usart_send(const uint8_t *b, size_t n)
{
    while (n--) {
        while (!(UCSR0A & _BV(UDRE0))) { }
        UDR0 = *b++;
    }
}

/* ---- Timer2: CTC, /128, OCR2A = 124 → 16 MHz / 128 / 125 = 1000 Hz ---- */
static volatile uint32_t g_ms;

ISR(TIMER2_COMPA_vect) { g_ms++; }

void hal_tick_init(void)
{
    TCCR2A = _BV(WGM21);
    TCCR2B = _BV(CS22) | _BV(CS20);                    /* clk/128 */
    OCR2A = 124u;
    TIMSK2 = _BV(OCIE2A);
}

uint32_t hal_millis(void)
{
    uint32_t v;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = g_ms; }
    return v;
}

/* ---- the LED on LED_PIN ---- */
#if FEATURE_LED
#if LED_PIN < 8
#define LED_PORT PORTD
#define LED_DDR  DDRD
#define LED_BIT  (LED_PIN)
#else
#define LED_PORT PORTB
#define LED_DDR  DDRB
#define LED_BIT  ((LED_PIN) - 8)
#endif

void hal_led_init(void) { LED_DDR |= _BV(LED_BIT); }

void hal_led(uint8_t on)
{
    if (on) LED_PORT |= _BV(LED_BIT); else LED_PORT &= (uint8_t)~_BV(LED_BIT);
}
#endif

/* ---- PWM on PWM_PIN (~976 Hz on Timer0, ~976 Hz 8-bit fast PWM on Timer1), duty a percentage 0..100 ---- */
#if FEATURE_PWM
#if PWM_PIN == 6
#define PWM_OCR OCR0A
#elif PWM_PIN == 5
#define PWM_OCR OCR0B
#elif PWM_PIN == 9
#define PWM_OCR OCR1A
#elif PWM_PIN == 10
#define PWM_OCR OCR1B
#else
#error "PWM_PIN must be 5, 6 (Timer0) or 9, 10 (Timer1) — D3/D11 belong to Timer2, the 1 ms tick"
#endif

void hal_pwm_init(void)
{
#if PWM_PIN == 6 || PWM_PIN == 5
    DDRD |= (PWM_PIN == 6) ? _BV(PD6) : _BV(PD5);
    TCCR0A = ((PWM_PIN == 6) ? _BV(COM0A1) : _BV(COM0B1)) | _BV(WGM01) | _BV(WGM00);
    TCCR0B = _BV(CS01) | _BV(CS00);                    /* clk/64 */
#else
    DDRB |= (PWM_PIN == 9) ? _BV(PB1) : _BV(PB2);
    TCCR1A = ((PWM_PIN == 9) ? _BV(COM1A1) : _BV(COM1B1)) | _BV(WGM10);   /* fast PWM 8-bit (mode 5) */
    TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);       /* clk/64 */
#endif
    PWM_OCR = 0u;
}

int64_t hal_pwm_apply(int64_t duty)
{
    if (duty < 0) duty = 0;
    if (duty > 100) duty = 100;
    PWM_OCR = (uint8_t)(((uint16_t)duty * 255u) / 100u);
    return duty;
}
#endif

/* ---- ADC, AVcc reference, clk/128 (125 kHz) ---- */
#if FEATURE_ADC
void hal_adc_init(void)
{
    ADMUX = _BV(REFS0);                                /* AVcc, channel 0, right-adjusted */
    ADCSRA = _BV(ADEN) | _BV(ADPS2) | _BV(ADPS1) | _BV(ADPS0);
}

uint16_t hal_adc_read(uint8_t channel)
{
    ADMUX = (uint8_t)(_BV(REFS0) | (channel & 0x07u));
    ADCSRA |= _BV(ADSC);
    while (ADCSRA & _BV(ADSC)) { }
    return ADC;
}
#endif
