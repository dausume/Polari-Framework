/*
 * brd-1 firmware: the Arduino UNO R3 (ATmega328P, 16 MHz) as one Polari rig — PLAIN C on avr-libc (RULE 2: no
 * Arduino core, no sketch). The same fields and the same frame loop as the Renode twin
 * (grpcbridge/custom/renode_twin/firmware/main.c), so the existing bridge config works with serialDevice swapped.
 *
 * It speaks the universal PolariPacket over USART0 (the ATmega16U2's USB-CDC on a real UNO, a TCP→pty bridge on the
 * simavr twin) through the GENERATED simrigstate_packets.h, rendered with c_twin target=avr (avr-gcc's double is
 * 4 bytes; the header converts binary32↔binary64 in software, the wire is unchanged):
 *
 *   Up:   SimRigState telemetry at 10 Hz — uptime_ms from the Timer2 1 ms tick, temp_c from the TMP36 on A0,
 *         the actuator state, the status word ('boot' → 'ok' after 1 s → 'commanded').
 *   Down: SimRigState commands decode into a scratch struct; ONLY the actuator fields apply (led_on → PORTB5 = D13,
 *         pwm_duty → OCR0A on D6); identity and sensors stay the firmware's own; status becomes 'commanded' and the
 *         next frame carries it back up (the provable loop).
 *
 * Datasheet facts used here (DatasheetFact rows, board.custom.uno_facts):
 *   ATmega328P datasheet DS40002061B (Microchip 2020) — Table 20-7 p.199: 115.2 kBd at 16 MHz is UBRR0 = 16 with
 *     U2X0 = 1 (+2.1 %) or UBRR0 = 8 with U2X0 = 0 (-3.5 %); §24.7 p.256: ADC = Vin·1024/Vref.
 *     https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf
 *   TMP36 (Analog Devices TMP35/TMP36/TMP37 datasheet): 10 mV/°C, 750 mV at 25 °C → T = (mV − 500) / 10.
 *     https://www.analog.com/media/en/technical-documentation/data-sheets/TMP35_36_37.pdf
 */
#include <stdint.h>
#include <string.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>

#include "board_config.h"          /* knobs rendered by `pol board gen`: RIG_NAME, DEVICE_ID, USART_U2X */
#include "simrigstate_packets.h"   /* GENERATED (c_twin target=avr) — never edited by hand */

#if USART_U2X
#define UBRR0_VALUE 16u            /* U2X0 = 1: +2.1 % (what Optiboot and the 16U2 side use) */
#else
#define UBRR0_VALUE 8u             /* U2X0 = 0: -3.5 % (works on the twin; marginal against the 16U2) */
#endif
#define TELEMETRY_MS 100u          /* 10 Hz */
#define RX_RING 64u                /* power of two */

/* ---- USART0 RX: an ISR-fed ring, drained by the main loop into the header's resync-safe parser ---- */
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

static int rx_pop(uint8_t *b)
{
    if (rx_tail == rx_head) return 0;
    *b = rx_ring[rx_tail];
    rx_tail = (uint8_t)((rx_tail + 1u) & (RX_RING - 1u));
    return 1;
}

static void usart_init(void)
{
    UBRR0H = (uint8_t)(UBRR0_VALUE >> 8);
    UBRR0L = (uint8_t)UBRR0_VALUE;
#if USART_U2X
    UCSR0A = _BV(U2X0);
#else
    UCSR0A = 0;
#endif
    UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);               /* 8N1 */
    UCSR0B = _BV(RXEN0) | _BV(TXEN0) | _BV(RXCIE0);
}

static void usart_send(const uint8_t *b, size_t n)
{
    while (n--) {
        while (!(UCSR0A & _BV(UDRE0))) { }
        UDR0 = *b++;
    }
}

/* ---- Timer2: CTC, /128, OCR2A = 124 → 16 MHz / 128 / 125 = 1000 Hz ---- */
static volatile uint32_t g_ms;

