/* avr/wdt.h — the formal/static tier's stand-in (sc-2b): the watchdog calls as no-ops with their argument kept. */
#ifndef POLARI_FORMAL_AVR_WDT_H
#define POLARI_FORMAL_AVR_WDT_H
#define WDTO_250MS 4
#define wdt_enable(p) ((void)(p))
#define wdt_reset() ((void)0)
#define wdt_disable() ((void)0)
#endif
