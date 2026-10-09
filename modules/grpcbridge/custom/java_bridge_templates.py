'''
@module grpcbridge.custom.java_bridge_templates

STATIC sources of the generated Polari Hardware Bridge app (grpc-j1):
the universal packet codec, the BIDIRECTIONAL DevicePort seam with
its two implementations (SimulatedDevice — the internal-simulation
phase, which also ACCEPTS commands and reflects them in subsequent
telemetry — and the real CDC-ACM serial port), config, the main
loop, the loopback selftest, and the packaging files (pom / systemd
/ installer / README). Per-class code (records, codecs, registry,
gRPC forwarder) is generated in java_bridge_codegen.

Templates use __TOKEN__ replacement (no brace escaping) via
java_bridge.render().

@consumers
  - grpcbridge.custom.java_bridge (project assembly)
'''

POLARI_PACKET_JAVA = r'''package org.polari.bridge;

import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.PushbackInputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.zip.CRC32;

/**
 * The universal Polari hardware packet — ONE transport for every
 * board (LED, CNC, laser, sensor):
 *
 *   magic u16 | version u8 | msg_type u8 | device_id u16 |
 *   sequence u32 | payload_len u16 | payload | crc32 u32
 *
 * Little-endian throughout; CRC32 covers header + payload. The OS
 * just sees bytes; this class interprets them.
 *
 * grpc-j4: version 1 = the payload is the struct (every field);
 * version 2 = the payload starts with the prelude (instance index +
 * presence bits — the per-class codec reads it). Both parse.
 */
public final class PolariPacket {
    public static final int MAGIC = 0x504C; // "PL" (wire: 0x4C 0x50)
    public static final int VERSION = 1;    // what the 4-arg constructor frames (legacy)
    public static final int VERSION_MAX = 4; // 3: an index byte, 4: a u16 index (grpc-j4)
    public static final int HEADER_LEN = 12;
    public static final int MAX_PAYLOAD = 4096;

    public final int version;    // u8: 1 | 2 | 3 | 4
    public final int msgType;    // u8
    public final int deviceId;   // u16
    public final long sequence;  // u32
    public final byte[] payload;
    /** grpc-j4: the port this frame arrived on (set by BindingRouter). */
    public String sourcePort;

    public PolariPacket(int msgType, int deviceId, long sequence,
                        byte[] payload) {
        this(VERSION, msgType, deviceId, sequence, payload);
    }

    public PolariPacket(int version, int msgType, int deviceId,
                        long sequence, byte[] payload) {
        this.version = version;
        this.msgType = msgType;
        this.deviceId = deviceId;
        this.sequence = sequence;
        this.payload = payload;
    }

    public int wireLength() {
        return HEADER_LEN + payload.length + 4;
    }

    public byte[] encode() {
        ByteBuffer buf = ByteBuffer.allocate(wireLength())
                .order(ByteOrder.LITTLE_ENDIAN);
        buf.putShort((short) MAGIC);
        buf.put((byte) version);
        buf.put((byte) msgType);
        buf.putShort((short) deviceId);
        buf.putInt((int) sequence);
        buf.putShort((short) payload.length);
        buf.put(payload);
        CRC32 crc = new CRC32();
        crc.update(buf.array(), 0, HEADER_LEN + payload.length);
        buf.putInt((int) crc.getValue());
        return buf.array();
    }

    /**
     * Blocking read of one framed packet. Scans forward to the magic
     * (resync-safe on a noisy line; a second-byte mismatch that is
     * itself a start byte starts the next candidate — brd-fi finding
     * (3)). Returns null when the frame's CRC, version or length is
     * wrong — the caller counts and continues; on a PushbackInputStream
     * the rejected bytes after the first are pushed back and re-scanned,
     * so a frame starting inside a corrupted one is kept. Throws
     * EOFException when the stream ends.
     */
    public static PolariPacket read(InputStream in) throws IOException {
        PushbackInputStream pin = in instanceof PushbackInputStream
                ? (PushbackInputStream) in : null;
        int b = in.read();
        while (true) {
            if (b < 0) throw new EOFException("packet stream ended");
            if (b != (MAGIC & 0xFF)) {
                b = in.read();
                continue;
            }
            int b2 = in.read();
            if (b2 < 0) throw new EOFException("packet stream ended");
            if (b2 != ((MAGIC >> 8) & 0xFF)) {
                b = b2; // it may itself start the next candidate
                continue;
            }
            byte[] rest = readFully(in, HEADER_LEN - 2);
            ByteBuffer hdr = ByteBuffer.wrap(rest)
                    .order(ByteOrder.LITTLE_ENDIAN);
            int version = hdr.get() & 0xFF;
            int msgType = hdr.get() & 0xFF;
            int deviceId = hdr.getShort() & 0xFFFF;
            long sequence = hdr.getInt() & 0xFFFFFFFFL;
            int payloadLen = hdr.getShort() & 0xFFFF;
            if (version < 1 || version > VERSION_MAX
                    || payloadLen > MAX_PAYLOAD) {
                pushBack(pin, rest, null, null);
                return null;
            }
            byte[] payload = readFully(in, payloadLen);
            byte[] crcBytes = readFully(in, 4);
            long wireCrc = ByteBuffer.wrap(crcBytes)
                    .order(ByteOrder.LITTLE_ENDIAN)
                    .getInt() & 0xFFFFFFFFL;

            CRC32 crc = new CRC32();
            crc.update(new byte[]{(byte) (MAGIC & 0xFF),
                                  (byte) ((MAGIC >> 8) & 0xFF)});
            crc.update(rest);
            crc.update(payload);
            if (crc.getValue() != wireCrc) {
                pushBack(pin, rest, payload, crcBytes);
                return null; // corrupted frame — skip, keep reading
            }
            return new PolariPacket(version, msgType, deviceId, sequence,
                                    payload);
        }
    }

    /** Push back everything after the rejected candidate's first byte. */
    private static void pushBack(PushbackInputStream pin, byte[] rest,
                                 byte[] payload, byte[] crc)
            throws IOException {
        if (pin == null) return;
        int n = 1 + rest.length + (payload == null ? 0 : payload.length)
                + (crc == null ? 0 : crc.length);
        byte[] all = new byte[n];
        all[0] = (byte) ((MAGIC >> 8) & 0xFF);
        System.arraycopy(rest, 0, all, 1, rest.length);
        int off = 1 + rest.length;
        if (payload != null) {
            System.arraycopy(payload, 0, all, off, payload.length);
            off += payload.length;
        }
        if (crc != null) System.arraycopy(crc, 0, all, off, crc.length);
        pin.unread(all);
    }

    private static byte[] readFully(InputStream in, int n)
            throws IOException {
        byte[] out = new byte[n];
        int off = 0;
        while (off < n) {
            int got = in.read(out, off, n - off);
            if (got < 0) throw new EOFException("packet stream ended");
            off += got;
        }
        return out;
    }
}
'''