ISR(TIMER2_COMPA_vect) { g_ms++; }

static void tick_init(void)
{
    TCCR2A = _BV(WGM21);
    TCCR2B = _BV(CS22) | _BV(CS20);                    /* clk/128 */
    OCR2A = 124u;
    TIMSK2 = _BV(OCIE2A);
}

static uint32_t millis_now(void)
{
    uint32_t v;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = g_ms; }
    return v;
}

/* ---- Timer0: fast PWM on OC0A = PD6 = D6, clk/64 (~976 Hz); pwm_duty is a percentage 0..100 ---- */
static void pwm_init(void)
{
    DDRD |= _BV(PD6);
    TCCR0A = _BV(COM0A1) | _BV(WGM01) | _BV(WGM00);
    TCCR0B = _BV(CS01) | _BV(CS00);
    OCR0A = 0u;
}

static int64_t pwm_apply(int64_t duty)
{
    if (duty < 0) duty = 0;
    if (duty > 100) duty = 100;
    OCR0A = (uint8_t)(((uint16_t)duty * 255u) / 100u);
    return duty;
}

/* ---- ADC channel 0, AVcc reference, clk/128 (125 kHz) ---- */
static void adc_init(void)
{
    ADMUX = _BV(REFS0);                                /* AVcc, channel 0, right-adjusted */
    ADCSRA = _BV(ADEN) | _BV(ADPS2) | _BV(ADPS1) | _BV(ADPS0);
}

static uint16_t adc_read0(void)
{
    ADCSRA |= _BV(ADSC);
    while (ADCSRA & _BV(ADSC)) { }
    return ADC;
}

/* the TMP36 on A0: mV = ADC·5000/1024 (AVcc = 5 V); °C = (mV − 500)/10 */
static polari_avr_double_t tmp36_c(uint16_t adc)
{
    polari_avr_double_t mv = (polari_avr_double_t)adc * (5000.0 / 1024.0);
    return (mv - 500.0) / 10.0;
}

static void led_apply(uint8_t on)
{
    if (on) PORTB |= _BV(PB5); else PORTB &= (uint8_t)~_BV(PB5);
}

/* static, so avr-size counts them (the RAM budget is measured, not guessed) */
static SimRigState_t state;
static polari_rx_t rx;
static uint8_t payload[SIMRIGSTATE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + SIMRIGSTATE_PAYLOAD_MAX + 4u];

static void apply_command(const uint8_t *p, uint16_t len)
{
    SimRigState_t cmd;
    if (SimRigState_decode(p, len, &cmd) != 0) return;
    state.led_on = cmd.led_on ? 1u : 0u;               /* ACTUATORS only */
    state.pwm_duty = pwm_apply(cmd.pwm_duty);
    led_apply(state.led_on);
    strcpy(state.status, "commanded");
}

int main(void)
{
    uint32_t seq = 0u, next_ms = 0u, now;
    uint8_t b;

    DDRB |= _BV(PB5);
    usart_init();
    tick_init();
    pwm_init();
    adc_init();
    memset(&state, 0, sizeof state);
    memset(&rx, 0, sizeof rx);
    strcpy(state.name, RIG_NAME);                      /* the Push match key upstream */
    strcpy(state.status, "boot");
    sei();

    for (;;) {
        while (rx_pop(&b))
            if (polari_rx_feed(&rx, b) && rx.msg_type == SIMRIGSTATE_MSG_TYPE)
                apply_command(rx.payload, rx.payload_len);

        now = millis_now();
        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        state.uptime_ms = (int64_t)now;
        state.temp_c = tmp36_c(adc_read0());
        if (state.status[0] == 'b' && now > 1000u) strcpy(state.status, "ok");
        usart_send(wire, polari_packet_encode(wire, SIMRIGSTATE_MSG_TYPE, DEVICE_ID, seq++,
                                              payload, SimRigState_encode(&state, payload)));
    }
}
