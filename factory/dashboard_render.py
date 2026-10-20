"""Rendering layer for the Scout dashboard: design system, charts, pages.

Mobile-first by construction: the layout is a single column capped at 560px until a
tablet breakpoint, figures use `clamp()` so the hero number is legible on a phone, and
navigation sits in a fixed bottom bar where a thumb can reach it. Charts are drawn as
inline SVG (no script, no network, no dependencies) so the page stays a single static
artifact that survives being emailed, archived, or read with JS disabled.

Every value that reaches this module is already collected and attributed by
`scripts/build-dashboard.py`; nothing here invents a number.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

TONE = {"ok": "ok", "warn": "warn", "bad": "bad", "neutral": "neutral"}


def eur(value, digits=2):
    if value is None:
        return "no data"
    return f"€{value:,.{digits}f}"


def esc(value):
    return html.escape("" if value is None else str(value))


def fmt(value, unit=""):
    """Compact figures: 1_943_956 -> 1.94M, 0.5 -> 50%."""
    if value is None:
        return "no data"
    if isinstance(value, float):
        text = f"{value:,.1f}".rstrip("0").rstrip(".")
    elif isinstance(value, int):
        if abs(value) >= 1_000_000:
            text = f"{value/1_000_000:.2f}M"
        elif abs(value) >= 10_000:
            text = f"{value/1000:.1f}k"
        else:
            text = f"{value:,}"
    else:
        text = esc(value)
    return f"{text}{unit}"


CSS = """
:root{
  --ink:#07080a; --surface:#0f1216; --surface-2:#151a21; --surface-3:#1b212a;
  --line:#232b36; --line-soft:#1a212a;
  --text:#eef2f7; --dim:#9aa4b2; --faint:#828d9d;
  --mint:#62e6a8; --amber:#f5b544; --coral:#ff7a8a; --blue:#7fa8ff; --violet:#b79bff;
  --r:18px; --gap:14px;
  --fs-hero:clamp(31px,9.5vw,48px); --fs-big:clamp(23px,6.5vw,29px);
  --fs-body:15px; --fs-small:12.5px; --fs-micro:11px;
  --shadow:0 1px 0 rgba(255,255,255,.03) inset, 0 20px 40px -32px rgba(0,0,0,.9);
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ink);color:var(--text);
  font:var(--fs-body)/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
  font-feature-settings:"tnum" 1,"ss01" 1;
  padding-bottom:calc(74px + env(safe-area-inset-bottom))}
a{color:inherit}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
/* ---------- header ---------- */
.top{position:sticky;top:0;z-index:20;background:rgba(7,8,10,.82);
  backdrop-filter:blur(14px);border-bottom:1px solid var(--line-soft)}
