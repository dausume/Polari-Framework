"""
@module iso.custom.iso_probe_kit

The PROBE KIT that rides on the stick (ISO plan §P, D-P2 "scripts first"): one JSON report, three launchers —
Windows (PowerShell over CIM, started by a .bat that bypasses the execution policy), macOS (system_profiler, a
.command plus the one Terminal line a FAT stick needs), Linux (a shell script over /sys and lspci/lsusb) — and a
README.html at the stick's root with one big button per OS (his requirement: user-friendly). Every launcher writes
`probe/cache/<hash>.json` next to itself and prints the same three lines. Apple silicon gets the message verbatim.

@consumers
  - iso.iso_api (GET /api/iso/probe-kit → a zip), polari-cli apps_usb (`pol apps usb write --probe`), iso.iso_selftest
"""
import io
import json
import zipfile

from iso.custom.iso_compat import APPLE_SILICON_MESSAGE

README_HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Polari probe stick</title>
<style>body{font:17px/1.5 system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#1d1d1c;background:#fcfcfb}
h1{font-size:1.8rem}.btn{display:block;padding:1.1rem 1.3rem;margin:.8rem 0;border:2px solid #2a78d6;border-radius:14px;font-size:1.25rem;text-decoration:none;color:#1d1d1c;background:#fff}
.btn small{display:block;font-size:.95rem;color:#5d5d58;margin-top:.2rem}code{background:#eee;padding:.1rem .35rem;border-radius:4px}.note{color:#5d5d58}
@media(prefers-color-scheme:dark){body{background:#1a1a19;color:#ececea}.btn{background:#232322;color:#ececea;border-color:#3987e5}.btn small{color:#a5a5a0}code{background:#333}.note{color:#a5a5a0}}</style></head><body>
<h1>Polari probe stick</h1>
<p>This stick looks at a computer and tells you whether Ubuntu and Polari will run on it, before anything is installed. Nothing is changed on the computer. Pick the system this computer runs now:</p>
<a class="btn" href="probe/windows/RUN-ON-WINDOWS.bat">I am on Windows<small>Double-click RUN-ON-WINDOWS.bat on the stick (if the browser will not open it). Windows may ask once whether to run it: choose "Run anyway".</small></a>
<a class="btn" href="probe/macos/RUN-ON-MAC.command">I am on a Mac<small>Double-click RUN-ON-MAC.command. If macOS refuses, open Terminal and paste: <code>bash /Volumes/*/probe/macos/polari-probe.sh</code></small></a>
<a class="btn" href="probe/linux/polari-probe.sh">I am on Linux<small>In a terminal: <code>bash /media/$USER/*/probe/linux/polari-probe.sh</code></small></a>
<p>When it finishes, it says in plain words whether Ubuntu will run here. Then plug this stick into any computer with Polari: it reads the report, you choose what this computer should become, and Polari puts the installer for it onto this same stick.</p>
<p class="note">The report stays on the stick under <code>probe/cache/</code>. It contains the computer's hardware ids and sizes, never your files or passwords.</p>
</body></html>
'''

COMMON_TAIL_NOTE = 'The report is saved on the stick. Next: plug the stick into a computer with Polari, which reads it and plans the install.'

PROBE_PS1 = r'''# polari-probe.ps1 — reads this computer's hardware and OS into one JSON report on the stick. Changes nothing.
$ErrorActionPreference = 'SilentlyContinue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cache = Join-Path (Split-Path -Parent $here) 'cache'; New-Item -ItemType Directory -Force -Path $cache | Out-Null
$cs = Get-CimInstance Win32_ComputerSystem; $os = Get-CimInstance Win32_OperatingSystem; $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$bb = Get-CimInstance Win32_BaseBoard; $csp = Get-CimInstance Win32_ComputerSystemProduct; $bios = Get-CimInstance Win32_BIOS
$disks = Get-CimInstance Win32_DiskDrive | ForEach-Object { @{ name = $_.Model; size_gb = [math]::Round($_.Size / 1GB, 1); serial = $_.SerialNumber } }
$free = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace
$gpu = (Get-CimInstance Win32_VideoController | Select-Object -First 1).Name
$wifi = (Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.PhysicalAdapter -and $_.Name -match 'Wi-?Fi|Wireless|802\.11' } | Select-Object -First 1).Name
$nics = (Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.PhysicalAdapter }).Count
$ids = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^(PCI|USB)\\' } | ForEach-Object { $_.InstanceId }
$secure = 'unknown'; try { $secure = if (Confirm-SecureBootUEFI) { 'on' } else { 'off' } } catch { $secure = 'unavailable (legacy BIOS?)' }
$firmware = if ($env:firmware_type) { $env:firmware_type } else { try { $null = Confirm-SecureBootUEFI; 'UEFI' } catch { 'BIOS' } }
$tpm = 'unknown'; try { $t = Get-Tpm; $tpm = if ($t.TpmPresent) { 'present' } else { 'absent' } } catch {}
$bitlocker = 'unknown'; try { $b = Get-BitLockerVolume -MountPoint 'C:'; $bitlocker = if ($b.ProtectionStatus -eq 'On') { 'bitlocker' } else { 'off' } } catch {}
$raid = (Get-CimInstance Win32_SCSIController | Where-Object { $_.Name -match 'RAID|RST' } | Select-Object -First 1).Name
$fast = 'unknown'; try { $fs = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power' -Name HiberbootEnabled; $fast = [bool]$fs.HiberbootEnabled } catch {}
$virt = $false; try { $virt = [bool]$cpu.VirtualizationFirmwareEnabled } catch {}
$battery = [bool](Get-CimInstance Win32_Battery)
$report = [ordered]@{
  probe = 'polari-probe/1'; os_name = 'Windows'; os_version = "$($os.Caption) $($os.Version)"; hostname = $cs.Name
  manufacturer = $cs.Manufacturer; model = $cs.Model; cpu = $cpu.Name; arch = $os.OSArchitecture; virtualization = $virt
  memory_gb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1); disks = @($disks); free_gb = [math]::Round($free / 1GB, 1)
  firmware = $firmware; secure_boot = $secure; tpm = $tpm; disk_encryption = $bitlocker; raid_mode = $(if ($raid) { 'raid' } else { 'ahci' })
  fast_startup = $fast; gpu = $gpu; wifi = $wifi; nics = $nics; battery = $battery; device_ids = @($ids)
  dmi_uuid = $csp.UUID; board_serial = $bb.SerialNumber; disk_serial = $(if ($disks) { $disks[0].serial } else { '' })
  probed_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}
$basis = "$($report.dmi_uuid)|$($report.board_serial)|$($report.disk_serial)|$($report.cpu)|$($report.memory_gb)"
$sha = [System.Security.Cryptography.SHA256]::Create(); $hash = ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($basis)) | ForEach-Object { $_.ToString('x2') }) -join ''
$report.hw_hash = $hash.Substring(0, 16)
$out = Join-Path $cache "$($report.hw_hash).json"
$report | ConvertTo-Json -Depth 5 | Set-Content -Path $out -Encoding UTF8
Write-Host ''
Write-Host "Polari probe: recorded this computer ($($cs.Manufacturer) $($cs.Model), $($report.memory_gb) GB, $($report.os_version))."
Write-Host "Firmware $firmware, Secure Boot $secure, TPM $tpm, disk encryption $bitlocker, storage mode $($report.raid_mode)."
Write-Host "POLARI_TAIL_NOTE"
Write-Host ''
Read-Host 'Press Enter to close'
'''.replace('POLARI_TAIL_NOTE', COMMON_TAIL_NOTE)

RUN_BAT = r'''@echo off
title Polari probe
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0polari-probe.ps1"
'''

PROBE_MAC = r'''#!/bin/bash
# polari-probe.sh (macOS) — reads this Mac's hardware into one JSON report on the stick. Changes nothing.
HERE="$(cd "$(dirname "$0")" && pwd)"; CACHE="$(dirname "$HERE")/cache"; mkdir -p "$CACHE"
J=$(system_profiler -json SPHardwareDataType SPSoftwareDataType SPStorageDataType SPDisplaysDataType SPPCIDataType SPUSBDataType SPNetworkDataType SPPowerDataType 2>/dev/null)
python3 - "$J" "$CACHE" <<'PY'
import hashlib, json, subprocess, sys, time
j = json.loads(sys.argv[1] or '{}'); cache = sys.argv[2]
hw = (j.get('SPHardwareDataType') or [{}])[0]; sw = (j.get('SPSoftwareDataType') or [{}])[0]
chip = hw.get('chip_type') or hw.get('cpu_type') or ''
arch = subprocess.run(['uname', '-m'], capture_output=True, text=True).stdout.strip()
apple_silicon = arch == 'arm64' and 'Apple' in chip
ids = []
def walk(items, kind):
    for it in items or []:
        v = it.get('vendor_id') or it.get('sppci_vendor-id') or ''; d = it.get('product_id') or it.get('sppci_device-id') or ''
        v = str(v).replace('0x', '').strip()[-4:]; d = str(d).replace('0x', '').strip()[-4:]
        if v and d: ids.append(f'{kind} {v}:{d}')
        walk(it.get('_items'), kind)
walk(j.get('SPPCIDataType'), 'pci'); walk(j.get('SPUSBDataType'), 'usb')
disks = [{'name': s.get('_name', ''), 'size_gb': round((s.get('size_in_bytes') or 0) / 1e9, 1), 'serial': ''} for s in (j.get('SPStorageDataType') or []) if s.get('mount_point') == '/']
free = round(((j.get('SPStorageDataType') or [{}])[0].get('free_space_in_bytes') or 0) / 1e9, 1)
fv = subprocess.run(['fdesetup', 'status'], capture_output=True, text=True).stdout
gpu = ((j.get('SPDisplaysDataType') or [{}])[0].get('sppci_model') or (j.get('SPDisplaysDataType') or [{}])[0].get('_name') or '')
battery = bool(j.get('SPPowerDataType')) and any('sppower_battery' in str(k) for p in j.get('SPPowerDataType') for k in p)
mem = hw.get('physical_memory') or '0 GB'
try: mem_gb = float(str(mem).split()[0])
except Exception: mem_gb = 0.0
r = {'probe': 'polari-probe/1', 'os_name': 'macOS', 'os_version': sw.get('os_version', ''), 'hostname': sw.get('local_host_name', ''), 'manufacturer': 'Apple',
     'model': hw.get('machine_model', ''), 'cpu': chip, 'arch': arch, 'virtualization': not apple_silicon, 'memory_gb': mem_gb, 'disks': disks, 'free_gb': free,
     'firmware': 'UEFI', 'secure_boot': 'unknown', 'tpm': 't2' if 'T2' in json.dumps(hw) else 'absent', 'disk_encryption': 'filevault' if 'On' in fv else 'off',
     'raid_mode': 'ahci', 'fast_startup': False, 'gpu': gpu, 'wifi': 'built-in', 'nics': 1, 'battery': battery, 'device_ids': ids, 'apple_silicon': apple_silicon,
     't2': 'T2' in json.dumps(hw), 'dmi_uuid': hw.get('platform_UUID', ''), 'board_serial': hw.get('serial_number', ''), 'disk_serial': '',
     'probed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
basis = '|'.join(str(r.get(k) or '') for k in ('dmi_uuid', 'board_serial', 'disk_serial', 'cpu', 'memory_gb'))
r['hw_hash'] = hashlib.sha256(basis.encode()).hexdigest()[:16]
json.dump(r, open(f"{cache}/{r['hw_hash']}.json", 'w'), indent=1)
print()
if apple_silicon:
    print('APPLE_SILICON_MESSAGE')
else:
    print(f"Polari probe: recorded this Mac ({r['model']}, {mem_gb:g} GB, macOS {r['os_version']}). FileVault {r['disk_encryption']}.")
    print('POLARI_TAIL_NOTE')
print()
PY
read -r -p "Press Enter to close" _
'''.replace('APPLE_SILICON_MESSAGE', APPLE_SILICON_MESSAGE.replace("'", "\\'")).replace('POLARI_TAIL_NOTE', COMMON_TAIL_NOTE)

RUN_COMMAND = '''#!/bin/bash
bash "$(dirname "$0")/polari-probe.sh"
'''

PROBE_LINUX = r'''#!/bin/bash
# polari-probe.sh (Linux) — reads this computer's hardware into one JSON report on the stick. Changes nothing.
HERE="$(cd "$(dirname "$0")" && pwd)"; CACHE="$(dirname "$HERE")/cache"; mkdir -p "$CACHE"
python3 - "$CACHE" <<'PY'
import glob, hashlib, json, os, re, shutil, subprocess, sys, time
cache = sys.argv[1]
def sh(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception: return ''
def dmi(n):
    try: return open(f'/sys/class/dmi/id/{n}').read().strip()
    except Exception: return ''
ids = []
for p in glob.glob('/sys/bus/pci/devices/*/modalias') + glob.glob('/sys/bus/usb/devices/*/modalias'):
    try: ids.append(open(p).read().strip())
    except Exception: pass
cpu = sh("grep -m1 'model name' /proc/cpuinfo | cut -d: -f2").strip()
mem_gb = round(int(sh("grep MemTotal /proc/meminfo | awk '{print $2}'") or 0) / 1024 / 1024, 1)
virt = bool(sh("grep -m1 -oE 'vmx|svm' /proc/cpuinfo"))
disks = [{'name': l.split()[0], 'size_gb': round(float(l.split()[1]) / 1e9, 1), 'serial': ''} for l in sh("lsblk -dbn -o NAME,SIZE,TYPE | awk '$3==\"disk\"'").splitlines() if l.strip()]
free = round(shutil.disk_usage('/').free / 1e9, 1)
firmware = 'UEFI' if os.path.isdir('/sys/firmware/efi') else 'BIOS'
sb = sh("mokutil --sb-state 2>/dev/null"); secure = 'on' if 'enabled' in sb else ('off' if 'disabled' in sb else 'unknown')
tpm = 'present' if os.path.exists('/dev/tpm0') else 'absent'
enc = 'luks' if 'crypt' in sh("lsblk -o TYPE") else 'off'
gpu = sh("lspci | grep -iE 'vga|3d|display' | head -1 | cut -d: -f3").strip()
wifi = sh("lspci | grep -i -E 'wireless|wi-fi|network controller' | head -1 | cut -d: -f3").strip()
nics = len([n for n in os.listdir('/sys/class/net') if not re.match(r'^(lo|docker|br-|veth|virbr)', n)])
battery = bool(glob.glob('/sys/class/power_supply/BAT*'))
iommu = bool(os.listdir('/sys/kernel/iommu_groups')) if os.path.isdir('/sys/kernel/iommu_groups') else False
r = {'probe': 'polari-probe/1', 'os_name': sh("lsb_release -is 2>/dev/null") or 'Linux', 'os_version': sh("lsb_release -rs 2>/dev/null") or sh('uname -r'), 'hostname': sh('hostname'),
     'manufacturer': dmi('sys_vendor'), 'model': dmi('product_name'), 'cpu': cpu, 'arch': sh('uname -m'), 'virtualization': virt, 'iommu': iommu, 'memory_gb': mem_gb, 'disks': disks,
     'free_gb': free, 'firmware': firmware, 'secure_boot': secure, 'tpm': tpm, 'disk_encryption': enc, 'raid_mode': 'ahci', 'fast_startup': False, 'gpu': gpu, 'wifi': wifi,
     'nics': nics, 'battery': battery, 'device_ids': ids, 'dmi_uuid': dmi('product_uuid'), 'board_serial': dmi('board_serial'), 'disk_serial': '',
     'probed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
basis = '|'.join(str(r.get(k) or '') for k in ('dmi_uuid', 'board_serial', 'disk_serial', 'cpu', 'memory_gb'))
r['hw_hash'] = hashlib.sha256(basis.encode()).hexdigest()[:16]
json.dump(r, open(f"{cache}/{r['hw_hash']}.json", 'w'), indent=1)
print(); print(f"Polari probe: recorded this computer ({r['manufacturer']} {r['model']}, {mem_gb:g} GB, {r['os_name']} {r['os_version']}).")
print(f"Firmware {firmware}, Secure Boot {secure}, TPM {tpm}, disk encryption {enc}, virtualization {'yes' if virt else 'no'}, IOMMU {'yes' if iommu else 'no'}.")
print('POLARI_TAIL_NOTE'); print()
PY
'''.replace('POLARI_TAIL_NOTE', COMMON_TAIL_NOTE)


def kit_files():
    """{relative path on the stick: text} — the whole probe kit."""
    return {
        'README.html': README_HTML,
        'probe/windows/polari-probe.ps1': PROBE_PS1,
        'probe/windows/RUN-ON-WINDOWS.bat': RUN_BAT,
        'probe/macos/polari-probe.sh': PROBE_MAC,
        'probe/macos/RUN-ON-MAC.command': RUN_COMMAND,
        'probe/linux/polari-probe.sh': PROBE_LINUX,
        'probe/cache/README.txt': 'Probe reports land here as <hardware-hash>.json. Plug the stick into a computer with Polari to plan the installs.\n',
        'probe/kit.json': json.dumps({'kit': 'polari-probe-kit/1', 'files': ['README.html', 'probe/windows/polari-probe.ps1', 'probe/windows/RUN-ON-WINDOWS.bat',
                                                                             'probe/macos/polari-probe.sh', 'probe/macos/RUN-ON-MAC.command', 'probe/linux/polari-probe.sh']}, indent=1),
    }


def kit_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for path, text in kit_files().items():
            info = zipfile.ZipInfo(path); info.external_attr = (0o755 if path.endswith(('.sh', '.command', '.bat')) else 0o644) << 16
            z.writestr(info, text)
    return buf.getvalue()
