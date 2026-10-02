"""
@module grpcbridge.custom.java_bridge_wire

grpc-j4 (his ruling 2026-10-02) — the Java side of the computer↔firmware MAPPING, generated from the SAME wire spec
(grpcbridge.custom.wire_contract.spec) the C header (c_twin_v2) comes from:

  BridgeBinding / BindingRouter   the bridge's bindings (bridge.properties `binding.K.*`) and the DevicePort that opens
                                  one serial port per bound interface, tags every frame with the port it came from and
                                  routes a command for (class, index k) to binding k's port
  <Class><Field>Enum              one Java enum per EnumMapping (toWire / fromWire, 0 = the unknown slot)
  codec wire methods              encodeV2(record, index, present) / decodeFrame(packet) → Frame{record, index, present}
                                  (a v1 packet = index 0, every field present) / describe(frame)
  proto enums                     `enum <Class><Field>` in the bridge's bundled proto (the field itself stays string)
  properties                      bridge.name + binding.count + binding.K.{class,object,index,port,board_instance,
                                  interface,name,wire_version,contract_hash}

@consumers
  - grpcbridge.custom.java_bridge (project assembly) · java_bridge_codegen (registry + forwarder call these names)
"""
from grpcbridge.custom.java_bridge_codegen import java_field_name

BRIDGE_BINDING_JAVA = r'''package org.polari.bridge;

import java.util.Properties;

/**
 * grpc-j4: one hardware-interface binding of this bridge — which row
 * (class + object name) a port + instance index IS. The identifiers ride
 * the gRPC message (hardware_interface), never the wire struct: the
 * bridge re-attaches them from here when a frame arrives with index k.
 */
public final class BridgeBinding {
    public final String name;
    public final String objectClass;
    public final String objectName;
    public final int index;
    public final String port;
    public final String boardInstance;
    public final String interfaceName;
    public final int wireVersion;
    public final String contractHash;

    private BridgeBinding(Properties p, String k) {
        this.name = p.getProperty(k + "name", "");
        this.objectClass = p.getProperty(k + "class", "");
        this.objectName = p.getProperty(k + "object", "");
        this.index = Integer.parseInt(p.getProperty(k + "index", "0"));
        this.port = p.getProperty(k + "port", "");
        this.boardInstance = p.getProperty(k + "board_instance", "");
        this.interfaceName = p.getProperty(k + "interface", "");
        this.wireVersion = Integer.parseInt(
                p.getProperty(k + "wire_version", "2"));
        this.contractHash = p.getProperty(k + "contract_hash", "");
    }

    static BridgeBinding from(Properties p, String prefix) {
        return new BridgeBinding(p, prefix);
    }
}
'''

BINDING_ROUTER_JAVA = r'''package org.polari.bridge;

import java.io.EOFException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * grpc-j4: the DevicePort over every bound interface of this bridge —
 * one serial port per distinct binding port (a twin's pty, a board's
 * by-id path), a reader thread per port, frames tagged with the port
 * they arrived on; a command for (class, index k) goes to binding k's
 * port only. The rest of the app is unchanged (one seam).
 */
public final class BindingRouter implements DevicePort {
    private static final Object END = new Object();
    private static final Object CORRUPT = new Object();
    private final BridgeConfig cfg;
    private final Map<String, SerialCdcPort> ports = new LinkedHashMap<>();
    private final BlockingQueue<Object> queue = new LinkedBlockingQueue<>();
    private int live;

    public BindingRouter(BridgeConfig cfg) throws Exception {
        this.cfg = cfg;
        for (BridgeBinding b : cfg.bindings) {
            if (!ports.containsKey(b.port)) {
                ports.put(b.port, new SerialCdcPort(b.port, cfg.baud));
            }
        }
        for (Map.Entry<String, SerialCdcPort> e : ports.entrySet()) {
            live++;
            Thread t = new Thread(() -> pump(e.getKey(), e.getValue()),
                    "port " + e.getKey());
            t.setDaemon(true);
            t.start();
        }
    }

    private void pump(String path, SerialCdcPort port) {
        try {
            while (true) {
                PolariPacket p = port.next();
                if (p == null) {
                    queue.put(CORRUPT);
                    continue;
                }
                p.sourcePort = path;
                queue.put(p);
            }
        } catch (Exception ended) {
            System.out.println("[bridge] port " + path + " ended: "
                    + ended);
        } finally {
            queue.offer(END);
        }
    }

    @Override
    public PolariPacket next() throws Exception {
        while (true) {
            Object o = queue.take();
            if (o == END) {
                if (--live == 0) throw new EOFException("every port ended");
                continue;
            }
            return o == CORRUPT ? null : (PolariPacket) o;
        }
    }

    @Override
    public void send(PolariPacket packet) throws Exception {
        ports.values().iterator().next().send(packet);
    }

    @Override
    public void sendTo(String objectClass, int index, PolariPacket packet)
            throws Exception {
        BridgeBinding b = cfg.find(objectClass, index);
        if (b == null) {
            throw new IllegalStateException("no binding for " + objectClass
                    + " index " + index + " on this bridge");
        }
        ports.get(b.port).send(packet);
    }

    @Override
    public String describe() {
        return "bindings " + cfg.bindings.size() + " on ports "
                + ports.keySet();
    }

    @Override
    public void close() throws Exception {
        for (SerialCdcPort p : ports.values()) p.close();
    }
}
'''


