/* board_config.h — rendered by `pol board gen` (board.custom.gen) for variant uno-sim-rig (app sim_rig); the knobs are
 * also in the FirmwareBuild row's repro block. */
#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

#define RIG_NAME     "uno-rig"
#define DEVICE_ID    3u
#define USART_U2X    1
#define TELEMETRY_HZ 10u
#define FEATURE_LED  1
#define FEATURE_PWM  1
#define FEATURE_ADC  1
#define FEATURE_COMMANDS 1
#define LED_PIN      13
#define PWM_PIN      6
#define ADC_CHANNEL  0
#define TEMP_TMP36   1
#define BLINK_MS     0u
#define SEND_NAME    1     /* 0: telemetry omits `name` (the binding is the identity) */

#endif /* BOARD_CONFIG_H */