DEVICE_PORT_JAVA = r'''package org.polari.bridge;

/**
 * The ONE seam between the bridge and a device, and it is
 * BIDIRECTIONAL: telemetry packets come up via next(), command
 * packets go down via send(). The simulated MCU today and the real
 * serial device later are the same interface — flipping the
 * `source` knob changes nothing else in the app.
 */
public interface DevicePort extends AutoCloseable {
    /**
     * Next telemetry packet (blocking). Null means a corrupted
     * frame was skipped; java.io.EOFException means the port ended.
     */
    PolariPacket next() throws Exception;

    /** Send a command packet down to the device. */
    void send(PolariPacket packet) throws Exception;

    /**
     * grpc-j4: send to the interface bound as instance `index` of
     * `objectClass` (BindingRouter routes to that binding's port); a
     * single-port device just sends.
     */
    default void sendTo(String objectClass, int index,
                        PolariPacket packet) throws Exception {
        send(packet);
    }

    /**
     * ucd-0e3 bridge lifecycle: how many times this port's physical
     * connection was lost and reopened. 0 for a port that never
     * disconnects (the simulated MCU).
     */
    default long reconnects() {
        return 0;
    }

    String describe();

    @Override
    default void close() throws Exception {
    }
}
'''

SIMULATED_DEVICE_JAVA = r'''package org.polari.bridge;

import java.io.ByteArrayInputStream;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The built-in synthetic MCU — the internal-simulation phase of the
 * Polari Hardware Bridge. Emits sample records for every registered
 * msg_type at a fixed rate, running every frame through the REAL
 * wire framing (encode -> parse) so the simulation exercises the
 * exact path real hardware will.
 *
 * It also ACCEPTS commands, like a real device: a command packet
 * for a msg_type replaces that class's state, and every subsequent
 * telemetry frame for it reflects the commanded state — so the full
 * Polari -> gRPC -> packet -> device -> telemetry -> Polari round
 * trip is provable with no hardware attached.
 */
public final class SimulatedDevice implements DevicePort {
    private final int deviceId;
    private final int rateHz;
    private final long frameIntervalNanos;
    private final int[] msgTypes = CodecRegistry.msgTypes();
    private final Map<Integer, byte[]> commandedState =
            new ConcurrentHashMap<>();
    private long seq = 0;
    private long nextDue = System.nanoTime();

    public SimulatedDevice(int deviceId, int rateHz) {
        this.deviceId = deviceId;
        this.rateHz = rateHz;
        this.frameIntervalNanos =
                rateHz > 0 ? 1_000_000_000L / rateHz : 0;
    }

    @Override
    public PolariPacket next() throws Exception {
        if (frameIntervalNanos > 0) {
            long wait = nextDue - System.nanoTime();
            if (wait > 0) {
                Thread.sleep(wait / 1_000_000L,
                             (int) (wait % 1_000_000L));
            }
            nextDue += frameIntervalNanos;
        }
        int msgType = msgTypes[(int) (seq % msgTypes.length)];
        byte[] state = commandedState.get(msgType);
        byte[] payload = state != null
                ? state
                : CodecRegistry.sampleFrame(msgType, seq);
        byte[] wire = new PolariPacket(msgType, deviceId, seq, payload)
                .encode();
        seq++;
        return PolariPacket.read(new ByteArrayInputStream(wire));
    }

    @Override
    public void send(PolariPacket packet) {
        // the MCU applies the command: state = the commanded struct
        commandedState.put(packet.msgType, packet.payload);
    }

    @Override
    public String describe() {
        return "simulated MCU (" + msgTypes.length
                + " msg types @ " + rateHz + " Hz)";
    }
}
'''

