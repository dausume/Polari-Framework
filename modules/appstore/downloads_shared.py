"""
@module appstore.downloads_shared

Shared building blocks for the server-rendered download surfaces
(/downloads, /downloads/apps, /downloads/offline): the page shell +
styling, size formatting, and the TRANSPARENCY components
(AI-Notes/plans/DOWNLOADS_PAGE_PLAN.md §Transparency) — every
download surface explains itself in plain language: what-is-this
explainers, per-item provenance lines (pre-prepped vs generated on
demand), honest wait estimates. All server-rendered, zero JS
(<details> collapses natively), one styling source so the three
pages read as one product.

@consumers
  - appstore.downloads_page
  - appstore.app_debs_page   (dl-4)
  - appstore.offline_page    (dl-5)
  - appstore.selftest_downloads
"""

import html


def human_size(size):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return (f'{size:.0f} {unit}' if unit == 'B'
                    else f'{size / 1.0:.1f} {unit}')
        size /= 1024.0
    return f'{size:.1f} GB'


# --- transparency: per-item provenance lines ------------------------
# Plan rule: pre-prepped items say when they were built and where the
# version comes from; on-demand items say they are generated fresh on
# click and deleted from the server afterwards, with an HONEST wait
# estimate (recorded history or "never generated yet").

def prepped_provenance(built_date):
    return ('<span class="prov prov-prepped">Pre-prepped &mdash; '
            f'built on this server {html.escape(built_date)}, '
            'version read from the file name. Downloads '
            'instantly.</span>')


def on_demand_provenance(estimate_text):
    return ('<span class="prov prov-demand">Generated fresh when '
            'you click, then removed from the server after '
            f'delivery. {html.escape(estimate_text)}</span>')


# --- transparency: what-is-this explainers --------------------------
# Each entry = (question, answer_html). Questions are escaped here;
# answers may carry markup, so callers own their escaping.

EXPLAIN_DEB = (
    'What is a .deb file?',
    'The standard installer format on Ubuntu and other '
    'Debian-family Linux &mdash; the equivalent of a setup file on '
    'other systems. Your computer\'s own <em>Software Install</em> '
    'app reads it, shows what will be installed, and asks for your '
    'password through the system dialog. Nothing runs until you '
    'approve it.')

EXPLAIN_PREPPED_VS_DEMAND = (
    'What do "pre-prepped" and "generated on demand" mean?',
    '<strong>Pre-prepped</strong> files are built ahead of time and '
    'sit ready on this server, so the download starts instantly. '
    '<strong>Generated on demand</strong> files are packaged fresh '
    'at the moment you ask for them &mdash; you wait briefly while '
    'the server builds your copy, and the server deletes its copy '
    'after delivery instead of keeping a duplicate on disk. Each '
    'item on these pages says which kind it is.')

EXPLAIN_INTERNET = (
    'What gets downloaded from the internet during install?',
    'Supporting software the apps need (for example Docker) comes '
    'from Ubuntu\'s own official repositories during the install '
    '&mdash; fetched by your system\'s package manager, from the '
    'same place all your other Ubuntu software comes from. Nothing '
    'is fetched from anywhere else.')

EXPLAIN_DISK = (
    'What ends up on my disk, and where?',
    'Programs install into the system software areas '
    '(<code>/usr</code>, <code>/opt</code>) and app data lives '
    'under <code>/var/lib/polari</code>. The .deb file you '
    'downloaded is only the delivery vehicle &mdash; once the '
    'install finishes it is safe to delete from your Downloads '
    'folder.')


def explainer_block(entries, heading='What is all this?'):
    """The what-is-this section: one native <details> per question,
    collapsed by default, no JS."""
    items = ''
    for question, answer in entries:
        items += (f'\n<details class="explain">'
                  f'<summary>{html.escape(question)}</summary>'
                  f'<p>{answer}</p></details>')
    return (f'<section class="step explain-block">'
            f'<h2>{html.escape(heading)}</h2>{items}\n</section>')


# --- the page shell -------------------------------------------------

