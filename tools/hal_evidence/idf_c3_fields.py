"""READ-ONLY: dump ESP-IDF's ESP32-C3 register-header facts (field shift/width, register offsets) as TSV for econ's cross-check.
Reads only <IDF>/components/soc/esp32c3/register/soc/{ledc,apb_saradc,systimer,uart,interrupt_core0,system}_reg.h; writes stdout.
    docker run --rm --network none -v "$PWD":/chk:ro prf-esp-engines:noble python3 /chk/idf_c3_fields.py /opt/esp/idf > idf-c3-fields.tsv
"""
import hashlib, os, re, subprocess, sys
idf = sys.argv[1] if len(sys.argv) > 1 else '/opt/esp/idf'
d = os.path.join(idf, 'components/soc/esp32c3/register/soc')
try:
    ver = open(os.path.join(idf, 'version.txt')).read().strip()
except OSError:
    ver = subprocess.run(['git', '-C', idf, 'describe', '--tags'], capture_output=True, text=True).stdout.strip() or '?'
print('#idf\t%s' % ver)
for h in ('ledc_reg.h', 'apb_saradc_reg.h', 'systimer_reg.h', 'uart_reg.h', 'interrupt_core0_reg.h', 'system_reg.h'):
    p = os.path.join(d, h)
    src = open(p).read()
    print('#file\t%s\tsha256\t%s' % (h, hashlib.sha256(src.encode()).hexdigest()))
    for m in re.finditer(r'^#define\s+(\w+)_REG\s+\(?\s*(?:REG_UART_BASE\(i\)|DR_REG_\w+)\s*\+\s*(0x[0-9A-Fa-f]+)\s*\)?', src, re.M):
        print('R\t%s\t%s\t%s' % (h, m.group(1), m.group(2)))
    for m in re.finditer(r'^#define\s+(\w+)_S\s+(\d+)\b', src, re.M):
        v = re.search(r'^#define\s+%s_V\s+(0x[0-9A-Fa-f]+|\d+)' % re.escape(m.group(1)), src, re.M)
        print('F\t%s\t%s\t%s\t%s' % (h, m.group(1), m.group(2), v.group(1) if v else '?'))
