"""
@module grpcbridge.custom.java_bridge_door

td-4 (AI-Notes/plans/TWIN_DOOR_PLAN.md sections 3, 3a, 5): the generated bridge's way THROUGH A TWIN DOOR - static Java sources, written beside
java_bridge_templates' TcpDevicePort.

  ISLE_TRUST_JAVA   IsleTrust: the PEM bundle a bridge trusts (ISLE_TRUST_BUNDLE, else /etc/isle-trust/ca-certificates.crt, else the JVM's own store). One place,
                    used by the twin door (wss) and by the gRPC channel (grpc.tls=verified).
  WS_PORT_JAVA      WsDevicePort: a twin session's serial stream as WebSocket binary frames (java.net.http, no new Maven dependency). The first frame is the
                    token as text; the frames and the lifecycle (lost -> reopen with backoff, snapshot on attach) are SerialCdcPort's, as for TcpDevicePort.
  TWIN_PORT_JAVA    TwinPort: which port a twin source opens, read from bridge.properties (`twin.uart` = tcp://host:port | wss://host/path; unset = the old
                    twin.host / twin.port). The token comes from the environment (TWIN_TOKEN), never from a file the bridge prints or a URL.

@consumers
  - grpcbridge.custom.java_bridge (project assembly)
"""

ISLE_TRUST_JAVA = r'''package org.polari.bridge;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.KeyStore;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.util.Base64;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

/**
 * td-4: WHOSE certificates this bridge trusts when it dials out over
 * TLS (a twin door, the Polari gRPC port with grpc.tls=verified).
 *
 * The PEM bundle named by the environment variable ISLE_TRUST_BUNDLE;
 * unset, the bundle at /etc/isle-trust/ca-certificates.crt when that
 * file is there (where an isle device keeps the system bundle with
 * the isle root in it); otherwise the JVM's own trust store. A bundle
 * that is NAMED but cannot be read is a refusal, never a quiet fall
 * back to something else. Verification is never turned off here.
 */
public final class IsleTrust {
    public static final String ENV = "ISLE_TRUST_BUNDLE";
    public static final String DEFAULT_PATH =
            "/etc/isle-trust/ca-certificates.crt";
    private static final Pattern CERT = Pattern.compile(
            "-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
            Pattern.DOTALL);

    private IsleTrust() {
    }

    /** The PEM bundle to trust, or null = the JVM's own trust store. */
    public static File bundle() throws IOException {
        String named = System.getenv(ENV);
        if (named != null && !named.isEmpty()) {
            File f = new File(named);
            if (!f.isFile() || !f.canRead()) {
                throw new IOException(ENV + " names " + named
                        + ", which is not a readable file: nothing is "
                        + "trusted in its place");
            }
            return f;
        }
        File usual = new File(DEFAULT_PATH);
        return usual.isFile() && usual.canRead() ? usual : null;
    }

    /** In words, for the bridge's own log. */
    public static String describe() {
        try {
            File pem = bundle();
            return pem == null ? "the JVM's own trust store"
                    : "the certificates in " + pem.getPath();
        } catch (IOException e) {
            return e.getMessage();
        }
    }

    public static SSLContext context() throws Exception {
        File pem = bundle();
        if (pem == null) {
            return SSLContext.getDefault();
        }
        KeyStore store = KeyStore.getInstance(KeyStore.getDefaultType());
        store.load(null, null);
        CertificateFactory x509 = CertificateFactory.getInstance("X.509");
        String text = new String(Files.readAllBytes(pem.toPath()),
                StandardCharsets.ISO_8859_1);
        Matcher m = CERT.matcher(text);
        int kept = 0;
        while (m.find()) {
            try {
                byte[] der = Base64.getMimeDecoder().decode(m.group(1));
                store.setCertificateEntry("bundle-" + kept,
                        x509.generateCertificate(
                                new ByteArrayInputStream(der)));
                kept++;
            } catch (CertificateException | IllegalArgumentException bad) {
                // one unreadable entry trusts nothing more; the rest stand
            }
        }
        if (kept == 0) {
            throw new IOException("no certificate could be read from "
                    + pem.getPath());
        }
        TrustManagerFactory tmf = TrustManagerFactory.getInstance(
                TrustManagerFactory.getDefaultAlgorithm());
        tmf.init(store);
        SSLContext ctx = SSLContext.getInstance("TLS");
        ctx.init(null, tmf.getTrustManagers(), null);
        return ctx;
    }
}
'''

