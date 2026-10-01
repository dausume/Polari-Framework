# The UNO firmware (brd-1; brd-fi: one project per VARIANT) — plain C on avr-libc (RULE 2: no Arduino core). The SAME
# flags board.custom.build runs through the engines ladder (worker image prf-board-engines, or a local avr-gcc); the
# board selftest asserts they match. A generated project holds main.c (the variant's app), hal.c/hal.h, board_config.h
# (the variant's knobs) and the generated <class>_packets.h.
#
#   make            # firmware.elf + firmware.hex + the avr-size line
#   make size
MCU   = atmega328p
F_CPU = 16000000UL
CC    = avr-gcc
CFLAGS = -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Os -std=gnu99 -Wall -Wextra -Werror -ffunction-sections -fdata-sections
LDFLAGS = -Wl,--gc-sections
SRCS = $(sort $(wildcard *.c))

all: firmware.hex size

firmware.elf: $(SRCS) $(wildcard *.h)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(SRCS)

firmware.hex: firmware.elf
	avr-objcopy -O ihex -R .eeprom $< $@

size: firmware.elf
	avr-size -A firmware.elf

clean:
	rm -f firmware.elf firmware.hex

.PHONY: all size clean