SERIAL_PORT_JAVA = r'''package org.polari.bridge;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.PushbackInputStream;

/**
 * A USB CDC-ACM serial device (/dev/ttyACM*), both directions.
 * Plain file I/O — the kernel's cdc_acm driver does the transport;
 * stty puts the line in raw mode first. No native libraries, no
 * custom kernel module.
 *
 * ucd-0e3 bridge lifecycle: a lost connection (EOF or any IOException
 * while reading) never crashes the bridge — the stream is closed,
 * logged, and REOPENED with backoff (0.5s, 1, 2, 4, capped at 8s;
 * forever). Every successful (re)open requests a SNAPSHOT from every
 * exposed class that declares one (CodecRegistry's generated
 * knowledge — HAS_SNAPSHOT_COMMAND); a class without a `snapshot`
 * field gets nothing sent.
 */
public final class SerialCdcPort implements DevicePort {
    /**
     * Test seam (package-private): how open() gets its raw streams.
     * `attempt` is the 0-based count of opens so far. Production code
     * never supplies one — the real CDC-ACM path (RealOpener) is used.
     */
    interface Opener {
        InputStream[] openInput(String device, int baud, int attempt)
                throws Exception;

        OutputStream openOutput(String device, int attempt)
                throws Exception;
    }

    private final String device;
    private final int baud;
    private final Opener opener;
    private PushbackInputStream in;
    private OutputStream out;
    private long framesSinceOpen;
    private int openAttempts;
    private long reconnectCount;

    public SerialCdcPort(String device, int baud) throws Exception {
        this(device, baud, null);
    }

    SerialCdcPort(String device, int baud, Opener opener) throws Exception {
        this.device = device;
        this.baud = baud;
        this.opener = opener != null ? opener : new RealOpener();
        open();
    }

    private void open() throws Exception {
        InputStream[] raw = opener.openInput(device, baud, openAttempts);
        InputStream first = raw[0];
        this.in = first instanceof PushbackInputStream
                ? (PushbackInputStream) first
                : new PushbackInputStream(first,
                        PolariPacket.HEADER_LEN + PolariPacket.MAX_PAYLOAD + 4);
        this.out = opener.openOutput(device, openAttempts);
        framesSinceOpen = 0;
        openAttempts++;
        System.out.println("{\"t\":\"serial-open\",\"device\":\""
                + device + "\",\"attempt\":" + openAttempts + "}");
        requestSnapshots();
    }

    /** ucd-0e3: SNAPSHOT on attach — one command frame per exposed
     *  class that declares a `snapshot` field; nothing for a class
     *  that does not. */
    private void requestSnapshots() throws Exception {
        for (int msgType : CodecRegistry.msgTypes()) {
            if (!CodecRegistry.hasSnapshotCommand(msgType)) continue;
            PolariPacket pkt = CodecRegistry.snapshotPacket(msgType, 0);
            if (pkt == null) continue;
            send(pkt);
            System.out.println("{\"t\":\"snapshot-requested\"}");
        }
    }

    @Override
    public PolariPacket next() throws Exception {
        while (true) {
            try {
                PolariPacket p = PolariPacket.read(in);
                framesSinceOpen++;
                return p;
            } catch (IOException lost) {  // EOFException IS an IOException
                System.out.println("{\"t\":\"serial-lost\",\"device\":\""
                        + device + "\",\"after_frames\":" + framesSinceOpen
                        + "}");
                closeQuiet();
                reconnectCount++;
                reopenWithBackoff();
            }
        }
    }

    /** Reopen forever, 0.5s / 1 / 2 / 4, capped at 8s between tries —
     *  a reconnect, never a crash. */
    private void reopenWithBackoff() throws Exception {
        long backoffMs = 500;
        while (true) {
            try {
                open();
                return;
            } catch (Exception failed) {
                try {
                    Thread.sleep(backoffMs);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw failed;
                }
                backoffMs = Math.min(backoffMs * 2, 8000);
            }
        }
    }

    private void closeQuiet() {
        try {
            if (in != null) in.close();
        } catch (Exception ignore) {
            // best-effort: the stream is already gone
        }
        try {
            if (out != null) out.close();
        } catch (Exception ignore) {
            // best-effort: the stream is already gone
        }
    }

    @Override
    public synchronized void send(PolariPacket packet) throws Exception {
        out.write(packet.encode());
        out.flush();
    }

    @Override
    public long reconnects() {
        return reconnectCount;
    }

    @Override
    public String describe() {
        return "serial " + device;
    }

    @Override
    public void close() throws Exception {
        closeQuiet();
    }

    /** Production path: stty raw mode, then plain CDC-ACM file I/O —
     *  the device path, baud and dialout check are unchanged. */
    private static final class RealOpener implements Opener {
        @Override
        public InputStream[] openInput(String device, int baud,
                                       int attempt) throws Exception {
            Process stty = new ProcessBuilder(
                    "stty", "-F", device, "raw", "-echo",
                    String.valueOf(baud)).inheritIO().start();
            if (stty.waitFor() != 0) {
                throw new IllegalStateException(
                        "stty failed for " + device
                        + " — is the device present and are you in the "
                        + "dialout group?");
            }
            return new InputStream[]{new FileInputStream(device)};
        }

        @Override
        public OutputStream openOutput(String device, int attempt)
                throws Exception {
            return new FileOutputStream(device);
        }
    }
}
'''

SEQUENCE_TRACKER_JAVA = r'''package org.polari.bridge;

import java.util.HashMap;
import java.util.Map;

/**
 * ucd-0e3 bridge lifecycle: per msg_type sequence-gap counting, plus
 * reboot-vs-reconnect by `boot_session` (CodecRegistry.hasBootSession
 * names which classes carry the field — a class without it is inert
 * to the reboot rule, only gap/reorder counting applies).
 *
 * Boot session != packet sequence: a NEW boot_session for a msg_type
 * is a REBOOT — fresh state, sequence tracking resets for EVERY
 * msg_type (no gap counted across it). The SAME boot_session with
 * sequence > last+1 is a transport loss (gapsSeen/framesLost). The
 * SAME boot_session with sequence <= last is a duplicate/out-of-order
 * frame (reordered) — still forwarded by the caller, never dropped.
 */
public final class SequenceTracker {
    public static final class Result {
        public final boolean reboot;
        public final long gap;
        public final boolean reordered;
        public final Long previousBootSession;

        Result(boolean reboot, long gap, boolean reordered,
               Long previousBootSession) {
            this.reboot = reboot;
            this.gap = gap;
            this.reordered = reordered;
            this.previousBootSession = previousBootSession;
        }
    }

    private final Map<Integer, Long> lastSeq = new HashMap<>();
    private final Map<Integer, Long> lastBoot = new HashMap<>();
    public long gapsSeen;
    public long framesLost;
    public long reordered;
    public long reboots;

    /** `bootSession` is null for a class with no boot_session field —
     *  the reboot rule is inert for it; only gap/reorder applies. */
    public Result observe(int msgType, long sequence, Long bootSession) {
        boolean isReboot = false;
        Long previous = null;
        if (bootSession != null) {
            Long prevBoot = lastBoot.get(msgType);
            if (prevBoot != null && !prevBoot.equals(bootSession)) {
                isReboot = true;
                previous = prevBoot;
                reboots++;
                lastSeq.clear();   // a reboot resets tracking for EVERY msg_type
            }
            lastBoot.put(msgType, bootSession);
        }
        long gap = 0;
        boolean isReordered = false;
        if (!isReboot) {
            Long prevSeq = lastSeq.get(msgType);
            if (prevSeq != null) {
                if (sequence > prevSeq + 1) {
                    gap = sequence - prevSeq - 1;
                    gapsSeen++;
                    framesLost += gap;
                } else if (sequence <= prevSeq) {
                    isReordered = true;
                    reordered++;
                }
            }
        }
        lastSeq.put(msgType, sequence);
        return new Result(isReboot, gap, isReordered, previous);
    }
}
'''

