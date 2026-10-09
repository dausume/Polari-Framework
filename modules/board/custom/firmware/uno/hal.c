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
#ifndef RX_RING
#define RX_RING 64u                /* power of two; a variant may set it (build flag RX_RING=N) */
#endif
/* sc-0 (FIRMWARE_SCENARIO_PLAN.md §3, scenario 1b): rx_head / rx_tail are uint8_t — ONE `lds` each, so the ISR and
 * the main loop can never see half an index. A ring past 256 slots would need 16-bit indices (two loads: a torn
 * head) and, with these uint8_t indices, would silently use 256 of its slots. Refuse that build instead (the
 * Technique `static-guard`): the fault becomes a compile error, not a runtime race. */
_Static_assert(RX_RING >= 2u && RX_RING <= 256u && (RX_RING & (RX_RING - 1u)) == 0u,
               "RX_RING must be a power of two in 2..256: rx_head/rx_tail are uint8_t (one lds each, so they cannot tear)");

/* ---- USART0 RX: an ISR-fed ring, drained by the main loop into the header's resync-safe parser. A variant with no
 * command path (FEATURE_COMMANDS 0) never enables the receiver: no ISR, no ring — smaller, and nothing a host sends
 * can disturb it. ---- */
#if FEATURE_COMMANDS
static volatile uint8_t rx_ring[RX_RING];
static volatile uint8_t rx_head, rx_tail;

#if HAL_UART_ERRCOUNT
/* sc-1 (FIRMWARE_SCENARIO_PLAN.md §3a, scenario 4): the USART's own error bits, which no shipped variant reads. FE0
 * (the stop bit was 0) and DOR0 (a byte arrived while UDR0 was full) are valid only BEFORE UDR0 is read
 * (DS40002061B §20.11.2), so the status is read first; a full ring drop is counted too. The byte is still queued:
 * the parser's CRC + resync decides. Counters, never a policy. */
static volatile uint16_t g_uart_fe, g_uart_dor, g_rx_dropped;

ISR(USART_RX_vect)
{
    uint8_t st = UCSR0A;
    uint8_t b = UDR0, next = (uint8_t)((rx_head + 1u) & (RX_RING - 1u));
    if (st & _BV(FE0)) g_uart_fe++;
    if (st & _BV(DOR0)) g_uart_dor++;
    if (next != rx_tail) {
        rx_ring[rx_head] = b;
        rx_head = next;
    } else {
        g_rx_dropped++;
    }
}

uint16_t hal_uart_errors(uint8_t which)
{
    uint16_t v;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = which == 0 ? g_uart_fe : which == 1 ? g_uart_dor : g_rx_dropped; }
    return v;
}
#else
ISR(USART_RX_vect)
{
    uint8_t b = UDR0, next = (uint8_t)((rx_head + 1u) & (RX_RING - 1u));
    if (next != rx_tail) {         /* full: the byte is dropped; the parser's CRC + resync recovers */
        rx_ring[rx_head] = b;
        rx_head = next;
    }
}
#endif

POLARI_NODE(hal_rx_pop, out(b, "byte", "the oldest received byte, when one is waiting"),
            out(return, "flag", "1 = a byte was popped, 0 = the ring is empty"), uses(USART0),
            role("pop one byte from the USART0 RX ring the RX ISR fills"))
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

POLARI_NODE(hal_usart_send, in(b, "bytes", "the frame to send"), in(n, "B", "how many bytes"),
            role("send n bytes on USART0, blocking on UDRE0 per byte (115200 8N1)"))
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

/* g_ms is FOUR bytes the tick ISR writes; reading it is four `lds`. The atomic block masks interrupts across them
 * (+6 B, +3 cycles). HAL_MILLIS_ATOMIC 0 is the scenario variant uno-sim-rig-torn (sc-0, FIRMWARE_SCENARIO_PLAN.md
 * §3): the bare read, which a tick landing between the loads TEARS (0x000000FF reads back as 0x000001FF = 511). It
 * exists only so the fault can be forced and shown on the twin — never ship it. */
#ifndef HAL_MILLIS_ATOMIC
#define HAL_MILLIS_ATOMIC 1
#endif

