#!/usr/bin/env python3
"""Render the Valhalla Capital equity curve as a self-contained inline SVG.

Reads overseer_portfolio_daily.csv and emits an SVG fragment (no <?xml?>,
no external deps, no JS) sized for a responsive container via viewBox. The
curve plots daily portfolio total_value across the full run, with the live
cutover, the peak, and the shutdown marked. A dashed baseline tracks invested
capital so the eye can read profit/loss against the money actually deployed.

Colors are pulled from the dashboard's distilled palette (see styles.css):
  cyan  #54e5d0  positive / line
  pink  #ff6b9d  loss / shutdown
  amber #f0b866  peak / cutover
  navy  #0c0e1a  ground
The output is written to assets/equity-curve.svg.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CSV_PATH = Path(
    "/home/eve/valhalla-recovery/valhalla-final-20260616-2259/csv/overseer_portfolio_daily.csv"
)
OUT_PATH = Path(__file__).parent / "assets" / "equity-curve.svg"

# -- Canvas geometry (user units; the SVG scales fluidly via viewBox) --------
W, H = 960, 420
PAD_L, PAD_R, PAD_T, PAD_B = 56, 24, 28, 52
PLOT_W = W - PAD_L - PAD_R
PLOT_H = H - PAD_T - PAD_B

# -- Palette (distilled from the dashboard) ----------------------------------
COL_LINE = "#54e5d0"
COL_LINE_DIM = "#2a7a6f"
COL_LOSS = "#ff6b9d"
COL_PEAK = "#f0b866"
COL_BASE = "#6b6f8a"
COL_GRID = "#1f2340"
COL_AXIS = "#3d4060"
COL_TEXT = "#6b6f8a"
COL_FILL_TOP = "rgba(84, 229, 208, 0.18)"
COL_FILL_BOT = "rgba(84, 229, 208, 0.0)"

CUTOVER = date(2026, 5, 1)


@dataclass(frozen=True)
class Point:
    d: date
    value: float
    invested: float


def load_points() -> list[Point]:
    pts: list[Point] = []
    with CSV_PATH.open(newline="") as fh:
        for row in csv.DictReader(fh):
            y, m, dd = (int(x) for x in row["date"].split("-"))
            pts.append(
                Point(
                    d=date(y, m, dd),
                    value=round(float(row["total_value"]), 2),
                    invested=round(float(row["invested_capital"]), 2),
                )
            )
    return sorted(pts, key=lambda p: p.d)


def make_scales(pts: list[Point]):
    d0, d1 = pts[0].d, pts[-1].d
    span_days = (d1 - d0).days or 1
    values = [p.value for p in pts] + [p.invested for p in pts]
    vmin, vmax = min(values), max(values)
    # Pad the value axis to round-ish bounds for clean gridlines.
    lo = (int(vmin) // 50) * 50
    hi = ((int(vmax) // 50) + 1) * 50

    def sx(d: date) -> float:
        return PAD_L + (d - d0).days / span_days * PLOT_W

    def sy(v: float) -> float:
        return PAD_T + (hi - v) / (hi - lo) * PLOT_H

    return sx, sy, lo, hi, d0, d1


def fmt(n: float) -> str:
    """Trim trailing zeros so path coords stay compact."""
    return f"{n:.1f}".rstrip("0").rstrip(".")


def build_svg() -> str:
    pts = load_points()
    sx, sy, lo, hi, d0, d1 = make_scales(pts)

    peak = max(pts, key=lambda p: p.value)
    last = pts[-1]

    # -- Gridlines + Y labels (every $100) ----------------------------------
    grid_parts: list[str] = []
    ylab_parts: list[str] = []
    v = lo
    while v <= hi:
        gy = sy(v)
        grid_parts.append(
            f'<line x1="{PAD_L}" y1="{fmt(gy)}" x2="{W - PAD_R}" y2="{fmt(gy)}" '
            f'stroke="{COL_GRID}" stroke-width="1"/>'
        )
        ylab_parts.append(
            f'<text x="{PAD_L - 10}" y="{fmt(gy + 3.5)}" text-anchor="end" '
            f'class="ec-tick">${int(v)}</text>'
        )
        v += 100

    # -- X labels: first of each month present in the data ------------------
    seen_months: set[tuple[int, int]] = set()
    xlab_parts: list[str] = []
    month_names = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    for p in pts:
        key = (p.d.year, p.d.month)
        if key not in seen_months:
            seen_months.add(key)
            gx = sx(p.d)
            xlab_parts.append(
                f'<text x="{fmt(gx)}" y="{H - PAD_B + 20}" text-anchor="middle" '
                f'class="ec-tick">{month_names[p.d.month]}</text>'
            )

    # -- Invested-capital baseline (stepped, dashed) ------------------------
    base_cmds: list[str] = []
    prev_inv: float | None = None
    for p in pts:
        x, y = sx(p.d), sy(p.invested)
        if prev_inv is None:
            base_cmds.append(f"M{fmt(x)} {fmt(y)}")
        elif p.invested != prev_inv:
            # vertical step up to the new capital level, then continue
            base_cmds.append(f"L{fmt(x)} {fmt(sy(prev_inv))}")
            base_cmds.append(f"L{fmt(x)} {fmt(y)}")
        else:
            base_cmds.append(f"L{fmt(x)} {fmt(y)}")
        prev_inv = p.invested
    base_path = " ".join(base_cmds)

    # -- Equity line + area fill --------------------------------------------
    line_cmds: list[str] = []
    for i, p in enumerate(pts):
        x, y = sx(p.d), sy(p.value)
        line_cmds.append(f"{'M' if i == 0 else 'L'}{fmt(x)} {fmt(y)}")
    line_path = " ".join(line_cmds)

    base_y = sy(lo)
    area_path = (
        f"M{fmt(sx(pts[0].d))} {fmt(base_y)} "
        + " ".join(f"L{fmt(sx(p.d))} {fmt(sy(p.value))}" for p in pts)
        + f" L{fmt(sx(pts[-1].d))} {fmt(base_y)} Z"
    )

    # -- Live-cutover marker (vertical rule) --------------------------------
    cut_x = sx(CUTOVER)
    cutover = (
        f'<line x1="{fmt(cut_x)}" y1="{PAD_T}" x2="{fmt(cut_x)}" y2="{H - PAD_B}" '
        f'stroke="{COL_PEAK}" stroke-width="1" stroke-dasharray="2 4" opacity="0.55"/>'
        f'<text x="{fmt(cut_x + 5)}" y="{PAD_T + 12}" class="ec-note" '
        f'fill="{COL_PEAK}">live cutover</text>'
    )

    # -- Peak marker --------------------------------------------------------
    px, py = sx(peak.d), sy(peak.value)
    peak_marker = (
        f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="4" fill="{COL_PEAK}" '
        f'stroke="#0c0e1a" stroke-width="1.5"/>'
        f'<text x="{fmt(px - 8)}" y="{fmt(py - 9)}" text-anchor="end" '
        f'class="ec-label" fill="{COL_PEAK}">peak ${peak.value:,.2f}</text>'
    )

    # -- Shutdown marker ----------------------------------------------------
    lx, ly = sx(last.d), sy(last.value)
    shutdown_marker = (
        f'<circle cx="{fmt(lx)}" cy="{fmt(ly)}" r="4.5" fill="{COL_LOSS}" '
        f'stroke="#0c0e1a" stroke-width="1.5"/>'
        f'<text x="{fmt(lx)}" y="{fmt(ly + 22)}" text-anchor="end" '
        f'class="ec-label" fill="{COL_LOSS}">86’d · ${last.value:,.2f}</text>'
    )

    title_id = "ec-title"
    desc_id = "ec-desc"
    final_pct = (last.value / last.invested - 1) * 100

    svg = f'''<svg viewBox="0 0 {W} {H}" class="equity-curve" role="img"
     xmlns="http://www.w3.org/2000/svg"
     aria-labelledby="{title_id} {desc_id}"
     preserveAspectRatio="xMidYMid meet">
  <title id="{title_id}">Valhalla Capital equity curve, 19 Feb to 16 June 2026</title>
  <desc id="{desc_id}">Daily portfolio value over the run. It traded quietly around
    a rising invested-capital baseline through April, peaked at ${peak.value:,.2f} on
    1 May at the live-trading cutover, then ground down for six weeks to ${last.value:,.2f}
    ({final_pct:+.2f} percent against invested capital), where the minus ten percent stop
    tripped and the agent was retired.</desc>
  <defs>
    <linearGradient id="ec-area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{COL_FILL_TOP}"/>
      <stop offset="100%" stop-color="{COL_FILL_BOT}"/>
    </linearGradient>
  </defs>
  <style>
    .ec-tick {{ font: 11px "IBM Plex Mono", ui-monospace, monospace; fill: {COL_TEXT}; letter-spacing: 0.02em; }}
    .ec-label {{ font: 600 12px "IBM Plex Mono", ui-monospace, monospace; letter-spacing: 0.03em; }}
    .ec-note {{ font: 10px "IBM Plex Mono", ui-monospace, monospace; letter-spacing: 0.08em; text-transform: uppercase; }}
  </style>

  <!-- gridlines -->
  <g>{''.join(grid_parts)}</g>

  <!-- axes -->
  <line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{H - PAD_B}" stroke="{COL_AXIS}" stroke-width="1"/>
  <line x1="{PAD_L}" y1="{H - PAD_B}" x2="{W - PAD_R}" y2="{H - PAD_B}" stroke="{COL_AXIS}" stroke-width="1"/>

  <!-- area under the curve -->
  <path d="{area_path}" fill="url(#ec-area)" stroke="none"/>

  <!-- invested-capital baseline -->
  <path d="{base_path}" fill="none" stroke="{COL_BASE}" stroke-width="1.25"
        stroke-dasharray="4 4" opacity="0.7"/>
  <text x="{W - PAD_R}" y="{fmt(sy(1000) - 6)}" text-anchor="end" class="ec-note"
        fill="{COL_BASE}">invested capital</text>

  <!-- live cutover -->
  {cutover}

  <!-- equity line -->
  <path d="{line_path}" fill="none" stroke="{COL_LINE}" stroke-width="2"
        stroke-linejoin="round" stroke-linecap="round"/>

  <!-- markers -->
  {peak_marker}
  {shutdown_marker}

  <!-- axis labels -->
  <g>{''.join(ylab_parts)}</g>
  <g>{''.join(xlab_parts)}</g>
</svg>
'''
    return svg


def main() -> None:
    svg = build_svg()
    OUT_PATH.write_text(svg, encoding="utf-8")
    pts = load_points()
    peak = max(pts, key=lambda p: p.value)
    print(f"wrote {OUT_PATH} ({len(svg)} bytes)")
    print(f"  points: {len(pts)}  range: {pts[0].d} .. {pts[-1].d}")
    print(f"  peak:   ${peak.value:,.2f} on {peak.d}")
    print(f"  final:  ${pts[-1].value:,.2f}")


if __name__ == "__main__":
    main()
