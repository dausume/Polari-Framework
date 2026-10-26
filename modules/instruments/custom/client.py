"""
@module instruments.custom.client

osc-3 (OSCILLOSCOPE_PLAN.md §3d, D-osc-2): the oscilloscope CLIENT — reads a real or emulated Agilent-lineage scope (Rigol DHO / Keysight) into
the canonical capture. Two transports:
  * `scpi-raw` (default): a plain TCP socket, newline-terminated commands, the IEEE 488.2 block read by its header — stdlib only, so every
    selftest runs without a wheel; the DHO's port 5555 is the default port;
  * `vxi-11` / `hislip` / `usbtmc`: PyVISA + PyVISA-py (MIT) when importable — `TCPIP::<host>::INSTR`, `TCPIP::<host>::hislip0::INSTR`,
    `USB::...::INSTR` resource strings; without the wheels the client REFUSES by name (`ScopeRefusal`), never degrades silently.
    (This path is written to PyVISA's documented API — query / query_binary_values(header_fmt='ieee') — and is UNTESTED here: no wheel in the
    dev image yet, D-osc-6.)

  with ScopeClient(address, port=5555) as sc:
      sc.idn()                                   -> '<four fields>'
      sc.query(':ACQ:SRAT?')                     -> text
      sc.channel_settings(1)                     -> {scale_v_div, offset_v, coupling, bw_limit, probe}
      sc.read_channel(1, fmt='WORD', mode='RAW', page=250000, max_points=None) -> a canonical dict (fields + payload + sha256)
      sc.capture([1, 2, 3, 4])                   -> [canonical dict per channel] — ONE acquisition (`:STOP` first so every channel is the same shot)
A refusal reply where a block was expected ("The instruction is not supported!") raises ScopeRefusal with the words.
"""
import hashlib
import socket

from instruments.custom import scpi
from instruments.custom import lineage as L

DEFAULT_PORT = 5555
PAGE_POINTS = 250000      # scopehal's chunk; a scope that pages smaller is honoured by the preamble's own point count per page


class ScopeRefusal(Exception):
    pass


