"""
@module board.custom.uart_sampling

tmp-6 (AI-Notes/plans/TEMPERATURE_PLAN.md): AN AVR USART RECEIVER SAMPLING A SENDER'S LINE, bit by bit, as the datasheet describes it - so a
byte that crosses between two clocks arrives as that receiver would latch it (intact, a wrong byte, a framing error, or not at all).

  receive(sender, rx_bit_s, u2x, phase=0.5, frame_bits=10) -> [{byte, fe, t, t_done, of}]   t = sample 1 of the start bit, t_done = the
        stop bit's last voting sample (when the byte is latched), of = the byte the sender meant
        sender = [(t_start_s, byte, bit_s)] - each frame a start bit (0), 8 data bits LSB first, a stop bit (1), every bit bit_s long; the
        line is high between frames. The receiver's sample clock ticks every rx_bit_s / S (S = 16, or 8 with U2X), its first tick `phase`
        of a tick after t = 0 (a knob: the sender's edge lands at an unknown phase of the sample clock). Start: a low sample after a high
        one is sample 1; samples SF, SF+1, SF+2 vote (majority) - high = a false start, scanning resumes. Every later bit votes on the
        same three samples of its own S-sample window; the stop bit voted low = a framing error (the byte is still latched). Scanning for
        the next start resumes right after the stop bit's last voting sample.
  window(u2x, phases=64) -> (rslow, rfast)   the sender/receiver rate ratios at which the worst pattern first fails at some phase, found by
                                             bisection on receive() itself
  model_limits(u2x, d=8) -> (rslow, rfast)   the same edges in closed form: Rslow = (D+1)S / (S + D S + SF) (the stop bit fails when its 2nd
                                             voting sample, SF+1, falls in the last data bit: a majority needs two), Rfast = (D+2)S / ((D+1)S +
                                             SF + 2) (the next frame's start must come after the last voting sample, SF+2, with sample 1 up to one
                                             sample late)
  rate_limits(u2x, d=8) -> (rslow, rfast)    DS40002061B section 20.8.3's own equations: Rslow = (D+1)S / (S-1 + D S + SF), Rfast = (D+2)S /
                                             ((D+1)S + SM). They sit ONE SAMPLE from model_limits on each side (8N1: 95.36 / 104.58 % against the
                                             model's 94.74 / 103.90 %; U2X 96.00 / 103.90 % against 94.74 / 102.56 %): the equations count the
                                             first voting sample for a slow sender and the middle one for a fast sender. Both are kept and shown;
                                             a run's bytes come from receive().

Source: Microchip ATmega48A/PA/88A/PA/168A/PA/328/P datasheet DS40002061B (2020), section 20.8.1 Asynchronous Clock Recovery (start bit
detection, samples 8, 9, 10 - or 4, 5, 6 with U2X - by majority), section 20.8.2 Asynchronous Data Recovery (the same three samples per
bit; the stop bit; "a new high to low transition ... can come right after the last of the bits used for majority voting"), section
20.8.3 (the equations above; S = 16 / 8, SF = 8 / 4, SM = 9 / 5). The ATmega16U2 (the UNO R3's USB-serial chip) has the same USART
receiver: Atmel ATmega8U2/16U2/32U2 datasheet 7799D-AVR-11/10, sections 18.8.1 - 18.8.3, pp. 161 - 164 (the same text, figures 18-5 ..
18-7 and equations; its Table 18-2 prints the same -4.54 % in the D = 8 row).
"""
import bisect

#: u2x -> (S samples per bit, SF the first voting sample, SM the middle one) - DS40002061B section 20.8.3
SAMPLING = {0: (16, 8, 9), 1: (8, 4, 5)}


def rate_limits(u2x, d=8):
    s, sf, sm = SAMPLING[1 if u2x else 0]
    return (d + 1) * s / float(s - 1 + d * s + sf), (d + 2) * s / float((d + 1) * s + sm)


def model_limits(u2x, d=8):
    s, sf, _ = SAMPLING[1 if u2x else 0]
    return (d + 1) * s / float(s + d * s + sf), (d + 2) * s / float((d + 1) * s + sf + 2)