LIFECYCLE_SELFTEST_JAVA = r'''package org.polari.bridge;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * ucd-0e3 bridge lifecycle, proven generically against whichever
 * classes THIS bridge carries (CodecRegistry's generated knowledge
 * decides which cases exercise a real class; a bridge with no
 * boot_session / snapshot field prints an honest SKIP for those two
 * — never a guess):
 *
 *  (a) reconnect: a lost stream is reopened with backoff, never a
 *      crash — every frame still forwarded, no gap across it;
 *  (b) sequence-gap counting (generic: needs no class at all);
 *  (c) reboot vs reconnect by `boot_session` (needs a class that
 *      declares one);
 *  (d) SNAPSHOT requested on every (re)attach (needs a class that
 *      declares `snapshot`).
 */
public final class LifecycleSelfTest {
    public static void main(String[] args) throws Exception {
        int failures = 0;
        failures += testReconnect();
        failures += testGap();
        failures += testReboot();
        failures += testSnapshotOnAttach();
        if (failures > 0) {
            System.out.println("LIFECYCLE FAILED: " + failures);
            System.exit(1);
        }
        System.out.println("LIFECYCLE OK");
    }

    private static int firstMsgType() {
        int[] types = CodecRegistry.msgTypes();
        return types.length > 0 ? types[0] : -1;
    }

    /** (a) a stream that ends after frames 50,51; a second stream that
     *  continues with 52 — serial-lost then serial-open attempt=2, no
     *  gap, all 3 frames forwarded. */
    private static int testReconnect() {
        int msgType = firstMsgType();
        if (msgType < 0) {
            System.out.println(
                    "SKIP: lifecycle reconnect — no exposed class");
            return 0;
        }
        PrintStream prev = System.out;
        try {
            byte[] f50 = new PolariPacket(msgType, 7, 50,
                    CodecRegistry.sampleFrame(msgType, 50)).encode();
            byte[] f51 = new PolariPacket(msgType, 7, 51,
                    CodecRegistry.sampleFrame(msgType, 51)).encode();
            byte[] f52 = new PolariPacket(msgType, 7, 52,
                    CodecRegistry.sampleFrame(msgType, 52)).encode();
            final byte[] stream1 = concat(f50, f51);
            final byte[] stream2 = f52;

            ByteArrayOutputStream log = new ByteArrayOutputStream();
            System.setOut(new PrintStream(log, true));
            SerialCdcPort port = new SerialCdcPort("test-device", 115200,
                    new SerialCdcPort.Opener() {
                        @Override
                        public InputStream[] openInput(String device,
                                int baud, int attempt) {
                            return new InputStream[]{new ByteArrayInputStream(
                                    attempt == 0 ? stream1 : stream2)};
                        }

                        @Override
                        public OutputStream openOutput(String device,
                                int attempt) {
                            return new ByteArrayOutputStream();
                        }
                    });
            List<Long> seqs = new ArrayList<>();
            for (int i = 0; i < 3; i++) {
                PolariPacket p = port.next();
                if (p != null) seqs.add(p.sequence);
            }
            System.setOut(prev);
            String logged = log.toString();
            boolean ok = seqs.equals(Arrays.asList(50L, 51L, 52L))
                    && port.reconnects() == 1
                    && logged.contains("\"t\":\"serial-lost\"")
                    && logged.contains("\"t\":\"serial-open\",\"device\":"
                            + "\"test-device\",\"attempt\":2");
            System.out.println((ok ? "PASS" : "FAIL")
                    + ": lifecycle reconnect seqs=" + seqs
                    + " reconnects=" + port.reconnects());
            return ok ? 0 : 1;
        } catch (Exception e) {
            System.setOut(prev);
            System.out.println("FAIL: lifecycle reconnect threw " + e);
            return 1;
        }
    }

    /** (b) 50, 51, 55 on one msg_type — gapsSeen 1, framesLost 3. */
    private static int testGap() {
        SequenceTracker t = new SequenceTracker();
        t.observe(1, 50, null);
        t.observe(1, 51, null);
        t.observe(1, 55, null);
        boolean ok = t.gapsSeen == 1 && t.framesLost == 3;
        System.out.println((ok ? "PASS" : "FAIL")
                + ": lifecycle gap gapsSeen=" + t.gapsSeen
                + " framesLost=" + t.framesLost);
        return ok ? 0 : 1;
    }

    /** (c) boot_session A: 10,11 then B: 1,2 — device-reboot, no gap
     *  across the boundary, reboots=1. Runs against a real class of
     *  this bridge when one declares boot_session; none (today: every
     *  shipped class) skips honestly. */
    private static int testReboot() {
        int msgType = -1;
        for (int mt : CodecRegistry.msgTypes()) {
            if (CodecRegistry.hasBootSession(mt)) {
                msgType = mt;
                break;
            }
        }
        if (msgType < 0) {
            System.out.println("SKIP: lifecycle reboot — no class on "
                    + "this bridge declares boot_session");
            return 0;
        }
        try {
            SequenceTracker t = new SequenceTracker();
            PolariPacket p10 = withBootSessionPacket(msgType, 10, 100L);
            PolariPacket p11 = withBootSessionPacket(msgType, 11, 100L);
            PolariPacket p1 = withBootSessionPacket(msgType, 1, 200L);
            PolariPacket p2 = withBootSessionPacket(msgType, 2, 200L);

            observeOne(t, p10);
            observeOne(t, p11);
            SequenceTracker.Result r = observeOne(t, p1);
            observeOne(t, p2);

            boolean ok = r.reboot && t.gapsSeen == 0 && t.reboots == 1;
            System.out.println((ok ? "PASS" : "FAIL")
                    + ": lifecycle reboot reboot=" + r.reboot
                    + " gapsSeen=" + t.gapsSeen + " reboots=" + t.reboots);
            return ok ? 0 : 1;
        } catch (Exception e) {
            System.out.println("FAIL: lifecycle reboot threw " + e);
            return 1;
        }
    }

    private static PolariPacket withBootSessionPacket(int msgType, long seq,
            long bootSession) throws Exception {
        byte[] payload = CodecRegistry.withBootSession(msgType, seq,
                bootSession);
        byte[] wire = new PolariPacket(CodecRegistry.wireVersionOf(msgType),
                msgType, 7, seq, payload).encode();
        return PolariPacket.read(new ByteArrayInputStream(wire));
    }

    private static SequenceTracker.Result observeOne(SequenceTracker t,
            PolariPacket p) {
        Long boot = CodecRegistry.hasBootSession(p.msgType)
                ? CodecRegistry.bootSessionOf(p.msgType, p) : null;
        return t.observe(p.msgType, p.sequence, boot);
    }

    /** (d) the first bytes written to the port after open ARE the
     *  snapshot command — for whichever class of this bridge declares
     *  `snapshot` (none: nothing written, SKIP honestly). */
    private static int testSnapshotOnAttach() {
        boolean any = false;
        for (int mt : CodecRegistry.msgTypes()) {
            if (CodecRegistry.hasSnapshotCommand(mt)) {
                any = true;
                break;
            }
        }
        if (!any) {
            System.out.println("SKIP: lifecycle snapshot-on-attach — no "
                    + "class on this bridge declares `snapshot`");
            return 0;
        }
        PrintStream prev = System.out;
        try {
            final ByteArrayOutputStream capturedOut =
                    new ByteArrayOutputStream();
            ByteArrayOutputStream log = new ByteArrayOutputStream();
            System.setOut(new PrintStream(log, true));
            new SerialCdcPort("test-device", 115200,
                    new SerialCdcPort.Opener() {
                        @Override
                        public InputStream[] openInput(String device,
                                int baud, int attempt) {
                            return new InputStream[]{
                                    new ByteArrayInputStream(new byte[0])};
                        }

                        @Override
                        public OutputStream openOutput(String device,
                                int attempt) {
                            return capturedOut;
                        }
                    });
            System.setOut(prev);
            byte[] written = capturedOut.toByteArray();
            String logged = log.toString();
            PolariPacket cmd = written.length > 0
                    ? PolariPacket.read(new ByteArrayInputStream(written))
                    : null;
            boolean ok = cmd != null
                    && CodecRegistry.hasSnapshotCommand(cmd.msgType)
                    && CodecRegistry.describe(cmd).contains("snapshot=true")
                    && logged.contains("\"t\":\"snapshot-requested\"");
            System.out.println((ok ? "PASS" : "FAIL")
                    + ": lifecycle snapshot-on-attach "
                    + (cmd != null ? CodecRegistry.describe(cmd)
                                   : "(nothing written)"));
            return ok ? 0 : 1;
        } catch (Exception e) {
            System.setOut(prev);
            System.out.println(
                    "FAIL: lifecycle snapshot-on-attach threw " + e);
            return 1;
        }
    }

    private static byte[] concat(byte[]... parts) {
        int n = 0;
        for (byte[] p : parts) n += p.length;
        byte[] out = new byte[n];
        int off = 0;
        for (byte[] p : parts) {
            System.arraycopy(p, 0, out, off, p.length);
            off += p.length;
        }
        return out;
    }
}
'''