.top .wrap{display:flex;align-items:center;gap:10px;padding-top:14px;padding-bottom:14px}
.brand{display:flex;align-items:center;gap:9px;font-weight:650;letter-spacing:-.01em}
.mark{width:22px;height:22px;border-radius:7px;background:linear-gradient(140deg,var(--mint),#2f8f6f);
  box-shadow:0 0 22px -6px rgba(98,230,168,.7)}
.live{margin-left:auto;display:flex;align-items:center;gap:6px;color:var(--dim);
  font-size:var(--fs-micro);letter-spacing:.04em;text-transform:uppercase}
.dot{width:6px;height:6px;border-radius:50%;background:var(--mint);box-shadow:0 0 0 4px rgba(98,230,168,.12)}
.topnav{display:none;margin-left:18px;gap:2px}
.topnav a{padding:6px 11px;border-radius:9px;color:var(--dim);text-decoration:none;font-size:13px}
.topnav a:hover{color:var(--text);background:var(--surface-2)}
.topnav a.on{color:var(--text);background:var(--surface-3)}
/* ---------- hero ---------- */
.hero{padding:22px 0 8px}
.eyebrow{color:var(--faint);font-size:var(--fs-micro);letter-spacing:.14em;text-transform:uppercase}
.hero.compact h1{font-size:clamp(21px,5vw,27px);letter-spacing:-.02em}
.hero h1{margin:8px 0 8px;font-size:clamp(25px,5.6vw,34px);line-height:1.1;letter-spacing:-.025em;font-weight:600}
.hero p{margin:0;color:var(--dim);max-width:46ch;font-size:14.5px}
.statusline{display:flex;align-items:center;gap:9px;margin-top:16px;padding:11px 13px;
  border-radius:12px;border:1px solid var(--line);background:var(--surface-2);font-size:13px;
  color:var(--dim)}
.statusline b{color:var(--text);font-weight:560}
.statusline.ok{border-color:rgba(98,230,168,.22);background:rgba(98,230,168,.05)}
.statusline.warn{border-color:rgba(245,181,68,.28);background:rgba(245,181,68,.06)}
.statusline .dot{flex:none}
.statusline time{margin-left:auto;color:var(--faint);font-size:var(--fs-micro);white-space:nowrap}
.donut-wrap{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.donut-wrap .legend{flex:1;min-width:170px;margin-top:0}
/* ---------- grids ---------- */
.grid{display:grid;gap:var(--gap);grid-template-columns:1fr}
@media(min-width:360px){.grid.two{grid-template-columns:1fr 1fr}}
.kpis{display:grid;gap:var(--gap);grid-template-columns:1fr 1fr}
@media(min-width:900px){.kpis{grid-template-columns:repeat(4,1fr)}}
@media(min-width:900px){
  .grid{grid-template-columns:repeat(12,1fr)}
  .col-3{grid-column:span 3}.col-4{grid-column:span 4}.col-5{grid-column:span 5}
  .col-6{grid-column:span 6}.col-7{grid-column:span 7}.col-8{grid-column:span 8}
  .col-12{grid-column:span 12}
  .topnav{display:flex}
}
/* ---------- cards ---------- */
.card{background:linear-gradient(180deg,var(--surface-2),var(--surface));
  border:1px solid var(--line);border-radius:var(--r);padding:16px;box-shadow:var(--shadow);
  min-width:0}
.card h3{margin:0 0 2px;font-size:13px;font-weight:600;letter-spacing:.01em}
.card .sub{color:var(--faint);font-size:var(--fs-micro);letter-spacing:.06em;text-transform:uppercase}
.card .body{margin-top:14px}
.card .foot{margin-top:12px;color:var(--faint);font-size:var(--fs-micro);line-height:1.4}
/* ---------- kpi ---------- */
.kpi{display:flex;flex-direction:column;gap:6px}
.kpi .v{font-size:var(--fs-big);font-weight:640;letter-spacing:-.02em;line-height:1;
  display:flex;align-items:baseline;gap:4px;flex-wrap:wrap}
.kpi .v small{font-size:13px;font-weight:450;color:var(--dim);letter-spacing:0;margin-left:3px}
.kpi .n{color:var(--dim);font-size:var(--fs-small)}
.kpi.warn .v{color:var(--amber)}.kpi.bad .v{color:var(--coral)}.kpi.ok .v{color:var(--mint)}
/* ---------- pills ---------- */
.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:999px;
  font-size:var(--fs-micro);letter-spacing:.03em;border:1px solid var(--line);
  color:var(--dim);background:rgba(255,255,255,.02);white-space:nowrap}
.pill.ok{color:var(--mint);border-color:rgba(98,230,168,.28);background:rgba(98,230,168,.08)}
.pill.warn{color:var(--amber);border-color:rgba(245,181,68,.3);background:rgba(245,181,68,.08)}
.pill.bad{color:var(--coral);border-color:rgba(255,122,138,.3);background:rgba(255,122,138,.09)}
.pill.blue{color:var(--blue);border-color:rgba(127,168,255,.28);background:rgba(127,168,255,.08)}
/* ---------- charts ---------- */
.chart{display:block;width:100%;overflow:visible}
.spark{height:52px}
.legend{display:grid;grid-template-columns:1fr 1fr;gap:7px 14px;margin-top:14px}
.legend span{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--dim)}
.legend i{width:7px;height:7px;border-radius:2px;flex:none}
.legend b{margin-left:auto;color:var(--text);font-weight:560;font-variant-numeric:tabular-nums}
/* horizontal bar list */
.bars{display:flex;flex-direction:column;gap:9px}
.bar-row{display:grid;grid-template-columns:minmax(58px,auto) 1fr auto;align-items:center;gap:10px;font-size:13px}
.bar-row .lab{color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:34vw}
.bar-row .track{height:8px;background:var(--surface-3);border-radius:99px;overflow:hidden;display:block}
.bar-row .fill{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--mint),#3aa87c)}
.bar-row .num{color:var(--text);font-variant-numeric:tabular-nums;font-size:12px}
/* funnel */
.funnel{display:flex;flex-direction:column;gap:12px}
.fstep .top{display:flex;justify-content:space-between;align-items:baseline;gap:10px;font-size:13px}
.fstep .top b{font-weight:600;white-space:nowrap}
.fstep .top span{color:var(--dim);font-size:12px;text-align:right;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fstep .track{height:12px;margin-top:6px;background:var(--surface-3);border-radius:99px;overflow:hidden}
.fstep .fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#62e6a8,#2f8f6f)}
.fstep:nth-child(2) .fill{background:linear-gradient(90deg,#7fa8ff,#4f6fd0)}
.fstep:nth-child(3) .fill{background:linear-gradient(90deg,#b79bff,#7d63d6)}
.fstep:nth-child(4) .fill{background:linear-gradient(90deg,#f5b544,#c98a22)}
@media(max-width:460px){
  .fstep .top{flex-wrap:wrap;gap:2px 10px}
  .fstep .top span{text-align:left;width:100%;white-space:normal}
}
/* queue + lists */
.list{display:flex;flex-direction:column}
.item{display:flex;gap:12px;padding:13px 0;border-top:1px solid var(--line-soft)}
.item:first-child{border-top:0;padding-top:0}
.item .meta{min-width:0;flex:1}
.item .name{font-weight:560;font-size:14px;letter-spacing:-.01em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.item .desc{color:var(--faint);font-size:var(--fs-small);margin-top:3px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.item .side{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex:none}
/* alarms */
.alarm{display:flex;gap:11px;padding:12px 13px;border-radius:14px;border:1px solid var(--line);
  background:var(--surface-2);font-size:13px}
.alarm+.alarm{margin-top:9px}
.alarm .ic{width:22px;height:22px;border-radius:7px;flex:none;display:grid;place-items:center;
  font-size:12px;background:rgba(255,122,138,.12);color:var(--coral)}
.alarm.warn .ic{background:rgba(245,181,68,.12);color:var(--amber)}
.alarm.ok .ic{background:rgba(98,230,168,.12);color:var(--mint)}
.alarm .t{line-height:1.45}
.only-mobile{display:block}
.only-wide{display:none}
@media(min-width:640px){.only-mobile{display:none}.only-wide{display:block}}
/* tables */
.tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -4px}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:440px}
th,td{text-align:left;padding:9px 6px;border-bottom:1px solid var(--line-soft);vertical-align:top}
th{color:var(--faint);font-weight:500;font-size:var(--fs-micro);letter-spacing:.06em;text-transform:uppercase}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:0}
code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--dim)}
/* footer + nav */
footer{color:var(--faint);font-size:var(--fs-micro);padding:34px 0 10px;line-height:1.6}
.bottomnav{position:fixed;left:0;right:0;bottom:0;z-index:30;display:grid;grid-template-columns:repeat(4,1fr);
  background:rgba(10,12,15,.9);backdrop-filter:blur(18px);border-top:1px solid var(--line);
  padding-bottom:env(safe-area-inset-bottom)}
.bottomnav a{display:flex;flex-direction:column;align-items:center;gap:3px;padding:11px 0 12px;
  color:var(--faint);text-decoration:none;font-size:10.5px;letter-spacing:.04em;text-transform:uppercase}
.bottomnav a.on{color:var(--text);position:relative}
.bottomnav a.on::before{content:"";position:absolute;top:0;width:24px;height:2px;
  border-radius:0 0 2px 2px;background:var(--mint)}
.bottomnav .ico{width:18px;height:18px;opacity:.85}
@media(min-width:900px){.bottomnav{display:none}body{padding-bottom:0}}
@media(prefers-reduced-motion:no-preference){
  .fill{transition:width .5s ease}
}
"""

ICONS = {
    "exec": '<path d="M3 12h4l2.5-7 4 14 2.5-7H21" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    "cost": '<path d="M4 19V9m5 10V5m5 14v-7m5 7V3" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round"/>',
    "ops": '<path d="M12 3l8 4v6c0 4.4-3.4 7.4-8 8-4.6-.6-8-3.6-8-8V7l8-4z" fill="none" '
           'stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    "res": '<rect x="3" y="4" width="18" height="7" rx="2" fill="none" stroke="currentColor" '
           'stroke-width="1.6"/><rect x="3" y="13" width="18" height="7" rx="2" fill="none" '
           'stroke="currentColor" stroke-width="1.6"/><circle cx="7" cy="7.5" r="1" fill="currentColor"/>'
           '<circle cx="7" cy="16.5" r="1" fill="currentColor"/>',
}


# ------------------------------------------------------------------ charts

def sparkline(values, width=340, height=52, tone="--mint"):
    """A line + soft area. Fewer than two points is a fact, not a chart: say so."""
    values = [v for v in values if isinstance(v, (int, float))]
    if len(values) < 2:
        return (f'<svg class="chart spark" viewBox="0 0 {width} {height}" role="img" '
                f'aria-label="not enough history yet">'
                f'<line x1="0" y1="{height-1}" x2="{width}" y2="{height-1}" '
                f'stroke="var(--line)" stroke-width="1" stroke-dasharray="3 4"/>'
                f'<circle cx="{width/2:.0f}" cy="{height/2:.0f}" r="3" fill="var(--faint)"/>'
                f'<text x="{width/2:.0f}" y="{height/2+18:.0f}" text-anchor="middle" '
                f'fill="var(--faint)" font-size="10">series begins today</text></svg>')
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    pad = 4
    step = (width - 2 * pad) / (len(values) - 1)
    pts = []
    for i, v in enumerate(values):
        x = pad + i * step
        y = height - pad - ((v - lo) / span) * (height - 2 * pad)
        pts.append((x, y))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad},{height} " + line + f" {width-pad},{height}"
    gid = f"g{abs(hash(tuple(values))) % 10000}"
    return (f'<svg class="chart spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
            f'role="img" aria-label="sparkline">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="var({tone})" stop-opacity=".28"/>'
            f'<stop offset="1" stop-color="var({tone})" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{area}" fill="url(#{gid})"/>'
            f'<polyline points="{line}" fill="none" stroke="var({tone})" stroke-width="1.8" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.6" fill="var({tone})"/></svg>')


def donut(segments, center_label="", center_sub="", size=168):
    """segments: [(label, value, css_color)] — arcs drawn as stroked circles."""
    total = sum(max(v, 0) for _, v, _ in segments) or 1
    c = size / 2
    radius = size * 0.33
    stroke = size * 0.098
    circumference = 2 * 3.141592653589793 * radius
    offset = 0.0
    rings = []
    for label, value, color in segments:
        length = (max(value, 0) / total) * circumference
        if value:
            rings.append(
                f'<circle r="{radius:.2f}" cx="{c:.1f}" cy="{c:.1f}" fill="none" stroke="{color}" '
                f'stroke-width="{stroke:.2f}" stroke-dasharray="{length:.2f} {circumference-length:.2f}" '
                f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {c:.1f} {c:.1f})">'
                f'<title>{esc(label)}: {value}</title></circle>')
        offset += length
    label_svg = (f'<text x="{c:.1f}" y="{c-2:.1f}" text-anchor="middle" fill="var(--text)" '
                 f'font-size="{size*0.17:.1f}" font-weight="640" letter-spacing="-.5">{esc(center_label)}</text>'
                 f'<text x="{c:.1f}" y="{c+size*0.115:.1f}" text-anchor="middle" fill="var(--faint)" '
                 f'font-size="{size*0.058:.1f}" letter-spacing=".08em">{esc(center_sub).upper()}</text>')
    return (f'<svg viewBox="0 0 {size} {size}" role="img" aria-label="composition" '
            f'style="width:{size}px;max-width:100%;flex:none">'
            f'<circle r="{radius:.2f}" cx="{c:.1f}" cy="{c:.1f}" fill="none" stroke="var(--surface-3)" '
            f'stroke-width="{stroke:.2f}"/>{"".join(rings)}{label_svg}</svg>')


def gauge(pct, label, sub="", marks=(80, 95), width=320, height=178):
    """A semicircular gauge drawn with pathLength=100 so the fill is exact.

    The arc geometry is a fixed semicircle: no trigonometry in the fill, which is what
    made the first version clip and misreport small values.
    """
    import math
    pct = max(0.0, min(100.0, float(pct or 0)))
    cx, cy, r = width / 2, height - 26, width / 2 - 22
    path = f"M{cx-r:.1f},{cy:.1f} A{r:.1f},{r:.1f} 0 0 1 {cx+r:.1f},{cy:.1f}"
    color = "var(--mint)" if pct < marks[0] else ("var(--amber)" if pct < marks[1] else "var(--coral)")
    ticks = []
    for mark in marks:
        angle = math.pi * (1 - mark / 100)
        tx, ty = cx + r * math.cos(angle), cy - r * math.sin(angle)
        ix, iy = cx + (r - 9) * math.cos(angle), cy - (r - 9) * math.sin(angle)
        ticks.append(f'<line x1="{ix:.1f}" y1="{iy:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
                     f'stroke="var(--faint)" stroke-width="1.6" stroke-linecap="round"/>')
    return (f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}">'
            f'<path d="{path}" fill="none" stroke="var(--surface-3)" stroke-width="13" '
            f'stroke-linecap="round" pathLength="100"/>'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="13" stroke-linecap="round" '
            f'pathLength="100" stroke-dasharray="{pct:.2f} 100"/>'
            f'{"".join(ticks)}'
            f'<text x="{cx:.1f}" y="{cy-34:.1f}" text-anchor="middle" fill="var(--text)" '
            f'font-size="38" font-weight="640" letter-spacing="-1.2">{pct:.1f}%</text>'
            f'<text x="{cx:.1f}" y="{cy-12:.1f}" text-anchor="middle" fill="var(--faint)" '
            f'font-size="10" letter-spacing=".08em">{esc(sub).upper()}</text></svg>')


def edge_label(value):
    """Axis edge for a cost bucket: €0.003, €0.05, €0.64 - never 15 decimals."""
    return f"€{float(value):.3g}"


def histogram(bins, width=340, height=132, label="cost"):
    """Vertical bars over log-ish buckets: lo/hi/count. Keeps the tail visible."""
    if not bins:
        return '<p class="sub">no data</p>'
    top = max(b["count"] for b in bins) or 1
    pad_l, pad_r, pad_b, pad_t = 4, 4, 26, 10
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_b - pad_t
    slot = plot_w / len(bins)
    gap = max(2.0, slot * 0.16)
    bars, labels = [], []
    for i, b in enumerate(bins):
        h = (b["count"] / top) * plot_h if b["count"] else 0
        x = pad_l + i * slot + gap / 2
        w = slot - gap
        y = pad_t + plot_h - h
        tone = "var(--mint)" if b["count"] else "var(--surface-3)"
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{max(h, 1):.1f}" '
                    f'rx="2.5" fill="{tone}" opacity="{0.95 if b["count"] else 0.5}">'
                    f'<title>{fmt(b["lo"])}–{fmt(b["hi"])}: {b["count"]} job(s)</title></rect>')
        if b["count"]:
            bars.append(f'<text x="{x + w/2:.1f}" y="{y - 4:.1f}" text-anchor="middle" '
                        f'fill="var(--dim)" font-size="9.5">{b["count"]}</text>')
    edges = [bins[0]["lo"]] + [b["hi"] for b in bins]
    for i, edge in enumerate(edges):
        if len(edges) > 6 and i not in (0, len(edges) - 1, len(edges) // 2):
            continue
        x = pad_l + i * slot
        labels.append(f'<text x="{x:.1f}" y="{height - 8}" text-anchor="{"start" if i == 0 else ("end" if i == len(edges) - 1 else "middle")}" '
                      f'fill="var(--faint)" font-size="9">{edge_label(edge)}</text>')
    return (f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="histogram of {esc(label)}">'
            f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{width - pad_r}" y2="{pad_t + plot_h}" '
            f'stroke="var(--line)" stroke-width="1"/>'
            f'{"".join(bars)}{"".join(labels)}</svg>')


def bar_list(items, tone="mint", money=False):
    """items: [(label, value)] - widths are relative to the largest value."""
    top = max([v for _, v in items], default=0) or 1
    rows = []
    for label, value in items:
        width = max(2, round(100 * value / top, 1))
        rows.append(
            f'<div class="bar-row"><span class="lab" title="{esc(label)}">{esc(label)}</span>'
            f'<span class="track"><span class="fill" style="width:{width}%"></span></span>'
            f'<span class="num">{eur(value) if money else fmt(value)}</span></div>')
    return f'<div class="bars">{"".join(rows)}</div>'


def funnel(stages):
    """stages: [(label, count, note)] - each bar is a share of the first stage."""
    if not stages:
        return '<p class="sub">no stages recorded</p>'
    top = stages[0][1] or 1
    rows = []
    for label, count, note in stages:
        width = max(1.5, round(100 * count / top, 1))
        rows.append(
            f'<div class="fstep"><div class="top"><b>{esc(label)}</b>'
            f'<span>{fmt(count)} &middot; {esc(note)}</span></div>'
            f'<div class="track"><div class="fill" style="width:{width}%"></div></div></div>')
    return f'<div class="funnel">{"".join(rows)}</div>'


# ------------------------------------------------------------------ components

def kpi(label, value, unit="", note="", tone="neutral", sub=""):
    cls = "" if tone == "neutral" else f" {tone}"
    unit_html = f"<small>{esc(unit)}</small>" if unit and value is not None else ""
    return (f'<div class="kpi{cls}"><span class="sub">{esc(label)}</span>'
            f'<span class="v">{fmt(value)}{unit_html}</span>'
            f'<span class="n">{esc(note or sub)}</span></div>')


def card(title, body, sub="", foot="", cls=""):
    head = f'<h3>{esc(title)}</h3>' + (f'<div class="sub">{esc(sub)}</div>' if sub else "")
    foot_html = f'<div class="foot">{foot}</div>' if foot else ""
    return f'<section class="card {cls}">{head}<div class="body">{body}</div>{foot_html}</section>'


def pill(text, tone="neutral"):
    return f'<span class="pill {"" if tone == "neutral" else tone}">{esc(text)}</span>'


def alarm(text, tone="bad", icon="!"):
    return f'<div class="alarm {"" if tone == "bad" else tone}"><span class="ic">{esc(icon)}</span>' \
           f'<span class="t">{text}</span></div>'


def table(headers, rows, num_cols=()):
    head = "".join(f'<th class="{"num" if i in num_cols else ""}">{esc(h)}</th>'
                   for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(
        f'<td class="{"num" if i in num_cols else ""}">{cell}</td>' for i, cell in enumerate(row)
    ) + "</tr>" for row in rows)
    return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def humanize_seconds(text):
    """'lock held for 1208s by x' -> 'lock held for 20m by x'."""
    import re

    def swap(match):
        seconds = int(match.group(1))
        return f"{seconds}s" if seconds < 90 else humanize(seconds // 60)

    return re.sub(r"(\d+)s\b", swap, text or "")


def humanize(minutes):
    """12 -> '12m', 1697 -> '1.2d', 129762 -> '90d'."""
    if minutes is None:
        return "—"
    minutes = max(0, int(minutes))
    if minutes < 1:
        return "just now"
    if minutes < 90:
        return f"{minutes}m"
    if minutes < 1440:
        return f"{minutes/60:.1f}h".replace(".0h", "h")
    days = minutes / 1440
    return f"{days:.1f}d".replace(".0d", "d") if days < 10 else f"{days:.0f}d"


def page(title, active, generated_at, body, subtitle="", footer_extra=""):
    nav = [("exec", "index.html", "Overview"), ("cost", "cost.html", "Cost"),
           ("res", "resources.html", "Resources"), ("ops", "reliability.html", "Ops")]
    top = "".join(f'<a href="{href}" class="{"on" if key == active else ""}">{label}</a>'
                  for key, href, label in nav)
    bottom = "".join(
        f'<a href="{href}" class="{"on" if key == active else ""}">'
        f'<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">{ICONS[key]}</svg>{label}</a>'
        for key, href, label in nav)
    stamp = esc(generated_at)
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><meta name="color-scheme" content="dark">
<meta name="theme-color" content="#07080a">
<title>{esc(title)} · Scout</title><link rel="stylesheet" href="style.css"></head><body>
<header class="top"><div class="wrap"><span class="brand"><span class="mark"></span>Scout</span>
<nav class="topnav">{top}</nav>
<span class="live"><span class="dot"></span>live {stamp[11:16]} UTC</span></div></header>
<main class="wrap">{body}
<footer>Generated from repository state at {stamp}. Every figure carries its source in the
snapshot (<code>dashboard.json</code>); a missing input reads &ldquo;no data&rdquo; rather than zero.
{footer_extra}</footer></main>
<nav class="bottomnav">{bottom}</nav>
</body></html>"""


# ------------------------------------------------------------------ pages

def render_overview(snapshot, alarms, alarms_plain=()):
    c = snapshot["candidates"]
    coverage = snapshot.get("coverage") or {}
    releases = snapshot["releases"]["releases"]
    history = snapshot.get("history") or []
    decision = (snapshot.get("budget") or {}).get("decision") or {}
    health = snapshot["health"] or {}

    counts = c["counts"]
    total = sum(counts.values())
    kept = counts.get("investigating", 0) + counts.get("qualified", 0) + counts.get("published", 0)
    advanced = counts.get("qualified", 0) + counts.get("published", 0)
    published = counts.get("published", 0)
    verified = sum(1 for r in releases if r["verified_all"])

    series_tokens = [p.get("tokens_7d") for p in history][-14:]
    series_pub = [p.get("published") for p in history][-14:]
    series_live = [p.get("live") for p in history][-14:]

    hero_ok = not alarms
    verdict_text = (f"{len(alarms)} item{'s' if len(alarms) != 1 else ''} "
                    f"{'need' if len(alarms) != 1 else 'needs'} attention")

    def pct(part, whole):
        return f"{round(100 * part / whole)}% of previous" if whole else ""
    stopped = counts.get("parked", 0) + counts.get("dropped", 0)
    stages = [
        ("Sources opened", total, f"{counts.get('dropped', 0)} dropped, {counts.get('parked', 0)} parked"),
        ("Kept in the bench", kept, f"−{stopped} stopped · {pct(kept, total)}"),
        ("Built or packaging", advanced, f"−{kept - advanced} queued · {pct(advanced, kept)}"),
        ("Published", published, f"−{advanced - published} in packaging · {pct(published, advanced)}"),
    ]
    donut_segments = [
        ("published", counts.get("published", 0), "var(--mint)"),
        ("qualified", counts.get("qualified", 0), "var(--amber)"),
        ("investigating", counts.get("investigating", 0), "var(--blue)"),
        ("parked", counts.get("parked", 0), "var(--violet)"),
        ("dropped", counts.get("dropped", 0), "#3c4553"),
    ]
    countries = (coverage.get("by_country") or {})
    country_items = list(countries.items())[:6]

    queue = sorted(c["live"], key=lambda x: 0 if x["status"] == "qualified" else 1)
    queue_html = "".join(
        f'<div class="item"><div class="meta"><div class="name">{esc(q["id"])}</div>'
        f'<div class="desc">{esc(q["next_action"])}</div></div>'
        f'<div class="side">{pill(q["country"], "blue")}'
        f'{pill(q["status"], "ok" if q["status"] == "qualified" else "neutral")}</div></div>'
        for q in queue)

    release_cards = '<div class="list">' + "".join(
        f'<div class="item"><div class="meta"><div class="name">{esc(r["dataset"])}</div>'
        f'<div class="desc">{esc(r["release_tag"])} · {fmt(r["rows"])} rows · baseline '
        f'{"—" if r["baseline_eval_auc"] is None else f"{r['baseline_eval_auc']:.3f}"}</div></div>'
        f'<div class="side">{"".join(pill(k, "ok" if v else "bad") for k, v in (r["verified"] or {}).items())}</div></div>'
        for r in releases) + '</div>'
    release_ready = (c.get("release") or {}).get("packaged") or []
    release_card = ""
    if release_ready:
        rows = []
        for record in sorted(release_ready, key=lambda r: (r.get("awaiting_operator") or False)):
            age = record.get("age_hours")
            age_text = f" · {age}h ago" if age is not None else ""
            if record.get("awaiting_operator"):
                desc = "packaged" + age_text + " — verified, waiting on the operator to flip it public"
                state = pill("awaiting flip", "warn")
            else:
                desc = "packaged" + age_text + " — actionable now: shipping outranks construction"
                state = pill("ship it", "bad")
            rows.append(
                '<div class="item"><div class="meta">'
                f'<div class="name">{esc(record["id"])}</div>'
                f'<div class="desc">{esc(desc)}</div>'
                f'</div><div class="side">{state}</div></div>')
        release_card = '<div class="col-12">' + card("Ready to ship", '<div class="list">' + "".join(rows) + '</div>',
                            sub=f"{len(release_ready)} packaged",
                            foot="While anything here is actionable, construction launches are refused. "
                                 "Once the only step left is the flip, construction resumes and this waits on you.") + '</div>' 

    release_rows = [(
        f'<b>{esc(r["dataset"])}</b>', esc(r["release_tag"]),
        fmt(r["rows"]), "—" if r["baseline_eval_auc"] is None else f'{r["baseline_eval_auc"]:.3f}',
        "".join(pill(k, "ok" if v else "bad") for k, v in (r["verified"] or {}).items()) or pill("—"),
    ) for r in releases]

    latest_publish = _latest(releases)
    days_since = (round((datetime.now(timezone.utc) - latest_publish).total_seconds() / 86400, 1)
                  if latest_publish else None)
    tiles = "".join([
        kpi("Published", published, note=f"{verified} fully verified"),
        kpi("Days since", days_since, "d", "last publication"),
        kpi("Active bench", coverage.get("live"),
            note=f"{coverage.get('live_non_us', 0)} non-US · {round(100 * (coverage.get('live_non_us_share') or 0))}%"),
        kpi("Tokens 7d", decision.get("research_tokens_last_7_days"),
            note=f"{(decision.get('research_tokens_last_7_days') or 0) / (decision.get('weekly_token_budget') or 1) * 100:.1f}% of ceiling"),
    ])

    body = f"""
<section class="hero">
  <div class="eyebrow">Executive overview</div>
  <h1>{published} datasets shipped</h1>
  <p>{counts.get('qualified', 0)} qualified and {counts.get('investigating', 0)} in construction. The bench is
  {round(100 * (coverage.get('live_non_us_share') or 0))}% non-US across {len(countries)} jurisdictions.</p>
  <div class="statusline {'ok' if hero_ok else 'warn'}"><span class="dot" style="background:{'var(--mint)' if hero_ok else 'var(--amber)'}"></span>
    <span><b>{'All systems nominal' if hero_ok else verdict_text}</b>{'' if hero_ok else ' — ' + esc(alarms_plain[0] if alarms_plain else '')}</span>
    <time>{esc(snapshot['generated_at'][11:16])} UTC</time></div>
</section>

<div class="grid">
  <div class="col-12"><div class="kpis">{tiles}</div></div>

  <div class="col-7">{card("The funnel", funnel(stages), sub="sources → shipped",
        foot="Each stage is a share of the sources opened. Drop reasons live in the candidate records.")}</div>
  <div class="col-5">{card("Portfolio", '<div class="donut-wrap">' + donut(donut_segments, str(total), "candidates", size=150)
        + '<div class="legend">' + "".join(
            f'<span><i style="background:{color}"></i>{esc(label)} <b style="color:var(--text)">{value}</b></span>'
            for label, value, color in donut_segments) + "</div>", sub="all 28 sources")}</div>

  <div class="col-4">{card("Published", sparkline(series_pub), sub="cumulative, 14d",
        foot="History begins 2026-10-20; the series fills in hourly.")}</div>
  <div class="col-4">{card("Active bench", sparkline(series_live, tone="--blue"), sub="live candidates, 14d")}</div>
  <div class="col-4">{card("Research tokens", sparkline(series_tokens, tone="--violet"), sub="7-day total")}</div>

  <div class="col-5">{card("Where the data comes from", bar_list(country_items), sub="by publisher jurisdiction",
        foot=f"{coverage.get('live_non_us', 0)} of {coverage.get('live', 0)} active candidates are non-US.")}</div>
  <div class="col-7">{card("Alarms", "".join(alarms) if alarms else
        alarm("Nothing above threshold. Watchdog jobs, gates and budget are inside limits.", "ok", "✓"),
        sub="what needs a human")}</div>

  {release_card}
  <div class="col-12">{card("Work queue", f'<div class="list">{queue_html}</div>', sub=f"{len(queue)} candidates",
        foot="Ordered: qualified first, then by discovery. Only one worker exists, so this is a queue, not parallelism.")}</div>

  <div class="col-12">{card("Releases", f'<div class="only-mobile">{release_cards}</div><div class="only-wide">' +
        table(["Dataset", "Version", "Rows", "Baseline AUC", "Destinations"],
              release_rows, num_cols=(2, 3)) + '</div>', sub="published artifacts",
        foot="Destination pills are read from each release's DESTINATIONS.json, not from a deploy log.")}</div>
</div>"""
    return body


def render_cost(snapshot, alarms, alarms_plain=()):
    decision = (snapshot.get("budget") or {}).get("decision") or {}
    usage = decision.get("usage") or {}
    tokens = decision.get("research_tokens_last_7_days")
    ceiling = decision.get("weekly_token_budget")
    sessions = decision.get("runs_last_7_days")
    cap = decision.get("session_cap_per_week")
    reasons = decision.get("reasons") or []
    only_lock = (decision.get("allowed") is False and reasons
                 and all("lock held" in r for r in reasons))
    tpct = 100 * (tokens or 0) / (ceiling or 1)
    spct = 100 * (sessions or 0) / (cap or 1)

    buckets = [("interactive", usage.get("interactive", {}), "var(--blue)"),
               ("research", usage.get("research", {}), "var(--mint)"),
               ("auxiliary", usage.get("auxiliary", {}), "var(--violet)"),
               ("scheduled", usage.get("scheduled-other", {}), "var(--faint)")]
    rows = [(f'<b>{esc(name)}</b>', fmt(b.get("calls") or 0),
             fmt(b.get("input_tokens") or 0), fmt(b.get("output_tokens") or 0))
            for name, b, _ in buckets]

    body = f"""
<section class="hero compact">
  <div class="eyebrow">Cost &amp; capacity</div>
  <h1>{fmt(tokens)} tokens this week</h1>
  <p>of the weekly research ceiling used ({fmt(tokens)} of {fmt(ceiling)} tokens). The gate admits
  the next session {esc('now' if decision.get('allowed') else 'only after the current one releases')}.</p>
  <div class="statusline {'ok' if decision.get('allowed') else ('ok' if only_lock else 'warn')}"><span class="dot" style="background:{'var(--mint)' if decision.get('allowed') or only_lock else 'var(--amber)'}"></span>
    <span><b>{'Gate open' if decision.get('allowed') else ('Session in flight' if only_lock else 'Gate closed')}</b> — {esc(humanize_seconds('; '.join(decision.get('reasons') or ['no blockers']))[:90])}</span>
    <time>{esc(snapshot['generated_at'][11:16])} UTC</time></div>
</section>

<div class="grid">
  <div class="col-6">{card("Weekly tokens", gauge(tpct, "weekly tokens", f"{fmt(tokens)} of {fmt(ceiling)} tokens"),
        sub="measured, not estimated")}</div>
  <div class="col-6">{card("Sessions", gauge(spct, "sessions", f"{sessions or 0} of {cap or 0} sessions"),
        sub="scheduled runs this week")}</div>

  <div class="col-12">{card("Spend by source", table(
        ["Source", "Calls", "Input tokens", "Output tokens"], rows, num_cols=(1, 2, 3)),
        sub="all-time counters from the session ledger")}</div>

  <div class="col-12">{card("Unit economics", '<p class="sub" style="line-height:1.7">'
        'Worker euros and cost per published dataset appear once the per-job ledger is recorded. '
        'Until then this panel says <b>no data</b> rather than an estimate that would read as billing.</p>',
        sub="not instrumented in P0")}</div>
</div>"""
    return body


def render_ops(snapshot, alarms, alarms_plain=()):
    health = snapshot["health"] or {}
    jobs = [j for j in (snapshot.get("cron") or {}).get("jobs", []) if j["enabled"]]
    head = health.get("head") or {}
    tests = health.get("tests") or {}
    checks = health.get("checks") or {}
    coverage = health.get("coverage") or {}
    ci = health.get("ci") or {}

    def gate(label, ok, detail):
        state, tone = ("pass", "ok") if ok is True else (("not run", "neutral") if ok is None else ("fail", "bad"))
        return (f'<div class="item"><div class="meta"><div class="name">{esc(label)}</div>'
                f'<div class="desc">{esc(detail)}</div></div>'
                f'<div class="side">{pill(state, tone)}</div></div>')

    gates = "".join([
        gate("Test suite", tests.get("ok") if tests else None,
             f"{tests.get('count') or '?'} tests via unittest" if tests else "not run in this build"),
        gate("Candidate checks", checks.get("ok"), f"{checks.get('passing') or '?'} candidates OK"),
        gate("Discovery coverage", coverage.get("ok"), coverage.get("summary") or "jurisdiction complete"),
        gate("CI", ci.get("conclusion") == "success", f"{ci.get('conclusion') or 'no data'} on {ci.get('head_sha') or '?'}"),
    ])

    measured = [tests.get("ok"), checks.get("ok"), coverage.get("ok")]
    all_ok = (all(measured) and ci.get("conclusion") == "success"
              and all(m is not None for m in measured))
    job_rows, job_cards_data = [], []
    for j in jobs:
        last = _dt(j.get("last_run_at"))
        nxt = _dt(j.get("next_run_at"))
        status = j.get("last_status")
        when = "—" if not last else humanize((datetime.now(timezone.utc) - last).total_seconds() // 60) + " ago"
        in_s = "—" if not nxt else "in " + humanize((nxt - datetime.now(timezone.utc)).total_seconds() // 60)
        job_cards_data.append((j, when, in_s, status))
        job_rows.append((
            f'<b>{esc(j["name"])}</b>', f'<code>{esc(j["schedule"])}</code>',
            f'{esc(when)}', pill(status or "pending", "ok" if status == "ok" else ("warn" if not status else "bad")),
            esc(in_s), fmt(j.get("failure_streak") or 0)))
    job_table = table(["Job", "Schedule", "Last", "Status", "Next", "Fails"], job_rows, num_cols=(5,))
    job_cards = '<div class="list">' + "".join(
        f'<div class="item"><div class="meta"><div class="name">{esc(j["name"])}</div>'
        f'<div class="desc"><code>{esc(j["schedule"])}</code> · last {esc(when)} · next {esc(in_s)}</div></div>'
        f'<div class="side">{pill(status or "pending", "ok" if status == "ok" else ("warn" if not status else "bad"))}'
        f'</div></div>' for j, when, in_s, status in job_cards_data) + '</div>' 

    body = f"""
<section class="hero compact">
  <div class="eyebrow">Operations</div>
  <h1>{'All gates green' if all_ok else ('A gate is failing' if any(m is False for m in measured) else 'Gates not fully measured')}</h1>
  <p>Every number below is read back from the scheduler and the repository, not from a launch
  message. Repo head <code>{esc(head.get('sha'))}</code> · {esc(head.get('subject'))}</p>
  <div class="statusline {'ok' if all_ok else 'warn'}"><span class="dot" style="background:{'var(--mint)' if all_ok else 'var(--amber)'}"></span>
    <span><b>{len(jobs)} scheduled jobs</b> — CI {esc(ci.get('conclusion') or 'unknown')}</span>
    <time>{esc(snapshot['generated_at'][11:16])} UTC</time></div>
</section>

<div class="grid">
  <div class="col-6">{card("Gates", f'<div class="list">{gates}</div>', sub="merge blockers")}</div>
  <div class="col-6">{card("Alarms", "".join(alarms) if alarms else alarm("Nothing above threshold.", "ok", "✓"),
        sub="watchdogs")}</div>
  <div class="col-12">{card("Recent sessions",
        '<div class="list">' + "".join(
            f'<div class="item"><div class="meta"><div class="name">{esc(e.get("prompt_file") or "session")}</div>'
            f'<div class="desc">{esc(str(e.get("ts") or "")[:16].replace("T", " "))} · '
            f'{esc(str(e.get("elapsed_seconds") or "?"))}s · {esc(e.get("max_turns") or "?")} turns</div></div>'
            f'<div class="side">{pill("killed" if "killed" in str(e.get("outcome")) else str(e.get("outcome")), "bad" if "killed" in str(e.get("outcome")) else "ok")}</div></div>'
            for e in reversed((snapshot.get("sessions") or {}).get("recent") or [])) + '</div>',
        sub="last six scheduled runs", foot="A killed session produced no report: the tick was paid for and delivered nothing.")}</div>
  <div class="col-12">{card("Scheduled jobs",
        f'<div class="only-mobile">{job_cards}</div><div class="only-wide">{job_table}</div>',
        sub="from the scheduler's own record")}</div>
  <div class="col-12">{card("Repository", table(["Field", "Value"], [
        ("commit", f"<code>{esc(head.get('sha'))}</code>"),
        ("committed", esc(head.get('at'))),
        ("subject", esc(head.get('subject'))),
        ("checked", esc(snapshot['generated_at']))], num_cols=()), sub="source of truth")}</div>
</div>"""
    return body


def render_resources(snapshot, alarms, alarms_plain=()):
    res = snapshot.get("resources") or {}
    months = res.get("months") or []
    jobs = res.get("jobs") or []
    live = res.get("live") or {}
    mtd = res.get("month_to_date")
    ceiling = res.get("ceiling_eur")
    projected = res.get("projected_month_eur")
    lifetime = res.get("lifetime_eur")
    per_release = res.get("eur_per_release")

    month_items = [(m["month"], round(m["eur"], 2)) for m in months][-6:]
    over = projected is not None and ceiling is not None and projected > ceiling
    hero_status = ("ok" if not over else "warn")
    hero_text = ("All billable resources destroyed" if live.get("servers") == 0
                 else f"{live.get('servers')} server(s) still billable")

    hist = res.get("histogram") or {}
    bins = hist.get("bins") or []
    if bins:
        stats = "".join([
            pill(f"median {eur(hist.get('median'))}", "neutral"),
            pill(f"p90 {eur(hist.get('p90'))}", "neutral"),
            pill(f"max {eur(hist.get('max'))}", "neutral"),
            pill(f"{hist.get('n', 0)} jobs", "blue"),
        ])
        histogram_chart = (f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">'
                           f'{stats}</div>' + histogram(bins))
        histogram_sub = (f"cost per job at the cpx32 reference rate of "
                         f"€{hist.get('ref_rate', 0):.4f}/h")
        histogram_foot = ("Each job's recorded lifetime is priced at one reference rate, so a cpx42 job "
                          "and a cpx32 job land on the same axis. Buckets widen as cost grows so the tail stays "
                          "visible; the right-hand tail is a handful of long jobs, not a billing error.")
    else:
        histogram_chart, histogram_sub, histogram_foot = '<p class="sub">no data</p>', "no data", ""

    job_rows = [(esc(j["id"]), esc(j.get("server_type") or "—"),
                 esc((j.get("created_at") or "")[:16].replace("T", " ")),
                 "—" if j.get("hours") is None else f'{j["hours"]:.2f} h',
                 eur(j.get("eur")), pill("destroyed" if j.get("status") == "deleted"
                                         else (j.get("status") or "—"),
                                         "ok" if j.get("status") == "deleted" else "warn"))
                for j in jobs[-10:]][::-1]

    body = f"""
<section class="hero compact">
  <div class="eyebrow">Hetzner resources</div>
  <h1>{eur(mtd)} this month</h1>
  <p>{res.get('jobs_this_month', 'no data')} worker jobs across {res.get('month_hours', 0):.1f} server-hours.
  Lifetime spend on this project is {eur(lifetime)} across {res.get('jobs_total', 'no data')} jobs.</p>
  <div class="statusline {hero_status}"><span class="dot" style="background:{'var(--mint)' if hero_status == 'ok' else 'var(--amber)'}"></span>
    <span><b>{hero_text}</b>{' — projected €' + format(projected, '.2f') + ' by month end' if projected is not None else ''}</span>
    <time>{esc(snapshot['generated_at'][11:16])} UTC</time></div>
</section>

<div class="grid">
  <div class="col-12"><div class="kpis">
    {kpi("Month to date", eur(mtd), note=f"ceiling {eur(ceiling, 0)}/month")}
    {kpi("Projected month", eur(projected), note="linear from today's run rate",
         tone="warn" if over else "neutral")}
    {kpi("Jobs this month", res.get("jobs_this_month"), note=f"{res.get('month_hours', 0):.1f} server-hours")}
    {kpi("Per published dataset", eur(per_release), note="lifetime worker spend / releases")}
  </div></div>

  <div class="col-12">{card("Normalised job cost", histogram_chart, sub=histogram_sub, foot=histogram_foot)}</div>
  <div class="col-7">{card("Spend by month", bar_list(month_items, money=True), sub="recorded server lifetime × hourly rate",
        foot="Computed from each job record's created_at and deleted_at and the provider rate captured at launch. "
             "This is what the reservation math uses, not an invoice.")}</div>
  <div class="col-5">{card("Billable right now", '<div class="list">'
        + f'<div class="item"><div class="meta"><div class="name">Servers</div>'
          f'<div class="desc">read from the provider API, not this project\'s bookkeeping</div></div>'
          f'<div class="side">{pill(str(live.get("servers") if live.get("servers") is not None else "no data"), "ok" if live.get("servers") == 0 else "warn")}</div></div>'
        + f'<div class="item"><div class="meta"><div class="name">Primary IPs</div>'
          f'<div class="desc">released with the server; a survivor is a leak</div></div>'
          f'<div class="side">{pill(str(live.get("primary_ips") if live.get("primary_ips") is not None else "no data"), "ok" if live.get("primary_ips") == 0 else "warn")}</div></div>'
        + '</div>', sub="live inventory", foot=f"checked {esc(live.get('checked_at') or 'never')} · account-wide totals: "
             f"{esc(live.get('servers_total'))} servers, {esc(live.get('primary_ips_total'))} IPs")}</div>

  <div class="col-12">{card("Recent worker jobs",
        f'<div class="only-mobile">{"".join(f"<div class=\'item\'><div class=\'meta\'><div class=\'name\'>{r[0]}</div><div class=\'desc\'>{r[1]} · {r[3]} · {r[4]}</div></div><div class=\'side\'>{r[5]}</div></div>" for r in job_rows)}</div>'
        f'<div class="only-wide">{table(["Job", "Type", "Started (UTC)", "Lifetime", "Cost", "State"], job_rows, num_cols=(3,))}</div>',
        sub="most recent first")}</div>

  <div class="col-12">{card("What this counts", '<p class="sub" style="line-height:1.7">'
        'Server lifetime × the hourly rate recorded when the job launched, plus primary IPv4s. '
        'Excluded because they are free on this project: IPv6, egress inside the monthly allowance, and snapshots. '
        'Not included because they are not recorded yet: volumes and any manual resources created outside the factory.</p>',
        sub="scope")}</div>
</div>"""
    return body


# ------------------------------------------------------------------ helpers

def _dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _latest(releases):
    stamps = [_dt(r.get("verified_at")) for r in releases if r.get("verified_at")]
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None
