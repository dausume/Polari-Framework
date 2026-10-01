/* board_config.h — the knobs of one UNO firmware build, rendered by `pol board gen` (board.custom.gen).
 * The template's copy carries the defaults; a generated project carries the person's values (also recorded in the
 * FirmwareBuild row's repro block). */
#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

#define RIG_NAME  "uno-rig"   /* SimRigState.name — the Push match key of the row this board updates */
#define DEVICE_ID 3u          /* PolariPacket device_id (renode-rig is 2) */
#define USART_U2X 1           /* 1: UBRR0 = 16, +2.1 % (Optiboot / 16U2 compatible); 0: UBRR0 = 8, -3.5 % */

#endif /* BOARD_CONFIG_H */
