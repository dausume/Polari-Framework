"""@module appstore.objects.appstore_hosting._shared — what the appstore_hosting row classes share (constants, seeds, helpers); split from appstore_hosting_basis.py (sap-2c)."""
from appstore.appstore_ai_basis import host_check

HOSTING_KINDS_REMOTE = ('cpu-vps', 'gpu-vps', 'gpu-dedicated',
                        'managed-endpoint')
def option_fit(option, profiles):
    """Derived fit of one option against the tool's hosting
    profiles — the option's specs run through the SAME ai-6
    host_check logic (an option is a machine we don't own yet).
    Specs of 0 (marketplace listings vary) → 'unverified', stated.
    Pure; option may be an object or dict."""
    def field(name, default=0):
        if isinstance(option, dict):
            return option.get(name, default)
        return getattr(option, name, default)
    cores = field('cores') or 0
    ram = field('ram_mb') or 0
    if not cores or not ram:
        return [{'profile': p.get('name', ''),
                 'verdict': 'unverified',
                 'detail': ['specs vary per listing — check the '
                            'provider page']}
                for p in profiles]
    machine = {
        'name': field('name', ''), 'hasSpecs': True,
        'logicalCpus': cores,
        'totalRamMb': ram, 'availableRamMb': ram,
        'freeDiskMb': field('disk_mb') or 0,
        # unlike res-1 machines, an option DECLARES its GPU
        'gpu': bool(field('gpu_model', '')),
    }
    result = host_check({'profiles': list(profiles)}, [machine])
    return result['machines'][0]['profiles']
def hosting_options_payload(rows, profiles):
    """The /ai-hosting page payload. Pure over rows + the localai
    requirement profiles (may be empty → fits are unverified)."""
    options = []
    for row in rows:
        def field(name, default=''):
            if isinstance(row, dict):
                return row.get(name, default)
            return getattr(row, name, default)
        if not field('published', True):
            continue
        options.append({
            'name': field('name'),
            'provider': field('provider'),
            'title': field('title'),
            'kind': field('kind'),
            'cores': field('cores', 0),
            'ram_mb': field('ram_mb', 0),
            'disk_mb': field('disk_mb', 0),
            'gpu_model': field('gpu_model'),
            'price_amount': field('price_amount', 0.0),
            'price_unit': field('price_unit'),
            'price_as_of': field('price_as_of'),
            'price_source': field('price_source'),
            'price_note': field('price_note'),
            'sovereignty': field('sovereignty'),
            'notes': field('notes'),
            'fit': option_fit(row, profiles),
        })
    options.sort(key=lambda o: (o['kind'], o['provider'], o['name']))
    return {
        'ok': True,
        'count': len(options),
        'options': options,
        'profiles': list(profiles),
        'honesty': ('prices are as of their price_as_of date and '
                    'go stale — re-check the source before '
                    'deciding; fit is derived from declared specs, '
                    'unverified where listings vary'),
    }
