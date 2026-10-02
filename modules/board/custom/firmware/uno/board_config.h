/* board_config.h — the knobs of one UNO firmware build, rendered by `pol board gen` (board.custom.gen) from a
 * FirmwareVariant row (brd-fi). The template's copy carries the uno-sim-rig defaults; a generated project carries the
 * variant's values (also recorded in the FirmwareBuild row's repro block). */
#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

#define RIG_NAME     "uno-rig"   /* the class row's name — the Push match key of the row this board updates */
#define DEVICE_ID    3u          /* PolariPacket device_id (renode-rig is 2) */
#define USART_U2X    1           /* 1: UBRR0 = 16, +2.1 % (Optiboot / 16U2 compatible); 0: UBRR0 = 8, -3.5 % */
#define TELEMETRY_HZ 10u         /* frames per second, 1..50 */
#define FEATURE_LED  1
#define FEATURE_PWM  1
#define FEATURE_ADC  1
#define FEATURE_COMMANDS 1     /* 0: transmit only — no receiver, no RX ISR */
#define LED_PIN      13          /* Arduino digital pin 2..13 (D13 = the on-board LED) */
#define PWM_PIN      6           /* 5 | 6 (Timer0) | 9 | 10 (Timer1) */
#define ADC_CHANNEL  0           /* A0..A5 — the sim-rig sensor */
#define TEMP_TMP36   1           /* 1: temp_c = (mV - 500)/10 (TMP36); 0: temp_c = the raw ADC count */
#define BLINK_MS     0u          /* blink app: toggle period */
#define INSTANCE_INDEX 0u        /* brd-wire: this board's index among its bridge's bound instances (wire v2 prelude) */
#define SEND_NAME    1           /* 0: telemetry omits `name` (a bound board's identity is its binding) */

#endif /* BOARD_CONFIG_H */
