# Inline SVG chart primitives

Copy-paste primitives for a static dashboard: no library, no script, no network. Each charts one
question and degrades honestly when the data cannot support a chart.

## Sizing rules

- Set `viewBox`, use `width:100%`, one height per chart type so cards align.
- Sparkline: 320–340 × 48–56. Gauge: 320 × 178, semicircle radius `width/2 - 22`.
- Donut: 150–168 square, stroke ≈ 10% of size, legend beside it (not under) above 560px.
- Use CSS variables for colour so the palette stays in one place; pass a tone name
  (`--mint`, `--amber`, `--coral`) rather than a hex string.

## Sparkline (with the honesty fallback)

Fewer than two points is not a chart. Say so instead of drawing a line from one dot.

```python
def sparkline(values, width=340, height=52, tone="--mint"):
    values = [v for v in values if isinstance(v, (int, float))]
    if len(values) < 2:
        return (f'<svg viewBox="0 0 {width} {height}" role="img">'
                f'<line x1="0" y1="{height-1}" x2="{width}" y2="{height-1}" '
                f'stroke="var(--line)" stroke-dasharray="3 4"/>'
                f'<text x="{width/2}" y="{height/2}" text-anchor="middle" '
                f'font-size="10">series begins today</text></svg>')
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    pad, step = 4, (width - 8) / (len(values) - 1)
    pts = [(pad + i * step, height - pad - ((v - lo) / span) * (height - 2 * pad))
           for i, v in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad},{height} " + line + f" {width-pad},{height}"
    return (f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" role="img">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="var({tone})" stop-opacity=".28"/>'
            f'<stop offset="1" stop-color="var({tone})" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{area}" fill="url(#g)"/>'
            f'<polyline points="{line}" fill="none" stroke="var({tone})" stroke-width="1.8" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')
```

## Semicircular gauge — use `pathLength`, not trigonometry

The fill must be exact at 5% as well as 95%. Computing the arc endpoint with `cos/sin` and
large-arc flags is where gauges clip their card and misreport small values. One fixed path plus
`pathLength="100"` and `stroke-dasharray="{pct} 100"` is exact for every value.

```python
def gauge(pct, marks=(80, 95), width=320, height=178):
    pct = max(0.0, min(100.0, float(pct or 0)))
    cx, cy, r = width / 2, height - 26, width / 2 - 22
    path = f"M{cx-r:.1f},{cy:.1f} A{r:.1f},{r:.1f} 0 0 1 {cx+r:.1f},{cy:.1f}"
    colour = "var(--mint)" if pct < marks[0] else ("var(--amber)" if pct < marks[1] else "var(--coral)")
    return (f'<svg viewBox="0 0 {width} {height}" role="img">'
            f'<path d="{path}" fill="none" stroke="var(--surface-3)" stroke-width="13" '
            f'stroke-linecap="round" pathLength="100"/>'
            f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="13" '
            f'stroke-linecap="round" pathLength="100" stroke-dasharray="{pct:.2f} 100"/>'
            f'<text x="{cx}" y="{cy-34}" text-anchor="middle" font-size="38" '
            f'font-weight="640">{pct:.1f}%</text></svg>')
```

Threshold ticks are optional: `angle = pi * (1 - mark/100)`, then a short radial line. Keep the
numeric label inside the arc or the card looks empty at low values.

## Donut with a legend that carries numbers

Arcs as stroked circles on a shared circumference, one `stroke-dashoffset` accumulator. Verify the
centre is `size/2` — hard-coding `cx=84` breaks the moment `size` is not 168.

```python
circumference = 2 * math.pi * radius
for value, colour in segments:
    length = value / total * circumference
    rings.append(f'<circle r="{radius}" cx="{c}" cy="{c}" fill="none" stroke="{colour}" '
                 f'stroke-width="{stroke}" stroke-dasharray="{length:.2f} {circumference-length:.2f}" '
                 f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {c} {c})"/>')
    offset += length
```

Legend format: `label … count · share%` in two columns. Never use the page background colour for a
segment — it vanishes and the ring looks broken.

## Funnel / conversion bars

A funnel is only honest if each stage says what it is a share **of**. Use "% of previous" rather
than "% of total", and print the absolute loss (`−16 stopped`) so the reader does not do arithmetic
to find the missing rows.

```html
<div class="fstep"><div class="top"><b>Kept in the bench</b>
  <span>−16 stopped · 43% of previous</span></div>
  <div class="track"><div class="fill" style="width:43%"></div></div></div>
```

```css
.fstep .track{height:12px;background:var(--surface-3);border-radius:99px;overflow:hidden}
.fstep .fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#62e6a8,#2f8f6f)}
@media(max-width:460px){.fstep .top{flex-wrap:wrap}.fstep .top span{width:100%;white-space:normal}}
```

The media query is load-bearing: at 390pt the label and the delta truncate to "7 dropp".

## Bar list (categorical counts)

HTML rows, not SVG: a label, a proportional track, and the number. Crisper at small sizes and
accessible without extra work.

```html
<div class="bar-row"><span class="lab">GB</span>
  <span class="track"><span class="fill" style="width:33%"></span></span>
  <span class="num">2</span></div>
```

```css
.bar-row .track{display:block;height:8px;background:var(--surface-3);border-radius:99px;overflow:hidden}
.bar-row .fill{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--mint),#3aa87c)}
```

`display:block` on the fill is load-bearing: `height:100%` on an inline `<span>` is ignored, the bar
tracks render at zero height, and the chart looks like an empty card rather than a bug.

When the bars are money, format the number as currency (`€2.45`, never `2.5` beside a € heading) and
scale widths from the largest value, not from a rounded display value.

## Histogram (a distribution with a tail)

Job costs, latencies and token counts are long-tailed: a linear axis over €0.003–€0.63 puts 45 of 51
jobs in the first bar. Widen the buckets as the value grows (a 1-2-5 sequence) and say so in the
caption, or the equal-width bars imply a spacing the buckets do not have.

Bucket edges: take the 1-2-5 steps inside `[min, max]`, round the first edge **down** to a single
magnitude so the axis label stays readable (`€0.003`, not `€0.0037`), append `max * 1.01` when the
last step lands below the maximum, and make the final bucket inclusive of its upper edge. Cap the
count at ~8 buckets; below 390pt only three edges can carry a label (first, middle, last) at
`:.3g` formatting.

```python
rects.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{max(h,1):.1f}" rx="2.5" '
             f'fill="{tone}"><title>{lo}–{hi}: {count} job(s)</title></rect>')
# count above each non-empty bar, so the height is never the only encoding
```

Ship the summary statistics as text above the chart — median, p90, max, n — because a histogram
without them answers "what shape" but not "what do I budget". In a test, assert
`sum(bucket counts) == n`; an off-by-one edge silently drops the cheapest and dearest jobs.

## Checklist before shipping a chart

- Does it render with one data point, zero data points, and all-zero values?
- Do the bars actually paint? An inline `<span>` fill with `height:100%` is invisible until it is
  `display:block`.
- Is every number on the chart also available as text (screen readers, screenshots)?
- Does it fit at 390pt without clipping the card's rounded corner?
- For a histogram: do the bucket counts sum to the sample size, and does the caption say that the
  buckets widen to the right?
- Does colour encode one thing consistently across all three pages?
