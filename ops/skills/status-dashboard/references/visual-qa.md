# Visual QA for a generated dashboard

Valid markup can still be unusable: labels truncate, arcs clip, a hero eats the first screen. The
only way to catch it is to render at real widths and look.

## The loop

1. **Render at phone width with headless Chromium.** A fixed `--window-size` is deterministic and
   independent of browser-session state:

   ```bash
   chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
     --force-device-scale-factor=2 --window-size=390,1400 --screenshot=/tmp/mobile.png <url>
   ```

   Use `--force-device-scale-factor=2` so the image has real pixel density; use 1280×900 for the
   desktop pass. Serve locally (`python3 -m http.server` on a scratch port) while iterating, then
   repeat against the live URL — and always append `?ts=<epoch>` to a live URL, because Pages will
   happily serve the previous build.

   If you are driving a browser session instead and captures start timing out after
   `Emulation.setDeviceMetricsOverride`, take one capture per fresh session or fall back to the
   headless command above; do not keep retrying a wedged session.

2. **Measure before judging.** Objective checks catch what the eye misses:

   ```js
   ({w: innerWidth, sw: document.documentElement.scrollWidth,
     overflow: [...document.querySelectorAll('*')]
       .filter(e => e.getBoundingClientRect().right > innerWidth + 1).length})
   ```

   `scrollWidth > innerWidth` or a non-zero overflow count is a horizontal-scroll bug. Also check
   `grid-template-columns`, computed font sizes (anything under ~10.5px), and whether the bottom nav
   is `display:none` at the width you think you are testing — the reported `innerWidth` is the truth,
   not the size you asked for.

3. **Ask for defects, not praise.** Prompt the vision model with the audience and the failure modes:
   *"Judge hierarchy, spacing, contrast, chart legibility. Concrete defects only — truncation,
   clipping, overlap, ambiguous numbers. Name the three worst and how to fix them."* Vague prompts
   produce a description of the screenshot; specific prompts produce a bug list.

4. **Fix only what is a defect, then re-render.** The second pass should confirm, not re-litigate the
   design. Two rounds is the budget; a third usually means the composition is wrong, not the details.

## Defect checklist (in the order they actually occur)

- **Truncation at 390pt** — funnel deltas, long job names, table cells. Fix with a narrow-width wrap
  rule, not a smaller font.
- **Clipped SVG** — an arc touching the card edge, a gauge whose endpoints sit on the corner radius.
  Check the `viewBox` against `cy + stroke/2`.
- **Wrong proportionality** — a gauge that looks the same at 5% and 60%, or a donut using the page
  background for one segment (invisible).
- **Redundant hero** — "Attention needed" at 52px over four KPIs. The hero should carry a fact, and
  alarms belong in a list with an action.
- **Duplicated metric** — the same percentage as the headline and inside a card. One is the answer,
  the other is noise.
- **Dead whitespace** — a large gap between rows usually means a wrapper column with no content, or
  a card stretching a grid row. Measure before "fixing" it; the gap may be the screenshot's crop.
- **Contrast** — muted text under ~4.5:1 on a near-black surface; active nav state conveyed by colour
  alone.
- **Table at phone width** — if you can read all six columns in the screenshot, you are not at 390pt.

## What not to "fix"

- Do not shrink type to win an argument with a narrow viewport; reflow it.
- Do not add a mobile menu to a three-item nav; use the bottom bar.
- Do not delete a chart because a critic called it redundant until you have checked whether it
  carries composition data no other panel shows.
