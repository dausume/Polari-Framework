'''
@module grpcbridge.java_bridge_templates

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
  - grpcbridge.java_bridge (project assembly)
'''

POLARI_PACKET_JAVA = r'''package org.polari.bridge;

import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
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
 */
public final class PolariPacket {
    public static final int MAGIC = 0x504C; // "PL" (wire: 0x4C 0x50)
    public static final int VERSION = 1;
    public static final int HEADER_LEN = 12;

    public final int msgType;    // u8
    public final int deviceId;   // u16
    public final long sequence;  // u32
    public final byte[] payload;

    public PolariPacket(int msgType, int deviceId, long sequence,
                        byte[] payload) {
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
        buf.put((byte) VERSION);
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
     * (resync-safe on a noisy line). Returns null when the frame's
     * CRC or version is wrong — the caller counts and continues.
     * Throws EOFException when the stream ends.
     */
    public static PolariPacket read(InputStream in) throws IOException {
        while (true) {
            int b = in.read();
            if (b < 0) throw new EOFException("packet stream ended");
            if (b != (MAGIC & 0xFF)) continue;
            int b2 = in.read();
            if (b2 < 0) throw new EOFException("packet stream ended");
            if (b2 != ((MAGIC >> 8) & 0xFF)) continue;

            byte[] rest = readFully(in, HEADER_LEN - 2);
            ByteBuffer hdr = ByteBuffer.wrap(rest)
                    .order(ByteOrder.LITTLE_ENDIAN);
            int version = hdr.get() & 0xFF;
            int msgType = hdr.get() & 0xFF;
            int deviceId = hdr.getShort() & 0xFFFF;
            long sequence = hdr.getInt() & 0xFFFFFFFFL;
            int payloadLen = hdr.getShort() & 0xFFFF;
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
            if (crc.getValue() != wireCrc || version != VERSION) {
                return null; // corrupted frame — skip, keep reading
            }
            return new PolariPacket(msgType, deviceId, sequence,
                                    payload);
        }
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
import java.io.InputStream;
import java.io.OutputStream;

/**
 * A USB CDC-ACM serial device (/dev/ttyACM*), both directions.
 * Plain file I/O — the kernel's cdc_acm driver does the transport;
 * stty puts the line in raw mode first. No native libraries, no
 * custom kernel module.
 */
public final class SerialCdcPort implements DevicePort {
    private final String device;
    private final InputStream in;
    private final OutputStream out;

    public SerialCdcPort(String device, int baud) throws Exception {
        this.device = device;
        Process stty = new ProcessBuilder(
                "stty", "-F", device, "raw", "-echo",
                String.valueOf(baud)).inheritIO().start();
        if (stty.waitFor() != 0) {
            throw new IllegalStateException(
                    "stty failed for " + device
                    + " — is the device present and are you in the "
                    + "dialout group?");
        }
        this.in = new FileInputStream(device);
        this.out = new FileOutputStream(device);
    }

    @Override
    public PolariPacket next() throws Exception {
        return PolariPacket.read(in);
    }

    @Override
    public void send(PolariPacket packet) throws Exception {
        out.write(packet.encode());
        out.flush();
    }

    @Override
    public String describe() {
        return "serial " + device;
    }

    @Override
    public void close() throws Exception {
        in.close();
        out.close();
    }
}
'''

BRIDGE_CONFIG_JAVA = r'''package org.polari.bridge;

import java.io.FileInputStream;
import java.util.Properties;

/** bridge.properties, parsed. Every knob has a safe default. */
public final class BridgeConfig {
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

        DevicePort port = "serial".equals(cfg.source)
                ? new SerialCdcPort(cfg.serialDevice, cfg.baud)
                : new SimulatedDevice(cfg.deviceId, cfg.simRateHz);

        Object forwarder = null;
        java.lang.reflect.Method push = null;
        if (cfg.grpcEnabled) {
            Class<?> f = Class.forName(
                    "org.polari.bridge.grpc.GrpcForwarder");
            forwarder = f.getConstructor(String.class,
                            DevicePort.class)
                    .newInstance(cfg.grpcTarget, port);
            push = f.getMethod("push", PolariPacket.class);
            f.getMethod("startCommands").invoke(forwarder);
        }

        System.out.println("[bridge] source=" + port.describe()
                + " grpc="
                + (cfg.grpcEnabled ? cfg.grpcTarget : "off"));

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
                System.out.println("[bridge] seq=" + packet.sequence
                        + " device=" + packet.deviceId + " "
                        + CodecRegistry.decodeToLine(packet.msgType,
                                                     packet.payload));
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