POLARI_NODE(hal_millis, out(return, "ms", "milliseconds since hal_tick_init, from the Timer2 1 ms tick"),
            role("read the 1 ms tick counter (4 bytes the tick ISR writes, read inside an atomic block)"))
uint32_t hal_millis(void)
{
    uint32_t v;
#if HAL_MILLIS_ATOMIC
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = g_ms; }
#else
    v = g_ms;
#endif
    return v;
}

/* ---- sc-1 scenario 3: a button on D2 = INT0 (falling edge, pull-up). HAL_INT0_DEBOUNCE_MS 0 counts EVERY edge (the
 * BEFORE build: a ringing contact gives two edges, two counts); > 0 ignores edges within that many ms of the last one
 * it counted (the Technique `debounce`). g_ms is read bare inside the ISR: interrupts are off there, so its four loads
 * cannot be split by the tick. ---- */
#if HAL_INT0
static volatile uint16_t g_presses;
static volatile uint8_t g_toggle_pending;   /* ucd-0e2: set by the ISR, consumed (cleared) by hal_take_toggle_pending */
#if HAL_INT0_DEBOUNCE_MS
static uint32_t g_last_press;
static uint8_t g_pressed_once;
#endif

ISR(INT0_vect)
{
#if HAL_INT0_DEBOUNCE_MS
    uint32_t now = g_ms;
    if (g_pressed_once && (uint32_t)(now - g_last_press) < (uint32_t)HAL_INT0_DEBOUNCE_MS) return;
    g_pressed_once = 1u;
    g_last_press = now;
#endif
    g_presses++;
    g_toggle_pending = 1u;   /* ucd-0e2 (button_clock.c led_toggle): the ISR only counts + marks; no other work here */
}

void hal_button_init(void)
{
#ifndef POLARI_PIN_CONFIG
    /* a GENERATED pin_config_init() (cmod.custom.pin_config_gen) owns these DDRD/PORTD/EICRA/EIFR/EIMSK writes when
     * POLARI_PIN_CONFIG is defined (ucd-0b) — the two never both run. EICRA/EIMSK are read-modify-write: D3's sense
     * atom (HAL_INT1, below) shares both registers (EICRA's ISC1x bits, EIMSK's INT1 bit) and may init either first. */
    DDRD &= (uint8_t)~_BV(PD2);
    PORTD |= _BV(PD2);                                 /* pull-up: the button pulls D2 to ground */
    EICRA = (uint8_t)((EICRA & (uint8_t)~(_BV(ISC01) | _BV(ISC00))) | _BV(ISC01));   /* falling edge, ISC1x untouched */
    EIFR = _BV(INTF0);                                 /* w1c: clears only INTF0 (DS40002061B §13.2.5) */
    EIMSK |= _BV(INT0);                                 /* OR, not assign: INT1 may already be enabled (HAL_INT1) */
#endif
}

POLARI_NODE(hal_presses, out(return, "count", "D2 debounced press count since boot"), uses(BUTTON_PIN),
            role("atomic read of the INT0 press counter"))
uint16_t hal_presses(void)
{
    uint16_t v;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = g_presses; }
    return v;
}

uint8_t hal_take_toggle_pending(void)
{
    uint8_t v;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = g_toggle_pending; g_toggle_pending = 0u; }
    return v;
}
#endif

/* ---- ucd-0e2: the sense pin, D3 = INT1, ANY edge (ISC11:ISC10 = 01 — DS40002061B §13.2.1 p.80, Table 13-1) — the
 * independent witness that the LED line (wired D6->D3 on the bench/twin) really switched. The ISR ONLY counts and
 * stamps (reads g_ms bare: interrupts are off inside an ISR, so its four loads cannot be split by the tick); emitting
 * sense_rise/sense_fall ButtonClockEvents is the main loop's job (button_clock.c), never the ISR's. ---- */
#if HAL_INT1
static volatile uint16_t g_sense_rises, g_sense_falls;
static volatile uint32_t g_last_edge_ms;

ISR(INT1_vect)
{
    uint8_t level = (PIND & _BV(PD3)) != 0u;
    g_last_edge_ms = g_ms;
    if (level) g_sense_rises++; else g_sense_falls++;
}

