# grpcbridge - cost of the hosted bridge (sim-2)

Measured 2026-10-19 on isle-core (6 cpus, 7.7 GB) against a throwaway container of the new image (`docker run -p 9872:9870 --memory 768m`), a real
uno-light twin session beside it on the board worker. Reproduce: `polari-rf-node/prf-bridge-engines/build.sh`, then
`BOARD_ENGINES_URL=... BRIDGE_ENGINES_URL=... PYTHONPATH=.:modules python3 -m grpcbridge.grpcbridge_hosted_selftest`.

| what | measured | how |
|---|---|---|
| image `prf-bridge-engines:trixie` | **505 607 418 B** (id 831ae65ada9b; the first build was 505 607 014 B, the cost block was measured on it). The warmed Maven repository is 47.1 MB of it (`du`: 51 MB); the rest is the Debian JDK 21 (`openjdk-21-jdk-headless` 83 MB download), Maven 3.9.9, python3-falcon + gunicorn | `docker image inspect`, `docker history` |
| uncached image build on isle-core | **5 min 39 s** (apt + the Maven warm-up; network-bound) | `time ./build.sh` |
| JDK, not JRE | the worker BUILDS the jar, and Maven needs `javac`, so the image carries `openjdk-21-jdk-headless`; the generated pom targets release 17 | Dockerfile |
| jar | **18 443 382 B** (the shaded `polari-hw-bridge.jar` of the uno-light project: grpc-java 1.64.0 + protobuf 3.25.3 + the generated codecs) | worker detail `jar_bytes` |
| jar build, uncached | **6.0 s** from `POST /bridges` to the process running (offline from the warmed repository; includes starting the JVM) | timer around `hosted_bridges.start` + polling |
| jar build, cached by the project's sha | **0.3 s** from `POST /bridges` to running (no mvn run) | same timer, second bridge of the same code |
| RSS of one hosted bridge, log-only (no gRPC classes loaded) | **49 908 kB** (JVM `-Xmx160m -XX:+UseSerialGC`), 50 088 kB ten seconds later | `/proc/<pid>/status` VmRSS via the worker detail |
| RSS of one hosted bridge, gRPC to the test node | **81 080 kB**, 81 720 kB ten seconds later | same |
| CPU of one hosted bridge | log-only: **0.56 CPU-s** at 20 s (JVM start-up), then **+0.16 CPU-s per 10 s** idle; with gRPC: **1.27 CPU-s** at 20 s, then **+0.23 CPU-s per 10 s** idle (about 2 % of one core) | `/proc/<pid>/stat` utime+stime |
| the container, one bridge, log-only | **47.8 MiB** of the 768 MiB cap (gunicorn worker included) | `docker stats --no-stream` |
| cap | `BRIDGES_MAX` = 6 per worker (6 x 81 MB = about 0.5 GB), compose limit 1024 MB | `bridge_hosted.py`, `docker-compose.hw-engines.yml` |
| latency, the whole path (test node, over the LAN) | press on the twin (PD2 0 then 1, 70 ms apart) -> the server's `LightState` row reads `toggles=1 source=button` in **146 ms**; `light-toggle` posted on the server -> the twin's PD6 falls **31 ms** after the post returns | `grpcbridge_hosted_selftest` proof |

Undetermined: CPU of a bridge while the board reports continuously (the light reports on change only, so idle numbers above are the whole load); the cost
of a first build when the Maven repository must be fetched online (the offline path covers every dependency the generated pom names; the online fallback
is in the worker but was not exercised).