def _jid(text):
    return ''.join(ch if ch.isalnum() else '_' for ch in str(text)).upper()


def enum_class_name(cls, field):
    stem = ''.join(part[:1].upper() + part[1:] for part in field.split('_'))
    return '%s%sEnum' % (cls, stem)


def render_enums(cls, spec):
    """{relative codec path: java} — one enum per EnumMapping of the class."""
    out = {}
    for f in spec['fields']:
        if not f['enum']:
            continue
        name = enum_class_name(cls, f['name'])
        consts = [(_jid(f['enum']['unknown']), 0, f['enum']['unknown'])] + \
            [(_jid(lab), i + 1, lab) for i, lab in enumerate(f['enum']['labels'])]
        body = ',\n'.join('    %s(%d, "%s")' % c for c in consts)
        out['%s.java' % name] = f'''package org.polari.bridge.codec;

/** EnumMapping {cls}.{f["name"]} (grpc-j4): the object state's string ↔ ONE wire byte; 0 = the unknown slot. */
public enum {name} {{
{body};

    public final int wire;
    public final String label;

    {name}(int wire, String label) {{
        this.wire = wire;
        this.label = label;
    }}

    public static int toWire(String label) {{
        for ({name} v : values()) {{
            if (v.wire != 0 && v.label.equals(label)) return v.wire;
        }}
        return 0;
    }}

    public static String fromWire(int wire) {{
        for ({name} v : values()) {{
            if (v.wire == wire) return v.label;
        }}
        return {consts[0][0]}.label;
    }}
}}
'''
    return out


def render_proto_enums(cls, spec):
    """`enum <Class><Field>` blocks for the bridge's bundled proto (values prefixed: proto enum scoping)."""
    blocks = []
    for f in spec['fields']:
        if not f['enum']:
            continue
        stem = ''.join(part[:1].upper() + part[1:] for part in f['name'].split('_'))
        pre = '%s_%s' % (_jid(cls), _jid(f['name']))
        lines = ['  %s_%s = 0;' % (pre, _jid(f['enum']['unknown']))] + \
            ['  %s_%s = %d;' % (pre, _jid(lab), i + 1) for i, lab in enumerate(f['enum']['labels'])]
        blocks.append('// grpc-j4 EnumMapping %s.%s — the field stays `string` in the message; the struct carries 1 byte\n'
                      'enum %s%s {\n%s\n}' % (cls, f['name'], cls, stem, '\n'.join(lines)))
    return '\n\n'.join(blocks)


