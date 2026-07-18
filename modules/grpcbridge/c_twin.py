"""
@module grpcbridge.c_twin

grpc-j3 (first sliver, pulled forward for hwsim-1): generate the
firmware-side C header `<class>_packets.h` from the SAME contract
field_map the .proto and the Java codec came from — firmware, Java,
and Polari agree on the wire by construction.

Layout is the byte-exact twin of the generated Java PolariPacket +
<Class>Codec: 12-byte little-endian header (magic 0x504C u16 |
version=1 u8 | msg_type u8 | device_id u16 | sequence u32 |
payload_len u16), payload fields in TAG order (int64/double LE 8B,
bool 1B, strings u16-length-prefixed UTF-8), CRC32 (IEEE reflected)
over header+payload appended LE. Strings land in fixed char[64]
buffers on the MCU (truncated + NUL-terminated on decode) — the
nanopb-style bound that keeps this embeddable on the SAMD21 tier.

@consumers
  - grpcbridge.contract_api (GET /api/grpc/exposures/{class}/c-header)
  - grpcbridge/renode_twin firmware (hwsim-1)
  - grpcbridge.selftest_c_twin
"""

C_STR_MAX = 64

#: proto type -> (C type, fixed wire size; strings are variable)
C_TYPES = {
    'int64': ('int64_t', 8),
    'double': ('double', 8),
    'bool': ('uint8_t', 1),
    'string': (f'char[{C_STR_MAX}]', None),
    'bytes': (f'uint8_t[{C_STR_MAX}]', None),
}

#: Shared framing/CRC support, emitted once per translation unit
#: (guarded) so multi-class firmwares don't collide.
_COMMON = r'''#ifndef POLARI_PACKET_COMMON_H
#define POLARI_PACKET_COMMON_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define POLARI_MAGIC      0x504CU  /* wire bytes: 0x4C 0x50 */
#define POLARI_VERSION    1U
#define POLARI_HEADER_LEN 12U

/* CRC32 (IEEE reflected, poly 0xEDB88320) — identical to
 * java.util.zip.CRC32 and Python zlib.crc32. Bitwise (no table):
 * cycles are cheap at telemetry rates, flash is not. */
static uint32_t polari_crc32(const uint8_t *d, size_t n)
{
    uint32_t c = 0xFFFFFFFFu;
    size_t i;
    int k;
    for (i = 0; i < n; i++) {
        c ^= d[i];
        for (k = 0; k < 8; k++)
            c = (c >> 1) ^ (0xEDB88320u
                            & (uint32_t)(-(int32_t)(c & 1u)));
    }
    return ~c;
}

static void polari_put_u16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
}

static void polari_put_u32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;         p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

static uint16_t polari_get_u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t polari_get_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8)
         | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* Frame a payload into `out` (must hold POLARI_HEADER_LEN+len+4).
 * Returns the wire length. */
static size_t polari_packet_encode(uint8_t *out, uint8_t msg_type,
                                   uint16_t device_id, uint32_t seq,
                                   const uint8_t *payload,
                                   uint16_t len)
{
    polari_put_u16(out, POLARI_MAGIC);
    out[2] = POLARI_VERSION;
    out[3] = msg_type;
    polari_put_u16(out + 4, device_id);
    polari_put_u32(out + 6, seq);
    polari_put_u16(out + 10, len);
    memcpy(out + POLARI_HEADER_LEN, payload, len);
    polari_put_u32(out + POLARI_HEADER_LEN + len,
                   polari_crc32(out, POLARI_HEADER_LEN + len));
    return POLARI_HEADER_LEN + (size_t)len + 4u;
}

/* Incremental receive parser: feed one byte at a time; returns 1
 * when rx holds a complete CRC-valid packet (msg_type/payload/len
 * fields populated), 0 otherwise. Resync-safe: bad magic, oversize
 * or bad CRC restart the hunt. */
typedef struct {
    uint8_t buf[POLARI_HEADER_LEN + POLARI_RX_PAYLOAD_MAX + 4u];
    size_t have;
    uint16_t need_payload;
    uint8_t msg_type;
    uint16_t device_id;
    uint32_t sequence;
    const uint8_t *payload;
    uint16_t payload_len;
} polari_rx_t;

static int polari_rx_feed(polari_rx_t *rx, uint8_t b)
{
    if (rx->have == 0u) {
        if (b != (uint8_t)(POLARI_MAGIC & 0xFFu)) return 0;
    } else if (rx->have == 1u) {
        if (b != (uint8_t)(POLARI_MAGIC >> 8)) { rx->have = 0u; return 0; }
    }
    rx->buf[rx->have++] = b;
    if (rx->have == POLARI_HEADER_LEN) {
        if (rx->buf[2] != POLARI_VERSION) { rx->have = 0u; return 0; }
        rx->need_payload = polari_get_u16(rx->buf + 10);
        if (rx->need_payload > POLARI_RX_PAYLOAD_MAX) {
            rx->have = 0u;
            return 0;
        }
    }
    if (rx->have >= POLARI_HEADER_LEN
        && rx->have == POLARI_HEADER_LEN + (size_t)rx->need_payload + 4u) {
        size_t body = POLARI_HEADER_LEN + (size_t)rx->need_payload;
        uint32_t crc = polari_get_u32(rx->buf + body);
        rx->have = 0u;
        if (crc != polari_crc32(rx->buf, body)) return 0;
        rx->msg_type = rx->buf[3];
        rx->device_id = polari_get_u16(rx->buf + 4);
        rx->sequence = polari_get_u32(rx->buf + 6);
        rx->payload = rx->buf + POLARI_HEADER_LEN;
        rx->payload_len = rx->need_payload;
        return 1;
    }
    return 0;
}

#endif /* POLARI_PACKET_COMMON_H */'''


