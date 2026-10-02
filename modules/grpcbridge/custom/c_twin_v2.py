"""
@module grpcbridge.custom.c_twin_v2

grpc-j4 (his ruling 2026-10-02): the WIRE V2 firmware header — `<class>_packets.h` rendered from a wire spec
(grpcbridge.custom.wire_contract.spec): the same 12-byte header (version byte 2), then a packed prelude of
ceil((w + n) / 8) bytes — the instance index in w bits (0 for one instance, 1 for two, ceil(log2 n) otherwise) and one
presence bit per field in TAG order — then ONLY the present fields (enum fields one byte, 0 = the unknown slot).

The C API (every name prefixed by the class):
  <C>_t                      the struct — fields only, never an identifier of the hardware interface
  <C>_mask_t, <C>_F_<FIELD>  presence bits (tag order); <C>_F_ALL
  <C>_<FIELD>_<LABEL>        enum constants; <C>_<field>_name(v) the name table (unknown for 0 / out of range)
  <C>_index_t, <C>_WIRE_VERSION, <C>_INDEX_BYTES      the index representation (none / packed bits = v2, an explicit
                                             index byte = v3, a 16-bit index = v4 — wire_contract.index_repr)
  <C>_encode(s, p, index, present)          → payload length (prelude + the present fields); for ONE instance (n = 1)
                                             every index symbol is ELIDED (his ruling): <C>_encode(s, p, present),
                                             <C>_decode(p, len, s, &present), no <C>_index_t / _INDEX_* at all
  <C>_frame(out, device_id, seq, payload, len)  → the framed packet with the class's version byte + msg_type
  <C>_decode(p, len, s, &index, &present)   → 0 | -1 truncated; writes ONLY the present fields into s
  <C>_decode_rx(rx, s, &index, &present)    → as decode, -2 for a v1 frame (an old bridge's command is refused, never
                                               misread)
The shared block (guard POLARI_PACKET_V2_COMMON_H) accepts frame versions 1..4 and RESYNCS inside a rejected candidate
(brd-fi finding (3)): on a bad magic / version / oversize / CRC the parser keeps the bytes it holds and slides to the
next 0x4C inside them, instead of dropping them. Its function names equal the v1 block's on purpose: a v1 and a v2
class header in one translation unit fail to compile (one unit speaks one wire version).

`target=avr` as in c_twin (software binary32↔binary64 for double fields, AVR-clean comparisons). The v1 header
(c_twin.render_c_header without `wire`) is untouched — its sha is pinned.

@consumers
  - grpcbridge.custom.c_twin.render_c_header(…, wire=spec)
"""
from grpcbridge.custom.c_twin import C_STR_MAX, C_TYPES, _AVR_DOUBLE, _COMMON

#: the CRC + little-endian helpers of the v1 block, verbatim (one copy of the arithmetic)
_HELPERS = _COMMON[_COMMON.index('/* CRC32'):_COMMON.index('/* Frame a payload')].rstrip()

