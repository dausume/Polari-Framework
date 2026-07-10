/*
 * hwsim-1 firmware: the Renode MCU twin of one Polari rig.
 *
 * Bare-metal STM32F4 (Cortex-M4, default 16 MHz HSI). Speaks the
 * universal PolariPacket over USART2 — the SAME wire the Polari
 * Hardware Bridge's SerialCdcPort reads — via the GENERATED
 * simrigstate_packets.h (fetched per-class from
 * /api/grpc/exposures/SimRigState/c-header at build time: the
 * firmware knows ONLY the one class it needs to know).
 *
 * Up:   SimRigState telemetry ~10 Hz (uptime, triangle-wave temp,
 *       actuator state, status word).
 * Down: command packets decode into the same struct; firmware applies
 *       ACTUATOR fields only (pwm_duty, led_on) — identity and
 *       sensors stay its own — and reports status "commanded", which
 *       the next telemetry frames carry back up (the provable loop).
 */

#include <stdint.h>
#include <string.h>

/* Big enough for every class this rig speaks (headers each derive
 * their own bound; the shared rx parser needs the max). */
#define POLARI_RX_PAYLOAD_MAX 256u

#include "simrigstate_packets.h"
#include "fpgaregisterstate_packets.h"
#include "ledmatrix4x4state_packets.h"
/* hwsim-3: the FPGA register map twin — offsets generated from the
 * SAME RegisterDefinition rows the Verilog came from. */
#include "hardware_runtime_regs.h"

/* ---- STM32F4 registers (only what this firmware needs) ---------- */
#define REG(a) (*(volatile uint32_t *)(a))

#define RCC_AHB1ENR   REG(0x40023830u)   /* GPIOAEN = bit 0  */
#define RCC_APB1ENR   REG(0x40023840u)   /* USART2EN = bit 17 */

#define GPIOA_MODER   REG(0x40020000u)
#define GPIOA_AFRL    REG(0x40020020u)

#define USART2_SR     REG(0x40004400u)
#define USART2_DR     REG(0x40004404u)
#define USART2_BRR    REG(0x40004408u)
#define USART2_CR1    REG(0x4000440Cu)

#define USART_SR_RXNE (1u << 5)
#define USART_SR_TXE  (1u << 7)

#define SYST_CSR      REG(0xE000E010u)   /* COUNTFLAG = bit 16 */
#define SYST_RVR      REG(0xE000E014u)
#define SYST_CVR      REG(0xE000E018u)

#define DEVICE_ID     2u                 /* renode-rig */

static void uart_init(void)
{
    RCC_AHB1ENR |= 1u;                       /* GPIOA clock */
    RCC_APB1ENR |= (1u << 17);               /* USART2 clock */
    /* PA2/PA3 -> AF7 (USART2 TX/RX) */
    GPIOA_MODER = (GPIOA_MODER & ~0x000000F0u) | 0x000000A0u;
    GPIOA_AFRL  = (GPIOA_AFRL  & ~0x0000FF00u) | 0x00007700u;
    USART2_BRR = 0x8Bu;                      /* 115200 @ 16 MHz */
    USART2_CR1 = (1u << 13) | (1u << 3) | (1u << 2); /* UE|TE|RE */
}

static void uart_send(const uint8_t *b, size_t n)
{
    size_t i;
    for (i = 0; i < n; i++) {
        while (!(USART2_SR & USART_SR_TXE)) { }
        USART2_DR = b[i];
    }
}

static int uart_recv(uint8_t *b)
{
    if (USART2_SR & USART_SR_RXNE) {
        *b = (uint8_t)USART2_DR;
        return 1;
    }
    return 0;
}

/* Millisecond tick: SysTick free-runs at 1 kHz; COUNTFLAG polls
 * clear-on-read, so the main loop just accumulates. */
static uint32_t g_ms;

static void tick_init(void)
{
    SYST_RVR = 16000u - 1u;   /* 16 MHz / 1000 */
    SYST_CVR = 0u;
    SYST_CSR = 5u;            /* enable | processor clock */
}

static void tick_poll(void)
{
    if (SYST_CSR & (1u << 16)) g_ms++;
}