BRIDGE_CONFIG_JAVA = r'''package org.polari.bridge;

import java.io.FileInputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

/** bridge.properties, parsed. Every knob has a safe default. */
public final class BridgeConfig {
    /** grpc-j4: this bridge's name + its hardware-interface bindings. */
    public final String bridgeName;
    public final List<BridgeBinding> bindings = new ArrayList<>();
    public final String source;        // simulated | serial
    public final String serialDevice;
    public final int baud;
    public final int simRateHz;        // 0 = as fast as possible
    public final long maxFrames;       // 0 = run forever
    public final int deviceId;
    public final boolean grpcEnabled;
    public final String grpcTarget;

    private BridgeConfig(Properties p) {
        this.source = p.getProperty("source", "simulated");
        this.serialDevice =
                p.getProperty("serial.device", "/dev/ttyACM0");
        this.baud = Integer.parseInt(
                p.getProperty("serial.baud", "115200"));
        this.simRateHz = Integer.parseInt(
                p.getProperty("sim.rate_hz", "10"));
        this.maxFrames = Long.parseLong(
                p.getProperty("max_frames", "0"));
        this.deviceId = Integer.parseInt(
                p.getProperty("device.id", "1"));
        this.grpcEnabled = Boolean.parseBoolean(
                p.getProperty("grpc.enabled", "false"));
        this.grpcTarget =
                p.getProperty("grpc.target", "localhost:3002");
        this.bridgeName = p.getProperty("bridge.name", "");
        int n = Integer.parseInt(p.getProperty("binding.count", "0"));
        for (int i = 0; i < n; i++) {
            bindings.add(BridgeBinding.from(p, "binding." + i + "."));
        }
    }

    /** The binding of instance `index` of `objectClass`, or null. */
    public BridgeBinding find(String objectClass, int index) {
        for (BridgeBinding b : bindings) {
            if (b.objectClass.equals(objectClass) && b.index == index) {
                return b;
            }
        }
        return null;
    }

    /** The binding of the row `objectName` of `objectClass`, or null. */
    public BridgeBinding findByObject(String objectClass,
                                      String objectName) {
        for (BridgeBinding b : bindings) {
            if (b.objectClass.equals(objectClass)
                    && b.objectName.equals(objectName)) {
                return b;
            }
        }
        return null;
    }

    public static BridgeConfig load(String path) throws Exception {
        Properties p = new Properties();
        try (FileInputStream in = new FileInputStream(path)) {
            p.load(in);
        }
        return new BridgeConfig(p);
    }
}
'''