WS_PORT_JAVA = r'''package org.polari.bridge;

import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.io.OutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.net.http.WebSocketHandshakeException;
import java.nio.ByteBuffer;
import java.time.Duration;
import java.util.Arrays;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

/**
 * td-4: a simulated device reached THROUGH A TWIN DOOR - the serial
 * stream of a twin session as WebSocket binary frames over HTTPS
 * (`twin.uart=wss://<door>/sessions/<id>/uart`). The worker's device
 * publishes no ports; the door is reached by name through its isle
 * agent, with a certificate checked against IsleTrust.
 *
 * The first frame is the session's token as text ({"token": "..."});
 * the door checks it and sends nothing back until the firmware
 * speaks. After that every binary frame is serial bytes, in order,
 * both ways. The frames, the codecs and the lifecycle ARE
 * SerialCdcPort's (as for TcpDevicePort): a lost connection is logged
 * (ws-lost), reopened with backoff, and every (re)attach requests a
 * SNAPSHOT from each class that declares one.
 *
 * What a reconnect cannot fix ends the port in words instead of
 * retrying forever (SerialCdcPort.Over): a refused token, an unknown
 * session, a newer connection that took the stream, a door that
 * answers HTTP 4xx. A certificate that does not verify refuses at the
 * first connect. Everything else the door says (the session's twin
 * closed the stream, the twin's port or the worker could not be
 * reached) is a lost connection.
 */
public final class WsDevicePort implements DevicePort {
    private final String url;
    private final SerialCdcPort inner;

    public WsDevicePort(String url, String token, int connectTimeoutS)
            throws Exception {
        this.url = url;
        URI uri = URI.create(url);
        String scheme = uri.getScheme() == null ? "" : uri.getScheme();
        String host = uri.getHost() == null ? "" : uri.getHost();
        boolean loopback = host.equals("127.0.0.1")
                || host.equals("localhost") || host.equals("[::1]");
        if (!scheme.equals("wss") && !(scheme.equals("ws") && loopback)) {
            throw new IllegalArgumentException("the twin door " + url
                    + " must be wss:// (ws:// is accepted for a loopback "
                    + "test only)");
        }
        HttpClient.Builder http = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5));
        if (scheme.equals("wss")) {
            http.sslContext(IsleTrust.context());
        }
        WsOpener opener = new WsOpener(http.build(), uri, token);
        long deadline = System.nanoTime()
                + connectTimeoutS * 1_000_000_000L;
        long backoffMs = 250;
        SerialCdcPort opened;
        while (true) {
            try {
                opened = new SerialCdcPort(url, 0, opener, "ws");
                break;
            } catch (Exception failed) {
                String certain = certain(failed);
                if (certain != null) {
                    throw new IOException("the twin door " + url
                            + " cannot be used: " + certain, failed);
                }
                if (System.nanoTime() + backoffMs * 1_000_000L > deadline) {
                    throw new IOException("cannot reach the twin door "
                            + url + " within " + connectTimeoutS + "s: "
                            + failed, failed);
                }
                Thread.sleep(backoffMs);
                backoffMs = Math.min(backoffMs * 2, 2000);
            }
        }
        this.inner = opened;
    }

    /** A failure that trying again cannot change, in words; or null. */
    private static String certain(Throwable failed) {
        for (Throwable t = failed; t != null; t = t.getCause()) {
            if (t instanceof javax.net.ssl.SSLException) {
                return "its certificate was not accepted (" + t.getMessage()
                        + "); trusted here: " + IsleTrust.describe();
            }
            if (t instanceof SerialCdcPort.Over) {
                return t.getMessage();
            }
        }
        return null;
    }

    @Override
    public PolariPacket next() throws Exception {
        try {
            return inner.next();
        } catch (SerialCdcPort.Over refused) {
            System.out.println("{\"t\":\"ws-refused\",\"code\":"
                    + refused.code + "}");
            inner.close();
            throw new EOFException(refused.getMessage());
        }
    }

    @Override
    public void send(PolariPacket packet) throws Exception {
        inner.send(packet);
    }

    @Override
    public long reconnects() {
        return inner.reconnects();
    }

    @Override
    public String describe() {
        return "twin-door " + url;
    }

    @Override
    public void close() throws Exception {
        inner.close();
    }

    private static final class End {
        final int code;
        final String reason;

        End(int code, String reason) {
            this.code = code;
            this.reason = reason == null ? "" : reason;
        }
    }

    /** One WebSocket per attempt: openInput dials and sends the token,
     *  openOutput hands back the same link's output. */
    private static final class WsOpener implements SerialCdcPort.Opener {
        private final HttpClient http;
        private final URI uri;
        private final String token;
        private Link current;

        WsOpener(HttpClient http, URI uri, String token) {
            this.http = http;
            this.uri = uri;
            this.token = token;
        }

        @Override
        public InputStream[] openInput(String device, int baud,
                                       int attempt) throws Exception {
            if (current != null) {
                current.abort();
            }
            Link link = new Link();
            try {
                link.ws = http.newWebSocketBuilder()
                        .connectTimeout(Duration.ofSeconds(5))
                        .buildAsync(uri, link).get(8, TimeUnit.SECONDS);
            } catch (ExecutionException e) {
                link.abort();
                Throwable cause = e.getCause() != null ? e.getCause() : e;
                if (cause instanceof WebSocketHandshakeException) {
                    int status = ((WebSocketHandshakeException) cause)
                            .getResponse().statusCode();
                    if (status >= 400 && status < 500) {
                        throw new SerialCdcPort.Over(status, "the door "
                                + "answered HTTP " + status + " instead of "
                                + "opening the stream (is the path "
                                + "/sessions/<id>/uart, and is the door "
                                + "deployed under that name?)");
                    }
                }
                throw new IOException(String.valueOf(cause), cause);
            } catch (Exception e) {
                link.abort();
                throw e;
            }
            try {
                link.ws.sendText("{\"token\":\""
                        + token.replace("\\", "\\\\").replace("\"", "\\\"")
                        + "\"}", true).get(5, TimeUnit.SECONDS);
            } catch (Exception e) {
                // a door that closes at once (an unknown session, 4404)
                // can beat the token to it: its reason is the answer,
                // not "the send failed"
                End said = link.said(2000);
                link.abort();
                if (said != null) {
                    throw Link.ended(said);
                }
                throw new IOException("the twin door did not take the "
                        + "token: " + e, e);
            }
            current = link;
            return new InputStream[]{link.in};
        }

        @Override
        public OutputStream openOutput(String device, int attempt) {
            return current.out;
        }
    }

    /** One open WebSocket: binary frames in -> a byte stream; bytes
     *  written -> one binary frame per write. */
    private static final class Link implements WebSocket.Listener {
        private final BlockingQueue<Object> queue =
                new LinkedBlockingQueue<>();
        volatile WebSocket ws;
        /** set when the door (or the network) ended this link */
        private volatile End closed;

        final InputStream in = new InputStream() {
            private byte[] chunk = new byte[0];
            private int at;
            private End end;

            private void fill() throws IOException {
                while (at >= chunk.length) {
                    if (end == null) {
                        Object got;
                        try {
                            got = queue.take();
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                            throw new InterruptedIOException();
                        }
                        if (got instanceof byte[]) {
                            chunk = (byte[]) got;
                            at = 0;
                            continue;
                        }
                        end = (End) got;
                    }
                    throw ended(end);
                }
            }

            @Override
            public int read() throws IOException {
                fill();
                return chunk[at++] & 0xFF;
            }

            @Override
            public int read(byte[] b, int off, int len) throws IOException {
                if (len == 0) {
                    return 0;
                }
                fill();
                int n = Math.min(len, chunk.length - at);
                System.arraycopy(chunk, at, b, off, n);
                at += n;
                return n;
            }

            @Override
            public void close() {
                abort();
            }
        };

        final OutputStream out = new OutputStream() {
            @Override
            public void write(int b) throws IOException {
                write(new byte[]{(byte) b}, 0, 1);
            }

            @Override
            public synchronized void write(byte[] b, int off, int len)
                    throws IOException {
                try {
                    ws.sendBinary(ByteBuffer.wrap(
                            Arrays.copyOfRange(b, off, off + len)), true)
                            .get(5, TimeUnit.SECONDS);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new InterruptedIOException();
                } catch (Exception e) {
                    End said = closed;
                    if (said != null) {
                        throw ended(said);   // the door's own reason
                    }
                    throw new IOException(
                            "the twin door did not take the bytes: " + e, e);
                }
            }

            @Override
            public void close() {
                abort();
            }
        };

        /** IOException = lost, reopen; SerialCdcPort.Over = never. */
        private static IOException ended(End end) {
            String said = end.reason.isEmpty() ? "" : ": " + end.reason;
            switch (end.code) {
                case 4400:
                    throw new SerialCdcPort.Over(4400, "the twin door did not "
                            + "accept the first frame as a token" + said);
                case 4401:
                    throw new SerialCdcPort.Over(4401, "the token did not reach "
                            + "the twin door in time" + said);
                case 4403:
                    throw new SerialCdcPort.Over(4403, "the twin door refused the "
                            + "token: TWIN_TOKEN is not this session's"
                            + said);
                case 4404:
                    throw new SerialCdcPort.Over(4404, "the twin door knows no "
                            + "such session: it ended, or the id in "
                            + "twin.uart is wrong" + said);
                case 4409:
                    throw new SerialCdcPort.Over(4409, "a newer connection took "
                            + "this session's serial stream (one bridge "
                            + "per session)" + said);
                default:
                    return new IOException("the twin door closed the "
                            + "connection (code " + end.code + said + ")");
            }
        }

        /** What the door said when it closed this link, waiting up to
         *  `ms` for it; null = it has not closed it. */
        End said(long ms) throws InterruptedException {
            long until = System.nanoTime() + ms * 1_000_000L;
            while (closed == null && System.nanoTime() < until) {
                Thread.sleep(20);
            }
            return closed;
        }

        void abort() {
            WebSocket w = ws;
            if (w != null) {
                w.abort();
            }
            queue.offer(new End(1006, "closed here"));
        }

        @Override
        public CompletionStage<?> onBinary(WebSocket webSocket,
                                           ByteBuffer data, boolean last) {
            byte[] bytes = new byte[data.remaining()];
            data.get(bytes);
            if (bytes.length > 0) {
                queue.offer(bytes);
            }
            webSocket.request(1);
            return null;
        }

        @Override
        public CompletionStage<?> onText(WebSocket webSocket,
                                         CharSequence data, boolean last) {
            webSocket.request(1);   // the door sends no text on uart
            return null;
        }

        @Override
        public CompletionStage<?> onClose(WebSocket webSocket, int code,
                                          String reason) {
            closed = new End(code, reason);
            queue.offer(closed);
            return null;
        }

        @Override
        public void onError(WebSocket webSocket, Throwable error) {
            closed = new End(1006, String.valueOf(error));
            queue.offer(closed);
        }
    }
}
'''

