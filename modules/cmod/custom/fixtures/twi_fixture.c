/*
 * twi_fixture.c — cmod fixture (ucd-0b2a §5h C / D-ucd-11): a plain avr-libc TWI (I2C) init, annotated with the
 * same POLARI_NODE grammar the real UNO HAL uses — proving the widened TargetDefinition model on a bus with TWO
 * named pins (SDA, SCL), not just GPIO/UART/ADC. Parsed by cmod/custom/selftest_requirements.py standalone; never
 * added to the UNO firmware project or the seeded graph.
 */
#include <avr/io.h>
#include <stdint.h>

#ifndef POLARI_NODE
#define POLARI_NODE(...)
#endif

/* SDA_PIN / SCL_PIN are declared (uses()) because the scan cannot see WHICH physical pins a bare TWBR/TWSR/TWCR
 * touch implies (no RegisterField row for the TWI bit fields yet, board.custom.register_fields_atmega328p) — the
 * annotation names the two pins the atom needs; a real board binding ties each macro to a BoardPin. */
POLARI_NODE(twi_init, uses(SDA_PIN, SCL_PIN), role("bring up the TWI bus at its default bit rate"))
void twi_init(void)
{
    TWSR &= (uint8_t)~0x03u;   /* prescaler = 1 (TWPS1:0 = 00) */
    TWBR = 72u;                /* ~100 kHz SCL at 16 MHz F_CPU, TWPS = 0 */
    TWCR = _BV(2);             /* TWEN: enable the TWI hardware */
}
