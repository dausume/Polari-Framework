"""
@module grpcbridge.java_bridge_codegen

PER-CLASS Java generation for the Polari Hardware Bridge (grpc-j1),
all driven by the SAME field_map the .proto contract was generated
from (grpc-1) — so the binary struct, the proto, and Polari's schema
agree by construction:

  <Class>Record  — the struct as a Java class (fields in tag order)
  <Class>Codec   — binary twin of the C struct: little-endian,
                   u16-length-prefixed UTF-8 strings; encode/decode/
                   sample (the simulated MCU's synthetic values)
  CodecRegistry  — msg_type -> codec dispatch
  GrpcForwarder  — proto <-> struct in BOTH directions: Push
                   telemetry up, Commands stream down to the device

@consumers
  - grpcbridge.java_bridge (project assembly)
"""

_JAVA_KEYWORDS = {
    'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
    'char', 'class', 'const', 'continue', 'default', 'do', 'double',
    'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
    'goto', 'if', 'implements', 'import', 'instanceof', 'int',
    'interface', 'long', 'native', 'new', 'package', 'private',
    'protected', 'public', 'return', 'short', 'static', 'strictfp',
    'super', 'switch', 'synchronized', 'this', 'throw', 'throws',
    'transient', 'try', 'void', 'volatile', 'while', 'record',
}

JAVA_TYPES = {'int64': 'long', 'bool': 'boolean', 'double': 'double',
              'string': 'String', 'bytes': 'byte[]'}

#: Fixed wire size of the non-length-prefixed types.
FIXED_SIZES = {'int64': 8, 'bool': 1, 'double': 8}


def java_field_name(name):
    return name + '_' if name in _JAVA_KEYWORDS else name


def proto_accessor(name):
    """protoc's underscores-to-camel Java accessor stem."""
    out = []
    cap = False
    for ch in name:
        if ch == '_':
            cap = True
            continue
        out.append(ch.upper() if cap else ch)
        cap = False
    stem = ''.join(out)
    return stem[0].upper() + stem[1:] if stem else stem


def ordered_fields(field_map):
    """(name, spec) in tag order — THE struct layout order."""
    fields = field_map.get('fields', {})
    return sorted(fields.items(), key=lambda kv: kv[1]['tag'])


def _sample_expr(spec, field_name='', class_name=''):
    ptype = spec['proto_type']
    if ptype == 'int64':
        return 'seq'
    if ptype == 'bool':
        return '(seq % 2 == 0)'
    if ptype == 'double':
        return 'Math.sin(seq / 10.0)'
    if ptype == 'bytes':
        return 'new byte[]{(byte) seq}'
    if spec.get('comment'):  # JSON-carrying string — stay honest JSON
        return '"{\\"sim\\": " + seq + "}"'
    if field_name == 'name':
        # A device streams telemetry about ITSELF: identity stays
        # STABLE across frames (Polari's `name` unique-key convention
        # — grpc-2's Push matches on it), only measurements vary.
        # Varying this would create one object row PER FRAME upstream.
        return f'"sim-{class_name.lower()}"'
    return '"sim-" + seq'


def render_record(class_name, field_map, version, chash):
    lines = [
        'package org.polari.bridge.codec;',
        '',
        f'/** The {class_name} struct — generated from contract '
        f'v{version} (hash {chash}), fields in tag order. */',
        f'public final class {class_name}Record {{',
    ]
    to_string = []
    for name, spec in ordered_fields(field_map):
        jname = java_field_name(name)
        jtype = JAVA_TYPES[spec['proto_type']]
        note = f'  // {spec["comment"]}' if spec.get('comment') else ''
        lines.append(f'    public {jtype} {jname};{note}')
        if spec['proto_type'] == 'bytes':
            to_string.append(
                f'"{name}=bytes[" + ({jname} == null ? 0 : '
                f'{jname}.length) + "]"')
        else:
            to_string.append(f'"{name}=" + {jname}')
    joined = '\n                + ", " + '.join(to_string) \
        if to_string else '""'
    lines += [
        '',
        '    @Override',
        '    public String toString() {',
        f'        return "{class_name}{{" + {joined}',
        '                + "}";',
        '    }',
        '}',
        '',
    ]
    return '\n'.join(lines)