TWIN_PORT_JAVA = r'''package org.polari.bridge;

import java.net.URI;

/**
 * td-4: WHICH port a twin source opens, read from bridge.properties,
 * never guessed.
 *
 *   twin.uart=wss://<door>/sessions/<id>/uart   through the worker's
 *       twin door (WsDevicePort). The session's token comes from the
 *       environment variable TWIN_TOKEN: it is never written to a URL
 *       or printed.
 *   twin.uart=tcp://<host>:<port>               the session's raw
 *       serial port (TcpDevicePort): a worker that publishes its
 *       ports, the dev compose.
 *   twin.uart unset                             twin.host / twin.port,
 *       as before (TcpDevicePort).
 *
 * `source=twin-door` says in the properties that a door is meant: it
 * refuses a missing twin.uart instead of falling back to TCP.
 */
public final class TwinPort {
    public static final String TCP = "twin-tcp";
    public static final String DOOR = "twin-door";
    public static final String TOKEN_ENV = "TWIN_TOKEN";

    private TwinPort() {
    }

    public static boolean is(String source) {
        return TCP.equals(source) || DOOR.equals(source);
    }

    public static DevicePort open(BridgeConfig cfg) throws Exception {
        String uart = cfg.twinUart;
        if (uart.isEmpty()) {
            if (DOOR.equals(cfg.source)) {
                throw new IllegalArgumentException("source=twin-door needs "
                        + "twin.uart=wss://<door>/sessions/<id>/uart in "
                        + "bridge.properties");
            }
            return new TcpDevicePort(cfg.twinHost, cfg.twinPort,
                    cfg.twinConnectTimeoutS);
        }
        URI u = URI.create(uart);
        String scheme = u.getScheme() == null ? "" : u.getScheme();
        if (scheme.equals("tcp")) {
            if (DOOR.equals(cfg.source)) {
                throw new IllegalArgumentException("source=twin-door with "
                        + "twin.uart=" + uart + ": a door is wss://, the "
                        + "raw port is source=twin-tcp");
            }
            if (u.getHost() == null || u.getPort() < 1) {
                throw new IllegalArgumentException("twin.uart=" + uart
                        + " needs a host and a port (tcp://host:port)");
            }
            return new TcpDevicePort(u.getHost(), u.getPort(),
                    cfg.twinConnectTimeoutS);
        }
        if (scheme.equals("wss") || scheme.equals("ws")) {
            String token = System.getenv(TOKEN_ENV);
            if (token == null || token.isEmpty()) {
                throw new IllegalStateException("the twin door " + uart
                        + " needs the session's token in the environment "
                        + "variable " + TOKEN_ENV + " (it is never read "
                        + "from bridge.properties or a URL)");
            }
            return new WsDevicePort(uart, token, cfg.twinConnectTimeoutS);
        }
        throw new IllegalArgumentException("twin.uart=" + uart
                + " is neither tcp://host:port nor wss://host/path");
    }
}
'''
