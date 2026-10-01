/*
 * hal.h — the UNO's peripherals for every firmware variant (brd-fi): USART0 + its RX ring, the Timer2 1 ms tick, the
 * LED pin, one PWM pin, the ADC. PLAIN C on avr-libc (RULE 2). Which of them exist in a build is decided by the
 * variant's FEATURE_* knobs in board_config.h (rendered by `pol board gen uno --variant <name>`); an unused
 * peripheral is not compiled at all, so a smaller variant is a smaller .hex.
 *
 * Datasheet facts (DatasheetFact rows, board.custom.uno_facts): ATmega328P DS40002061B — Table 20-7 p.199 (115.2 kBd at
 * 16 MHz: UBRR0 = 16 with U2X0, +2.1 %; UBRR0 = 8 without, -3.5 %); §24.7 p.256 (ADC = Vin·1024/Vref).
 */
#ifndef POLARI_UNO_HAL_H
#define POLARI_UNO_HAL_H

#include <stddef.h>
#include <stdint.h>

#include "board_config.h"

#ifndef FEATURE_LED
#define FEATURE_LED 0
#endif
#ifndef FEATURE_PWM
#define FEATURE_PWM 0
#endif
#ifndef FEATURE_ADC
#define FEATURE_ADC 0
#endif
#ifndef FEATURE_COMMANDS
#define FEATURE_COMMANDS 1
#endif

#define TELEMETRY_MS (1000u / TELEMETRY_HZ)

void hal_usart_init(void);
#if FEATURE_COMMANDS
int hal_rx_pop(uint8_t *b);
#endif
void hal_usart_send(const uint8_t *b, size_t n);

void hal_tick_init(void);
uint32_t hal_millis(void);

#if FEATURE_LED
void hal_led_init(void);
void hal_led(uint8_t on);
#endif

#if FEATURE_PWM
void hal_pwm_init(void);
int64_t hal_pwm_apply(int64_t duty);   /* percentage 0..100, clamped; returns what was applied */
#endif

#if FEATURE_ADC
void hal_adc_init(void);
uint16_t hal_adc_read(uint8_t channel);   /* 0..5 = A0..A5, AVcc reference, 10-bit */
#endif

#endif /* POLARI_UNO_HAL_H */