_COMMON_V2 = r'''#ifndef POLARI_PACKET_V2_COMMON_H
#define POLARI_PACKET_V2_COMMON_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define POLARI_MAGIC       0x504CU  /* wire bytes: 0x4C 0x50 */
#define POLARI_VERSION     2U       /* wire v2: payload = prelude (packed index + presence) + present fields */
#define POLARI_VERSION_MIN 1U       /* v1 frames still parse (an old firmware / bridge) */
#define POLARI_VERSION_MAX 4U       /* v3: an explicit index byte; v4: an explicit 16-bit index (grpc-j4) */
#define POLARI_HEADER_LEN  12U

__HELPERS__

/* Frame a payload into `out` (must hold POLARI_HEADER_LEN+len+4) with the given version byte. Returns the wire
 * length. A class header's <C>_frame() passes its own <C>_WIRE_VERSION. */
static size_t polari_packet_encode_v(uint8_t *out, uint8_t version, uint8_t msg_type,
                                     uint16_t device_id, uint32_t seq,
                                     const uint8_t *payload,
                                     uint16_t len)
{
    polari_put_u16(out, POLARI_MAGIC);
    out[2] = version;
    out[3] = msg_type;
    polari_put_u16(out + 4, device_id);
    polari_put_u32(out + 6, seq);
    polari_put_u16(out + 10, len);
    memcpy(out + POLARI_HEADER_LEN, payload, len);
    polari_put_u32(out + POLARI_HEADER_LEN + len,
                   polari_crc32(out, POLARI_HEADER_LEN + len));
    return POLARI_HEADER_LEN + (size_t)len + 4u;
}

typedef struct {
    uint8_t buf[POLARI_HEADER_LEN + POLARI_RX_PAYLOAD_MAX + 4u];
    size_t have;
    uint16_t need_payload;
    uint8_t version;
    uint8_t msg_type;
    uint16_t device_id;
    uint32_t sequence;
    const uint8_t *payload;
    uint16_t payload_len;
} polari_rx_t;

/* 1 = buf holds a complete CRC-valid frame, 0 = need more bytes, -1 = the candidate at buf[0] is no frame. */
static int polari_rx_check(polari_rx_t *rx)
{
    size_t total;
    if (rx->have >= 1u && rx->buf[0] != (uint8_t)(POLARI_MAGIC & 0xFFu)) return -1;
    if (rx->have >= 2u && rx->buf[1] != (uint8_t)(POLARI_MAGIC >> 8)) return -1;
    if (rx->have < POLARI_HEADER_LEN) return 0;
    if (rx->buf[2] < POLARI_VERSION_MIN || rx->buf[2] > POLARI_VERSION_MAX) return -1;
    rx->need_payload = polari_get_u16(rx->buf + 10);
    if (rx->need_payload > POLARI_RX_PAYLOAD_MAX) return -1;
    total = POLARI_HEADER_LEN + (size_t)rx->need_payload + 4u;
    if (rx->have < total) return 0;
    if (polari_get_u32(rx->buf + total - 4u) != polari_crc32(rx->buf, total - 4u)) return -1;
    return 1;
}

/* Feed one byte; returns 1 when rx holds a complete CRC-valid frame (version / msg_type / payload populated, valid
 * until the next feed). A rejected candidate is NOT thrown away: the parser slides to the next 0x4C among the bytes it
 * already holds and re-examines them, so a frame that starts inside garbage or inside a corrupted frame is kept. */
static int polari_rx_feed(polari_rx_t *rx, uint8_t b)
{
    size_t i;
    int r;
    rx->buf[rx->have++] = b;
    for (;;) {
        r = polari_rx_check(rx);
        if (r == 0) return 0;
        if (r == 1) {
            rx->version = rx->buf[2];
            rx->msg_type = rx->buf[3];
            rx->device_id = polari_get_u16(rx->buf + 4);
            rx->sequence = polari_get_u32(rx->buf + 6);
            rx->payload = rx->buf + POLARI_HEADER_LEN;
            rx->payload_len = rx->need_payload;
            rx->have = 0u;
            return 1;
        }
        for (i = 1u; i < rx->have && rx->buf[i] != (uint8_t)(POLARI_MAGIC & 0xFFu); i++) { }
        memmove(rx->buf, rx->buf + i, rx->have - i);
        rx->have -= i;
    }
}

#endif /* POLARI_PACKET_V2_COMMON_H */'''.replace('__HELPERS__', _HELPERS)


def _uint_for(bits):
    for t, n in (('uint8_t', 8), ('uint16_t', 16), ('uint32_t', 32)):
        if bits <= n:
            return t
    return 'uint64_t'


def _pre_type(bits):
    """The prelude accumulator: one byte, or a 32/64-bit word (never 16: AVR's int promotion would overflow)."""
    return 'uint8_t' if bits <= 8 else ('uint32_t' if bits <= 32 else 'uint64_t')


def _cid(text):
    return ''.join(ch if ch.isalnum() else '_' for ch in str(text)).upper()


