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

Seeded through moduleService.seed_upsert (is_prior discipline).
"""

_AS_OF = '2026-08-16'

#: GPU street prices (trackers/market reports, dated). Everything
#: else: estimate-within-researched-build-totals, said so.
SEED_COMPUTER_PARTS = [
    {
        'name': 'gpu-rtx3090-used',
        'title': 'NVIDIA RTX 3090 24GB (used)',
        'kind': 'gpu', 'model': 'RTX 3090', 'condition': 'used',
        'specs_json': '{"vram_mb": 24576, "watts": 350, '
                      '"pcie_slots": 1}',
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
        'specs_json': '{"vram_mb": 16384, "watts": 180, '
                      '"pcie_slots": 1}',
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
        'specs_json': '{"vram_mb": 24576, "watts": 450, '
                      '"pcie_slots": 1}',
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
        'specs_json': '{"vram_mb": 32768, "watts": 575, '
                      '"pcie_slots": 1}',
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
        'specs_json': '{"socket": "AM5", "ram_type": "DDR5", '
                      '"ram_slots": 4}',
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
        'specs_json': '{"capacity_mb": 32768, "ram_type": "DDR5", '
                      '"modules": 2}',
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
        'specs_json': '{"capacity_mb": 65536, "ram_type": "DDR5", '
                      '"modules": 2}',
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

    # ---- Dustin's owned Xeon Gold 6338N + the build around it ----
    {
        'name': 'cpu-xeon-6338n-owned',
        'title': 'Intel Xeon Gold 6338N (32c/64t, Ice Lake-SP) — '
                 'OWNED',
        'kind': 'cpu', 'model': 'Xeon Gold 6338N',
        'condition': 'used',
        'specs_json': '{"cores": 32, "threads": 64, '
                      '"socket": "LGA4189"}',
        'price_amount': 850.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://www.ebay.com/itm/395040642466',
        'price_note': 'VALUATION of an owned chip, not a purchase: '
                      'working units ask ~$1,000-1,100 best-offer, '
                      'parts-only floor $550, EU outlier $2,300 — '
                      'realistic resale ~$700-1,000',
        'notes': '8-channel DDR4 (~200 GB/s populated) + AVX-512: '
                 'CPU inference lives on memory bandwidth — this '
                 'is a different class from any desktop CPU here',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'mb-x12spl-f-used',
        'title': 'Supermicro X12SPL-F (LGA4189, C621A) — used',
        'kind': 'motherboard', 'model': 'X12SPL-F',
        'condition': 'used',
        'specs_json': '{"socket": "LGA4189", "ram_type": "DDR4", '
                      '"ram_slots": 8}',
        'price_amount': 445.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://www.ebay.com/itm/356780873298',
        'price_note': 'used ~$445; new ~$700; single-socket ATX, '
                      '8 DIMM slots (all 8 channels), PCIe 4.0 x16 '
                      'free for a GPU later',
        'notes': 'the cheapest sensible single-socket LGA4189 '
                 'board found',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'ram-ddr4-rdimm-16gb-2666',
        'title': '16 GB DDR4-2666 ECC RDIMM (refurb, per module)',
        'kind': 'ram', 'model': 'DDR4-2666 RDIMM',
        'condition': 'refurbished',
        'specs_json': '{"capacity_mb": 16384, '
                      '"ram_type": "DDR4", "modules": 1}',
        'price_amount': 60.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://pcserverandparts.com/components/'
                        'ram-memory/',
        'price_note': 'estimate from refurb market (32GB modules '
                      '$110-359 in the 2026 RAM squeeze; 16GB/2666 '
                      'sits low) — verify; the 6338N caps at 2666 '
                      'so do NOT pay the 3200 premium',
        'notes': 'buy EIGHT: populating all 8 channels IS the '
                 'performance (bandwidth, not capacity, feeds '
                 'CPU inference)',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'cooler-lga4189',
        'title': 'LGA4189 tower cooler',
        'kind': 'cooler', 'model': 'LGA4189 tower',
        'condition': 'new',
        'specs_json': '{}',
        'price_amount': 75.0, 'price_unit': 'USD',
        'price_as_of': _AS_OF,
        'price_source': 'https://www.ebay.com/sch/i.html?_nkw='
                        'lga4189+cooler',
        'price_note': 'estimate — Dynatron-class ~$60, Noctua '
                      'DX-4189 ~$120; the socket needs its own '
                      'mounting, desktop coolers do not fit',
        'notes': '185 W TDP wants a real tower, not a 1U blower '
                 '(noise)', 'published': True, 'is_prior': True,
    },
    # cmp-c-1 additions (2026-08-25): the two kinds the taxonomy
    # introduced. Prices are estimates with their own as-of date.
    {
        'name': 'nic-10gbe-dual',
        'title': '10 GbE dual-port PCIe NIC (X550-class, used)',
        'kind': 'nic', 'model': 'X550-T2 class',
        'condition': 'used',
        'specs_json': '{"speed_gbps": 10, "ports": 2, '
                      '"pcie_slots": 1}',
        'price_amount': 120.0, 'price_unit': 'USD',
        'price_as_of': '2026-08-25',
        'price_source': 'https://www.ebay.com/sch/i.html?_nkw='
                        'x550-t2',
        'price_note': 'estimate from used market — verify; '
                      'genuine-vs-clone card provenance matters '
                      'on this model',
        'notes': 'hosting-node upgrade — member nodes are fine '
                 'on onboard 1 GbE',
        'published': True, 'is_prior': True,
    },
    {
        'name': 'fpga-arty-a7-100t',
        'title': 'Arty A7-100T FPGA dev board (Artix-7)',
        'kind': 'fpga-accelerator', 'model': 'Arty A7-100T',
        'condition': 'new',
        'specs_json': '{"luts": 101440, '
                      '"fpga_family": "Artix-7", '
                      '"interface": "usb-jtag", '
                      '"pcie_slots": 0}',
        'price_amount': 299.0, 'price_unit': 'USD',
        'price_as_of': '2026-08-25',
        'price_source': 'https://digilent.com/shop/'
                        'arty-a7-100t-artix-7-fpga-development-'
                        'board/',
        'price_note': 'estimate — verify at retailer',
        'notes': 'bench board (USB-JTAG, not a PCIe '
                 'accelerator) — satisfies the fpga-lab '
                 'profile\'s presence floor; oss-cad-suite flow '
                 'covers Artix-7',
        'published': True, 'is_prior': True,
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

    {
        'name': 'build-xeon-6338n',
        'title': 'Around YOUR Xeon 6338N — 32-core / 128 GB '
                 'bandwidth machine (no GPU needed to start)',
        'purpose': 'The cheapest self-host path given the owned '
                   'chip: CPU-only inference on 8-channel DDR4 '
                   '(~200 GB/s) runs 30B-70B quantized models '
                   'entirely in RAM at assistant-usable speeds — '
                   'the CPU cost is $0 (owned). PCIe 4.0 x16 '
                   'stays free for a GPU later.',
        'parts_json': '["cpu-xeon-6338n-owned", "mb-x12spl-f-used", '
                      '"ram-ddr4-rdimm-16gb-2666", '
                      '"ram-ddr4-rdimm-16gb-2666", '
                      '"ram-ddr4-rdimm-16gb-2666", '
                      '"ram-ddr4-rdimm-16gb-2666", '
                      '"ram-ddr4-rdimm-16gb-2666", '
                      '"ram-ddr4-rdimm-16gb-2666", '
                      '"ram-ddr4-rdimm-16gb-2666", '
                      '"ram-ddr4-rdimm-16gb-2666", '
                      '"cooler-lga4189", "ssd-nvme-2tb", '
                      '"psu-850w-gold", "case-atx"]',
        'specs_json': '{"cores": 32, "ram_mb": 131072, '
                      '"disk_mb": 2097152, "gpu_model": "", '
                      '"vram_mb": 0}',
        'notes': 'the CPU line in the total is the chip\'s market '
                 'VALUATION — already owned, so cash outlay is '
                 'the total minus it (~$1,300); start with 4 '
                 'DIMMs (~$1,060 outlay) at half bandwidth if '
                 'budget-first',
        'published': True, 'is_prior': True,
    },
]


def seed_computerparts(manager):
    """Upsert parts-then-builds through moduleService.seed_upsert
    (builds reference parts by name; prices/dates CHANGE, so the
    seed must converge live prior rows — never insert-by-name).
    Composition absent -> loud no-op, honest empty report."""
    from computerparts.parts_basis import (
        ComputerBuildDefinition, ComputerPartDefinition,
    )
    try:
        from moduleService.seed_upsert import upsert_seed_pairs
    except ImportError as exc:
        print(f'[ComputerPartsSeed] moduleService.seed_upsert '
              f'unavailable ({exc}) — computerparts seeds NOT '
              f'applied', flush=True)
        return []
    return upsert_seed_pairs(
        manager,
        [('ComputerPartDefinition', ComputerPartDefinition,
          SEED_COMPUTER_PARTS),
         ('ComputerBuildDefinition', ComputerBuildDefinition,
          SEED_COMPUTER_BUILDS)],
        tag='ComputerPartsSeed')
