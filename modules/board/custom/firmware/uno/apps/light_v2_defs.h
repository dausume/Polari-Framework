/*
 * light_v2_defs.h - the light_v2.c app's own file-scope macros and globals (the frame encoder macro, the telemetry mask, the shared
 * wire buffer, the frame counter), kept in a header exactly like light_defs.h does for the v1 app. fgm-6a: the telemetry mask
 * leaves out command_id - that field is the HOST's command number going down; the board reports last_command_id instead.
 */
#ifndef LIGHT_V2_DEFS_H
#define LIGHT_V2_DEFS_H

#include <stdint.h>

#include "board_config.h"
#include "lightstatev2_packets.h"

#ifdef LIGHTSTATEV2_INDEX_WIDTH
#define TX_ENCODE(s, p, m) LightStateV2_encode((s), (p), INSTANCE_INDEX, (m))
#else
#define TX_ENCODE(s, p, m) LightStateV2_encode((s), (p), (m))
#endif

/* boot_session persists across resets in EEPROM address 0 (avr-libc eeprom_read_dword / eeprom_write_dword) */
#define EEPROM_BOOT_SESSION_ADDR ((uint32_t *)0x0000)

static uint8_t payload[LIGHTSTATEV2_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + LIGHTSTATEV2_PAYLOAD_MAX + 4u];
static uint32_t g_seq;   /* wire frame sequence */

/* what a report carries: every field the board owns (command_id is the host's, so it is never sent up) */
#define TELEMETRY_MASK ((LightStateV2_mask_t)(LIGHTSTATEV2_F_ALL & ~LIGHTSTATEV2_F_COMMAND_ID \
                                              & (SEND_NAME ? ~(LightStateV2_mask_t)0 : ~LIGHTSTATEV2_F_NAME)))

/* a command number is a u16 the sender picks: 1..65535 (0 = none) */
#define COMMAND_ID_MAX 65535

#endif /* LIGHT_V2_DEFS_H */