BRIDGE_MAIN_JAVA = r'''package org.polari.bridge;

/**
 * The Polari Hardware Bridge: a lightweight headless app that lets
 * Polari communicate with hardware whenever it wants to. Long-term
 * an isle-app; today internal simulation software — the loop below
 * is identical for the simulated MCU and the real serial device.
 *
 * Up:   DevicePort -> PolariPacket -> per-class codec -> log line
 *       (+ gRPC Push into Polari when enabled).
 * Down: Polari's Commands stream -> proto -> struct -> PolariPacket
 *       -> DevicePort.send (wired by the forwarder when enabled).
 *
 * The gRPC forwarder is loaded reflectively so the core has ZERO
 * gRPC dependency unless grpc.enabled=true.
 *
 * Usage: java -jar polari-hw-bridge.jar [bridge.properties]
 *             [--max-frames=N]
 */
public final class BridgeMain {
    public static void main(String[] args) throws Exception {
        String configPath = "bridge.properties";
        long maxFramesOverride = -1;
        for (String a : args) {
            if (a.startsWith("--max-frames=")) {
                maxFramesOverride = Long.parseLong(
                        a.substring("--max-frames=".length()));
            } else if (!a.startsWith("--")) {
                configPath = a;
            }
        }
        BridgeConfig cfg = BridgeConfig.load(configPath);
        long maxFrames = maxFramesOverride >= 0
                ? maxFramesOverride : cfg.maxFrames;

        // grpc-j4: bindings → one port per bound interface, routed by
        // (class, instance index); none → the single legacy port.
        DevicePort port = !"serial".equals(cfg.source)
                ? new SimulatedDevice(cfg.deviceId, cfg.simRateHz)
                : cfg.bindings.isEmpty()
                ? new SerialCdcPort(cfg.serialDevice, cfg.baud)
                : new BindingRouter(cfg);

        Object forwarder = null;
        java.lang.reflect.Method push = null;
        if (cfg.grpcEnabled) {
            Class<?> f = Class.forName(
                    "org.polari.bridge.grpc.GrpcForwarder");
            forwarder = f.getConstructor(String.class,
                            DevicePort.class, BridgeConfig.class)
                    .newInstance(cfg.grpcTarget, port, cfg);
            push = f.getMethod("push", PolariPacket.class);
            f.getMethod("startCommands").invoke(forwarder);
        }

        System.out.println("[bridge] source=" + port.describe()
                + " grpc="
                + (cfg.grpcEnabled ? cfg.grpcTarget : "off"));

        // ucd-0e3 bridge lifecycle: per msg_type sequence-gap counting
        // + reboot vs reconnect by boot_session (inert for a class
        // with neither field — CodecRegistry's generated knowledge).
        SequenceTracker tracker = new SequenceTracker();

        long frames = 0, bytes = 0, corrupted = 0;
        long started = System.nanoTime();
        try {
            while (maxFrames == 0 || frames < maxFrames) {
                PolariPacket packet;
                try {
                    packet = port.next();
                } catch (java.io.EOFException end) {
                    System.out.println("[bridge] source ended");
                    break;
                }
                if (packet == null) {
                    corrupted++;
                    continue;
                }
                frames++;
                bytes += packet.wireLength();
                Long bootSession = CodecRegistry.hasBootSession(packet.msgType)
                        ? CodecRegistry.bootSessionOf(packet.msgType, packet)
                        : null;
                SequenceTracker.Result lc = tracker.observe(
                        packet.msgType, packet.sequence, bootSession);
                if (lc.reboot) {
                    System.out.println("{\"t\":\"device-reboot\","
                            + "\"boot_session\":" + bootSession
                            + ",\"previous\":" + lc.previousBootSession
                            + "}");
                }
                System.out.println("[bridge] seq=" + packet.sequence
                        + " device=" + packet.deviceId + " "
                        + (packet.version >= 2 ? "index="
                           + CodecRegistry.indexOf(packet) + " " : "")
                        + CodecRegistry.describe(packet)
                        + " gaps=" + tracker.gapsSeen
                        + " lost=" + tracker.framesLost
                        + " reordered=" + tracker.reordered
                        + " reboots=" + tracker.reboots
                        + " reconnects=" + port.reconnects());
                if (push != null) {
                    push.invoke(forwarder, packet);
                }
            }
        } finally {
            port.close();
        }
        double secs = (System.nanoTime() - started) / 1e9;
        System.out.printf(
                "[bridge] done: frames=%d bytes=%d corrupted=%d "
                + "in %.2fs (%.1f frames/s)%n",
                frames, bytes, corrupted, secs,
                frames / Math.max(secs, 1e-9));
    }
}
'''