class _Line(object):
    """The sender's line level at any time: high between frames, each frame's bits from its own start."""

    def __init__(self, sender, frame_bits):
        self.frames = sorted((float(t), int(b) & 0xFF, float(bit)) for t, b, bit in sender)
        self.starts = [f[0] for f in self.frames]
        self.n = frame_bits

    def level(self, t):
        i = bisect.bisect_right(self.starts, t) - 1
        if i < 0:
            return 1
        t0, b, bit = self.frames[i]
        k = int((t - t0) // bit)
        if k >= self.n:
            return 1
        if k == 0:
            return 0
        if k <= 8:
            return (b >> (k - 1)) & 1
        return 1

    def next_start(self, t):
        i = bisect.bisect_left(self.starts, t)
        return self.starts[i] if i < len(self.starts) else None


def receive(sender, rx_bit_s, u2x, phase=0.5, frame_bits=10):
    s, sf, _ = SAMPLING[1 if u2x else 0]
    tick = float(rx_bit_s) / s
    line = _Line(sender, frame_bits)
    if not line.frames:
        return []
    end = max(t + frame_bits * bit for t, _, bit in line.frames) + 2 * rx_bit_s

    def at(n):
        return (n + phase) * tick

    def vote(n):
        return 1 if sum(line.level(at(n + k)) for k in range(3)) >= 2 else 0

    out, n, prev = [], 0, 1
    while at(n) < end:
        lv = line.level(at(n))
        if prev and not lv:
            n0 = n                                    # sample 1 of the start bit
            if vote(n0 + sf - 1):
                n, prev = n0 + 1, 0                   # a false start: keep scanning
                continue
            byte = 0
            for k in range(1, 9):
                byte |= vote(n0 + k * s + sf - 1) << (k - 1)
            stop = vote(n0 + (frame_bits - 1) * s + sf - 1)
            src = line.frames[max(0, bisect.bisect_right(line.starts, at(n0)) - 1)]
            out.append({'byte': byte, 'fe': not stop, 't': at(n0), 't_done': at(n0 + (frame_bits - 1) * s + sf + 1), 'of': src[1]})
            n = n0 + (frame_bits - 1) * s + sf + 2   # right after the stop bit's last voting sample
            prev = line.level(at(n - 1))
            continue
        prev = lv
        if lv:                                        # idle high: jump to the next frame's start edge
            nxt = line.next_start(at(n))
            if nxt is None:
                break
            n = max(n + 1, int((nxt / tick) - phase))
            prev = line.level(at(n - 1)) if n > 0 else 1
        else:
            n += 1
    return out


def _worst_ok(ratio, u2x, phases):
    """True when, at every phase, both worst patterns arrive intact: a lone 0x00 (the slow sender's stop bit read in data bit 7) and two
    back-to-back 0xFF (the fast sender's next start bit read as the stop bit)."""
    rx_bit = 1.0
    bit = rx_bit / ratio
    for p in range(phases):
        ph = (p + 0.5) / phases
        slow = receive([(3.0, 0x00, bit)], rx_bit, u2x, ph)
        fast = receive([(3.0, 0xFF, bit), (3.0 + 10 * bit, 0xFF, bit)], rx_bit, u2x, ph)
        if [(r['byte'], r['fe']) for r in slow] != [(0x00, False)] or [(r['byte'], r['fe']) for r in fast] != [(0xFF, False)] * 2:
            return False
    return True


def window(u2x, phases=64, tol=1e-5):
    """(rslow, rfast) found by bisection on the sampling model - the measured edges of the receiver's window."""
    def edge(lo_ok, hi_bad):
        while abs(hi_bad - lo_ok) > tol:
            mid = 0.5 * (lo_ok + hi_bad)
            if _worst_ok(mid, u2x, phases):
                lo_ok = mid
            else:
                hi_bad = mid
        return lo_ok
    return edge(1.0, 0.8), edge(1.0, 1.2)
