# The UNO firmware (brd-1) — plain C on avr-libc (RULE 2: no Arduino core). The SAME flags board.custom.build runs
# through the engines ladder (worker image prf-board-engines, or a local avr-gcc); the board selftest asserts they match.
#
#   make            # firmware.elf + firmware.hex + the avr-size line
#   make size
MCU   = atmega328p
F_CPU = 16000000UL
CC    = avr-gcc
CFLAGS = -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Os -std=gnu99 -Wall -Wextra -Werror -ffunction-sections -fdata-sections
LDFLAGS = -Wl,--gc-sections

all: firmware.hex size

firmware.elf: main.c simrigstate_packets.h board_config.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ main.c

firmware.hex: firmware.elf
	avr-objcopy -O ihex -R .eeprom $< $@

size: firmware.elf
	avr-size -A firmware.elf

clean:
	rm -f firmware.elf firmware.hex

.PHONY: all size clean