def wrap_page(title, body, page_label='Downloads', head_extra=''):
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head_extra}<title>{title} — {html.escape(page_label)}</title>
<style>
 :root{{--bg:#fcfcfb;--card:#ffffff;--ink:#1d1d1c;--ink2:#5d5d58;
   --line:#e4e4df;--accent:#2a78d6;--accent-ink:#ffffff;
   --chip:#f1f1ec;--good:#2c7a3f}}
 @media (prefers-color-scheme: dark){{
   :root{{--bg:#1a1a19;--card:#232322;--ink:#ececea;--ink2:#a5a5a0;
     --line:#3a3a38;--accent:#3987e5;--accent-ink:#ffffff;
     --chip:#2d2d2b;--good:#59b46e}}}}
 *{{box-sizing:border-box}}
 body{{font-family:system-ui,sans-serif;max-width:46rem;
   margin:0 auto;padding:2.5rem 1.25rem 3rem;line-height:1.55;
   color:var(--ink);background:var(--bg)}}
 h1{{font-size:1.7rem;margin:0 0 .5rem;line-height:1.25}}
 h2{{font-size:1.12rem;margin:0 0 .8rem;display:flex;
   align-items:center;gap:.6rem}}
 code{{background:var(--chip);padding:.08rem .35rem;
   border-radius:4px;font-size:.86em}}
 .hero{{margin-bottom:2rem}}
 .version{{margin:.1rem 0 .9rem;color:var(--ink2)}}
 .version strong{{color:var(--ink);background:var(--chip);
   border:1px solid var(--line);border-radius:999px;
   padding:.12rem .7rem;margin-left:.25rem}}
 .lede{{margin:0;color:var(--ink2)}}
 .step{{background:var(--card);border:1px solid var(--line);
   border-radius:12px;padding:1.1rem 1.25rem;margin:0 0 1.1rem}}
 .step-no{{flex:none;width:1.7rem;height:1.7rem;border-radius:50%;
   background:var(--accent);color:var(--accent-ink);
   font-size:.95rem;font-weight:700;display:inline-flex;
   align-items:center;justify-content:center}}
 .option-tag{{margin:0 0 .3rem;font-size:.8rem;font-weight:700;
   letter-spacing:.06em;text-transform:uppercase;
   color:var(--accent)}}
 .option-note{{margin:.1rem 0 .9rem;color:var(--ink2);
   font-size:.95em}}
 ol.dl-list{{list-style:none;margin:0;padding:0}}
 .dl-card{{display:flex;align-items:center;gap:.9rem;
   padding:.8rem .2rem;border-top:1px solid var(--line)}}
 .dl-card:first-child{{border-top:0}}
 .dl-card.hero-card{{border-top:0;background:var(--chip);
   border:1px solid var(--line);border-radius:10px;
   padding:.9rem 1rem}}
 .ordinal{{flex:none;width:1.5rem;height:1.5rem;border-radius:50%;
   border:2px solid var(--accent);color:var(--accent);
   font-size:.82rem;font-weight:700;display:inline-flex;
   align-items:center;justify-content:center}}
 .dl-info{{flex:1;min-width:0;display:flex;flex-direction:column;
   gap:.1rem}}
 .dl-name{{font-weight:650}}
 .blurb{{margin:0;color:var(--ink2);font-size:.92em}}
 .dl-meta{{color:var(--ink2);font-size:.82em;
   overflow-wrap:anywhere}}
 .prov{{font-size:.82em;overflow-wrap:anywhere}}
 .prov-prepped{{color:var(--good)}}
 .prov-demand{{color:var(--ink2)}}
 a.dl,button.dl{{flex:none;background:var(--accent);
   color:var(--accent-ink);text-decoration:none;font-weight:650;
   padding:.5rem 1.1rem;border-radius:8px;border:0;
   font-size:1em;cursor:pointer}}
 a.dl:hover,button.dl:hover{{filter:brightness(1.08)}}
 label.pick{{display:block;margin:.3rem 0}}
 .tabs{{display:flex;gap:.4rem;margin:0 0 .6rem}}
 .tab{{padding:.35rem 1rem;border-radius:999px;
   border:1px solid var(--line);color:var(--ink);
   text-decoration:none;font-weight:600}}
 .tab-on{{background:var(--accent);color:var(--accent-ink);
   border-color:var(--accent)}}
 select{{font-size:1em;padding:.15rem .3rem}}
 ol.howto{{margin:0;padding-left:1.3rem}}
 ol.howto li{{margin:.4rem 0}}
 .note{{color:var(--ink2);font-size:.9em}}
 .note a{{color:var(--accent)}}
 details.explain{{border-top:1px solid var(--line);
   padding:.55rem .2rem}}
 details.explain:first-of-type{{border-top:0}}
 details.explain summary{{cursor:pointer;font-weight:600;
   color:var(--ink)}}
 details.explain p{{margin:.5rem 0 .2rem;color:var(--ink2);
   font-size:.95em}}
 @media (max-width:480px){{
   .dl-card{{flex-wrap:wrap}}
   .dl-info{{flex-basis:calc(100% - 2.4rem)}}
   a.dl{{margin-left:2.4rem}}}}
</style></head><body>{body}</body></html>'''