void hal_sense_init(void)
{
#ifndef POLARI_PIN_CONFIG
    DDRD &= (uint8_t)~_BV(PD3);                        /* D3 input (the wired/witness pin, never driven by this build) */
    EICRA = (uint8_t)((EICRA & (uint8_t)~(_BV(ISC11) | _BV(ISC10))) | _BV(ISC10));   /* ISC11:10 = 01: any logical change */
    EIFR = _BV(INTF1);                                 /* w1c: clears only INTF1 */
    EIMSK |= _BV(INT1);                                 /* OR, not assign: INT0 may already be enabled (HAL_INT0) */
#endif
}

POLARI_NODE(hal_sense_read, out(rises, "count", "D3 rising edges seen since boot"),
            out(falls, "count", "D3 falling edges seen since boot"), out(last_ms, "ms", "hal_millis() at the last edge"),
            uses(SENSE_PIN), role("atomic snapshot of the INT1 edge counters + the last edge's timestamp"))
void hal_sense_read(uint16_t *rises, uint16_t *falls, uint32_t *last_ms)
{
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { *rises = g_sense_rises; *falls = g_sense_falls; *last_ms = g_last_edge_ms; }
}
#endif

/* ---- sc-1 (plan §4): the watchdog. After a watchdog reset WDRF stays set and the WDT stays ON at its shortest period
 * (DS40002061B §10.9.2), so a firmware that does not clear both before main resets forever; .init3 runs before the
 * C runtime's .init4..9 and main. HAL_WDT 0 (every shipped variant) compiles none of this. ---- */
#if HAL_WDT
void hal_wdt_boot(void) __attribute__((naked, used, section(".init3")));
void hal_wdt_boot(void)
{
    MCUSR = 0u;
    wdt_disable();
}
#endif

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

void hal_led_init(void)
{
#ifndef POLARI_PIN_CONFIG
    LED_DDR |= _BV(LED_BIT);   /* a GENERATED pin_config_init() owns this DDR write when POLARI_PIN_CONFIG is defined (ucd-0b) */
#endif
}

POLARI_NODE(hal_led, in(on, "bool", "0 = off, anything else = on"), uses(LED_PIN),
            role("set the LED on LED_PIN"))
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
#ifndef POLARI_PIN_CONFIG
    DDRD |= (PWM_PIN == 6) ? _BV(PD6) : _BV(PD5);   /* a GENERATED pin_config_init() owns this DDR write when POLARI_PIN_CONFIG is defined (ucd-0b) */
#endif
    TCCR0A = ((PWM_PIN == 6) ? _BV(COM0A1) : _BV(COM0B1)) | _BV(WGM01) | _BV(WGM00);
    TCCR0B = _BV(CS01) | _BV(CS00);                    /* clk/64 */
#else
#ifndef POLARI_PIN_CONFIG
    DDRB |= (PWM_PIN == 9) ? _BV(PB1) : _BV(PB2);   /* a GENERATED pin_config_init() owns this DDR write when POLARI_PIN_CONFIG is defined (ucd-0b) */
#endif
    TCCR1A = ((PWM_PIN == 9) ? _BV(COM1A1) : _BV(COM1B1)) | _BV(WGM10);   /* fast PWM 8-bit (mode 5) */
    TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);       /* clk/64 */
#endif
    PWM_OCR = 0u;
}

POLARI_NODE(hal_pwm_apply, in(duty, "%", "requested duty 0..100 (clamped)"), out(return, "%", "the duty applied"),
            uses(PWM_PIN), role("set the PWM duty on PWM_PIN (OCR = duty*255/100)"))
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

POLARI_NODE(hal_adc_read, in(channel, "", "A0..A5 (0..5)"), out(return, "count", "10-bit ADC = Vin*1024/Vref, 0..1023"),
            role("one blocking ADC conversion, AVcc reference"))
uint16_t hal_adc_read(uint8_t channel)
{
    ADMUX = (uint8_t)(_BV(REFS0) | (channel & 0x07u));
    ADCSRA |= _BV(ADSC);
    while (ADCSRA & _BV(ADSC)) { }
    return ADC;
}
#endif
