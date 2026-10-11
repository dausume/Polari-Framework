/*
 * light_defs.h — the light.c app's own file-scope macros and globals that its atoms use directly (the frame encoder
 * macro, the telemetry mask, the shared wire buffer, the frame counter). Kept in a header — not in light.c — for the
 * same reason button_clock_defs.h is: cmod.custom.glue copies an atom's function body verbatim and refuses one that
 * uses a macro the APP FILE defines itself, so everything the atoms touch lives here and compiles from headers alone.
 * `state` and `rx` are NOT here: light.c declares its own, and the generated glue declares its own under the same names.
 */
#ifndef LIGHT_DEFS_H
#define LIGHT_DEFS_H

#include <stdint.h>

#include "board_config.h"
#include "lightstate_packets.h"

/* the instance index exists ONLY when a bridge binds several boards of a class; the light test binds one */
#ifdef LIGHTSTATE_INDEX_WIDTH
#define TX_ENCODE(s, p, m) LightState_encode((s), (p), INSTANCE_INDEX, (m))
#else
#define TX_ENCODE(s, p, m) LightState_encode((s), (p), (m))
#endif

/* boot_session persists across resets in EEPROM address 0 (avr-libc eeprom_read_dword / eeprom_write_dword) */
#define EEPROM_BOOT_SESSION_ADDR ((uint32_t *)0x0000)

static uint8_t payload[LIGHTSTATE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + LIGHTSTATE_PAYLOAD_MAX + 4u];
static uint32_t g_seq;   /* wire frame sequence */

/* what telemetry carries: every field (led_on doubles as the command field, so it is simply included) */
#define TELEMETRY_MASK ((LightState_mask_t)(LIGHTSTATE_F_ALL & (SEND_NAME ? ~(LightState_mask_t)0 : ~LIGHTSTATE_F_NAME)))

#endif /* LIGHT_DEFS_H */