int main(void)
{
    SimRigState_t state;
    FpgaRegisterState_t fstate;
    LedMatrix4x4State_t led;
    uint32_t led_ram = 0u;   /* the MCU-driver grid state */
    uint8_t fpga_present;
    polari_rx_t rx;
    uint8_t payload[POLARI_RX_PAYLOAD_MAX];
    uint8_t wire[POLARI_HEADER_LEN + POLARI_RX_PAYLOAD_MAX + 4u];
    uint32_t seq = 0u, next_ms = 0u, phase;

    uart_init();
    tick_init();

    memset(&state, 0, sizeof state);
    memset(&fstate, 0, sizeof fstate);
    memset(&rx, 0, sizeof rx);
    strcpy(state.name, "renode-rig");   /* Push match key upstream */
    strcpy(state.status, "boot");
    state.led_on = 0u;
    strcpy(fstate.name, "renode-rig-fpga");
    memset(&led, 0, sizeof led);
    strcpy(led.name, "renode-led-grid");
    strcpy(led.driver, "mcu");
    led.width = 4; led.height = 4;
    /* Probe once: an absent FPGA (mcu-only scene) reads 0 — the rig
     * then honestly skips FPGA telemetry and refuses driver=fpga. */
    fpga_present = (FPGA_REG(FPGA_DEVICE_ID_OFFSET)
                    == FPGA_DEVICE_ID_VALUE);

    for (;;) {
        uint8_t b;
        tick_poll();

        /* Down: apply commands (actuators only; identity + sensors
         * remain the firmware's own truth). */
        while (uart_recv(&b)) {
            if (!polari_rx_feed(&rx, b))
                continue;
            if (rx.msg_type == SIMRIGSTATE_MSG_TYPE) {
                SimRigState_t cmd;
                if (SimRigState_decode(rx.payload, rx.payload_len,
                                       &cmd) == 0) {
                    state.pwm_duty = cmd.pwm_duty;
                    state.led_on = cmd.led_on;  /* real 1-byte bool */
                    strcpy(state.status, "commanded");
                }
            } else if (rx.msg_type == LEDMATRIX4X4STATE_MSG_TYPE) {
                /* THE OBJECT LIGHTS THE GRID: driver knob routes it
                 * through the FPGA register or the MCU's own RAM. */
                LedMatrix4x4State_t cmd;
                if (LedMatrix4x4State_decode(rx.payload,
                                             rx.payload_len,
                                             &cmd) == 0) {
                    if (cmd.driver[0])
                        strcpy(led.driver, cmd.driver);
                    if (!fpga_present)   /* no FPGA: mcu only, honest */
                        strcpy(led.driver, "mcu");
                    if (led.driver[0] == 'f') {
                        FPGA_REG(FPGA_LED_MATRIX_OFFSET) =
                            (uint32_t)cmd.pixels & 0xFFFFu;
                    } else {
                        led_ram = (uint32_t)cmd.pixels & 0xFFFFu;
                    }
                }
            } else if (rx.msg_type == FPGAREGISTERSTATE_MSG_TYPE) {
                /* Polari programs the FPGA: rw registers written
                 * straight into the (verilated) silicon; telemetry
                 * reads them back from the hardware, not from RAM. */
                FpgaRegisterState_t cmd;
                if (FpgaRegisterState_decode(rx.payload,
                                             rx.payload_len,
                                             &cmd) == 0) {
                    FPGA_REG(FPGA_COMMANDS_OFFSET) =
                        (uint32_t)cmd.commands;
                    FPGA_REG(FPGA_CONFIG_OFFSET) =
                        (uint32_t)cmd.config;
                    FPGA_REG(FPGA_MODE_MUX_OFFSET) =
                        (uint32_t)cmd.mode_mux;
                }
            }
        }

        /* Up: ~10 Hz telemetry. */
        if (g_ms >= next_ms) {
            next_ms += 100u;
            state.uptime_ms = (int64_t)g_ms;
            /* 20..30 C triangle wave, 20 s period, no libm */
            phase = (g_ms / 100u) % 200u;
            state.temp_c = 20.0
                + (double)(phase < 100u ? phase : 200u - phase) / 10.0;
            if (state.status[0] == 'b' && g_ms > 1000u)
                strcpy(state.status, "ok");
            uart_send(wire, polari_packet_encode(
                wire, SIMRIGSTATE_MSG_TYPE, DEVICE_ID, seq++,
                payload, SimRigState_encode(&state, payload)));

            /* LED grid: fpga driver reads pixels BACK FROM THE
             * SILICON (write-through proof); mcu driver from RAM. */
            led.pixels = (led.driver[0] == 'f' && fpga_present)
                ? (int64_t)(FPGA_REG(FPGA_LED_MATRIX_OFFSET)
                            & 0xFFFFu)
                : (int64_t)led_ram;
            uart_send(wire, polari_packet_encode(
                wire, LEDMATRIX4X4STATE_MSG_TYPE, DEVICE_ID, seq++,
                payload, LedMatrix4x4State_encode(&led, payload)));

            if (!fpga_present)
                continue;   /* mcu-only rig: no FPGA telemetry */

            /* The FPGA twin: every field read from the silicon —
             * rw values prove write-through, STATUS carries the
             * heartbeat + the MUX-selected input byte. */
            fstate.device_id =
                (int64_t)FPGA_REG(FPGA_DEVICE_ID_OFFSET);
            fstate.version =
                (int64_t)FPGA_REG(FPGA_VERSION_OFFSET);
            fstate.status = (int64_t)FPGA_REG(FPGA_STATUS_OFFSET);
            fstate.faults = (int64_t)FPGA_REG(FPGA_FAULTS_OFFSET);
            fstate.commands =
                (int64_t)FPGA_REG(FPGA_COMMANDS_OFFSET);
            fstate.config = (int64_t)FPGA_REG(FPGA_CONFIG_OFFSET);
            fstate.mode_mux =
                (int64_t)FPGA_REG(FPGA_MODE_MUX_OFFSET);
            uart_send(wire, polari_packet_encode(
                wire, FPGAREGISTERSTATE_MSG_TYPE, DEVICE_ID, seq++,
                payload, FpgaRegisterState_encode(&fstate, payload)));
        }
    }
}
