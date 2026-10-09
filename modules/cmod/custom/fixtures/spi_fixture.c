/*
 * spi_fixture.c — cmod fixture (ucd-0b2a §5h C / D-ucd-11): a plain avr-libc SPI init + a chip-select picker over
 * TWO devices, proving the widened TargetDefinition model yields MULTIPLE rows (two chip-selects) for one task, as
 * rows — never one kind for both. Parsed by cmod/custom/selftest_requirements.py standalone; never added to the
 * UNO firmware project or the seeded graph.
 */
#include <avr/io.h>
#include <stdint.h>

#ifndef POLARI_NODE
#define POLARI_NODE(...)
#endif

POLARI_NODE(spi_init, role("bring up the SPI controller as the bus controller, MSB first, clock/16"))
void spi_init(void)
{
    SPCR = _BV(6) | _BV(4);     /* SPE (enable) | MSTR (controller mode) */
    SPSR &= (uint8_t)~0x01u;    /* SPI2X off */
}

/* CS0_PIN / CS1_PIN are declared (uses()) — the scan sees no register touch naming a specific pin here (this
 * fixture's body never drives real hardware, by design: a real board binding ties each macro to a BoardPin and a
 * generator would emit the PORT/DDR writes); the annotation names the SELECTABLE intent only, exactly like the
 * review's "SPI with two chip-selects" test. */
POLARI_NODE(spi_select, in(cs, "", "0 or 1 — which device's chip-select line to drive low"), uses(CS0_PIN, CS1_PIN),
            role("drive the chosen device's chip-select line low, the other high"))
void spi_select(uint8_t cs)
{
    (void)cs;
}