LOOPBACK_SELFTEST_JAVA = r'''package org.polari.bridge;

import java.io.ByteArrayInputStream;

/**
 * Zero-dependency compile-and-run proof:
 *  1. every registered class round-trips
 *     sample -> payload -> wire frame -> parse -> decode,
 *  2. a corrupted CRC is rejected instead of yielding garbage,
 *  3. the COMMAND path works: a command packet sent to the
 *     simulated MCU changes the state its telemetry reports.
 */
public final class LoopbackSelfTest {
    public static void main(String[] args) throws Exception {
        int failures = 0;
        for (int msgType : CodecRegistry.msgTypes()) {
            String cls = CodecRegistry.className(msgType);
            byte[] payload = CodecRegistry.sampleFrame(msgType, 42);
            byte[] wire = new PolariPacket(msgType, 7, 42, payload)
                    .encode();
            PolariPacket parsed = PolariPacket.read(
                    new ByteArrayInputStream(wire));
            if (parsed == null || parsed.msgType != msgType
                    || parsed.deviceId != 7 || parsed.sequence != 42) {
                System.out.println("FAIL: frame round-trip " + cls);
                failures++;
                continue;
            }
            String line = CodecRegistry.decodeToLine(
                    parsed.msgType, parsed.payload);
            if (!line.startsWith(cls + "{")) {
                System.out.println("FAIL: decode " + cls + " -> "
                        + line);
                failures++;
                continue;
            }
            wire[wire.length - 1] ^= 0x55; // corrupt the CRC
            boolean rejected;
            try {
                rejected = PolariPacket.read(
                        new ByteArrayInputStream(wire)) == null;
            } catch (java.io.EOFException e) {
                rejected = true; // resync consumed the stream — fine
            }
            if (!rejected) {
                System.out.println(
                        "FAIL: corrupted CRC accepted for " + cls);
                failures++;
                continue;
            }
            System.out.println("PASS: " + cls + " " + line);
        }

        // command round-trip against the simulated MCU
        try (SimulatedDevice device = new SimulatedDevice(7, 0)) {
            int msgType = CodecRegistry.msgTypes()[0];
            byte[] commanded = CodecRegistry.sampleFrame(msgType,
                                                         12345);
            device.send(new PolariPacket(msgType, 7, 0, commanded));
            PolariPacket telemetry = null;
            for (int i = 0;
                 i <= CodecRegistry.msgTypes().length; i++) {
                telemetry = device.next();
                if (telemetry != null
                        && telemetry.msgType == msgType) break;
            }
            String expect = CodecRegistry.decodeToLine(msgType,
                                                       commanded);
            String got = telemetry == null ? "(none)"
                    : CodecRegistry.decodeToLine(telemetry.msgType,
                                                 telemetry.payload);
            if (!got.equals(expect)) {
                System.out.println("FAIL: command round-trip — "
                        + "telemetry " + got + " != commanded "
                        + expect);
                failures++;
            } else {
                System.out.println(
                        "PASS: command round-trip (telemetry "
                        + "reflects commanded state) " + got);
            }
        }

        // grpc-j4: wire v2 — every class through encodeV2 / decodeFrame
        // (a non-zero index where the width allows, field 0 absent)
        for (int msgType : CodecRegistry.msgTypes()) {
            String got = CodecRegistry.v2RoundTrip(msgType, 4242);
            if (got.startsWith("FAIL")) {
                System.out.println("FAIL: v2 round-trip — " + got);
                failures++;
            } else {
                System.out.println("PASS: v2 round-trip " + got);
            }
        }

        // grpc-j4 / brd-fi finding (3): garbage ending in the start
        // byte, then a frame, then a frame cut short, then a frame —
        // both whole frames survive on a pushback stream
        {
            int msgType = CodecRegistry.msgTypes()[0];
            byte[] good = new PolariPacket(msgType, 7, 50,
                    CodecRegistry.sampleFrame(msgType, 1)).encode();
            byte[] good2 = new PolariPacket(msgType, 7, 51,
                    CodecRegistry.sampleFrame(msgType, 2)).encode();
            java.io.ByteArrayOutputStream s =
                    new java.io.ByteArrayOutputStream();
            s.write(new byte[]{0x00, (byte) 0xFF, 0x4C});
            s.write(good);
            s.write(good, 0, Math.min(good.length - 1, 20));
            s.write(good2);
            s.write(new byte[64]);
            java.io.PushbackInputStream in = new java.io.PushbackInputStream(
                    new ByteArrayInputStream(s.toByteArray()), 8192);
            java.util.List<Long> seqs = new java.util.ArrayList<>();
            try {
                while (true) {
                    PolariPacket p = PolariPacket.read(in);
                    if (p != null) seqs.add(p.sequence);
                }
            } catch (java.io.EOFException end) {
                // stream consumed
            }
            if (seqs.equals(java.util.Arrays.asList(50L, 51L))) {
                System.out.println("PASS: resync keeps both frames " + seqs);
            } else {
                System.out.println("FAIL: resync kept " + seqs);
                failures++;
            }
        }

        if (failures > 0) {
            System.out.println("LOOPBACK FAILED: " + failures);
            System.exit(1);
        }
        System.out.println("LOOPBACK OK");
    }
}
'''