def render_codec(class_name, field_map, msg_type):
    fields = ordered_fields(field_map)
    encode_pre = []
    size_terms = [str(sum(FIXED_SIZES.get(s['proto_type'], 0)
                          for _, s in fields))]
    encode_puts = []
    decode_gets = []
    sample_sets = []
    for name, spec in fields:
        jname = java_field_name(name)
        ptype = spec['proto_type']
        if ptype == 'string':
            encode_pre.append(
                f'        byte[] b_{jname} = utf8(r.{jname});')
            size_terms.append(f'2 + b_{jname}.length')
            encode_puts.append(f'        putBlock(buf, b_{jname});')
            decode_gets.append(
                f'        r.{jname} = getString(buf);')
        elif ptype == 'bytes':
            encode_pre.append(
                f'        byte[] b_{jname} = r.{jname} == null '
                f'? new byte[0] : r.{jname};')
            size_terms.append(f'2 + b_{jname}.length')
            encode_puts.append(f'        putBlock(buf, b_{jname});')
            decode_gets.append(f'        r.{jname} = getBlock(buf);')
        elif ptype == 'int64':
            encode_puts.append(f'        buf.putLong(r.{jname});')
            decode_gets.append(f'        r.{jname} = buf.getLong();')
        elif ptype == 'bool':
            encode_puts.append(
                f'        buf.put((byte) (r.{jname} ? 1 : 0));')
            decode_gets.append(
                f'        r.{jname} = buf.get() != 0;')
        elif ptype == 'double':
            encode_puts.append(f'        buf.putDouble(r.{jname});')
            decode_gets.append(
                f'        r.{jname} = buf.getDouble();')
        sample_sets.append(
            f'        r.{java_field_name(name)} = '
            f'{_sample_expr(spec, name, class_name)};')

    nl = '\n'
    return f'''package org.polari.bridge.codec;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;

/**
 * Binary struct twin of the {class_name} contract: fields in tag
 * order, little-endian; strings/bytes are u16-length-prefixed.
 * The MCU-side C struct uses the identical layout (grpc-j3).
 */
public final class {class_name}Codec {{
    public static final int MSG_TYPE = {msg_type};
    public static final String CLASS_NAME = "{class_name}";

    public static byte[] encode({class_name}Record r) {{
{nl.join(encode_pre) + nl if encode_pre else ''}        int size = {' + '.join(size_terms)};
        ByteBuffer buf = ByteBuffer.allocate(size)
                .order(ByteOrder.LITTLE_ENDIAN);
{nl.join(encode_puts)}
        return buf.array();
    }}

    public static {class_name}Record decode(byte[] payload) {{
        ByteBuffer buf = ByteBuffer.wrap(payload)
                .order(ByteOrder.LITTLE_ENDIAN);
        {class_name}Record r = new {class_name}Record();
{nl.join(decode_gets)}
        return r;
    }}

    /** Synthetic record for the simulated MCU. */
    public static {class_name}Record sample(long seq) {{
        {class_name}Record r = new {class_name}Record();
{nl.join(sample_sets)}
        return r;
    }}

    private static byte[] utf8(String s) {{
        return (s == null ? "" : s).getBytes(StandardCharsets.UTF_8);
    }}

    private static void putBlock(ByteBuffer buf, byte[] b) {{
        buf.putShort((short) b.length);
        buf.put(b);
    }}

    private static byte[] getBlock(ByteBuffer buf) {{
        int n = buf.getShort() & 0xFFFF;
        byte[] b = new byte[n];
        buf.get(b);
        return b;
    }}

    private static String getString(ByteBuffer buf) {{
        return new String(getBlock(buf), StandardCharsets.UTF_8);
    }}
}}
'''


def render_registry(class_names):
    """CodecRegistry: msg_type = (index + 1) in the bridge's ordered
    class list — the knob-defined wire identity of each class."""
    msg_types = ', '.join(f'{c}Codec.MSG_TYPE' for c in class_names)
    cls_cases = '\n'.join(
        f'            case {c}Codec.MSG_TYPE: '
        f'return {c}Codec.CLASS_NAME;' for c in class_names)
    dec_cases = '\n'.join(
        f'            case {c}Codec.MSG_TYPE: '
        f'return {c}Codec.decode(payload).toString();'
        for c in class_names)
    sam_cases = '\n'.join(
        f'            case {c}Codec.MSG_TYPE: '
        f'return {c}Codec.encode({c}Codec.sample(seq));'
        for c in class_names)
    return f'''package org.polari.bridge;

import org.polari.bridge.codec.*;

/** Generated msg_type registry: one entry per exposed class. */
public final class CodecRegistry {{

    public static int[] msgTypes() {{
        return new int[]{{{msg_types}}};
    }}

    public static String className(int msgType) {{
        switch (msgType) {{
{cls_cases}
            default: return "unknown";
        }}
    }}

    public static String decodeToLine(int msgType, byte[] payload) {{
        switch (msgType) {{
{dec_cases}
            default: return "unknown msg_type " + msgType + " ("
                    + payload.length + " bytes)";
        }}
    }}

    public static byte[] sampleFrame(int msgType, long seq) {{
        switch (msgType) {{
{sam_cases}
            default: throw new IllegalArgumentException(
                    "unknown msg_type " + msgType);
        }}
    }}

    private CodecRegistry() {{
    }}
}}
'''


def _to_proto_setters(field_map):
    lines = []
    for name, spec in ordered_fields(field_map):
        jname = java_field_name(name)
        stem = proto_accessor(name)
        ptype = spec['proto_type']
        if ptype == 'string':
            lines.append(f'                .set{stem}(r.{jname} == '
                         f'null ? "" : r.{jname})')
        elif ptype == 'bytes':
            lines.append(
                f'                .set{stem}(com.google.protobuf.'
                f'ByteString.copyFrom(r.{jname} == null '
                f'? new byte[0] : r.{jname}))')
        else:
            lines.append(f'                .set{stem}(r.{jname})')
    return '\n'.join(lines)


