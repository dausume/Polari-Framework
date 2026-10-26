"""
@module instruments

Instruments — Bench instruments as rows: oscilloscope models with cited specs (channels, bandwidth, sample rate, depth, bits, LXI/SCPI transports), reachable endpoints typed at runtime, channel settings, and the CANONICAL WaveformCapture record (the IEEE 488.2 block kept verbatim plus the vendor preamble fields) that both the Agilent and Tektronix command lineages map onto. A DHO804 emulator (an SCPI server) feeds 4-channel captures from synthesised, replayed or device-derived signals so the same client, record and chart are proven before a real instrument is on the bench.
"""
from instruments.instruments_basis import *  # noqa: F401,F403