POM_XML = r'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.polari</groupId>
  <artifactId>polari-hw-bridge-__BRIDGE_NAME__</artifactId>
  <version>0.1.0</version>
  <packaging>jar</packaging>

  <properties>
    <maven.compiler.release>17</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <grpc.version>1.64.0</grpc.version>
    <protobuf.version>3.25.3</protobuf.version>
  </properties>

  <dependencies>
    <dependency>
      <groupId>io.grpc</groupId>
      <artifactId>grpc-netty-shaded</artifactId>
      <version>${grpc.version}</version>
    </dependency>
    <dependency>
      <groupId>io.grpc</groupId>
      <artifactId>grpc-protobuf</artifactId>
      <version>${grpc.version}</version>
    </dependency>
    <dependency>
      <groupId>io.grpc</groupId>
      <artifactId>grpc-stub</artifactId>
      <version>${grpc.version}</version>
    </dependency>
    <dependency>
      <groupId>com.google.protobuf</groupId>
      <artifactId>protobuf-java</artifactId>
      <version>${protobuf.version}</version>
    </dependency>
    <dependency>
      <groupId>org.apache.tomcat</groupId>
      <artifactId>annotations-api</artifactId>
      <version>6.0.53</version>
      <scope>provided</scope>
    </dependency>
  </dependencies>

  <build>
    <extensions>
      <extension>
        <groupId>kr.motd.maven</groupId>
        <artifactId>os-maven-plugin</artifactId>
        <version>1.7.1</version>
      </extension>
    </extensions>
    <plugins>
      <plugin>
        <!-- Pinned: Maven 3.6-era defaults ship compiler-plugin 3.1,
             which ignores maven.compiler.release and targets Java 5
             (build fails on any modern JDK). -->
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.13.0</version>
      </plugin>
      <plugin>
        <groupId>org.xolstice.maven.plugins</groupId>
        <artifactId>protobuf-maven-plugin</artifactId>
        <version>0.6.1</version>
        <configuration>
          <protocArtifact>com.google.protobuf:protoc:${protobuf.version}:exe:${os.detected.classifier}</protocArtifact>
          <pluginId>grpc-java</pluginId>
          <pluginArtifact>io.grpc:protoc-gen-grpc-java:${grpc.version}:exe:${os.detected.classifier}</pluginArtifact>
        </configuration>
        <executions>
          <execution>
            <goals>
              <goal>compile</goal>
              <goal>compile-custom</goal>
            </goals>
          </execution>
        </executions>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-shade-plugin</artifactId>
        <version>3.5.1</version>
        <executions>
          <execution>
            <phase>package</phase>
            <goals><goal>shade</goal></goals>
            <configuration>
              <finalName>polari-hw-bridge</finalName>
              <transformers>
                <transformer implementation="org.apache.maven.plugins.shade.resource.ManifestResourceTransformer">
                  <mainClass>org.polari.bridge.BridgeMain</mainClass>
                </transformer>
                <transformer implementation="org.apache.maven.plugins.shade.resource.ServicesResourceTransformer"/>
              </transformers>
            </configuration>
          </execution>
        </executions>
      </plugin>
    </plugins>
  </build>
</project>
'''

SYSTEMD_UNIT = r'''[Unit]
Description=Polari Hardware Bridge (__BRIDGE_NAME__)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/java -jar /opt/polari/bridge-__BRIDGE_NAME__/polari-hw-bridge.jar /opt/polari/bridge-__BRIDGE_NAME__/bridge.properties
Restart=on-failure
RestartSec=3
DynamicUser=yes
SupplementaryGroups=dialout
NoNewPrivileges=yes
ProtectSystem=strict
ReadOnlyPaths=/opt/polari/bridge-__BRIDGE_NAME__

[Install]
WantedBy=multi-user.target
'''

INSTALL_SH = r'''#!/bin/sh
# Install the Polari Hardware Bridge (__BRIDGE_NAME__) on Ubuntu.
# Run from the project root AFTER `mvn package` (needs Java 17+ and
# Maven; on a fresh box: sudo apt install openjdk-17-jre-headless
# and build the jar elsewhere, or apt install maven to build here).
set -eu

JAR=target/polari-hw-bridge.jar
DEST=/opt/polari/bridge-__BRIDGE_NAME__

if [ ! -f "$JAR" ]; then
    echo "missing $JAR — run: mvn package" >&2
    exit 1
fi
if ! command -v java >/dev/null 2>&1; then
    echo "java not found — run: sudo apt install openjdk-17-jre-headless" >&2
    exit 1
fi

sudo mkdir -p "$DEST"
sudo cp "$JAR" "$DEST/polari-hw-bridge.jar"
sudo cp bridge.properties "$DEST/bridge.properties"
sudo cp systemd/polari-hw-bridge-__BRIDGE_NAME__.service \
        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable polari-hw-bridge-__BRIDGE_NAME__.service
echo "installed. start with:"
echo "  sudo systemctl start polari-hw-bridge-__BRIDGE_NAME__"
echo "watch with:"
echo "  journalctl -fu polari-hw-bridge-__BRIDGE_NAME__"
'''

README_MD = r'''# Polari Hardware Bridge — __BRIDGE_NAME__

Generated by Polari (grpc-j1). A lightweight headless app that lets
Polari communicate with hardware whenever it wants to. Long-term an
isle-app; **today this is internal simulation software** — it ships
talking to a built-in simulated MCU, and moves to real hardware by
flipping ONE knob in `bridge.properties` (`source=serial`), nothing
else changes.

Both directions run through the same seam (`DevicePort`):

- **Telemetry up**: device packet -> struct codec -> proto -> gRPC
  `Push` into Polari.
- **Commands down**: Polari's gRPC `Commands` stream -> proto ->
  struct -> packet -> device. The simulated MCU applies commands to
  its state, which its next telemetry frames report.

## The three standardized layers

- **Physical**: USB CDC-ACM (`/dev/ttyACM0`) computer<->MCU; SPI
  MCU<->FPGA (out of scope for this app — the MCU handles it).
- **Transport**: the universal Polari packet
  (`magic|version|msg_type|device_id|sequence|len|payload|crc32`,
  little-endian) — every board uses the same framing.
- **Application**: the per-class binary structs in
  `src/main/java/org/polari/bridge/codec/` and the gRPC contracts in
  `src/main/proto/polari_bridge.proto`, BOTH generated from the same
  schema-stabilization snapshot in Polari — firmware, this bridge,
  and Polari agree by construction.

## Quick start (no Maven, no dependencies — core only)

    javac -d out $(find src/main/java -name '*.java' ! -path '*/grpc/*')
    java -cp out org.polari.bridge.LoopbackSelfTest
    java -cp out org.polari.bridge.BridgeMain bridge.properties --max-frames=20

## Full build (adds the gRPC forwarder, both directions)

    mvn package
    java -jar target/polari-hw-bridge.jar bridge.properties

Set `grpc.enabled=true` + `grpc.target=<host>:3002` to connect to
Polari's gRPC server (grpc-2): decoded telemetry is Pushed up and
the per-class Commands streams are wired down to the device.

## Install as a service (Ubuntu)

    ./install-ubuntu.sh
    sudo systemctl start polari-hw-bridge-__BRIDGE_NAME__

## Exposed classes (msg_type map)

__CLASS_TABLE__
'''