def render_codec_wire(cls, spec):
    """Methods appended inside <Class>Codec: the wire v2 encode/decode + describe."""
    w, n = spec['index_width'], spec['field_count']
    sizes, puts, gets, desc = [], [], [], []
    for i, f in enumerate(spec['fields']):
        j, t, bit = java_field_name(f['name']), f['ptype'], '(present & (1L << %d)) != 0' % i
        if f['enum']:
            e = enum_class_name(cls, f['name'])
            sizes.append(f'        if ({bit}) size += 1;')
            puts.append(f'        if ({bit}) buf.put((byte) {e}.toWire(r.{j}));')
            gets.append(f'        if ({bit}) r.{j} = {e}.fromWire(buf.get() & 0xFF);')
        elif t in ('string', 'bytes'):
            src = f'utf8(r.{j})' if t == 'string' else f'(r.{j} == null ? new byte[0] : r.{j})'
            sizes.append(f'        byte[] b_{j} = {src};\n        if ({bit}) size += 2 + b_{j}.length;')
            puts.append(f'        if ({bit}) putBlock(buf, b_{j});')
            gets.append(f'        if ({bit}) r.{j} = {"getString(buf)" if t == "string" else "getBlock(buf)"};')
        else:
            size = {'int64': 8, 'double': 8, 'bool': 1}[t]
            put = {'int64': f'buf.putLong(r.{j})', 'double': f'buf.putDouble(r.{j})', 'bool': f'buf.put((byte) (r.{j} ? 1 : 0))'}[t]
            get = {'int64': 'buf.getLong()', 'double': 'buf.getDouble()', 'bool': 'buf.get() != 0'}[t]
            sizes.append(f'        if ({bit}) size += {size};')
            puts.append(f'        if ({bit}) {put};')
            gets.append(f'        if ({bit}) r.{j} = {get};')
        shown = f'"bytes[" + (r.{j} == null ? 0 : r.{j}.length) + "]"' if t == 'bytes' else f'r.{j}'
        desc.append(f'        if ((f.present & (1L << {i})) != 0) parts.add("{f["name"]}=" + {shown});')
    enum_samples = '\n'.join(
        f'        r.{java_field_name(f["name"])} = {enum_class_name(cls, f["name"])}.fromWire(1 + (int) (seq % {len(f["enum"]["labels"])}));'
        for f in spec['fields'] if f['enum'])
    nl = '\n'
    return f'''
    /** A synthetic record whose enum fields hold mapped labels (the v2 loopback). */
    public static {cls}Record sampleV2(long seq) {{
        {cls}Record r = sample(seq);
{enum_samples}
        return r;
    }}

    // ---- grpc-j4 wire v2: prelude (index {w} bit(s) + {n} presence bits) + the present fields
    public static final int WIRE_FIELDS = {n};
    public static final int WIRE_VERSION = {spec["wire_version"]};   // 2 packed / none, 3 an index byte, 4 a u16 index
    public static final String INDEX_REPR = "{spec["index_repr"]}";
    public static final int INDEX_WIDTH = {w};                       // bits packed in the bitfield
    public static final int INDEX_BYTES = {spec["index_bytes"]};     // explicit index bytes before it
    public static final int INSTANCE_COUNT = {spec["instance_count"]};
    public static final int BITFIELD_BYTES = {spec["bitfield_bytes"]};
    public static final int PRELUDE_BYTES = {spec["prelude_bytes"]};
    public static final long PRESENT_ALL = {spec["present_all"]}L;
    public static final String HASH_V2 = "{spec["hash_v2"]}";

    /** One decoded frame: the record, the instance index, the presence bits. */
    public static final class Frame {{
        public final {cls}Record record;
        public final int index;
        public final long present;

        public Frame({cls}Record record, int index, long present) {{
            this.record = record;
            this.index = index;
            this.present = present;
        }}
    }}

    private static boolean bit(byte[] pre, int i) {{
        return ((pre[i >> 3] >> (i & 7)) & 1) != 0;
    }}

    public static byte[] encodeV2({cls}Record r, int index, long present) {{
        present &= PRESENT_ALL;
        int size = PRELUDE_BYTES;
{nl.join(sizes)}
        ByteBuffer buf = ByteBuffer.allocate(size).order(ByteOrder.LITTLE_ENDIAN);
        if (INDEX_BYTES == 1) buf.put((byte) index);
        if (INDEX_BYTES == 2) buf.putShort((short) index);
        byte[] pre = new byte[BITFIELD_BYTES];
        for (int i = 0; i < INDEX_WIDTH; i++) {{
            if (((index >> i) & 1) != 0) pre[i >> 3] |= (byte) (1 << (i & 7));
        }}
        for (int i = 0; i < WIRE_FIELDS; i++) {{
            int b = INDEX_WIDTH + i;
            if (((present >> i) & 1L) != 0) pre[b >> 3] |= (byte) (1 << (b & 7));
        }}
        buf.put(pre);
{nl.join(puts)}
        return buf.array();
    }}

    /** A v1 packet = index 0, every field present; v2 = the prelude decides. */
    public static Frame decodeFrame(org.polari.bridge.PolariPacket p) {{
        if (p.version < 2) return new Frame(decode(p.payload), 0, PRESENT_ALL);
        if (p.version != WIRE_VERSION) {{
            throw new IllegalArgumentException("{cls} frame version " + p.version
                    + " but this contract carries its index as " + INDEX_REPR + " (version " + WIRE_VERSION + ")");
        }}
        ByteBuffer buf = ByteBuffer.wrap(p.payload).order(ByteOrder.LITTLE_ENDIAN);
        int index = INDEX_BYTES == 1 ? buf.get() & 0xFF : INDEX_BYTES == 2 ? buf.getShort() & 0xFFFF : 0;
        byte[] pre = new byte[BITFIELD_BYTES];
        buf.get(pre);
        for (int i = 0; i < INDEX_WIDTH; i++) if (bit(pre, i)) index |= 1 << i;
        long present = 0;
        for (int i = 0; i < WIRE_FIELDS; i++) if (bit(pre, INDEX_WIDTH + i)) present |= 1L << i;
        {cls}Record r = new {cls}Record();
{nl.join(gets)}
        return new Frame(r, index, present);
    }}

    /** "{cls}{{field=value, …}}" over the PRESENT fields only. */
    public static String describe(Frame f) {{
        {cls}Record r = f.record;
        java.util.List<String> parts = new java.util.ArrayList<>();
{nl.join(desc)}
        return "{cls}{{" + String.join(", ", parts) + "}}";
    }}
'''