def _from_proto_getters(field_map):
    lines = []
    for name, spec in ordered_fields(field_map):
        jname = java_field_name(name)
        stem = proto_accessor(name)
        if spec['proto_type'] == 'bytes':
            lines.append(f'        r.{jname} = '
                         f'proto.get{stem}().toByteArray();')
        else:
            lines.append(f'        r.{jname} = proto.get{stem}();')
    return '\n'.join(lines)


def render_forwarder(classes):
    """GrpcForwarder: the proto<->struct converter, BOTH directions.
    `classes` = [(class_name, field_map)] in msg_type order. Compiled
    only by the Maven build (needs the generated proto stubs); the
    core app loads it reflectively when grpc.enabled=true."""
    push_fields = '\n'.join(
        f'    private StreamObserver<org.polari.sync.{c}> '
        f'{c[0].lower() + c[1:]}Push;' for c, _ in classes)
    push_cases = '\n'.join(
        f'            case {c}Codec.MSG_TYPE:\n'
        f'                push{c}({c}Codec.decode(packet.payload));\n'
        f'                break;' for c, _ in classes)
    command_starts = '\n'.join(
        f'        startCommands{c}();' for c, _ in classes)
    per_class = []
    for c, field_map in classes:
        lower = c[0].lower() + c[1:]
        per_class.append(f'''
    private void push{c}({c}Record r) {{
        if ({lower}Push == null) {{
            {lower}Push = {c}SyncGrpc.newStub(channel)
                    .push(new AckObserver("{c}"));
        }}
        {lower}Push.onNext(toProto{c}(r));
    }}

    private void startCommands{c}() {{
        {c}SyncGrpc.newStub(channel).commands(
                WatchRequest.newBuilder().setClassName("{c}")
                        .build(),
                new StreamObserver<org.polari.sync.{c}>() {{
                    @Override
                    public void onNext(org.polari.sync.{c} proto) {{
                        try {{
                            byte[] payload = {c}Codec.encode(
                                    fromProto{c}(proto));
                            port.send(new PolariPacket(
                                    {c}Codec.MSG_TYPE, 0,
                                    commandSeq.incrementAndGet(),
                                    payload));
                        }} catch (Exception e) {{
                            System.out.println(
                                    "[grpc] {c} command failed: " + e);
                        }}
                    }}

                    @Override
                    public void onError(Throwable t) {{
                        System.out.println(
                                "[grpc] {c} commands error: " + t);
                    }}

                    @Override
                    public void onCompleted() {{
                        System.out.println(
                                "[grpc] {c} commands completed");
                    }}
                }});
    }}

    private static org.polari.sync.{c} toProto{c}({c}Record r) {{
        return org.polari.sync.{c}.newBuilder()
{_to_proto_setters(field_map)}
                .build();
    }}

    private static {c}Record fromProto{c}(
            org.polari.sync.{c} proto) {{
        {c}Record r = new {c}Record();
{_from_proto_getters(field_map)}
        return r;
    }}''')
    nl = ''.join(per_class)
    return f'''package org.polari.bridge.grpc;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.stub.StreamObserver;
import java.util.concurrent.atomic.AtomicLong;
import org.polari.bridge.DevicePort;
import org.polari.bridge.PolariPacket;
import org.polari.bridge.codec.*;
import org.polari.sync.*;

/**
 * Proto <-> struct conversion in BOTH directions (grpc-2 server):
 * telemetry packets are decoded and Pushed up per class; each
 * class's Commands stream is subscribed and written down to the
 * device as packets. Loaded reflectively by BridgeMain so the core
 * app compiles and runs with zero gRPC dependencies.
 */
public final class GrpcForwarder {{
    private final ManagedChannel channel;
    private final DevicePort port;
    private final AtomicLong commandSeq = new AtomicLong();
{push_fields}

    public GrpcForwarder(String target, DevicePort port) {{
        this.channel = ManagedChannelBuilder.forTarget(target)
                .usePlaintext().build();
        this.port = port;
    }}

    /** Telemetry up: decoded packet -> proto -> Push stream. */
    public void push(PolariPacket packet) {{
        switch (packet.msgType) {{
{push_cases}
            default:
                break;
        }}
    }}

    /** Commands down: subscribe every class's Commands stream. */
    public void startCommands() {{
{command_starts}
    }}
{nl}

    private static final class AckObserver
            implements StreamObserver<PushSummary> {{
        private final String label;

        AckObserver(String label) {{
            this.label = label;
        }}

        @Override
        public void onNext(PushSummary summary) {{
            System.out.println("[grpc] " + label + " push ack: "
                    + "received=" + summary.getReceived()
                    + " applied=" + summary.getApplied());
        }}

        @Override
        public void onError(Throwable t) {{
            System.out.println("[grpc] " + label + " push error: "
                    + t);
        }}

        @Override
        public void onCompleted() {{
        }}
    }}
}}
'''
