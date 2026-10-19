/* board_config.h — rendered by `pol board gen` (board.custom.gen) for variant uno-light-unsensed (app light); the knobs are
 * also in the FirmwareBuild row's repro block. */
#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

#define RIG_NAME     "uno-light-unsensed"
#define DEVICE_ID    3u
#define USART_U2X    1
#define TELEMETRY_HZ 10u
#define FEATURE_LED  1
#define FEATURE_PWM  0
#define FEATURE_ADC  0
#define FEATURE_COMMANDS 1
#define LED_PIN      6
#define PWM_PIN      6
#define ADC_CHANNEL  0
#define TEMP_TMP36   1
#define BLINK_MS     0u
#define SEND_NAME    1     /* 0: telemetry omits `name` (the binding is the identity) */
#define FEATURE_BUTTON 1
#define FEATURE_SENSE  0
#define HAL_INT0     1              /* ucd-0e2: the button atom (hal.c) */
#define HAL_INT0_DEBOUNCE_MS 30u
#define BUTTON_PIN   2
#define EVENT_QUEUE_LEN 16u

#endif /* BOARD_CONFIG_H */
