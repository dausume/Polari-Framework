"""
@module computerparts.parts_seed

Researched 2026-08-16 (web; GPU street prices move fast — the
2026 market is badly inflated over MSRP, which is exactly why
every price here wears its date). GPU prices are from price
trackers / market reports; base-component prices are ESTIMATES
within researched whole-build totals, marked as such — verify at
a retailer before ordering.

Three example builds (Dustin's ask: "here are 3 examples of
computers that meet those specs") — all sized against the localai
'comfortable' hosting profile (8 cores / 16 GB / 60 GB / GPU),
which is also the DO RTX-4000-Ada-droplet class:
  - build-used-3090:  the researched VALUE play (24 GB used VRAM)
  - build-5060ti-16gb: all-new entry tier (16 GB VRAM)
  - build-used-4090:  the fast 24 GB tier

Seeded through composition.seed_upsert (is_prior discipline).
"""

_AS_OF = '2026-08-16'

#: GPU street prices (trackers/market reports, dated). Everything
#: else: estimate-within-researched-build-totals, said so.
SEED_COMPUTER_PARTS = [
    {
        'name': 'gpu-rtx3090-used',
        'title': 'NVIDIA RTX 3090 24GB (used)',
        'kind': 'gpu', 'model': 'RTX 3090', 'condition': 'used',
        'specs_json': '{"vram_mb": 24576, "watts": 350}',
        'price_amount': 700.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://www.compute-market.com/blog/'
                        'ai-pc-build-under-1000-2026',
        'price_note': 'used market ~$600-900; the researched '
                      'value play — 24 GB VRAM + 384-bit bus',
        'notes': 'runs 30B-class models at Q4; 3x the inference '
                 'speed of a 4060 Ti in the research',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'gpu-rtx5060ti-16gb',
        'title': 'NVIDIA RTX 5060 Ti 16GB (new)',
        'kind': 'gpu', 'model': 'RTX 5060 Ti', 'condition': 'new',
        'specs_json': '{"vram_mb": 16384, "watts": 180}',
        'price_amount': 430.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://convly.ai/'
                        'best-gpus-for-budget-builds-2026/',
        'price_note': 'the new-card budget path; a used 4060 Ti '
                      '16GB runs slightly less',
        'notes': '16 GB VRAM covers 13-14B models comfortably',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'gpu-rtx4090-used',
        'title': 'NVIDIA RTX 4090 24GB (used)',
        'kind': 'gpu', 'model': 'RTX 4090', 'condition': 'used',
        'specs_json': '{"vram_mb": 24576, "watts": 450}',
        'price_amount': 1700.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://www.buysellram.com/blog/'
                        'nvidia-consumer-gpu-price-report-'
                        'august-2026/',
        'price_note': 'used ~$1,400-2,000; NEW 4090s are '
                      'discontinued and price-inflated to '
                      '$2,500-3,700',
        'notes': 'the fast 24 GB tier; only sensible USED in 2026',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'gpu-rtx5090-new',
        'title': 'NVIDIA RTX 5090 32GB (new)',
        'kind': 'gpu', 'model': 'RTX 5090', 'condition': 'new',
        'specs_json': '{"vram_mb": 32768, "watts": 575}',
        'price_amount': 4700.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://videocardprices.com/card/'
                        'nvidia-rtx-5090/',
        'price_note': 'median US street price Aug 2026 — ~135% '
                      'OVER MSRP; listed for context, not '
                      'recommended at this price',
        'notes': 'not in any seeded build — the used 24 GB cards '
                 'are the researched value',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'cpu-ryzen7-7700',
        'title': 'AMD Ryzen 7 7700 (8 cores)',
        'kind': 'cpu', 'model': 'Ryzen 7 7700', 'condition': 'new',
        'specs_json': '{"cores": 8, "threads": 16, "socket": "AM5"}',
        'price_amount': 270.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://localaimaster.com/blog/'
                        'ai-pc-build-guide',
        'price_note': 'estimate within researched build totals — '
                      'verify at retailer',
        'notes': '8 cores matches the comfortable profile; '
                 'inference is GPU-bound, CPU just needs to keep up',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'mb-am5-b650',
        'title': 'AM5 B650 motherboard',
        'kind': 'motherboard', 'model': 'B650', 'condition': 'new',
        'specs_json': '{"socket": "AM5", "ram_type": "DDR5"}',
        'price_amount': 140.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://localaimaster.com/blog/'
                        'ai-pc-build-guide',
        'price_note': 'estimate — verify at retailer',
        'notes': '', 'published': True, 'is_prior': True,
    },
    {
        'name': 'ram-ddr5-32gb',
        'title': '32 GB DDR5 (2x16)',
        'kind': 'ram', 'model': 'DDR5-6000', 'condition': 'new',
        'specs_json': '{"capacity_mb": 32768, "ram_type": "DDR5"}',
        'price_amount': 95.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://localaimaster.com/blog/'
                        'ai-pc-build-guide',
        'price_note': 'estimate — verify at retailer',
        'notes': '', 'published': True, 'is_prior': True,
    },
    {
        'name': 'ram-ddr5-64gb',
        'title': '64 GB DDR5 (2x32)',
        'kind': 'ram', 'model': 'DDR5-6000', 'condition': 'new',
        'specs_json': '{"capacity_mb": 65536, "ram_type": "DDR5"}',
        'price_amount': 190.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://localaimaster.com/blog/'
                        'ai-pc-build-guide',
        'price_note': 'estimate — verify at retailer',
        'notes': 'lets CPU-offload layers when a model outgrows '
                 'VRAM', 'published': True, 'is_prior': True,
    },
    {
        'name': 'ssd-nvme-2tb',
        'title': '2 TB NVMe SSD',
        'kind': 'storage', 'model': 'PCIe 4.0 NVMe',
        'condition': 'new',
        'specs_json': '{"capacity_mb": 2097152}',
        'price_amount': 120.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://localaimaster.com/blog/'
                        'ai-pc-build-guide',
        'price_note': 'estimate — verify at retailer',
        'notes': 'models are gigabytes each — do not skimp here',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'psu-850w-gold',
        'title': '850 W 80+ Gold PSU',
        'kind': 'psu', 'model': '850W', 'condition': 'new',
        'specs_json': '{"watts": 850}',
        'price_amount': 110.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://localaimaster.com/blog/'
                        'ai-pc-build-guide',
        'price_note': 'estimate — verify at retailer',
        'notes': 'sized for a 350-450 W GPU with headroom',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'case-atx',
        'title': 'ATX case (good airflow)',
        'kind': 'case', 'model': 'ATX', 'condition': 'new',
        'specs_json': '{}',
        'price_amount': 80.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://localaimaster.com/blog/'
                        'ai-pc-build-guide',
        'price_note': 'estimate — verify at retailer',
        'notes': '', 'published': True, 'is_prior': True,
    },
    {
        'name': 'cooler-air-tower',
        'title': 'Air tower CPU cooler',
        'kind': 'cooler', 'model': 'air tower', 'condition': 'new',
        'specs_json': '{}',
        'price_amount': 40.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://localaimaster.com/blog/'
                        'ai-pc-build-guide',
        'price_note': 'estimate — verify at retailer',
        'notes': '', 'published': True, 'is_prior': True,
    },
]