_AS_OF = '2026-08-16'
SEED_REMOTE_HOSTING = [
    {
        'name': 'digitalocean-basic-8gb',
        'provider': 'DigitalOcean',
        'title': 'Basic Droplet — 4 vCPU / 8 GB / 160 GB SSD',
        'kind': 'cpu-vps',
        'cores': 4, 'ram_mb': 8192, 'disk_mb': 163840,
        'gpu_model': '',
        'price_amount': 48.0, 'price_unit': 'USD/mo',
        'price_as_of': _AS_OF,
        'price_source':
            'https://www.digitalocean.com/pricing/droplets',
        'price_note': 'per-second billing since Jan 2026',
        'sovereignty': 'your-cloud',
        'notes': 'shared vCPU; the straightforward minimal-profile '
                 'host — LocalAI CPU tag + small quantized models',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'digitalocean-gp-16gb',
        'provider': 'DigitalOcean',
        'title': 'General Purpose — 4 dedicated vCPU / 16 GB / '
                 '50 GB SSD',
        'kind': 'cpu-vps',
        'cores': 4, 'ram_mb': 16384, 'disk_mb': 51200,
        'gpu_model': '',
        'price_amount': 126.0, 'price_unit': 'USD/mo',
        'price_as_of': _AS_OF,
        'price_source':
            'https://www.digitalocean.com/pricing/droplets',
        'price_note': '',
        'sovereignty': 'your-cloud',
        'notes': 'dedicated CPU headroom; add block storage if '
                 'models outgrow the 50 GB boot disk',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'digitalocean-gpu-rtx4000',
        'provider': 'DigitalOcean',
        'title': 'GPU Droplet — RTX 4000 Ada 20 GB / 8 vCPU / '
                 '32 GB / 500 GB NVMe',
        'kind': 'gpu-vps',
        'cores': 8, 'ram_mb': 32768, 'disk_mb': 512000,
        'gpu_model': 'RTX 4000 Ada 20GB',
        'price_amount': 0.76, 'price_unit': 'USD/hr',
        'price_as_of': _AS_OF,
        'price_source':
            'https://www.digitalocean.com/pricing/gpu-droplets',
        'price_note': '~$555/mo if left running 24/7; billed even '
                      'while POWERED OFF — destroy to stop billing '
                      '(DO re-priced GPUs 2026-08-01)',
        'sovereignty': 'your-cloud',
        'notes': 'comfortable-profile host with room to spare',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'digitalocean-gpu-l40s',
        'provider': 'DigitalOcean',
        'title': 'GPU Droplet — L40S 48 GB / 8 vCPU / 64 GB / '
                 '500 GB NVMe',
        'kind': 'gpu-vps',
        'cores': 8, 'ram_mb': 65536, 'disk_mb': 512000,
        'gpu_model': 'L40S 48GB',
        'price_amount': 1.57, 'price_unit': 'USD/hr',
        'price_as_of': _AS_OF,
        'price_source':
            'https://www.digitalocean.com/pricing/gpu-droplets',
        'price_note': 'billed even while powered off — destroy to '
                      'stop',
        'sovereignty': 'your-cloud',
        'notes': 'large-model territory (48 GB VRAM)',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'hetzner-cx32',
        'provider': 'Hetzner',
        'title': 'Cloud CX32 — 4 vCPU / 8 GB / 80 GB (EU)',
        'kind': 'cpu-vps',
        'cores': 4, 'ram_mb': 8192, 'disk_mb': 81920,
        'gpu_model': '',
        'price_amount': 6.80, 'price_unit': 'EUR/mo',
        'price_as_of': _AS_OF,
        'price_source': 'https://www.hetzner.com/cloud/',
        'price_note': 'EU locations (US CPX line is pricier); '
                      'Hetzner re-priced June 2026 — verify in '
                      'their console',
        'sovereignty': 'your-cloud',
        'notes': 'the budget minimal-profile host by a wide margin',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'hetzner-gex131',
        'provider': 'Hetzner',
        'title': 'Dedicated GEX131 — RTX PRO 6000 Blackwell 96 GB',
        'kind': 'gpu-dedicated',
        'cores': 0, 'ram_mb': 0, 'disk_mb': 0,
        'gpu_model': 'RTX PRO 6000 Blackwell 96GB',
        'price_amount': 889.0, 'price_unit': 'EUR/mo',
        'price_as_of': _AS_OF,
        'price_source':
            'https://www.hetzner.com/pressroom/new-gex131/',
        'price_note': 'also ~EUR 1.42/hr flexible use, no setup '
                      'fee; CPU/RAM specs on the product page',
        'sovereignty': 'your-cloud',
        'notes': 'serious dedicated GPU; far beyond the '
                 'comfortable profile',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'runpod-rtx4090',
        'provider': 'RunPod',
        'title': 'RTX 4090 24 GB pod (community cloud)',
        'kind': 'gpu-vps',
        'cores': 16, 'ram_mb': 63488, 'disk_mb': 61440,
        'gpu_model': 'RTX 4090 24GB',
        'price_amount': 0.34, 'price_unit': 'USD/hr',
        'price_as_of': _AS_OF,
        'price_source': 'https://www.runpod.io/pricing',
        'price_note': 'community tier (marketplace machines); '
                      'secure cloud ~$0.69/hr; per-second billing '
                      '(RunPod updated prices 2026-07-27)',
        'sovereignty': 'your-cloud',
        'notes': 'pod CPU/RAM/disk are configurable — typical '
                 'listing shown; good burst/experiment host',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'vast-rtx4090',
        'provider': 'Vast.ai',
        'title': 'RTX 4090 24 GB (marketplace)',
        'kind': 'gpu-vps',
        'cores': 0, 'ram_mb': 0, 'disk_mb': 0,
        'gpu_model': 'RTX 4090 24GB',
        'price_amount': 0.39, 'price_unit': 'USD/hr',
        'price_as_of': _AS_OF,
        'price_source': 'https://vast.ai/pricing/gpu/RTX-4090',
        'price_note': 'marketplace — hosts set prices, they FLOAT '
                      '(~$0.29-0.59/hr on-demand seen); '
                      'interruptible is cheaper but can be paused',
        'sovereignty': 'your-cloud',
        'notes': 'cheapest 4090 access; host machines vary — '
                 'specs unverified by design',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'vast-rtx3090',
        'provider': 'Vast.ai',
        'title': 'RTX 3090 24 GB (marketplace)',
        'kind': 'gpu-vps',
        'cores': 0, 'ram_mb': 0, 'disk_mb': 0,
        'gpu_model': 'RTX 3090 24GB',
        'price_amount': 0.12, 'price_unit': 'USD/hr',
        'price_as_of': _AS_OF,
        'price_source': 'https://vast.ai/',
        'price_note': 'marketplace floor seen ~$0.06-0.12/hr; '
                      'floats per host',
        'sovereignty': 'your-cloud',
        'notes': 'the budget 24 GB VRAM path',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'linode-shared-8gb',
        'provider': 'Linode (Akamai)',
        'title': 'Shared 8 GB — 4 vCPU / 8 GB / 160 GB',
        'kind': 'cpu-vps',
        'cores': 4, 'ram_mb': 8192, 'disk_mb': 163840,
        'gpu_model': '',
        'price_amount': 48.0, 'price_unit': 'USD/mo',
        'price_as_of': _AS_OF,
        'price_source': 'https://www.linode.com/pricing/',
        'price_note': 'hourly billing capped at the monthly rate',
        'sovereignty': 'your-cloud',
        'notes': 'same shape/price as the DO basic droplet — '
                 'pick by region/preference',
        'published': True, 'is_prior': True,
    },
]