class ScopeClient:
    def __init__(self, address='127.0.0.1', port=DEFAULT_PORT, timeout=5.0, transport='scpi-raw', resource='', dialect='agilent'):
        self.address, self.port, self.timeout, self.transport, self.resource = address, int(port or DEFAULT_PORT), timeout, transport, resource
        self.dialect = dialect if dialect in ('agilent', 'tektronix') else 'agilent'    # which command tree + preamble lineage this instrument speaks
        self._sock = self._visa = None

    # ---------------------------------------------------------------- lifecycle
    def open(self):
        if self.transport == 'scpi-raw':
            self._sock = socket.create_connection((self.address, self.port), timeout=self.timeout)
            self._buf = b''
        else:
            try:
                import pyvisa
            except ImportError:
                raise ScopeRefusal('transport %s needs PyVISA + PyVISA-py (MIT) in the image; the wheels are not installed (D-osc-6)' % self.transport)
            rm = pyvisa.ResourceManager('@py')
            self._visa = rm.open_resource(self.resource or self.default_resource())
            self._visa.timeout = int(self.timeout * 1000)
        return self

    def default_resource(self):
        if self.transport == 'vxi-11':
            return 'TCPIP::%s::INSTR' % self.address
        if self.transport == 'hislip':
            return 'TCPIP::%s::hislip0::INSTR' % self.address
        return self.resource

    def close(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self._visa is not None:
            self._visa.close()
            self._visa = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    # ---------------------------------------------------------------- raw socket primitives
    def _readline(self):
        while b'\n' not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise ScopeRefusal('the instrument closed the connection')
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b'\n')
        return line.decode('utf-8', 'replace').rstrip('\r')

    def _readexact(self, n):
        while len(self._buf) < n:
            chunk = self._sock.recv(min(1 << 20, max(65536, n - len(self._buf))))
            if not chunk:
                raise ScopeRefusal('the instrument closed the connection mid-block')
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def write(self, cmd):
        if self._visa is not None:
            self._visa.write(cmd)
        else:
            self._sock.sendall((cmd + '\n').encode())

    def query(self, cmd):
        if self._visa is not None:
            return self._visa.query(cmd).strip()
        self.write(cmd)
        return self._readline()

    def query_block(self, cmd):
        """The IEEE 488.2 block a query answers -> payload bytes. A text reply instead (a refusal) raises ScopeRefusal with the words."""
        if self._visa is not None:
            return bytes(self._visa.query_binary_values(cmd, datatype='B', container=bytes, header_fmt='ieee', expect_termination=True))
        self.write(cmd)
        head = self._readexact(2)
        if head[:1] != b'#':
            rest = self._readline() if b'\n' in self._buf or True else ''
            raise ScopeRefusal((head + rest.encode()).decode('utf-8', 'replace').strip())
        n = scpi.block_header_length(head)
        count = int(self._readexact(n))
        payload = self._readexact(count)
        if self._buf[:1] == b'\n':
            self._buf = self._buf[1:]
        else:
            try:
                self._sock.settimeout(0.2)
                tail = self._sock.recv(1)
                if tail != b'\n':
                    self._buf = tail + self._buf
            except socket.timeout:
                pass
            finally:
                self._sock.settimeout(self.timeout)
        return payload

    # ---------------------------------------------------------------- the scope
    def idn(self):
        return self.query('*IDN?')

    def channel_settings(self, n):
        c = 'CHAN%d' % n
        return {'scale_v_div': float(self.query(':%s:SCALE?' % c)), 'offset_v': float(self.query(':%s:OFFS?' % c)),
                'coupling': self.query(':%s:COUP?' % c), 'bw_limit': self.query(':%s:BWL?' % c), 'probe': float(self.query(':%s:PROB?' % c)),
                'enabled': self.query(':%s:DISP?' % c) in ('1', 'ON')}

    def acquisition_info(self):
        return {'sample_rate_sps': float(self.query(':ACQ:SRAT?')), 'memory_depth_pts': float(self.query(':ACQ:MDEP?')),
                'trigger': {'mode': self.query(':TRIG:MODE?'), 'source': self.query(':TRIG:EDGE:SOUR?'), 'level': float(self.query(':TRIG:EDGE:LEV?')),
                            'slope': self.query(':TRIG:EDGE:SLOP?')}}

    def read_channel(self, n, fmt='WORD', mode='RAW', page=PAGE_POINTS, max_points=None):
        """One channel of the CURRENT acquisition, paged like scopehal does: WAV:SOUR, WAV:PRE?, then WAV:STAR/STOP/DATA? per page."""
        self.write(':WAV:SOUR CHAN%d' % n)
        self.write(':WAV:MODE %s' % mode)
        self.write(':WAV:FORM %s' % fmt)
        pre = L.parse_agilent_preamble(self.query(':WAV:PRE?'))
        total = int(self.query(':ACQ:MDEP?')) if mode == 'RAW' else pre['points']
        if max_points:
            total = min(total, int(max_points))
        bps = 2 if fmt == 'WORD' else 1
        chunks, got = [], 0
        while got < total:
            end = min(got + page, total)
            self.write(':WAV:STAR %d' % (got + 1))
            self.write(':WAV:STOP %d' % end)
            payload = self.query_block(':WAV:DATA?')
            if not payload:
                break
            chunks.append(payload)
            got += len(payload) // bps
        payload = b''.join(chunks)
        pre.update({'points': len(payload) // bps, 'format': fmt, 'channel': n, 'payload': payload,
                    'raw_sha256': hashlib.sha256(payload).hexdigest(), 'raw_bytes': len(payload)})
        return pre

    def capture(self, channels=(1, 2, 3, 4), fmt='WORD', mode='RAW', max_points=None):
        """ONE fresh acquisition with the asked channels on: each is switched on (as scopehal's EnableChannel does), then :SINGle and *OPC? -
        in NORMal trigger mode with no signal a real scope would wait, and the socket timeout then surfaces as the refusal (a knob later)."""
        if self.dialect == 'tektronix':
            return self.capture_tek(channels, width=2 if fmt in ('INT16', 'INT16_MSB') else 1, max_points=max_points)   # DAT:WID 1 unless 16-bit asked (scopehal's default)
        for n in channels:
            self.write(':CHAN%d:DISP ON' % n)
        self.write(':SINGle')
        self.query('*OPC?')
        info = self.acquisition_info()
        out = []
        for n in channels:
            r = self.read_channel(n, fmt=fmt, mode=mode, max_points=max_points)
            r.update(info)
            r['settings'] = self.channel_settings(n)
            out.append(r)
        return out

    # ---------------------------------------------------------------- the Tektronix dialect (scopehal TektronixOscilloscope.cpp, MSO5/6 path)
    def channel_settings_tek(self, n):
        c = 'CH%d' % n
        gain = float(self.query('%s:PRO:GAIN?' % c) or 1.0)
        return {'scale_v_div': float(self.query('%s:SCA?' % c)), 'offset_v': float(self.query('%s:OFFS?' % c)), 'coupling': self.query('%s:COUP?' % c),
                'bw_limit': self.query('%s:BAN?' % c), 'probe': (1.0 / gain) if gain else 1.0, 'enabled': self.query('DISP:WAVEV:%s:STATE?' % c) in ('1', 'ON')}

    def acquisition_info_tek(self):
        src = self.query('TRIG:A:EDGE:SOU?')
        return {'sample_rate_sps': float(self.query('HOR:MODE:SAMPLER?')), 'memory_depth_pts': float(self.query('HOR:MODE:RECO?')),
                'trigger': {'mode': self.query('TRIG:A:TYP?'), 'source': src, 'level': float(self.query('TRIG:A:LEV:%s?' % src)), 'slope': self.query('TRIG:A:EDGE:SLO?')}}

    def read_channel_tek(self, n, width=1, page=PAGE_POINTS, max_points=None):
        """DAT:SOU, DAT:WID, DAT:ENC SRI (signed little-endian), WFMO? (the preamble), then DAT:START/STOP + CURV? per page."""
        self.write('HEAD 0')
        self.write('DAT:SOU CH%d' % n)
        self.write('DAT:WID %d' % width)
        self.write('DAT:ENC SRI')
        pre = L.parse_tek_preamble(self.query('WFMO?'))
        total = int(float(self.query('HOR:MODE:RECO?')))
        if max_points:
            total = min(total, int(max_points))
        fmt = 'INT16' if width == 2 else 'INT8'
        chunks, got = [], 0
        while got < total:
            end = min(got + page, total)
            self.write('DAT:START %d' % (got + 1))
            self.write('DAT:STOP %d' % end)
            payload = self.query_block('CURV?')
            if not payload:
                break
            chunks.append(payload)
            got += len(payload) // width
        payload = b''.join(chunks)
        pre.update({'points': len(payload) // width, 'format': fmt, 'channel': n, 'payload': payload,
                    'raw_sha256': hashlib.sha256(payload).hexdigest(), 'raw_bytes': len(payload)})
        return pre

    def capture_tek(self, channels=(1, 2, 3, 4), width=1, max_points=None):
        for n in channels:
            self.write('DISP:WAVEV:CH%d:STATE ON' % n)
        self.write('ACQ:STOPA SEQ')
        self.write('ACQ:STATE ON')
        self.query('*OPC?')
        info = self.acquisition_info_tek()
        out = []
        for n in channels:
            r = self.read_channel_tek(n, width=width, max_points=max_points)
            r.update(info)
            r['settings'] = self.channel_settings_tek(n)
            out.append(r)
        return out