_BASE_PARTS = ('cpu-ryzen7-7700', 'mb-am5-b650', 'ssd-nvme-2tb',
               'psu-850w-gold', 'case-atx', 'cooler-air-tower')

SEED_COMPUTER_BUILDS = [
    {
        'name': 'build-used-3090',
        'title': 'Used-3090 value build (24 GB VRAM)',
        'purpose': 'The researched VALUE play for local AI: 30B-'
                   'class models at Q4, strong tokens/sec, room '
                   'for the audio/vision backends.',
        'parts_json': '["gpu-rtx3090-used", "ram-ddr5-64gb", '
                      + ', '.join('"%s"' % p
                                  for p in _BASE_PARTS) + ']',
        'specs_json': '{"cores": 8, "ram_mb": 65536, '
                      '"disk_mb": 2097152, '
                      '"gpu_model": "RTX 3090 24GB", '
                      '"vram_mb": 24576}',
        'notes': 'research shows $1,000-1,200 totals with used/'
                 'budget base parts; this list prices NEW base '
                 'components around the used GPU',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'build-5060ti-16gb',
        'title': 'All-new entry build (16 GB VRAM)',
        'purpose': 'Everything new with warranty: 13-14B models '
                   'comfortably, the smallest sensible buy-'
                   'instead-of-rent machine.',
        'parts_json': '["gpu-rtx5060ti-16gb", "ram-ddr5-32gb", '
                      + ', '.join('"%s"' % p
                                  for p in _BASE_PARTS) + ']',
        'specs_json': '{"cores": 8, "ram_mb": 32768, '
                      '"disk_mb": 2097152, '
                      '"gpu_model": "RTX 5060 Ti 16GB", '
                      '"vram_mb": 16384}',
        'notes': '',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'build-used-4090',
        'title': 'Used-4090 fast build (24 GB VRAM)',
        'purpose': 'The fast 24 GB tier: big quantized models at '
                   'interactive speed; matches or beats the '
                   'rented RTX-4000-Ada class.',
        'parts_json': '["gpu-rtx4090-used", "ram-ddr5-64gb", '
                      + ', '.join('"%s"' % p
                                  for p in _BASE_PARTS) + ']',
        'specs_json': '{"cores": 8, "ram_mb": 65536, '
                      '"disk_mb": 2097152, '
                      '"gpu_model": "RTX 4090 24GB", '
                      '"vram_mb": 24576}',
        'notes': 'buy the GPU used — new 4090s are discontinued '
                 'and inflated',
        'published': True, 'is_prior': True,
    },
]