def payload_max(s):
    total = s['prelude_bytes']
    for f in s['fields']:
        if f['enum']:
            total += 1
        else:
            fixed = C_TYPES[f['ptype']][1]
            total += fixed if fixed is not None else 2 + C_STR_MAX
    return total


def _field_code(cls, upper, f, avr):
    """(struct line, encode lines, decode lines) of one field; encode/decode guarded by its presence bit."""
    name, ptype, bit = f['name'], f['ptype'], '%s_F_%s' % (upper, _cid(f['name']))
    if f['enum']:
        return (f'    uint8_t {name};  /* enum: {upper}_{_cid(name)}_* (0 = {f["enum"]["unknown"]}) */',
                [f'    if (present & {bit}) {{ *p++ = s->{name}; }}'],
                [f'    if (m & {bit}) {{\n        if (end - p < 1) return -1;\n        s->{name} = *p++;\n    }}'])
    ctype, _ = C_TYPES[ptype]
    if avr and ptype == 'double':
        ctype = 'polari_avr_double_t'
    struct = (f'    {ctype.split("[")[0]} {name}[{C_STR_MAX}];' if '[' in ctype else f'    {ctype} {name};')
    if ptype == 'int64':
        enc = (f'    if (present & {bit}) {{\n        polari_put_u32(p, (uint32_t)s->{name});\n'
               f'        polari_put_u32(p + 4, (uint32_t)((uint64_t)s->{name} >> 32)); p += 8;\n    }}')
        dec = (f'    if (m & {bit}) {{\n        if (end - p < 8) return -1;\n'
               f'        s->{name} = (int64_t)((uint64_t)polari_get_u32(p) | ((uint64_t)polari_get_u32(p + 4) << 32)); p += 8;\n    }}')
    elif ptype == 'double' and avr:
        enc = (f'    if (present & {bit}) {{\n        polari_f32_to_f64(s->{name}, &lo, &hi);\n'
               f'        polari_put_u32(p, lo); polari_put_u32(p + 4, hi); p += 8;  /* binary32 -> binary64 (target avr) */\n    }}')
        dec = (f'    if (m & {bit}) {{\n        if (end - p < 8) return -1;\n'
               f'        s->{name} = polari_f64_to_f32(polari_get_u32(p), polari_get_u32(p + 4)); p += 8;\n    }}')
    elif ptype == 'double':
        enc = f'    if (present & {bit}) {{ memcpy(p, &s->{name}, 8); p += 8; }}  /* LE host assumed */'
        dec = (f'    if (m & {bit}) {{\n        if (end - p < 8) return -1;\n        memcpy(&s->{name}, p, 8); p += 8;\n    }}')
    elif ptype == 'bool':
        enc = f'    if (present & {bit}) {{ *p++ = s->{name} ? 1u : 0u; }}'
        dec = (f'    if (m & {bit}) {{\n        if (end - p < 1) return -1;\n        s->{name} = (*p++ != 0u);\n    }}')
    else:  # string / bytes: u16 length prefix, bounded on the MCU
        avail = '(uint16_t)(end - p)' if avr else 'end - p'
        enc = (f'    if (present & {bit}) {{\n        n = (uint16_t)strlen(s->{name});\n'
               f'        polari_put_u16(p, n); p += 2;\n        memcpy(p, s->{name}, n); p += n;\n    }}')
        dec = (f'    if (m & {bit}) {{\n        if (end - p < 2) return -1;\n        n = polari_get_u16(p); p += 2;\n'
               f'        if ({avail} < n) return -1;\n        cp = n < {C_STR_MAX - 1}u ? n : {C_STR_MAX - 1}u;\n'
               f'        memcpy(s->{name}, p, cp); s->{name}[cp] = 0; p += n;\n    }}')
    return struct, [enc], [dec]