def _c_fields(field_map):
    """Fields in tag order as (name, proto_type, comment)."""
    fields = field_map.get('fields', {})
    return [(n, fields[n]['proto_type'], fields[n].get('comment', ''))
            for n in sorted(fields, key=lambda n: int(fields[n]['tag']))]


def payload_max(field_map):
    """Worst-case payload size for the RX buffer bound."""
    total = 0
    for _, ptype, _ in _c_fields(field_map):
        fixed = C_TYPES[ptype][1]
        total += fixed if fixed is not None else 2 + C_STR_MAX
    return total


def render_c_header(class_name, field_map, msg_type, version=0,
                    contract_hash=''):
    """The complete `<class>_packets.h`: struct (tag order) + encode
    + decode, on top of the shared framing block."""
    upper = class_name.upper()
    struct_lines = []
    enc_lines = []
    dec_lines = []
    for name, ptype, comment in _c_fields(field_map):
        note = f'  /* {comment} */' if comment else ''
        ctype, fixed = C_TYPES[ptype]
        if '[' in ctype:
            base = ctype.split('[')[0]
            struct_lines.append(
                f'    {base} {name}[{C_STR_MAX}];{note}')
        else:
            struct_lines.append(f'    {ctype} {name};{note}')
        if ptype == 'int64':
            enc_lines.append(
                f'    polari_put_u32(p, (uint32_t)s->{name});\n'
                f'    polari_put_u32(p + 4, '
                f'(uint32_t)((uint64_t)s->{name} >> 32)); p += 8;')
            dec_lines.append(
                f'    if (end - p < 8) return -1;\n'
                f'    s->{name} = (int64_t)((uint64_t)'
                f'polari_get_u32(p)\n'
                f'        | ((uint64_t)polari_get_u32(p + 4) << 32));'
                f' p += 8;')
        elif ptype == 'double':
            enc_lines.append(
                f'    memcpy(p, &s->{name}, 8); p += 8;'
                '  /* LE host assumed (Cortex-M / x86) */')
            dec_lines.append(
                f'    if (end - p < 8) return -1;\n'
                f'    memcpy(&s->{name}, p, 8); p += 8;')
        elif ptype == 'bool':
            enc_lines.append(f'    *p++ = s->{name} ? 1u : 0u;')
            dec_lines.append(
                f'    if (end - p < 1) return -1;\n'
                f'    s->{name} = (*p++ != 0u);')
        else:  # string / bytes: u16 length prefix
            enc_lines.append(
                f'    n = (uint16_t)strlen(s->{name});\n'
                f'    polari_put_u16(p, n); p += 2;\n'
                f'    memcpy(p, s->{name}, n); p += n;')
            dec_lines.append(
                f'    if (end - p < 2) return -1;\n'
                f'    n = polari_get_u16(p); p += 2;\n'
                f'    if (end - p < n) return -1;\n'
                f'    cp = n < {C_STR_MAX - 1}u ? n : {C_STR_MAX - 1}u;'
                '  /* bounded: SAMD21-tier honest truncation */\n'
                f'    memcpy(s->{name}, p, cp); '
                f's->{name}[cp] = 0; p += n;')
    nl = '\n'
    return f'''/* Generated by Polari grpcbridge.c_twin (grpc-j3) — do not edit.
 * class: {class_name}   contract v{version}   hash {contract_hash}
 * Byte-exact twin of the Java {class_name}Codec / PolariPacket:
 * regenerate when the contract regenerates. */
#ifndef {upper}_PACKETS_H
#define {upper}_PACKETS_H

#ifndef POLARI_RX_PAYLOAD_MAX
#define POLARI_RX_PAYLOAD_MAX {payload_max(field_map)}u
#endif

{_COMMON}

#define {upper}_MSG_TYPE {int(msg_type)}u
#define {upper}_PAYLOAD_MAX {payload_max(field_map)}u

typedef struct {{
{nl.join(struct_lines)}
}} {class_name}_t;

/* struct -> payload bytes (tag order). Returns payload length. */
static uint16_t {class_name}_encode(const {class_name}_t *s,
                                    uint8_t *p)
{{
    uint8_t *start = p;
    uint16_t n;
    (void)n;
{nl.join(enc_lines)}
    return (uint16_t)(p - start);
}}

/* payload bytes -> struct. Returns 0, or -1 on truncated input. */
static int {class_name}_decode(const uint8_t *p, uint16_t len,
                               {class_name}_t *s)
{{
    const uint8_t *end = p + len;
    uint16_t n, cp;
    (void)n; (void)cp;
{nl.join(dec_lines)}
    return 0;
}}

#endif /* {upper}_PACKETS_H */
'''