def insert_into_codec(codec_text, methods):
    cut = codec_text.rstrip().rfind('}')
    return codec_text[:cut] + methods + '}\n'


def registry_methods(class_names):
    """indexOf / describe / v2RoundTrip, appended inside CodecRegistry."""
    idx = '\n'.join(f'                case {c}Codec.MSG_TYPE: return {c}Codec.decodeFrame(p).index;' for c in class_names)
    dsc = '\n'.join(f'                case {c}Codec.MSG_TYPE: return {c}Codec.describe({c}Codec.decodeFrame(p));' for c in class_names)
    rt = '\n'.join(f'''            case {c}Codec.MSG_TYPE: {{
                int index = {c}Codec.INSTANCE_COUNT - 1;
                long present = {c}Codec.PRESENT_ALL & ~1L;
                {c}Codec.Frame want = new {c}Codec.Frame({c}Codec.sampleV2(seq), index, present);
                PolariPacket p = new PolariPacket({c}Codec.WIRE_VERSION, msgType, 7, seq,
                        {c}Codec.encodeV2(want.record, index, present));
                try {{
                    PolariPacket back = PolariPacket.read(new java.io.ByteArrayInputStream(p.encode()));
                    {c}Codec.Frame got = {c}Codec.decodeFrame(back);
                    String a = {c}Codec.describe(want), b = {c}Codec.describe(got);
                    return a.equals(b) && got.index == index && got.present == present
                            ? "index=" + index + " v" + back.version + " " + b : "FAIL " + a + " != " + b;
                }} catch (java.io.IOException e) {{
                    return "FAIL " + e;
                }}
            }}''' for c in class_names)
    return f'''
    /** grpc-j4: the instance index a packet carries (0 for v1; -1 when it does not decode). */
    public static int indexOf(PolariPacket p) {{
        try {{
            switch (p.msgType) {{
{idx}
                default: return 0;
            }}
        }} catch (RuntimeException e) {{
            return -1;
        }}
    }}

    /** grpc-j4: the decoded line — the PRESENT fields of a v2 frame, every field of a v1 frame. */
    public static String describe(PolariPacket p) {{
        try {{
            switch (p.msgType) {{
{dsc}
                default: return decodeToLine(p.msgType, p.payload);
            }}
        }} catch (RuntimeException e) {{
            return "undecodable{{" + e.getMessage() + "}}";
        }}
    }}

    /** grpc-j4 loopback: sample → encodeV2 → frame → parse → decodeFrame, compared. */
    public static String v2RoundTrip(int msgType, long seq) {{
        switch (msgType) {{
{rt}
            default: return "FAIL unknown msg_type " + msgType;
        }}
    }}
'''


def properties_lines(bridge_name, rows):
    """bridge.name + the binding.K.* keys (rows: HardwareInterfaceBinding objects or dicts)."""
    g = lambda r, k: (r.get(k, '') if isinstance(r, dict) else getattr(r, k, ''))  # noqa: E731
    lines = ['# grpc-j4: the hardware-interface bindings of this bridge (HardwareInterfaceBinding rows)',
             'bridge.name=%s' % bridge_name, 'binding.count=%d' % len(rows)]
    for i, r in enumerate(rows):
        for key, attr in (('name', 'name'), ('class', 'object_class'), ('object', 'object_name'), ('index', 'instance_index'),
                          ('port', 'port'), ('board_instance', 'board_instance'), ('interface', 'interface_name'),
                          ('wire_version', 'wire_version'), ('contract_hash', 'contract_hash_v2')):
            lines.append('binding.%d.%s=%s' % (i, key, g(r, attr)))
    return lines