def render(class_name, s, msg_type, version=0, contract_hash='', target='host'):
    avr = target == 'avr'
    upper = class_name.upper()
    w, n, nbytes, ib = s['index_width'], s['field_count'], s['bitfield_bytes'], s['index_bytes']
    idx_t = 'uint16_t' if ib == 2 else 'uint8_t'
    # his ruling (2026-10-02): "if it is index 0 and only one instance, the struct in the firmware is not needed" —
    # n = 1 ELIDES every instance symbol: no index type/macros/parameters/code, no index bits (presence only)
    one = s['index_repr'] == 'none'
    i_enc = '' if one else f'{class_name}_index_t index, '
    i_dec = '' if one else f'{class_name}_index_t *index, '
    i_arg = '' if one else 'index, '
    mask_t, pre_t = _uint_for(n), _pre_type(s['prelude_bits'])
    struct_lines, enc, dec, bits, enums = [], [], [], [], []
    for f in s['fields']:
        st, e, d = _field_code(class_name, upper, f, avr)
        struct_lines.append(st)
        enc += e
        dec += d
        bits.append(f'#define {upper}_F_{_cid(f["name"])} (({class_name}_mask_t)1u << {f["bit"] - w})  /* {f["name"]} ({f["ptype"]}) */')
        if f['enum']:
            labels = f['enum']['labels']
            consts = ',\n'.join([f'    {upper}_{_cid(f["name"])}_{_cid(f["enum"]["unknown"])} = 0'] +
                                [f'    {upper}_{_cid(f["name"])}_{_cid(lab)} = {i + 1}' for i, lab in enumerate(labels)])
            cases = '\n'.join(f'    case {i + 1}: return "{lab}";' for i, lab in enumerate(labels))
            enums.append(f'/* enum mapping {class_name}.{f["name"]} (EnumMapping row): 1 byte on the wire */\nenum {{\n{consts}\n}};\n'
                         f'static inline const char *{class_name}_{f["name"]}_name(uint8_t v)\n{{\n    switch (v) {{\n{cases}\n'
                         f'    default: return "{f["enum"]["unknown"]}";\n    }}\n}}')
    has_double = any(f['ptype'] == 'double' and not f['enum'] for f in s['fields'])
    common = _COMMON_V2 + ('\n\n' + _AVR_DOUBLE if avr and has_double else '')
    head_enc = ''.join(f'    p[{i}] = (uint8_t)(index >> {8 * i});\n' if i else '    p[0] = (uint8_t)index;\n' for i in range(ib)) + \
        (f'    p += {ib};  /* the explicit index (v{s["wire_version"]}) */\n' if ib else '')
    head_dec = (f'    if (index) *index = ({idx_t})' + (' | '.join(f'(({idx_t})p[{i}] << {8 * i})' if i else f'({idx_t})p[0]' for i in range(ib)))
                + f';\n    p += {ib};\n') if ib else ''
    pre_bytes_enc = '\n'.join(f'    p[{i}] = (uint8_t)(pre >> {8 * i});' if i else '    p[0] = (uint8_t)pre;' for i in range(nbytes))
    pre_bytes_dec = ' | '.join(f'(({pre_t})p[{i}] << {8 * i})' if i else f'({pre_t})p[0]' for i in range(nbytes))
    idx_mask = f'(({pre_t})1u << {w}) - 1u' if w else '0u'
    enc_decl = '\n    uint32_t lo, hi;' if avr and has_double else ''
    nl = '\n'
    target_note = '   target avr' if avr else ''
    return f'''/* Generated by Polari grpcbridge.custom.c_twin (grpc-j3) + c_twin_v2 (grpc-j4) — do not edit.
 * class: {class_name}   contract v{version}   hash {contract_hash}{target_note}
 * wire v{s["wire_version"]}   hash2 {s["hash_v2"]}   {"single instance: nothing to tell apart (presence bits only)" if one else f'index width {w} bit(s) ({s["instance_count"]} instance(s), index {s["index_repr"]}' + (f", {ib} byte(s)" if ib else "") + f'; suggested {s["suggested_index_width"]} bit(s), packed_max_bits {s["packed_max_bits"]})'}   prelude {s["prelude_bytes"]} byte(s)
 * The struct carries FIELDS ONLY; the hardware-interface identity lives in the gRPC message and the binding row.
 * Regenerate when the contract, an enum mapping or the bindings change. */
#ifndef {upper}_PACKETS_H
#define {upper}_PACKETS_H

#ifndef POLARI_RX_PAYLOAD_MAX
#define POLARI_RX_PAYLOAD_MAX {payload_max(s)}u
#endif

{common}

#define {upper}_MSG_TYPE {int(msg_type)}u
#define {upper}_PAYLOAD_MAX {payload_max(s)}u
#define {upper}_WIRE_VERSION {s["wire_version"]}u
{'' if one else f'#define {upper}_INDEX_WIDTH {w}u' + nl + f'#define {upper}_INDEX_BYTES {ib}u' + nl}#define {upper}_PRELUDE_BYTES {s["prelude_bytes"]}u
#define {upper}_HASH_V2 "{s["hash_v2"]}"

typedef {mask_t} {class_name}_mask_t;
{'' if one else f'typedef {idx_t} {class_name}_index_t;' + nl}{nl.join(bits)}
#define {upper}_F_ALL (({class_name}_mask_t){hex(s["present_all"])}u)

{(nl + nl).join(enums) + nl if enums else ''}
typedef struct {{
{nl.join(struct_lines)}
}} {class_name}_t;

/* struct -> payload: the prelude ({'presence bits' if one else 'index: ' + s['index_repr'] + '; presence bits'}) + ONLY the fields set in `present`. */
static uint16_t {class_name}_encode(const {class_name}_t *s, uint8_t *p,
                                    {i_enc}{class_name}_mask_t present)
{{
    uint8_t *start = p;
    {pre_t} pre;
    uint16_t n;{enc_decl}
    (void)n;{'' if one else ' (void)index;'}
    present &= {upper}_F_ALL;
{head_enc}    pre = {f'({pre_t})present;' if one else f'({pre_t})((({pre_t})index & ({idx_mask})) | (({pre_t})present << {w}));'}
{pre_bytes_enc}
    p += {nbytes};
{nl.join(enc)}
    return (uint16_t)(p - start);
}}

/* payload -> struct: ONLY the present fields are written (a partial command leaves the rest alone).
 * Returns 0, or -1 on truncated input. {'present may' if one else 'index / present may'} be NULL. */
static int {class_name}_decode(const uint8_t *p, uint16_t len, {class_name}_t *s,
                               {i_dec}{class_name}_mask_t *present)
{{
    const uint8_t *end = p + len;
    {pre_t} pre;
    {class_name}_mask_t m;
    uint16_t n, cp;
    (void)n; (void)cp;
    if (len < {upper}_PRELUDE_BYTES) return -1;
{head_dec}    pre = ({pre_t})({pre_bytes_dec});
    p += {nbytes};
    m = ({class_name}_mask_t)(pre >> {w}) & {upper}_F_ALL;
{'' if one else f'    if (index && !{ib}u) *index = ({class_name}_index_t)(pre & ({idx_mask}));' + nl}    if (present) *present = m;
{nl.join(dec)}
    return 0;
}}

/* decode a parsed frame: -2 for any other version (a v1 frame from an old bridge, another index representation):
 * refused, never misread */
static int {class_name}_decode_rx(const polari_rx_t *rx, {class_name}_t *s,
                                  {i_dec}{class_name}_mask_t *present)
{{
    if (rx->version != {upper}_WIRE_VERSION) return -2;
    return {class_name}_decode(rx->payload, rx->payload_len, s, {i_arg}present);
}}

/* frame a payload with this class's version byte and msg_type */
static size_t {class_name}_frame(uint8_t *out, uint16_t device_id, uint32_t seq,
                                 const uint8_t *payload, uint16_t len)
{{
    return polari_packet_encode_v(out, {upper}_WIRE_VERSION, {upper}_MSG_TYPE, device_id, seq, payload, len);
}}

#endif /* {upper}_PACKETS_H */
'''
